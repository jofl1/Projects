import time
import cv2
import torch
import numpy as np
from ultralytics import YOLO
import threading
import queue
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, List
import json
import os
from datetime import datetime
from collections import deque, defaultdict

@dataclass
class TrackerConfig:
    """Configuration for the object tracker"""
    model_name: str = "yolov8s.pt"
    conf_thresh: float = 0.50
    iou_thresh: float = 0.50
    frame_skip_rate: int = 2
    max_queue_size: int = 5
    video_size: Tuple[int, int] = (640, 480)
    max_tracks_history: int = 30
    enable_recording: bool = False
    recording_fps: int = 30
    save_detections: bool = False
    
class PerformanceMonitor:
    """Monitor and display performance metrics"""
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.frame_times = deque(maxlen=window_size)
        self.processing_times = deque(maxlen=window_size)
        self.display_fps = 0.0
        self.processing_fps = 0.0
        self.avg_processing_time = 0.0
        
    def update(self, frame_time: float, processing_time: Optional[float] = None):
        self.frame_times.append(frame_time)
        if processing_time is not None:
            self.processing_times.append(processing_time)
        
        # Calculate FPS
        if len(self.frame_times) > 1:
            time_span = self.frame_times[-1] - self.frame_times[0]
            self.display_fps = len(self.frame_times) / time_span if time_span > 0 else 0
        
        if len(self.processing_times) > 0:
            self.avg_processing_time = np.mean(self.processing_times)
            self.processing_fps = 1.0 / self.avg_processing_time if self.avg_processing_time > 0 else 0

