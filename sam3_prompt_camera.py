#!/usr/bin/env python3
"""
SAM3 prompt camera demo.

Uses SAM3 text prompts to segment objects from a live camera.
No custom training data is required.
"""

from __future__ import annotations

import argparse
import os
import tempfile
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import ttk

import cv2
import numpy as np
from PIL import Image, ImageTk


@dataclass
class Detection:
    label: str
    confidence: float | None
    bbox_xyxy: list[float]
    center_px: list[float]
    area_px: float
    mask: np.ndarray


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SAM3 prompt segmentation on a camera.")
    parser.add_argument("--camera", type=int, default=0, help="Camera index, usually 0, 1, or 2.")
    parser.add_argument("--prompt", default="cup", help="Text prompt, comma-separated prompts allowed.")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold.")
    parser.add_argument("--model", default=None, help="Path to sam3.pt. Defaults to models/sam3.pt.")
    parser.add_argument("--width", type=int, default=640, help="Camera width.")
    parser.add_argument("--height", type=int, default=480, help="Camera height.")
    parser.add_argument("--fps", type=int, default=15, help="Camera FPS.")
    parser.add_argument("--every", type=float, default=0.8, help="Seconds between SAM3 inference calls.")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto", help="Inference device.")
    return parser.parse_args()


def resolve_model(explicit: str | None) -> Path:
    repo_root = Path(__file__).resolve().parent
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    candidates.extend(
        [
            repo_root / "models" / "sam3.pt",
            Path.home() / "Desktop" / "sam3.pt",
            Path.home() / "Downloads" / "sam3.pt",
            Path(r"C:\Users\USER\Documents\Codex\2026-06-09\so-arm101-ai-pro\dist\SO101Lab_Offline_Internal_2026.07.22\payload\models\sam3.pt"),
        ]
    )

    checked = []
    for candidate in candidates:
        candidate = candidate.expanduser()
        checked.append(str(candidate))
        if candidate.exists() and candidate.stat().st_size > 1_000_000:
            return candidate

    raise FileNotFoundError("sam3.pt was not found. Checked:\n" + "\n".join(f"  - {item}" for item in checked))


def require_sam3_predictor():
    try:
        from ultralytics.models.sam import SAM3SemanticPredictor
    except Exception as exc:
        print("ERROR: SAM3 support was not found in ultralytics.")
        print("Run:")
        print(r"  powershell -ExecutionPolicy Bypass -File .\setup_sam3.ps1")
        raise SystemExit(1) from exc

    return SAM3SemanticPredictor


def resolve_device(requested: str) -> str:
    if requested != "auto":
        return requested
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def open_camera(index: int, width: int, height: int, fps: int) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(index, cv2.CAP_ANY)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera index {index}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


class Sam3Detector:
    def __init__(self, model_path: Path, conf: float, device: str) -> None:
        SAM3SemanticPredictor = require_sam3_predictor()
        self.model_path = model_path
        self.conf = conf
        self.device = device
        self.predictor = SAM3SemanticPredictor(
            overrides=dict(
                model=str(model_path),
                task="segment",
                mode="predict",
                conf=conf,
                device=device,
                save=False,
                verbose=False,
            )
        )

    def set_conf(self, conf: float) -> None:
        self.conf = conf
        try:
            self.predictor.args.conf = conf
        except Exception:
            pass

    def detect(self, frame_bgr: np.ndarray, prompts: list[str]) -> list[Detection]:
        label = ", ".join(prompts) if prompts else "object"
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as handle:
            tmp_path = handle.name
        try:
            cv2.imwrite(tmp_path, frame_bgr)
            self.predictor.set_image(tmp_path)
            results = self.predictor(text=prompts)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return detections_from_results(results, frame_bgr.shape, label)


def detections_from_results(results, shape: tuple[int, ...], label: str) -> list[Detection]:
    if not results:
        return []
    result = results[0]
    if result.masks is None:
        return []

    height, width = shape[:2]
    masks = result.masks.data.detach().cpu().numpy()
    confidences = []
    if result.boxes is not None and len(result.boxes) == len(masks):
        for box in result.boxes:
            try:
                confidences.append(float(box.conf[0]))
            except Exception:
                confidences.append(None)
    else:
        confidences = [None] * len(masks)

    detections = []
    for index, raw_mask in enumerate(masks):
        mask = cv2.resize(raw_mask.astype(np.uint8), (width, height), interpolation=cv2.INTER_NEAREST)
        ys, xs = np.where(mask > 0)
        if len(xs) < 20:
            continue
        detection = Detection(
            label=label,
            confidence=confidences[index] if index < len(confidences) else None,
            bbox_xyxy=[float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())],
            center_px=[float(xs.mean()), float(ys.mean())],
            area_px=float(len(xs)),
            mask=(mask > 0).astype(np.uint8),
        )
        detections.append(detection)

    detections.sort(key=lambda item: item.area_px, reverse=True)
    return detections


