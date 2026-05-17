import cv2
import numpy as np
from tensorflow.keras.models import load_model
from ultralytics import YOLO
from twilio.rest import Client
import os
import time
from dotenv import load_dotenv
load_dotenv()

def main():

    # ================= PATH SETUP =================
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    model_path = os.path.join(project_root, "models", "keras_model.h5")
    labels_path = os.path.join(project_root, "models", "person_labels.txt")

    evidence_dir = os.path.join(project_root, "evidence")
    os.makedirs(evidence_dir, exist_ok=True)

    CONFIDENCE_THRESHOLD = 0.75

    COLOR_POSITIVE = (0, 255, 0)
    COLOR_NEGATIVE = (0, 0, 255)

    SAVE_INTERVAL = 5  # seconds
    last_saved_time = 0

    # ================= TWILIO CONFIG =================
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_number = '+12722964086'
    my_phone = '+919082346806'

    client = Client(account_sid, auth_token)
    sms_sent = False

    # ================= LOAD MODELS =================
    print("[INFO] Loading hygiene model...")
    hygiene_model = load_model(model_path, compile=False)

    with open(labels_path, "r") as f:
        labels = [line.strip() for line in f.readlines()]

    print("[INFO] Loading YOLO model...")
    yolo_model = YOLO("yolov8n.pt")

    print("[INFO] Models loaded successfully.")

    # ================= START CAMERA =================
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("[ERROR] Camera not accessible.")
        return

    print("[INFO] Webcam started. Press 'q' to quit.")

    # ================= FPS SETUP =================
    prev_time = 0

    # ================= SAVE FUNCTION =================
    def save_evidence(frame, label):
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{label}_{timestamp}.jpg"
        filepath = os.path.join(evidence_dir, filename)
        cv2.imwrite(filepath, frame)
        print(f"[INFO] Evidence saved: {filepath}")

    # ================= MAIN LOOP =================
    while True:

        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)

        # FPS calculation
        current_time = time.time()
        fps = 1 / (current_time - prev_time) if prev_time != 0 else 0
        prev_time = current_time

        results = yolo_model(frame)

        for r in results:
            boxes = r.boxes

            for box in boxes:

                cls = int(box.cls[0])

                # Only detect PERSON
                if cls != 0:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])

                person_crop = frame[y1:y2, x1:x2]

                if person_crop.size == 0:
                    continue

                # ================= CLASSIFIER =================
                resized = cv2.resize(person_crop, (224, 224))
                normalized = (resized.astype(np.float32) / 127.5) - 1
                input_data = np.expand_dims(normalized, axis=0)

                prediction = hygiene_model.predict(input_data, verbose=0)
                index = np.argmax(prediction)
                class_name = labels[index]
                confidence = prediction[0][index]

                if confidence >= CONFIDENCE_THRESHOLD:

                    label = class_name.split(" ", 1)[-1].strip().lower()
                    display_text = label.upper()

                    if "unhygienic" in label:

                        color = COLOR_NEGATIVE

                        # -------- SMS --------
                        if not sms_sent:
                            try:
                                message = client.messages.create(
                                    body="⚠️ Alert: Unhygienic person detected!",
                                    from_=twilio_number,
                                    to=my_phone
                                )
                                print(f"[ALERT] SMS sent! SID: {message.sid}")
                                sms_sent = True
                            except Exception as e:
                                print(f"[ERROR] SMS failed: {e}")

                        # -------- SAVE IMAGE --------
                        if current_time - last_saved_time > SAVE_INTERVAL:
                            save_evidence(frame, "unhygienic")
                            last_saved_time = current_time

                    else:
                        color = COLOR_POSITIVE
                        sms_sent = False

                    # ================= DRAW =================
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)

                    cv2.rectangle(frame, (x1, y1-35), (x2, y1), color, -1)

                    cv2.putText(frame,
                                f"{display_text} {confidence*100:.1f}%",
                                (x1 + 5, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.7,
                                (255,255,255),
                                2)

        # ================= FPS DISPLAY =================
        cv2.putText(frame,
                    f"FPS: {int(fps)}",
                    (20,40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (255,255,0),
                    2)

        cv2.imshow("Smart Kitchen Hygiene Monitor", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # ================= CLEANUP =================
    print("[INFO] Closing application...")
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()