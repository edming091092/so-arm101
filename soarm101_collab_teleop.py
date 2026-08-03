#!/usr/bin/env python3
"""
SO-ARM101 / SO-101 leader-follower teleoperation.

Move the leader arm by hand. The follower arm mirrors it through LeRobot.

Examples:
  python soarm101_collab_teleop.py --follower-port COM4 --leader-port COM5
  python soarm101_collab_teleop.py --follower-port COM5 --leader-port COM4
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time


def list_serial_ports() -> list[str]:
    try:
        from serial.tools import list_ports
    except Exception:
        return []

    return [port.device for port in list_ports.comports()]


def find_lerobot_teleoperate() -> str | None:
    cli = shutil.which("lerobot-teleoperate")
    if cli:
        return cli

    scripts_dir = os.path.dirname(os.path.abspath(sys.executable))
    candidates = [
        os.path.join(scripts_dir, "lerobot-teleoperate.exe"),
        os.path.join(scripts_dir, "lerobot-teleoperate"),
    ]

    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    return None


def require_lerobot_cli() -> str:
    cli = find_lerobot_teleoperate()
    if cli:
        return cli

    script_dir = os.path.dirname(os.path.abspath(__file__))
    setup_script = os.path.join(script_dir, "setup_lerobot_windows.ps1")

    print("ERROR: lerobot-teleoperate was not found.")
    print()
    print("Run the setup script first from PowerShell:")
    print(f"  powershell -ExecutionPolicy Bypass -File \"{setup_script}\"")
    print()
    print("Then run this script with the Python executable inside work\\lerobot_py312.")
    sys.exit(1)


def user_calibration_root() -> str:
    return os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "lerobot", "calibration")


def repo_calibration_root() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration")


def copy_file_if_missing(src: str, dst: str) -> bool:
    if os.path.exists(dst):
        return False
    if not os.path.exists(src):
        return False

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    return True


def validate_calibration_json(path: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return False

    required_motors = {
        "shoulder_pan",
        "shoulder_lift",
        "elbow_flex",
        "wrist_flex",
        "wrist_roll",
        "gripper",
    }
    required_fields = {"id", "drive_mode", "homing_offset", "range_min", "range_max"}

    if set(data) != required_motors:
        return False

    for motor_config in data.values():
        if not required_fields.issubset(motor_config):
            return False
        if motor_config["range_min"] < 0 or motor_config["range_max"] < 0:
            return False

    return True


def ensure_calibration_files(follower_id: str, leader_id: str) -> None:
    repo_root = repo_calibration_root()
    user_root = user_calibration_root()

    calibration_paths = [
        (
            os.path.join(repo_root, "robots", "so_follower", f"{follower_id}.json"),
            os.path.join(user_root, "robots", "so_follower", f"{follower_id}.json"),
            "follower",
        ),
        (
            os.path.join(repo_root, "teleoperators", "so_leader", f"{leader_id}.json"),
            os.path.join(user_root, "teleoperators", "so_leader", f"{leader_id}.json"),
            "leader",
        ),
    ]

    copied = []
    missing = []
    invalid = []

    for source, target, label in calibration_paths:
        if copy_file_if_missing(source, target):
            copied.append(target)

        if not os.path.exists(target):
            missing.append((label, target, source))
        elif not validate_calibration_json(target):
            invalid.append((label, target))

    if copied:
        print("Installed bundled calibration files:")
        for path in copied:
            print(f"  - {path}")

    if missing or invalid:
        print("ERROR: calibration files are missing or invalid.")
        print()
        for label, target, source in missing:
            print(f"Missing {label} calibration:")
            print(f"  expected: {target}")
            print(f"  bundled:  {source}")
        for label, target in invalid:
            print(f"Invalid {label} calibration:")
            print(f"  {target}")
        print()
        print("Fix options:")
        print("  1. Run setup_lerobot_windows.ps1 again to copy bundled calibration files.")
        print("  2. If this is a different arm set, run LeRobot calibration for that hardware.")
        print("  3. If calibration asks to use an existing file, press ENTER. Type c only when you intentionally want a fresh calibration.")
        sys.exit(1)


def print_port_hint() -> list[str]:
    ports = list_serial_ports()
    if not ports:
        print("No serial ports detected, or pyserial is not installed.")
        print("You can also try: lerobot-find-port")
        return []

    print("Detected serial ports:")
    for port in ports:
        print(f"  - {port}")

    return ports


def choose_port(prompt: str, ports: list[str]) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        if len(ports) == 1:
            return ports[0]
        print("Enter a COM port, for example COM5.")


def safety_countdown(seconds: int) -> None:
    print()
    print("Safety check:")
    print("  1. The follower arm is clamped firmly.")
    print("  2. The 1 meter workspace is clear.")
    print("  3. Power, USB, and servo cables are connected.")
    print("  4. Motor setup and calibration are complete.")
    print()
    print(f"Starting in {seconds} seconds. Press Ctrl+C to cancel.")
    for remaining in range(seconds, 0, -1):
        print(f"  {remaining}...")
        time.sleep(1)


def build_command(args: argparse.Namespace, passthrough: list[str], teleoperate_cli: str) -> list[str]:
    cmd = [
        teleoperate_cli,
        "--robot.type=so101_follower",
        f"--robot.port={args.follower_port}",
        f"--robot.id={args.follower_id}",
        "--teleop.type=so101_leader",
        f"--teleop.port={args.leader_port}",
        f"--teleop.id={args.leader_id}",
    ]

    if passthrough:
        cmd.extend(passthrough)

    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run SO-ARM101/SO-101 leader-to-follower teleoperation."
    )
    parser.add_argument("--follower-port", help="Follower arm USB port, e.g. COM4")
    parser.add_argument("--leader-port", help="Leader arm USB port, e.g. COM5")
    parser.add_argument("--follower-id", default="my_follower", help="Calibration id for follower arm")
    parser.add_argument("--leader-id", default="my_leader", help="Calibration id for leader arm")
    parser.add_argument("--no-countdown", action="store_true", help="Skip safety countdown")

    args, passthrough = parser.parse_known_args()

    teleoperate_cli = require_lerobot_cli()
    ensure_calibration_files(args.follower_id, args.leader_id)
    ports = print_port_hint()

    if not args.follower_port:
        print()
        args.follower_port = choose_port("Follower arm port: ", ports)

    if not args.leader_port:
        args.leader_port = choose_port("Leader arm port: ", ports)

    if platform.system() != "Windows" and os.geteuid() != 0:
        print()
        print("If you get a permission error, try:")
        print(f"  sudo chmod 666 {args.follower_port} {args.leader_port}")

    if not args.no_countdown:
        safety_countdown(5)

    cmd = build_command(args, passthrough, teleoperate_cli)
    print()
    print("Starting LeRobot teleoperation:")
    print("  " + " ".join(cmd))
    print()

    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        print()
        print("Teleoperation stopped.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