class ObjectTracker:
    """Main object tracking class"""
    def __init__(self, config: TrackerConfig):
        self.config = config
        self.device = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Running on: {self.device.upper()}")
        
        # Threading
        self.frame_queue = queue.Queue(maxsize=config.max_queue_size)
        self.stop_event = threading.Event()
        
        # Model
        self.model = None
        self.load_model()
        
        # Tracking data
        self.track_history = defaultdict(lambda: deque(maxlen=config.max_tracks_history))
        self.object_counts = defaultdict(int)
        self.total_detections = 0
        
        # Performance monitoring
        self.perf_monitor = PerformanceMonitor()
        
        # Recording
        self.video_writer = None
        self.detections_log = []
        
        # Display settings
        self.show_tracks = True
        self.show_stats = True
        self.paused = False
        
    def load_model(self):
        """Load YOLO model"""
        print(f"Loading YOLO model: {self.config.model_name}")
        self.model = YOLO(self.config.model_name)
        self.model.to(self.device)
        print("Model loaded.")
    
    def frame_reader_thread(self, cap_source: int, video_backend: int):
        """Thread function to read frames from the webcam"""
        print(f"Attempting to open camera {cap_source} with backend {video_backend}")
        cap = cv2.VideoCapture(cap_source, video_backend)
        
        if not cap.isOpened():
            print(f"Error: Could not open webcam with source {cap_source}")
            self.stop_event.set()
            return
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.video_size[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.video_size[1])
        
        print("Webcam opened successfully. Reading frames...")
        
        while not self.stop_event.is_set():
            if self.paused:
                time.sleep(0.1)
                continue
                
            ok, frame = cap.read()
            if not ok:
                print("Frame grab failed or stream ended.")
                self.stop_event.set()
                break
                
            # Use non-blocking queue operations
            try:
                self.frame_queue.put(frame, timeout=0.001)
            except queue.Full:
                # Drop oldest frame and add new one
                try:
                    self.frame_queue.get_nowait()
                    self.frame_queue.put_nowait(frame)
                except (queue.Empty, queue.Full):
                    pass
        
        cap.release()
        print("Frame reader thread finished.")
    
    def process_frame(self, frame: np.ndarray) -> Optional[object]:
        """Process a single frame with YOLO"""
        try:
            results = self.model.track(
                frame,
                imgsz=640,
                conf=self.config.conf_thresh,
                iou=self.config.iou_thresh,
                device=self.device,
                verbose=False,
                persist=True,
                tracker="bytetrack.yaml"  # More stable tracking
            )[0]
            return results
        except Exception as e:
            print(f"Error during model tracking: {e}")
            return None
    
    def draw_detections(self, frame: np.ndarray, results: object) -> int:
        """Draw bounding boxes and tracks on frame"""
        object_count = 0
        frame_detections = []
        
        if results and results.boxes is not None:
            for box in results.boxes:
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0].cpu())
                cls_id = int(box.cls[0].cpu())
                track_id = int(box.id[0].cpu()) if box.id is not None else -1
                
                object_count += 1
                class_name = self.model.names[cls_id]
                
                # Update statistics
                self.object_counts[class_name] += 1
                self.total_detections += 1
                
                # Store detection
                if self.config.save_detections:
                    frame_detections.append({
                        'track_id': track_id,
                        'class': class_name,
                        'confidence': conf,
                        'bbox': xyxy.tolist()
                    })
                
                # Draw bounding box
                x1, y1, x2, y2 = xyxy
                color = self.get_color_for_track(track_id)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # Draw label
                label = f"ID:{track_id} {class_name} {conf:.2f}" if track_id != -1 else f"{class_name} {conf:.2f}"
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                cv2.rectangle(frame, (x1, y1 - label_size[1] - 4), (x1 + label_size[0], y1), color, -1)
                cv2.putText(frame, label, (x1, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
                # Update track history
                if track_id != -1 and self.show_tracks:
                    center = ((x1 + x2) // 2, (y1 + y2) // 2)
                    self.track_history[track_id].append(center)
                    
                    # Draw track history
                    points = np.array(list(self.track_history[track_id]), dtype=np.int32)
                    if len(points) > 1:
                        cv2.polylines(frame, [points], False, color, 2)
        
        if self.config.save_detections and frame_detections:
            self.detections_log.append({
                'timestamp': datetime.now().isoformat(),
                'detections': frame_detections
            })
        
        return object_count
    
    def draw_stats(self, frame: np.ndarray, object_count: int):
        """Draw statistics overlay"""
        if not self.show_stats:
            return
            
        # Create semi-transparent overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (350, 150), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Draw stats
        y_offset = 30
        stats = [
            f"Objects: {object_count}",
            f"Display FPS: {self.perf_monitor.display_fps:.1f}",
            f"Process FPS: {self.perf_monitor.processing_fps:.1f}",
            f"Avg Process Time: {self.perf_monitor.avg_processing_time*1000:.1f}ms",
            f"Total Detections: {self.total_detections}"
        ]
        
        for stat in stats:
            cv2.putText(frame, stat, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            y_offset += 25
    
    def draw_controls(self, frame: np.ndarray):
        """Draw control instructions"""
        h, w = frame.shape[:2]
        controls = [
            "Q: Quit | P: Pause | T: Toggle Tracks",
            "S: Toggle Stats | R: Record | D: Save Detections"
        ]
        
        y_offset = h - 40
        for control in controls:
            cv2.putText(frame, control, (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 20
    
    def get_color_for_track(self, track_id: int) -> Tuple[int, int, int]:
        """Generate consistent color for track ID"""
        if track_id == -1:
            return (0, 255, 0)
        np.random.seed(track_id)
        return tuple(np.random.randint(0, 255, 3).tolist())
    
    def start_recording(self, frame_shape: Tuple[int, int]):
        """Start video recording"""
        if self.video_writer is not None:
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tracking_{timestamp}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(filename, fourcc, self.config.recording_fps, 
                                          (frame_shape[1], frame_shape[0]))
        print(f"Started recording to {filename}")
    
    def stop_recording(self):
        """Stop video recording"""
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None
            print("Recording stopped")
    
    def save_detections(self):
        """Save detection log to JSON file"""
        if not self.detections_log:
            print("No detections to save")
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"detections_{timestamp}.json"
        
        # Add summary statistics
        summary = {
            'total_detections': self.total_detections,
            'object_counts': dict(self.object_counts),
            'tracking_duration': time.time() - self.start_time,
            'detections': self.detections_log
        }
        
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"Saved detections to {filename}")
    
    def run(self):
        """Main tracking loop"""
        # Try different camera configurations
        camera_configs = [
            (0, cv2.CAP_AVFOUNDATION),
            (0, cv2.CAP_ANY),
            (1, cv2.CAP_ANY)
        ]
        
        thread = None
        for cap_source, cap_backend in camera_configs:
            self.stop_event.clear()
            thread = threading.Thread(target=self.frame_reader_thread, args=(cap_source, cap_backend))
            thread.daemon = True
            thread.start()
            
            time.sleep(2)  # Wait for camera to initialize
            
            if not self.stop_event.is_set() and self.frame_queue.qsize() > 0:
                print(f"Successfully opened camera {cap_source}")
                break
        else:
            print("Failed to open any camera")
            return
        
        self.start_time = time.time()
        frame_count = 0
        latest_results = None
        recording = False
        
        cv2.namedWindow("YOLOv8 Object Tracker", cv2.WINDOW_NORMAL)
        print("Controls: Q=Quit, P=Pause, T=Tracks, S=Stats, R=Record, D=Save Detections")
        
        while not self.stop_event.is_set():
            try:
                display_frame = self.frame_queue.get(timeout=0.1)
                frame_count += 1
            except queue.Empty:
                if self.stop_event.is_set():
                    break
                continue
            
            frame_time = time.time()
            
            # Process frame according to skip rate
            if frame_count % self.config.frame_skip_rate == 0 and not self.paused:
                process_start = time.time()
                latest_results = self.process_frame(display_frame)
                process_time = time.time() - process_start
                self.perf_monitor.update(frame_time, process_time)
            else:
                self.perf_monitor.update(frame_time)
            
            # Draw detections
            object_count = 0
            if latest_results is not None:
                object_count = self.draw_detections(display_frame, latest_results)
            
            # Draw UI elements
            self.draw_stats(display_frame, object_count)
            self.draw_controls(display_frame)
            
            if self.paused:
                cv2.putText(display_frame, "PAUSED", (display_frame.shape[1]//2 - 50, 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            
            # Record frame if enabled
            if recording and self.video_writer is not None:
                self.video_writer.write(display_frame)
            
            # Display frame
            cv2.imshow("YOLOv8 Object Tracker", display_frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("Quitting...")
                self.stop_event.set()
            elif key == ord('p'):
                self.paused = not self.paused
                print(f"{'Paused' if self.paused else 'Resumed'}")
            elif key == ord('t'):
                self.show_tracks = not self.show_tracks
                print(f"Tracks {'enabled' if self.show_tracks else 'disabled'}")
            elif key == ord('s'):
                self.show_stats = not self.show_stats
                print(f"Stats {'enabled' if self.show_stats else 'disabled'}")
            elif key == ord('r'):
                if not recording:
                    self.start_recording(display_frame.shape)
                    recording = True
                else:
                    self.stop_recording()
                    recording = False
            elif key == ord('d'):
                self.save_detections()
        
        # Cleanup
        print("Cleaning up...")
        self.stop_event.set()
        
        if recording:
            self.stop_recording()
        
        if thread and thread.is_alive():
            thread.join(timeout=2)
        
        cv2.destroyAllWindows()
        
        # Save final statistics
        if self.config.save_detections and self.detections_log:
            self.save_detections()
        
        print(f"\nFinal Statistics:")
        print(f"Total Detections: {self.total_detections}")
        print(f"Object Counts: {dict(self.object_counts)}")
        print("Resources released.")

def main():
    # Create configuration
    config = TrackerConfig(
        model_name="yolov8s.pt",
        conf_thresh=0.50,
        iou_thresh=0.50,
        frame_skip_rate=2,
        max_queue_size=5,
        video_size=(640, 480),
        max_tracks_history=30,
        enable_recording=False,
        save_detections=False
    )
    
    # Create and run tracker
    tracker = ObjectTracker(config)
    tracker.run()

if __name__ == "__main__":
    main()