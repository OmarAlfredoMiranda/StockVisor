import os
import io
import time
import threading
from typing import List, Dict, Optional

from flask import Flask, request, render_template, send_from_directory, jsonify, Response, url_for
from flask_cors import CORS
from PIL import Image
import cv2
from ultralytics import YOLO

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJ_ROOT = os.path.dirname(APP_DIR)
IMAGES_DIR = os.path.join(PROJ_ROOT, "data", "images")
OUTPUTS_DIR = os.path.join(PROJ_ROOT, "data", "outputs")

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

app = Flask(__name__)
CORS(app)

DEFAULT_MODEL = "yolov8n.pt"
DEFAULT_CONF = 0.25
DEFAULT_IMGSZ = 640

# Lazy-loaded model
_model = None
def get_model():
    global _model
    if _model is None:
        _model = YOLO(DEFAULT_MODEL)
    return _model

@app.route("/")
def home():
    return render_template("index.html", conf=DEFAULT_CONF)

@app.route("/legacy")
def legacy():
    return render_template("legacy_index.html", conf=DEFAULT_CONF)


@app.route("/single", methods=["GET","POST"])
def single():
    conf = float(request.form.get("conf", DEFAULT_CONF)) if request.method == "POST" else DEFAULT_CONF
    imgsz = int(request.form.get("imgsz", DEFAULT_IMGSZ)) if request.method == "POST" else DEFAULT_IMGSZ
    classes_str = (request.form.get("classes") or "").strip()
    out_url = None
    total = 0
    per_class: Dict[str,int] = {}

    if request.method == "POST":
        f = request.files.get("file")
        if not f:
            return render_template("single.html", conf=conf, imgsz=imgsz, classes_str=classes_str,
                                   out_url=None, total=0, per_class={})

        # Save upload
        in_path = os.path.join(IMAGES_DIR, f.filename)
        f.save(in_path)

        model = get_model()
        class_map = model.model.names if hasattr(model, "model") else model.names
        class_filter: Optional[List[int]] = None
        if classes_str:
            wanted = [c.strip() for c in classes_str.split(",") if c.strip()]
            # map to ids
            inv = {v:k for k,v in class_map.items()}
            ids = [inv.get(name) for name in wanted]
            class_filter = [int(i) for i in ids if i is not None]

        res = model.predict(source=in_path, conf=conf, imgsz=imgsz, classes=class_filter, verbose=False)
        r0 = res[0]
        im_annotated = r0.plot()
        # Count
        total = len(r0.boxes)
        for i in range(total):
            cls_id = int(r0.boxes.cls[i].item())
            cls_name = class_map.get(cls_id, str(cls_id))
            per_class[cls_name] = per_class.get(cls_name, 0) + 1

        out_name = f"annotated_{os.path.basename(in_path)}"
        out_path = os.path.join(OUTPUTS_DIR, out_name)
        Image.fromarray(im_annotated[..., ::-1]).save(out_path)
        out_url = url_for("outputs_file", filename=out_name)

    return render_template("single.html", conf=conf, imgsz=imgsz, classes_str=classes_str,
                           out_url=out_url, total=total, per_class=per_class)

@app.route("/outputs/<path:filename>")
def outputs_file(filename):
    return send_from_directory(OUTPUTS_DIR, filename)

############ LiveCam ############

_live_lock = threading.Lock()
_live_on = False
_live_cfg = {"cam":0, "conf":DEFAULT_CONF, "imgsz":DEFAULT_IMGSZ, "classes":""}
_live_frame = None
_live_stats = {"fps":0.0, "total":0, "per_class":{}}

def _parse_classes(model, classes_str: str) -> Optional[List[int]]:
    classes_str = (classes_str or "").strip()
    if not classes_str:
        return None
    class_map = model.model.names if hasattr(model, "model") else model.names
    inv = {v:k for k,v in class_map.items()}
    ids = []
    for name in [c.strip() for c in classes_str.split(",") if c.strip()]:
        idx = inv.get(name)
        if idx is not None:
            ids.append(int(idx))
    return ids or None

def _live_loop():
    global _live_on, _live_frame, _live_stats
    model = get_model()
    # open cam
    cam_id = int(_live_cfg.get("cam",0))
    cap = cv2.VideoCapture(cam_id, cv2.CAP_DSHOW)
    if not cap.isOpened():
        # try default
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    conf = float(_live_cfg.get("conf",DEFAULT_CONF))
    imgsz = int(_live_cfg.get("imgsz",DEFAULT_IMGSZ))
    classes = _parse_classes(model, _live_cfg.get("classes",""))

    last = time.time(); frames=0
    while True:
        with _live_lock:
            if not _live_on: break
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.05)
            continue
        # predict
        res = model.predict(source=frame, conf=conf, imgsz=imgsz, classes=classes, verbose=False)
        r0 = res[0]
        ann = r0.plot()  # BGR
        # update stats
        per_class = {}
        total = len(r0.boxes)
        model_map = model.model.names if hasattr(model, "model") else model.names
        for i in range(total):
            cid = int(r0.boxes.cls[i].item())
            cname = model_map.get(cid, str(cid))
            per_class[cname] = per_class.get(cname, 0) + 1
        frames += 1
        now = time.time()
        if now - last >= 1.0:
            fps = frames / (now - last)
            _live_stats = {"fps": fps, "total": total, "per_class": per_class}
            frames = 0; last = now
        # store frame (JPEG)
        ret, jpeg = cv2.imencode(".jpg", ann)
        if ret:
            _live_frame = jpeg.tobytes()
        else:
            _live_frame = None

    cap.release()

@app.route("/live")
def live():
    # defaults
    return render_template("live.html", cam=_live_cfg.get("cam",0), conf=_live_cfg.get("conf",DEFAULT_CONF),
                           imgsz=_live_cfg.get("imgsz",DEFAULT_IMGSZ), classes_str=_live_cfg.get("classes",""))

@app.route("/live/start", methods=["POST"])
def live_start():
    global _live_on, _live_cfg
    data = request.get_json(force=True)
    with _live_lock:
        _live_cfg = {
            "cam": int(data.get("cam",0)),
            "conf": float(data.get("conf",DEFAULT_CONF)),
            "imgsz": int(data.get("imgsz",DEFAULT_IMGSZ)),
            "classes": data.get("classes","")
        }
        if not _live_on:
            _live_on = True
            th = threading.Thread(target=_live_loop, daemon=True)
            th.start()
    return jsonify({"ok": True, "cfg": _live_cfg})

@app.route("/live/stop", methods=["POST"])
def live_stop():
    global _live_on
    with _live_lock:
        _live_on = False
    return jsonify({"ok": True})

@app.route("/live/stream")
def live_stream():
    def gen():
        # multipart/x-mixed-replace stream
        boundary = b"--frame"
        while True:
            with _live_lock:
                if not _live_on:
                    break
                frame = _live_frame
            if frame is None:
                time.sleep(0.05)
                continue
            yield boundary + b"\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(frame)).encode() + b"\r\n\r\n" + frame + b"\r\n"
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/live/stats")
def live_stats():
    return jsonify(_live_stats)

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