def draw_detections(frame_bgr: np.ndarray, detections: list[Detection], title: str) -> np.ndarray:
    output = frame_bgr.copy()
    overlay = output.copy()

    for index, detection in enumerate(detections, start=1):
        color = (0, 220, 255)
        overlay[detection.mask > 0] = (0, 160, 255)
        x1, y1, x2, y2 = [int(round(value)) for value in detection.bbox_xyxy]
        cx, cy = [int(round(value)) for value in detection.center_px]
        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
        cv2.circle(output, (cx, cy), 5, (0, 80, 255), -1)
        label = f"{index}:{detection.label}"
        if detection.confidence is not None:
            label += f" {detection.confidence:.2f}"
        cv2.putText(output, label, (x1, max(22, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

    output = cv2.addWeighted(overlay, 0.28, output, 0.72, 0)
    cv2.putText(output, title, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (30, 255, 30), 2)
    return output


class Sam3PromptApp:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.model_path = resolve_model(args.model)
        self.device = resolve_device(args.device)
        self.detector = Sam3Detector(self.model_path, args.conf, self.device)
        self.cap = open_camera(args.camera, args.width, args.height, args.fps)

        self.root = tk.Tk()
        self.root.title("SAM3 Prompt Camera")
        self.root.geometry("1040x660")
        self.root.configure(bg="#f5f7fb")
        self.root.protocol("WM_DELETE_WINDOW", self.stop)
        self.root.bind("q", lambda _event: self.stop())
        self.root.bind("Q", lambda _event: self.stop())

        self.running = True
        self.last_detect_time = 0.0
        self.last_detections: list[Detection] = []
        self.last_frame = None
        self.force_detect = True
        self.photo = None

        self.prompt_var = tk.StringVar(value=args.prompt)
        self.conf_var = tk.StringVar(value=f"{args.conf:.2f}")
        self.status_var = tk.StringVar(value=f"Device: {self.device}\nModel: {self.model_path}")

        self.video_label = tk.Label(self.root, bg="#111827")
        self.video_label.place(x=20, y=20, width=700, height=525)

        title = tk.Label(self.root, text="SAM3 prompt segmentation", font=("Segoe UI", 16, "bold"), bg="#f5f7fb", fg="#111827")
        title.place(x=745, y=24)

        ttk.Label(self.root, text="Prompt").place(x=748, y=72)
        prompt_entry = ttk.Entry(self.root, textvariable=self.prompt_var)
        prompt_entry.place(x=748, y=96, width=240)

        ttk.Label(self.root, text="Conf").place(x=748, y=134)
        conf_entry = ttk.Entry(self.root, textvariable=self.conf_var)
        conf_entry.place(x=748, y=158, width=80)

        apply_button = ttk.Button(self.root, text="Apply", command=self.apply_settings)
        apply_button.place(x=848, y=156, width=80)

        self.list_box = tk.Listbox(self.root, font=("Segoe UI", 10), activestyle="none")
        self.list_box.place(x=748, y=205, width=240, height=290)

        status = tk.Label(self.root, textvariable=self.status_var, bg="#f5f7fb", fg="#4b5563", justify="left", anchor="nw", wraplength=240)
        status.place(x=748, y=512, width=250, height=100)

        hint = tk.Label(self.root, text="Q: stop\nPrompt examples: cup, bottle, keyboard\nComma prompts: cup, bottle", justify="left", bg="#f5f7fb", fg="#4b5563")
        hint.place(x=20, y=560)

    def parse_prompts(self) -> list[str]:
        return [item.strip() for item in self.prompt_var.get().split(",") if item.strip()]

    def apply_settings(self) -> None:
        try:
            conf = max(0.01, min(0.99, float(self.conf_var.get().strip())))
        except ValueError:
            conf = 0.25
            self.conf_var.set("0.25")
        self.detector.set_conf(conf)
        self.force_detect = True
        self.status_var.set(f"Applied prompt='{self.prompt_var.get()}' conf={conf:.2f}")

    def update(self) -> None:
        if not self.running:
            return

        ok, frame = self.cap.read()
        if not ok:
            self.status_var.set("Camera read failed")
            self.root.after(200, self.update)
            return

        now = time.perf_counter()
        if self.force_detect or now - self.last_detect_time >= self.args.every:
            prompts = self.parse_prompts()
            try:
                self.last_detections = self.detector.detect(frame, prompts)
                self.last_detect_time = now
                self.force_detect = False
            except Exception as exc:
                self.status_var.set(f"SAM3 error: {exc}")

        prompts_text = self.prompt_var.get()
        title = f"SAM3 camera {self.args.camera} | prompt='{prompts_text}' | detections={len(self.last_detections)}"
        annotated = draw_detections(frame, self.last_detections, title)

        rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        image.thumbnail((700, 525), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(image=image)
        self.video_label.configure(image=self.photo)

        self.list_box.delete(0, tk.END)
        if self.last_detections:
            for detection in self.last_detections[:20]:
                conf = "" if detection.confidence is None else f" {detection.confidence:.2f}"
                cx, cy = detection.center_px
                self.list_box.insert(tk.END, f"{detection.label}{conf} | x={cx:.0f} y={cy:.0f}")
        else:
            self.list_box.insert(tk.END, "No object segmented")

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
        Sam3PromptApp(args).run()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
