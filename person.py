import time
import cv2
import torch
from ultralytics import YOLO
import threading
import queue

MODEL_NAME = "yolov8s.pt"  
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Running on: {DEVICE.upper()}")

CONF_THRESH = 0.50  
IOU_THRESH = 0.50   
FRAME_SKIP_RATE = 2 
MAX_QUEUE_SIZE = 5  

frame_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
stop_event = threading.Event()
latest_results = None 
latest_processed_frame_for_results = None 

def frame_reader_thread(cap_source, video_backend):
    """Thread function to read frames from the webcam."""
    global frame_queue, stop_event
    print(f"Attempting to open camera {cap_source} with backend {video_backend}")
    cap = cv2.VideoCapture(cap_source, video_backend)
    if not cap.isOpened():
        print(f"Error: Could not open webcam with source {cap_source} and backend {video_backend}.")
        stop_event.set() 
        return

    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) 
    print("Webcam opened successfully. Reading frames...")

    while not stop_event.is_set():
        ok, frame = cap.read()
        if not ok:
            print("Frame grab failed or stream ended.")
            stop_event.set() 
            break
        try:
            frame_queue.put(frame, timeout=0.1)  
        except queue.Full:
            try:
                frame_queue.get_nowait()
                frame_queue.put_nowait(frame)
            except queue.Empty: 
                pass
            except queue.Full: 
                pass
        except Exception as e:
            print(f"Error putting frame into queue: {e}")
            stop_event.set()
            break
    
    cap.release()
    print("Frame reader thread finished and webcam released.")

def main():
    global latest_results, latest_processed_frame_for_results, stop_event

    print(f"Loading YOLO model: {MODEL_NAME}")
    model = YOLO(MODEL_NAME)
    model.to(DEVICE)
    print("Model loaded.")

    camera_indices = [0, 1, -1] 
    backends = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY] 

    thread = None
    camera_opened_successfully = False
    
    print("Starting frame reader thread")
    CAP_SOURCE_TO_TRY = 0
    CAP_BACKEND_TO_TRY = cv2.CAP_AVFOUNDATION 

    thread = threading.Thread(target=frame_reader_thread, args=(CAP_SOURCE_TO_TRY, CAP_BACKEND_TO_TRY))
    thread.daemon = True 
    thread.start()

    time.sleep(2) 

    if stop_event.is_set() and not frame_queue.qsize() > 0 : 
        print("Failed to start frame reader thread or open camera. Exiting.")
        if thread.is_alive():
            thread.join()
        return

    start_time = time.time()
    processed_frame_count = 0 
    displayed_frame_count = 0 

    print("Press Q to quit")

    current_frame_for_processing = None

    while not stop_event.is_set():
        try:
            display_frame = frame_queue.get(timeout=0.1) 
            displayed_frame_count += 1
        except queue.Empty:
            if stop_event.is_set(): 
                break
            continue 

        if displayed_frame_count % FRAME_SKIP_RATE == 0:
            processed_frame_count += 1
            current_frame_for_processing = display_frame.copy() 

            try:
                results = model.track(
                    current_frame_for_processing,
                    imgsz=640,
                    conf=CONF_THRESH,
                    iou=IOU_THRESH,
                    device=DEVICE,
                    verbose=False,
                    persist=True 
                )[0]
                latest_results = results
                latest_processed_frame_for_results = current_frame_for_processing
            except Exception as e:
                print(f"Error during model tracking: {e}")
                latest_results = None 
        
        object_count_current_frame = 0
        if latest_results and latest_results.boxes is not None:
            
            target_frame_for_drawing = display_frame 

            for box in latest_results.boxes:
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0].cpu())
                cls_id = int(box.cls[0].cpu())
                track_id = int(box.id[0].cpu()) if box.id is not None else None 

                object_count_current_frame += 1 

                class_name = model.names[cls_id] 
                
                label = f"ID:{track_id} {class_name} {conf:.2f}" if track_id is not None else f"{class_name} {conf:.2f}"

                x1, y1, x2, y2 = xyxy
                cv2.rectangle(target_frame_for_drawing, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(target_frame_for_drawing, label, (x1, y1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.putText(display_frame, f"Objects: {object_count_current_frame}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        if displayed_frame_count > 0 and (displayed_frame_count % 30 == 0 or processed_frame_count % 10 == 0) : 
            current_time = time.time()
            display_fps = displayed_frame_count / (current_time - start_time)
            processing_fps = processed_frame_count / (current_time - start_time) if processed_frame_count > 0 else 0
            
            title = f"YOLOv8s | Disp FPS: {display_fps:.1f} | Proc FPS: {processing_fps:.1f}"
            cv2.setWindowTitle("YOLOv8 Object Tracker", title)


        cv2.imshow("YOLOv8 Object Tracker", display_frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("Q pressed, exiting...")
            stop_event.set()
            break

    print("Exiting main loop. Cleaning up...")
    stop_event.set() 
    if thread and thread.is_alive():
        print("Waiting for frame reader thread to join...")
        thread.join(timeout=2) 
        if thread.is_alive():
            print("Frame reader thread did not join in time.")
    
    while not frame_queue.empty():
        try:
            frame_queue.get_nowait()
        except queue.Empty:
            break
            
    cv2.destroyAllWindows()
    print("Resources released.")

if __name__ == "__main__":
    main()
