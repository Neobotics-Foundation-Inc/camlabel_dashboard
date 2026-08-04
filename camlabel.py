#!/usr/bin/env python3
"""Neoracer camera label dashboard: capture frames, box-label, save YOLO data.

Same pattern as wallfollow.py (stdlib HTTP + rclpy) on port 8082. Frames come
from /camera (the driver publishes JPEG bytes inside an Image message).
Save writes dataset/images/imgN.jpg plus dataset/labels/imgN.txt in YOLO
format (class_id cx cy w h, all normalized 0..1) and keeps classes.txt in
sync, so the dataset trains directly. Saved images can be reviewed with
their boxes, and training parameters save to dataset/train_params.txt.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import threading

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

PORT = 8082
BASE = Path(__file__).resolve().parent
DATASET = BASE / 'dataset'
IMAGES = DATASET / 'images'
LABELS = DATASET / 'labels'

_lock = threading.Lock()
_live = b''
_preview = b''
_pending = b''


class CameraNode(Node):
    def __init__(self):
        super().__init__('camlabel')
        self.create_subscription(Image, '/camera', self._cb, qos_profile_sensor_data)

    def _cb(self, msg):
        global _live, _preview
        import cv2
        import numpy as np
        if msg.encoding == 'jpeg':
            data = bytes(msg.data)
            arr = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        else:
            # Raw frame fallback for other camera drivers.
            arr = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, -1)
            if msg.encoding == 'rgb8':
                arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            data = cv2.imencode('.jpg', arr)[1].tobytes()
        # The live view streams a small low-quality preview (about 10 KB vs
        # 70 KB) so many cars and laptops fit in the shared WiFi airtime.
        # Capture and the saved dataset keep the full-resolution frame.
        prev = data
        if arr is not None:
            small = cv2.resize(arr, (320, 240))
            prev = cv2.imencode('.jpg', small, [cv2.IMWRITE_JPEG_QUALITY, 45])[1].tobytes()
        with _lock:
            _live = data
            _preview = prev


def _img_number(name):
    """img7.jpg -> 7, so numbering counts up."""
    m = re.match(r'img(\d+)\.jpg$', name)
    return int(m.group(1)) if m else 0


def _class_id(name):
    """Index of name in classes.txt, appending it if new."""
    path = DATASET / 'classes.txt'
    classes = path.read_text().splitlines() if path.exists() else []
    if name not in classes:
        classes.append(name)
        path.write_text('\n'.join(classes) + '\n')
    return classes.index(name)


class Handler(BaseHTTPRequestHandler):
    # Keep-alive: reuse one TCP connection per viewer instead of a new
    # handshake per frame. Matters a lot on congested WiFi.
    protocol_version = 'HTTP/1.1'
    def do_GET(self):
        if self.path == '/':
            self._send((BASE / 'camlabel.html').read_bytes(), 'text/html; charset=utf-8')
        elif self.path.startswith('/frame'):
            with _lock:
                data = _preview
            if data:
                self._send(data, 'image/jpeg')
            else:
                self.send_error(503)
        elif self.path.startswith('/pending'):
            with _lock:
                data = _pending
            if data:
                self._send(data, 'image/jpeg')
            else:
                self.send_error(404)
        elif self.path == '/count':
            n = len(list(IMAGES.glob('img*.jpg'))) if IMAGES.exists() else 0
            self._send(json.dumps({'count': n}).encode(), 'application/json')
        elif self.path == '/images':
            nums = sorted(_img_number(f.name) for f in IMAGES.glob('img*.jpg')) \
                if IMAGES.exists() else []
            self._send(json.dumps(nums).encode(), 'application/json')
        elif self.path.startswith('/img?n='):
            f = IMAGES / f'img{int(self.path.split("=")[1])}.jpg'
            if f.is_file():
                self._send(f.read_bytes(), 'image/jpeg')
            else:
                self.send_error(404)
        elif self.path.startswith('/label?n='):
            f = LABELS / f'img{int(self.path.split("=")[1])}.txt'
            path = DATASET / 'classes.txt'
            classes = path.read_text().splitlines() if path.exists() else []
            boxes = []
            if f.is_file():
                for line in f.read_text().splitlines():
                    i, cx, cy, w, h = line.split()
                    name = classes[int(i)] if int(i) < len(classes) else i
                    boxes.append({'cls': name, 'cx': float(cx), 'cy': float(cy),
                                  'w': float(w), 'h': float(h)})
            self._send(json.dumps({'boxes': boxes}).encode(), 'application/json')
        else:
            self.send_error(404)

    def do_POST(self):
        global _pending
        if self.path == '/capture':
            with _lock:
                _pending = _live
            self._send(b'ok', 'text/plain')
        elif self.path == '/discard':
            with _lock:
                _pending = b''
            self._send(b'ok', 'text/plain')
        elif self.path == '/train_params':
            params = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            DATASET.mkdir(parents=True, exist_ok=True)
            lines = [f'{k}: {v}' for k, v in params.items()]
            (DATASET / 'train_params.txt').write_text('\n'.join(lines) + '\n')
            self._send(b'ok', 'text/plain')
        elif self.path == '/save':
            boxes = json.loads(self.rfile.read(int(self.headers['Content-Length'])))['boxes']
            with _lock:
                data = _pending
                _pending = b''
            if not data:
                self.send_error(409)
                return
            IMAGES.mkdir(parents=True, exist_ok=True)
            LABELS.mkdir(parents=True, exist_ok=True)
            n = max((_img_number(f.name) for f in IMAGES.glob('img*.jpg')), default=0) + 1
            (IMAGES / f'img{n}.jpg').write_bytes(data)
            lines = [f'{_class_id(b["cls"])} {b["cx"]:.6f} {b["cy"]:.6f} {b["w"]:.6f} {b["h"]:.6f}'
                     for b in boxes]
            (LABELS / f'img{n}.txt').write_text('\n'.join(lines) + '\n' if lines else '')
            self._send(json.dumps({'saved': f'img{n}.jpg', 'count': n}).encode(),
                       'application/json')
        else:
            self.send_error(404)

    def _send(self, body, ctype):
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


def main():
    rclpy.init()
    node = CameraNode()
    threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()
    print(f'Camera label dashboard on http://0.0.0.0:{PORT}')
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()


if __name__ == '__main__':
    main()
