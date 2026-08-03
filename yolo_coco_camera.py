#!/usr/bin/env python3
"""
YOLO COCO live camera demo.

Uses a pretrained COCO YOLO model. No custom training data is required.
Press Q or close the window to stop.
"""

from __future__ import annotations

import argparse
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import cv2
from PIL import Image, ImageTk


COCO_NAMES_ZH = {
    "person": "人",
    "bicycle": "腳踏車",
    "car": "汽車",
    "motorcycle": "機車",
    "airplane": "飛機",
    "bus": "公車",
    "train": "火車",
    "truck": "卡車",
    "boat": "船",
    "traffic light": "紅綠燈",
    "fire hydrant": "消防栓",
    "stop sign": "停止標誌",
    "parking meter": "停車收費器",
    "bench": "長椅",
    "bird": "鳥",
    "cat": "貓",
    "dog": "狗",
    "horse": "馬",
    "sheep": "羊",
    "cow": "牛",
    "elephant": "大象",
    "bear": "熊",
    "zebra": "斑馬",
    "giraffe": "長頸鹿",
    "backpack": "背包",
    "umbrella": "雨傘",
    "handbag": "手提包",
    "tie": "領帶",
    "suitcase": "行李箱",
    "frisbee": "飛盤",
    "skis": "滑雪板",
    "snowboard": "單板滑雪板",
    "sports ball": "球",
    "kite": "風箏",
    "baseball bat": "球棒",
    "baseball glove": "棒球手套",
    "skateboard": "滑板",
    "surfboard": "衝浪板",
    "tennis racket": "網球拍",
    "bottle": "瓶子",
    "wine glass": "酒杯",
    "cup": "杯子",
    "fork": "叉子",
    "knife": "刀子",
    "spoon": "湯匙",
    "bowl": "碗",
    "banana": "香蕉",
    "apple": "蘋果",
    "sandwich": "三明治",
    "orange": "橘子",
    "broccoli": "花椰菜",
    "carrot": "胡蘿蔔",
    "hot dog": "熱狗",
    "pizza": "披薩",
    "donut": "甜甜圈",
    "cake": "蛋糕",
    "chair": "椅子",
    "couch": "沙發",
    "potted plant": "盆栽",
    "bed": "床",
    "dining table": "餐桌",
    "toilet": "馬桶",
    "tv": "電視",
    "laptop": "筆電",
    "mouse": "滑鼠",
    "remote": "遙控器",
    "keyboard": "鍵盤",
    "cell phone": "手機",
    "microwave": "微波爐",
    "oven": "烤箱",
    "toaster": "烤麵包機",
    "sink": "水槽",
    "refrigerator": "冰箱",
    "book": "書",
    "clock": "時鐘",
    "vase": "花瓶",
    "scissors": "剪刀",
    "teddy bear": "泰迪熊",
    "hair drier": "吹風機",
    "toothbrush": "牙刷",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run pretrained YOLO COCO detection on a camera.")
    parser.add_argument("--camera", type=int, default=0, help="Camera index, usually 0, 1, or 2.")
    parser.add_argument("--model", default="yolo11n.pt", help="COCO model path/name, e.g. yolo11n.pt or yolov8n.pt.")
    parser.add_argument("--conf", type=float, default=0.35, help="Confidence threshold.")
    parser.add_argument("--width", type=int, default=640, help="Camera width.")
    parser.add_argument("--height", type=int, default=480, help="Camera height.")
    parser.add_argument("--interval", type=int, default=2, help="Run YOLO every N frames.")
    parser.add_argument("--zh-labels", action="store_true", help="Show Chinese labels in the side list.")
    return parser.parse_args()


def require_ultralytics():
    try:
        from ultralytics import YOLO
    except Exception as exc:
        print("ERROR: ultralytics is not installed.")
        print("Run:")
        print(r"  powershell -ExecutionPolicy Bypass -File .\setup_yolo_coco.ps1")
        raise SystemExit(1) from exc

    return YOLO


class YoloCocoApp:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.root = tk.Tk()
        self.root.title("YOLO COCO Camera")
        self.root.geometry("980x620")
        self.root.configure(bg="#f5f7fb")
        self.root.protocol("WM_DELETE_WINDOW", self.stop)
        self.root.bind("q", lambda _event: self.stop())
        self.root.bind("Q", lambda _event: self.stop())

        self.running = True
        self.frame_count = 0
        self.last_annotated = None
        self.last_labels: list[str] = []
        self.last_time = time.perf_counter()
        self.fps_value = 0.0

        YOLO = require_ultralytics()
        self.model = YOLO(args.model)

        self.cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera index {args.camera}")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

        self.video_label = tk.Label(self.root, bg="#111827")
        self.video_label.place(x=20, y=20, width=700, height=525)

        title = tk.Label(
            self.root,
            text="COCO pretrained YOLO",
            font=("Segoe UI", 16, "bold"),
            bg="#f5f7fb",
            fg="#111827",
        )
        title.place(x=745, y=24)

        self.status = tk.StringVar(value="Starting camera...")
        status_label = tk.Label(self.root, textvariable=self.status, bg="#f5f7fb", fg="#4b5563", anchor="w")
        status_label.place(x=748, y=62, width=210, height=24)

        self.list_box = tk.Listbox(self.root, font=("Segoe UI", 10), activestyle="none")
        self.list_box.place(x=745, y=105, width=205, height=390)

        hint = tk.Label(
            self.root,
            text="Q: stop\nNo custom training.\nCOCO detects common objects.",
            justify="left",
            bg="#f5f7fb",
            fg="#4b5563",
        )
        hint.place(x=748, y=510)

    def format_label(self, class_name: str, conf: float) -> str:
        if self.args.zh_labels:
            label = COCO_NAMES_ZH.get(class_name, class_name)
            return f"{label} ({class_name}) {conf:.2f}"
        return f"{class_name} {conf:.2f}"

    def detect(self, frame):
        results = self.model.predict(frame, conf=self.args.conf, verbose=False)
        result = results[0]
        annotated = result.plot()

        labels = []
        if result.boxes is not None:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                class_name = self.model.names.get(cls_id, str(cls_id))
                labels.append(self.format_label(class_name, conf))

        return annotated, labels

    def update(self) -> None:
        if not self.running:
            return

        ok, frame = self.cap.read()
        if not ok:
            self.status.set("Camera read failed")
            self.root.after(200, self.update)
            return

        self.frame_count += 1
        if self.last_annotated is None or self.frame_count % max(1, self.args.interval) == 0:
            self.last_annotated, self.last_labels = self.detect(frame)

        display = self.last_annotated if self.last_annotated is not None else frame
        display = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(display)
        image.thumbnail((700, 525), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(image=image)
        self.video_label.configure(image=self.photo)

        now = time.perf_counter()
        dt = now - self.last_time
        self.last_time = now
        if dt > 0:
            self.fps_value = 0.9 * self.fps_value + 0.1 * (1.0 / dt)
        self.status.set(f"Camera {self.args.camera} | {self.fps_value:.1f} FPS")

        self.list_box.delete(0, tk.END)
        if self.last_labels:
            for label in self.last_labels[:20]:
                self.list_box.insert(tk.END, label)
        else:
            self.list_box.insert(tk.END, "No object detected")

        self.root.after(1, self.update)

    def stop(self) -> None:
        self.running = False
        try:
            self.cap.release()
        finally:
            self.root.destroy()

    def run(self) -> None:
        self.root.after(50, self.update)
        self.root.mainloop()


def main() -> int:
    args = parse_args()
    try:
        YoloCocoApp(args).run()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
