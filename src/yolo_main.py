import cv2
import numpy as np
from tensorflow.keras.models import load_model
from ultralytics import YOLO
import os
import time
import json
from datetime import datetime

# ================= CONFIG =================
CONF_THRESHOLD            = 0.75
DASHBOARD_UPDATE_INTERVAL = 3
EVIDENCE_SAVE_COOLDOWN    = 10
COUNT_COOLDOWN            = 3
MAX_ALERTS                = 50  # increased so history survives restarts

base = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(base)

DATA_FILE       = r"E:\Aditya\smart-Kitchen-Hygiene\dashboard_node\dashboard_data.json"
EVIDENCE_FOLDER = r"E:\Aditya\smart-Kitchen-Hygiene\dashboard_node\static\evidence"
os.makedirs(EVIDENCE_FOLDER, exist_ok=True)
# ================= LOAD MODELS =================
person_model   = load_model(os.path.join(root, "models", "keras_model.h5"))
veg_model      = load_model(os.path.join(root, "models", "Veg.h5"))
platform_model = load_model(os.path.join(root, "models", "kp_model.h5"))

person_labels   = open(os.path.join(root, "models", "person_labels.txt")).read().splitlines()
veg_labels      = open(os.path.join(root, "models", "Veg_labels.txt")).read().splitlines()
platform_labels = open(os.path.join(root, "models", "kp_labels.txt")).read().splitlines()

yolo = YOLO("yolov8n.pt")

# ================= LOAD PREVIOUS STATE FROM JSON =================
def load_previous_state():
    """Load counts and alerts from last session so they don't reset."""
    default_counts = {
        "person_clean": 0, "person_unhygienic": 0,
        "veg_fresh": 0,    "veg_rotten": 0,
        "platform_clean": 0, "platform_unclean": 0,
    }
    if not os.path.exists(DATA_FILE):
        print("[INFO] No previous session found — starting fresh.")
        return default_counts, []

    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        saved_counts = data.get("counts", {})
        saved_alerts = data.get("alerts", [])

        # Fill in any missing keys
        for k, v in default_counts.items():
            if k not in saved_counts:
                saved_counts[k] = v

        total = sum(saved_counts.values())
        print(f"[INFO] Restored previous session — {total} total detections, {len(saved_alerts)} alerts.")
        return saved_counts, saved_alerts

    except (json.JSONDecodeError, IOError) as e:
        print(f"[WARN] Could not load previous state: {e} — starting fresh.")
        return default_counts, []

# Restore counts and alerts from last run
counts, alerts = load_previous_state()

# ================= RUNTIME STATE =================
prev_status = {"person": None, "vegetable": None, "platform": None}
current_status = {"person": "—", "vegetable": "—", "platform": "—"}

last_dashboard_write   = 0
last_evidence_person   = 0
last_evidence_veg      = 0
last_evidence_platform = 0
last_count_person      = 0
last_count_veg         = 0
last_count_platform    = 0

frame_detected = {"person": False, "vegetable": False, "platform": False}


# ================= HELPERS =================
def classify(model, labels, img):
    img = cv2.resize(img, (224, 224))
    img = img / 255.0
    img = np.expand_dims(img, axis=0)
    pred = model.predict(img, verbose=0)
    idx  = np.argmax(pred)
    return labels[idx].lower(), float(pred[0][idx])


def add_alert(msg):
    global alerts
    timestamp = datetime.now().strftime("%H:%M:%S")
    full_msg  = f"{msg} at {timestamp}"
    if not alerts or alerts[-1] != full_msg:
        alerts.append(full_msg)
    alerts = alerts[-MAX_ALERTS:]


def save_evidence(frame, label, module):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"{module}_{label}_{timestamp}.jpg"
    path      = os.path.join(EVIDENCE_FOLDER, filename)
    cv2.imwrite(path, frame)
    print(f"[EVIDENCE] Saved: {filename}")


