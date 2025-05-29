import cv2
import sys
import time
import torch
from ultralytics import YOLO
from datetime import datetime
import numpy as np

# Initialize YOLO model
MODEL_NAME = "yolov8n.pt"  # Using nano model for faster processing
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Running on: {DEVICE.upper()}")

# Load YOLO model
print(f"Loading YOLO model: {MODEL_NAME}")
model = YOLO(MODEL_NAME)
model.to(DEVICE)
print("Model loaded.")

# Configuration
CONF_THRESH = 0.50  # Confidence threshold
IOU_THRESH = 0.50   # IOU threshold for NMS
PERSON_CLASS_ID = 0  # COCO dataset person class ID

# Tracking variables
tracked_persons = {}  # Dictionary to store tracked person IDs
new_person_cooldown = {}  # Cooldown for re-alerting about the same person
COOLDOWN_TIME = 10  # Seconds before alerting about the same person again
ALERT_DISTANCE_THRESHOLD = 100  # Pixel distance to consider same person

# Alert function
def alert_new_person(person_id, frame_time):
    timestamp = datetime.fromtimestamp(frame_time).strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n🚨 ALERT: New person detected! ID: {person_id} at {timestamp}\n")
    # You can add more alert methods here (sound, email, etc.)
    cv2.putText(frame, f"NEW PERSON ALERT!", (10, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

# Helper function to calculate center of bounding box
def get_box_center(xyxy):
    x1, y1, x2, y2 = xyxy
    return ((x1 + x2) / 2, (y1 + y2) / 2)

# Helper function to calculate distance between two points
def calculate_distance(p1, p2):
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

# Open camera
print("\n📷 Attempting to open camera...")
print("Note: On macOS, you may need to grant camera permissions to Terminal/Python")
print("Check System Preferences > Security & Privacy > Camera\n")

cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
if not cap.isOpened():
    print("❌ Could not open camera with AVFoundation backend.")
    print("Trying alternative camera index...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("\n❌ Camera access failed. Possible reasons:")
        print("1. Camera permissions not granted (check System Preferences > Security & Privacy > Camera)")
        print("2. Camera is being used by another application")
        print("3. No camera available")
        print("\nTo grant camera access on macOS:")
        print("1. Open System Preferences")
        print("2. Go to Security & Privacy > Privacy > Camera")
        print("3. Enable access for Terminal (or your Python IDE)")
        print("4. You may need to restart Terminal/IDE after granting permission")
        sys.exit(1)

print("✅  Camera opened. Press Q to quit.")
print("👁️  Person detection active. Alerts will show for new people.")

frame_count = 0
start_time = time.time()

while True:
    ok, frame = cap.read()
    if not ok:
        sys.exit("❌  Frame grab failed – camera vanished?")
    
    frame_count += 1
    current_time = time.time()
    
    # Process every 3rd frame for performance
    if frame_count % 3 == 0:
        # Run YOLO detection with tracking
        results = model.track(
            frame,
            imgsz=640,
            conf=CONF_THRESH,
            iou=IOU_THRESH,
            device=DEVICE,
            verbose=False,
            persist=True,
            classes=[PERSON_CLASS_ID]  # Only detect persons
        )[0]
        
        current_person_ids = set()
        
        if results.boxes is not None:
            for box in results.boxes:
                # Get box coordinates and info
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0].cpu())
                track_id = int(box.id[0].cpu()) if box.id is not None else None
                
                if track_id is not None:
                    current_person_ids.add(track_id)
                    
                    # Check if this is a new person
                    if track_id not in tracked_persons:
                        # Check if we should alert (not in cooldown)
                        should_alert = True
                        box_center = get_box_center(xyxy)
                        
                        # Check against recent alerts to avoid duplicate alerts for same person
                        for cooled_id, (cooled_time, cooled_pos) in list(new_person_cooldown.items()):
                            if current_time - cooled_time > COOLDOWN_TIME:
                                del new_person_cooldown[cooled_id]
                            elif calculate_distance(box_center, cooled_pos) < ALERT_DISTANCE_THRESHOLD:
                                should_alert = False
                                break
                        
                        if should_alert:
                            alert_new_person(track_id, current_time)
                            new_person_cooldown[track_id] = (current_time, box_center)
                        
                        tracked_persons[track_id] = current_time
                    else:
                        # Update last seen time
                        tracked_persons[track_id] = current_time
                    
                    # Draw bounding box and label
                    x1, y1, x2, y2 = xyxy
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    label = f"Person {track_id} ({conf:.2f})"
                    cv2.putText(frame, label, (x1, y1 - 8),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Remove persons not seen for 5 seconds
        for person_id in list(tracked_persons.keys()):
            if person_id not in current_person_ids and current_time - tracked_persons[person_id] > 5:
                del tracked_persons[person_id]
    
    # Display stats
    fps = frame_count / (current_time - start_time)
    cv2.putText(frame, f"FPS: {fps:.1f} | Persons: {len(tracked_persons)}", 
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Show frame
    cv2.imshow("Person Detection & Alert System", frame)
    
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
print("\n✅ Camera released and windows closed.")
