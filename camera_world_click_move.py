#!/usr/bin/env python3
"""
Camera pixel -> planar world coordinate -> SO-ARM101 action demo.

This is a teaching-oriented click-to-move tool for a fixed tabletop camera.
It does not assume a depth camera. Instead it uses calibration points:

  image pixel <-> tabletop world x/y in millimeters <-> follower joint action

After calibration, clicking the camera image estimates the tabletop coordinate
and interpolates a follower action from nearby calibration points.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

try:
    from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
    from lerobot.robots.so_follower.so_follower import SOFollower
    from lerobot.teleoperators.so_leader.config_so_leader import SOLeaderTeleopConfig
    from lerobot.teleoperators.so_leader.so_leader import SOLeader
except Exception:
    SOFollowerRobotConfig = None
    SOFollower = None
    SOLeaderTeleopConfig = None
    SOLeader = None


ACTION_KEYS = [
    "shoulder_pan.pos",
    "shoulder_lift.pos",
    "elbow_flex.pos",
    "wrist_flex.pos",
    "wrist_roll.pos",
    "gripper.pos",
]


@dataclass
class CalibPoint:
    pixel: list[float]
    world_mm: list[float]
    action: dict[str, float]


def sanitize_id(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("._-")
    if not clean:
        raise ValueError("arm-set-id cannot be empty")
    return clean


def action_changed(current: dict[str, float], previous: dict[str, float] | None, deadband: float) -> bool:
    if previous is None:
        return True
    return any(abs(float(value) - float(previous.get(key, value))) >= deadband for key, value in current.items())


def find_homography(points: list[CalibPoint]) -> np.ndarray | None:
    if len(points) < 4:
        return None
    src = np.array([point.pixel for point in points], dtype=np.float32)
    dst = np.array([point.world_mm for point in points], dtype=np.float32)
    homography, _mask = cv2.findHomography(src, dst, method=0)
    return homography


def pixel_to_world(pixel: tuple[float, float], homography: np.ndarray | None) -> tuple[float, float] | None:
    if homography is None:
        return None
    source = np.array([[[pixel[0], pixel[1]]]], dtype=np.float32)
    result = cv2.perspectiveTransform(source, homography)[0][0]
    return float(result[0]), float(result[1])


def interpolate_action(world_xy: tuple[float, float], points: list[CalibPoint], k: int = 4) -> dict[str, float] | None:
    usable = [point for point in points if point.action]
    if not usable:
        return None

    distances = []
    for point in usable:
        dx = world_xy[0] - point.world_mm[0]
        dy = world_xy[1] - point.world_mm[1]
        distance = math.hypot(dx, dy)
        distances.append((distance, point))

    distances.sort(key=lambda item: item[0])
    if distances[0][0] < 1e-6:
        return dict(distances[0][1].action)

    nearest = distances[: max(1, min(k, len(distances)))]
    weights = [1.0 / ((distance * distance) + 1e-6) for distance, _point in nearest]
    total_weight = sum(weights)

    output: dict[str, float] = {}
    keys = sorted({key for _distance, point in nearest for key in point.action})
    for key in keys:
        output[key] = sum(
            weight * float(point.action.get(key, 0.0))
            for weight, (_distance, point) in zip(weights, nearest)
        ) / total_weight

    return output


def default_calibration_path(arm_set_id: str) -> Path:
    return Path("calibration") / f"{sanitize_id(arm_set_id)}_camera_world.json"


class ClickMoveApp:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.root = tk.Tk()
        self.root.title("SO-ARM101 Camera World Click Move")
        self.root.geometry("1120x720")
        self.root.configure(bg="#f6f7f9")
        self.root.protocol("WM_DELETE_WINDOW", self.stop)

        self.cap: cv2.VideoCapture | None = None
        self.photo = None
        self.running = True
        self.frame = None
        self.display_size = (720, 540)
        self.image_scale = (1.0, 1.0)
        self.selected_pixel: tuple[float, float] | None = None
        self.selected_world: tuple[float, float] | None = None
        self.points: list[CalibPoint] = []
        self.homography: np.ndarray | None = None

        self.follower = None
        self.leader = None
        self.previous_leader_action: dict[str, float] | None = None
        self.last_leader_time = 0.0

        self.arm_set_var = tk.StringVar(value=args.arm_set_id)
        self.follower_port_var = tk.StringVar(value=args.follower_port)
        self.leader_port_var = tk.StringVar(value=args.leader_port)
        self.camera_var = tk.StringVar(value=str(args.camera))
        self.world_x_var = tk.StringVar(value="0")
        self.world_y_var = tk.StringVar(value="0")
        self.dry_run_var = tk.BooleanVar(value=True)
        self.follow_leader_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Start camera, connect arm, then record calibration points.")

        self.build_ui()
        self.load_if_exists(default_calibration_path(args.arm_set_id), quiet=True)

    def build_ui(self) -> None:
        title = tk.Label(self.root, text="Camera world click move", font=("Segoe UI", 17, "bold"), bg="#f6f7f9", fg="#111827")
        title.place(x=20, y=14)

        self.video_label = tk.Label(self.root, bg="#111827", cursor="crosshair")
        self.video_label.place(x=20, y=55, width=self.display_size[0], height=self.display_size[1])
        self.video_label.bind("<Button-1>", self.on_click)

        panel = tk.Frame(self.root, bg="#f6f7f9")
        panel.place(x=770, y=20, width=320, height=660)

        self.add_labeled_entry(panel, "Arm set id", self.arm_set_var, 0, 170)
        self.add_labeled_entry(panel, "Follower COM", self.follower_port_var, 54, 120)
        self.add_labeled_entry(panel, "Leader COM", self.leader_port_var, 108, 120)
        self.add_labeled_entry(panel, "Camera", self.camera_var, 162, 70)

        ttk.Button(panel, text="Start camera", command=self.start_camera).place(x=0, y=212, width=145, height=32)
        ttk.Button(panel, text="Connect arm", command=self.connect_arm).place(x=160, y=212, width=145, height=32)

        ttk.Checkbutton(panel, text="Teach follow leader", variable=self.follow_leader_var).place(x=0, y=258)
        ttk.Checkbutton(panel, text="Dry run", variable=self.dry_run_var).place(x=170, y=258)

        self.add_labeled_entry(panel, "World X mm", self.world_x_var, 302, 100)
        self.add_labeled_entry(panel, "World Y mm", self.world_y_var, 356, 100)

        ttk.Button(panel, text="Record calibration point", command=self.record_point).place(x=0, y=410, width=305, height=34)
        ttk.Button(panel, text="Move selected", command=self.move_selected).place(x=0, y=454, width=145, height=34)
        ttk.Button(panel, text="Save calibration", command=self.save_calibration).place(x=160, y=454, width=145, height=34)
        ttk.Button(panel, text="Load calibration", command=self.load_calibration).place(x=0, y=498, width=145, height=34)
        ttk.Button(panel, text="Clear points", command=self.clear_points).place(x=160, y=498, width=145, height=34)

        self.points_box = tk.Listbox(panel, font=("Consolas", 9), activestyle="none")
        self.points_box.place(x=0, y=544, width=305, height=76)

        status = tk.Label(panel, textvariable=self.status_var, justify="left", anchor="nw", wraplength=300, bg="#f6f7f9", fg="#374151")
        status.place(x=0, y=628, width=305, height=42)

        hint = tk.Label(
            self.root,
            text="Calibration: click a visible tabletop point, enter its world X/Y in millimeters, move the gripper to that point, then record. Use at least 4 points.",
            bg="#f6f7f9",
            fg="#4b5563",
            anchor="w",
        )
        hint.place(x=20, y=620, width=720, height=24)

    def add_labeled_entry(self, parent, label: str, variable: tk.StringVar, y: int, width: int) -> None:
        tk.Label(parent, text=label, bg="#f6f7f9", fg="#374151").place(x=0, y=y)
        ttk.Entry(parent, textvariable=variable).place(x=0, y=y + 24, width=width, height=28)

    def start_camera(self) -> None:
        try:
            camera = int(self.camera_var.get().strip())
        except ValueError:
            messagebox.showerror("Camera", "Camera must be a number.")
            return

        if self.cap is not None:
            self.cap.release()
        cap = cv2.VideoCapture(camera, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(camera, cv2.CAP_ANY)
        if not cap.isOpened():
            messagebox.showerror("Camera", f"Could not open camera {camera}.")
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.args.height)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap = cap
        self.status_var.set(f"Camera {camera} started.")

    def connect_arm(self) -> None:
        if SOFollower is None:
            messagebox.showerror("LeRobot", "LeRobot is not available. Run setup_lerobot_windows.ps1 first.")
            return

        arm_set_id = sanitize_id(self.arm_set_var.get())
        follower_id = f"{arm_set_id}_follower"
        leader_id = f"{arm_set_id}_leader"
        follower_port = self.follower_port_var.get().strip()
        leader_port = self.leader_port_var.get().strip()

        if not follower_port:
            messagebox.showerror("Follower", "Follower COM is required.")
            return

        try:
            self.follower = SOFollower(
                SOFollowerRobotConfig(
                    port=follower_port,
                    id=follower_id,
                    disable_torque_on_disconnect=False,
                )
            )
            self.follower.connect()

            if leader_port:
                self.leader = SOLeader(SOLeaderTeleopConfig(port=leader_port, id=leader_id))
                self.leader.connect()

            self.status_var.set(f"Connected follower {follower_id}" + (" and leader." if self.leader else "."))
        except Exception as exc:
            messagebox.showerror("Connect failed", str(exc))

    def on_click(self, event) -> None:
        if self.frame is None:
            return
        sx, sy = self.image_scale
        px = float(event.x) * sx
        py = float(event.y) * sy
        self.selected_pixel = (px, py)
        world = pixel_to_world(self.selected_pixel, self.homography)
        if world is not None:
            self.selected_world = world
            self.world_x_var.set(f"{world[0]:.1f}")
            self.world_y_var.set(f"{world[1]:.1f}")
            self.status_var.set(f"Selected pixel ({px:.0f}, {py:.0f}) -> world ({world[0]:.1f}, {world[1]:.1f}) mm")
        else:
            self.selected_world = None
            self.status_var.set(f"Selected pixel ({px:.0f}, {py:.0f}). Add at least 4 calibration points.")

    def current_action(self) -> dict[str, float] | None:
        if self.leader is not None and self.leader.is_connected:
            return {key: float(value) for key, value in self.leader.get_action().items()}
        if self.follower is not None and self.follower.is_connected:
            obs = self.follower.get_observation()
            return {key: float(obs[key]) for key in ACTION_KEYS if key in obs}
        return None

    def record_point(self) -> None:
        if self.selected_pixel is None:
            messagebox.showwarning("Calibration", "Click the camera image first.")
            return
        try:
            world = (float(self.world_x_var.get()), float(self.world_y_var.get()))
        except ValueError:
            messagebox.showerror("Calibration", "World X/Y must be numbers.")
            return

        action = self.current_action()
        if not action:
            messagebox.showerror("Calibration", "Connect follower or leader before recording an action.")
            return

        self.points.append(CalibPoint(list(self.selected_pixel), [world[0], world[1]], action))
        self.recompute_calibration()
        self.refresh_points_box()
        self.status_var.set(f"Recorded point {len(self.points)}.")

    def recompute_calibration(self) -> None:
        self.homography = find_homography(self.points)

    def refresh_points_box(self) -> None:
        self.points_box.delete(0, tk.END)
        for index, point in enumerate(self.points, start=1):
            self.points_box.insert(
                tk.END,
                f"{index:02d} px=({point.pixel[0]:.0f},{point.pixel[1]:.0f}) xy=({point.world_mm[0]:.0f},{point.world_mm[1]:.0f})",
            )

    def move_selected(self) -> None:
        if self.selected_pixel is None:
            messagebox.showwarning("Move", "Click a target in the camera image first.")
            return

        world = pixel_to_world(self.selected_pixel, self.homography)
        if world is None:
            messagebox.showwarning("Move", "Need at least 4 calibration points before moving.")
            return

        action = interpolate_action(world, self.points)
        if action is None:
            messagebox.showwarning("Move", "No calibration actions are available.")
            return

        self.selected_world = world
        self.world_x_var.set(f"{world[0]:.1f}")
        self.world_y_var.set(f"{world[1]:.1f}")

        if self.dry_run_var.get():
            self.status_var.set(f"Dry run target ({world[0]:.1f}, {world[1]:.1f}) mm. Uncheck Dry run to move.")
            return

        if self.follower is None or not self.follower.is_connected:
            messagebox.showerror("Move", "Follower is not connected.")
            return

        self.follower.send_action(action)
        self.status_var.set(f"Sent move to ({world[0]:.1f}, {world[1]:.1f}) mm.")

    def save_calibration(self) -> None:
        path = default_calibration_path(self.arm_set_var.get())
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "arm_set_id": sanitize_id(self.arm_set_var.get()),
            "camera": self.camera_var.get().strip(),
            "points": [
                {"pixel": point.pixel, "world_mm": point.world_mm, "action": point.action}
                for point in self.points
            ],
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.status_var.set(f"Saved {path}")

    def load_calibration(self) -> None:
        path = filedialog.askopenfilename(
            initialdir=str(Path("calibration").resolve()),
            title="Load camera-world calibration",
            filetypes=[("Calibration JSON", "*.json"), ("All files", "*.*")],
        )
        if path:
            self.load_if_exists(Path(path), quiet=False)

    def load_if_exists(self, path: Path, quiet: bool) -> None:
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.points = [
                CalibPoint(
                    pixel=[float(value) for value in item["pixel"]],
                    world_mm=[float(value) for value in item["world_mm"]],
                    action={key: float(value) for key, value in item["action"].items()},
                )
                for item in data.get("points", [])
            ]
            self.recompute_calibration()
            self.refresh_points_box()
            if not quiet:
                self.status_var.set(f"Loaded {len(self.points)} points from {path}")
        except Exception as exc:
            if not quiet:
                messagebox.showerror("Load failed", str(exc))

    def clear_points(self) -> None:
        self.points = []
        self.homography = None
        self.refresh_points_box()
        self.status_var.set("Calibration points cleared.")

    def follow_leader_once(self) -> None:
        if not self.follow_leader_var.get():
            return
        if self.leader is None or self.follower is None:
            return
        if not self.leader.is_connected or not self.follower.is_connected:
            return
        now = time.perf_counter()
        if now - self.last_leader_time < 0.05:
            return
        self.last_leader_time = now
        try:
            action = self.leader.get_action()
            if action_changed(action, self.previous_leader_action, self.args.deadband):
                self.follower.send_action(action)
                self.previous_leader_action = dict(action)
        except Exception as exc:
            self.status_var.set(f"Leader follow error: {exc}")

    def update_camera(self) -> None:
        if not self.running:
            return

        self.follow_leader_once()

        if self.cap is not None:
            ok, frame = self.cap.read()
            if ok:
                self.frame = frame
                display = self.draw_overlay(frame)
                rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(rgb)
                source_w, source_h = image.size
                image.thumbnail(self.display_size, Image.Resampling.LANCZOS)
                self.image_scale = (source_w / image.size[0], source_h / image.size[1])
                self.photo = ImageTk.PhotoImage(image=image)
                self.video_label.configure(image=self.photo)

        self.root.after(15, self.update_camera)

    def draw_overlay(self, frame) -> np.ndarray:
        output = frame.copy()
        for index, point in enumerate(self.points, start=1):
            x, y = int(point.pixel[0]), int(point.pixel[1])
            cv2.circle(output, (x, y), 6, (0, 220, 255), -1)
            cv2.putText(output, str(index), (x + 8, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 2)
        if self.selected_pixel is not None:
            x, y = int(self.selected_pixel[0]), int(self.selected_pixel[1])
            cv2.drawMarker(output, (x, y), (0, 80, 255), cv2.MARKER_CROSS, 24, 2)
        mode = "DRY RUN" if self.dry_run_var.get() else "LIVE MOVE"
        ready = "H ready" if self.homography is not None else f"{len(self.points)}/4 points"
        cv2.putText(output, f"{mode} | {ready}", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 255, 40), 2)
        return output

    def stop(self) -> None:
        self.running = False
        if self.cap is not None:
            self.cap.release()
        for device in [self.leader, self.follower]:
            try:
                if device is not None and device.is_connected:
                    device.disconnect()
            except Exception:
                pass
        self.root.destroy()

    def run(self) -> None:
        self.start_camera()
        self.root.after(50, self.update_camera)
        self.root.mainloop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Click camera image and move SO-ARM101 using planar calibration.")
    parser.add_argument("--arm-set-id", default="lab01", help="Unique id for this physical arm set.")
    parser.add_argument("--follower-port", default="COM5", help="Follower arm COM port.")
    parser.add_argument("--leader-port", default="COM4", help="Optional leader arm COM port for teaching calibration.")
    parser.add_argument("--camera", type=int, default=0, help="Camera index.")
    parser.add_argument("--width", type=int, default=640, help="Camera width.")
    parser.add_argument("--height", type=int, default=480, help="Camera height.")
    parser.add_argument("--deadband", type=float, default=0.8, help="Leader follow deadband.")
    return parser.parse_args()


def main() -> int:
    try:
        ClickMoveApp(parse_args()).run()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
