import cv2
import numpy as np
from tensorflow.keras.models import load_model
from ultralytics import YOLO
from twilio.rest import Client
import os
import time
from dotenv import load_dotenv
load_dotenv()

# ---------------- CONFIG ----------------
camera_index = 0
model_path = r"E:\Aditya\smart-Kitchen-Hygiene\models\Veg_model.h5"
labels_path = r"E:\Aditya\smart-Kitchen-Hygiene\models\Veg_labels.txt"
img_size = (224, 224)

CONFIDENCE_THRESHOLD = 0.80

# Twilio
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = '+12722964086'
my_phone = '+919082346806'

# Evidence
evidence_dir = "evidence_veg"
os.makedirs(evidence_dir, exist_ok=True)

SAVE_INTERVAL = 5
last_saved_time = 0

# -----------------------------------------

# Load models
model = load_model(model_path)
with open(labels_path, "r") as f:
    labels = [line.strip() for line in f.readlines()]

yolo = YOLO("yolov8n.pt")

client = Client(account_sid, auth_token)

# Camera
cap = cv2.VideoCapture(camera_index)

alert_sent = {"potato": False, "tomato": False}

prev_time = 0

# Save function
def save_evidence(frame, label):
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{label}_{timestamp}.jpg"
    path = os.path.join(evidence_dir, filename)
    cv2.imwrite(path, frame)
    print(f"[INFO] Saved: {path}")

# ---------------- MAIN LOOP ----------------
while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)

    # FPS
    current_time = time.time()
    fps = 1 / (current_time - prev_time) if prev_time != 0 else 0
    prev_time = current_time

    results = yolo(frame)

    for r in results:
        for box in r.boxes:

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            # Classifier
            resized = cv2.resize(crop, img_size)
            normalized = (resized.astype(np.float32) / 127.5) - 1
            input_data = np.expand_dims(normalized, axis=0)

            prediction = model.predict(input_data, verbose=0)
            class_index = np.argmax(prediction)
            confidence = prediction[0][class_index]
            label = labels[class_index].lower()

            if confidence > CONFIDENCE_THRESHOLD and "background" not in label:

                text = f"{label.upper()} {confidence*100:.1f}%"

                # Rotten
                if "rotten" in label:
                    color = (0, 0, 255)

                    if "potato" in label:
                        veg = "potato"
                    elif "tomato" in label:
                        veg = "tomato"
                    else:
                        veg = "unknown"

                    # SMS
                    if veg in alert_sent and not alert_sent[veg]:
                        try:
                            message = client.messages.create(
                                body=f"⚠️ Replace {veg.capitalize()}! It is Rotten.",
                                from_=twilio_number,
                                to=my_phone
                            )
                            print(f"SMS sent for {veg}")
                            alert_sent[veg] = True
                        except Exception as e:
                            print(e)

                    # Save image
                    if current_time - last_saved_time > SAVE_INTERVAL:
                        save_evidence(frame, "rotten")
                        last_saved_time = current_time

                # Fresh
                elif "fresh" in label:
                    color = (0, 255, 0)

                    if "potato" in label:
                        alert_sent["potato"] = False
                    elif "tomato" in label:
                        alert_sent["tomato"] = False

                else:
                    color = (255, 255, 0)

                # Draw box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)

                cv2.rectangle(frame, (x1, y1-30), (x2, y1), color, -1)

                cv2.putText(frame, text,
                            (x1+5, y1-8),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (255,255,255),
                            2)

    # FPS display
    cv2.putText(frame, f"FPS: {int(fps)}",
                (20,40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255,255,0),
                2)

    cv2.imshow("Vegetable Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()