def write_dashboard():
    """Write current state to JSON — this IS the persistent storage."""
    data = {
        "person":    current_status["person"],
        "vegetable": current_status["vegetable"],
        "platform":  current_status["platform"],
        "counts":    counts,
        "alerts":    alerts,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ================= CAMERA =================
cap       = cv2.VideoCapture(0)
prev_time = 0

print("[INFO] SYSTEM STARTED")
print(f"[INFO] JSON   -> {DATA_FILE}")
print(f"[INFO] Images -> {EVIDENCE_FOLDER}")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    now  = time.time()
    fps  = 1 / (now - prev_time) if prev_time != 0 else 0
    prev_time = now

    frame_detected["person"]    = False
    frame_detected["vegetable"] = False
    frame_detected["platform"]  = False

    results = yolo(frame)

    # ================= PLATFORM =================
    for r in results:
        for box in r.boxes:
            cls_name = yolo.names[int(box.cls[0])]
            if cls_name not in ["dining table", "sink", "bowl", "cup"]:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            if (x2-x1) < 150 or (y2-y1) < 150:
                continue
            roi = frame[y1:y2, x1:x2]
            if roi.size == 0:
                continue
            p_label, p_conf = classify(platform_model, platform_labels, roi)
            if p_conf <= CONF_THRESHOLD:
                continue

            is_unclean = "unclean" in p_label
            status_str = "unclean" if is_unclean else "clean"
            color      = (0, 0, 255) if is_unclean else (0, 255, 0)

            current_status["platform"] = status_str
            frame_detected["platform"] = True

            if prev_status["platform"] != status_str or (now - last_count_platform) > COUNT_COOLDOWN:
                if is_unclean:
                    counts["platform_unclean"] += 1
                    add_alert("Unclean platform detected")
                    if now - last_evidence_platform > EVIDENCE_SAVE_COOLDOWN:
                        save_evidence(frame, "unclean", "platform")
                        last_evidence_platform = now
                else:
                    counts["platform_clean"] += 1
                prev_status["platform"] = status_str
                last_count_platform     = now

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
            cv2.rectangle(frame, (x1, y1-30), (x2, y1), color, -1)
            cv2.putText(frame, f"PLATFORM {status_str.upper()} {p_conf*100:.1f}%",
                        (x1+5, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

    # ================= PERSON + VEG =================
    for r in results:
        for box in r.boxes:
            if box.conf[0] < 0.5:
                continue
            cls_name        = yolo.names[int(box.cls[0])]
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            if (x2-x1) < 100 or (y2-y1) < 100:
                continue
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            if cls_name == "person":
                label, conf = classify(person_model, person_labels, crop)
                if conf <= CONF_THRESHOLD:
                    continue
                is_unhygienic = "unhygienic" in label
                status_str    = "unhygienic" if is_unhygienic else "clean"
                color         = (0, 0, 255) if is_unhygienic else (0, 255, 0)

                current_status["person"] = status_str
                frame_detected["person"] = True

                if prev_status["person"] != status_str or (now - last_count_person) > COUNT_COOLDOWN:
                    if is_unhygienic:
                        counts["person_unhygienic"] += 1
                        add_alert("Unhygienic person detected")
                        if now - last_evidence_person > EVIDENCE_SAVE_COOLDOWN:
                            save_evidence(frame, "unhygienic", "person")
                            last_evidence_person = now
                    else:
                        counts["person_clean"] += 1
                    prev_status["person"] = status_str
                    last_count_person     = now

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                cv2.putText(frame, f"{label.upper()} {conf*100:.1f}%",
                            (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            elif cls_name in ["apple", "banana", "orange"]:
                label, conf = classify(veg_model, veg_labels, crop)
                if conf <= CONF_THRESHOLD:
                    continue
                is_rotten  = "rotten" in label
                status_str = "rotten" if is_rotten else "fresh"
                color      = (0, 0, 255) if is_rotten else (0, 255, 0)

                current_status["vegetable"] = status_str
                frame_detected["vegetable"] = True

                if prev_status["vegetable"] != status_str or (now - last_count_veg) > COUNT_COOLDOWN:
                    if is_rotten:
                        counts["veg_rotten"] += 1
                        add_alert(f"Rotten {cls_name} detected")
                        if now - last_evidence_veg > EVIDENCE_SAVE_COOLDOWN:
                            save_evidence(frame, "rotten", "veg")
                            last_evidence_veg = now
                    else:
                        counts["veg_fresh"] += 1
                    prev_status["vegetable"] = status_str
                    last_count_veg           = now

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                cv2.putText(frame, f"{label.upper()} {conf*100:.1f}%",
                            (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    # Hold last known status if not detected this frame
    if not frame_detected["person"]:
        current_status["person"] = prev_status["person"] if prev_status["person"] else "—"
    if not frame_detected["vegetable"]:
        current_status["vegetable"] = prev_status["vegetable"] if prev_status["vegetable"] else "—"
    if not frame_detected["platform"]:
        current_status["platform"] = prev_status["platform"] if prev_status["platform"] else "—"

    cv2.putText(frame, f"FPS: {int(fps)}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,0), 2)

    if now - last_dashboard_write >= DASHBOARD_UPDATE_INTERVAL:
        write_dashboard()
        last_dashboard_write = now

    cv2.imshow("Smart Kitchen Monitoring System", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Final save on exit
write_dashboard()
print("[INFO] Session saved to dashboard_data.json. Exiting.")

cap.release()
cv2.destroyAllWindows()