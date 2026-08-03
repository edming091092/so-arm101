#!/usr/bin/env python3
"""
SO-ARM101 / SO-101 leader-follower teleoperation.

Each different physical arm set must use its own calibration id.

Examples:
  python soarm101_collab_teleop.py --arm-set-id lab01 --follower-port COM4 --leader-port COM5
  python soarm101_collab_teleop.py --arm-set-id lab02 --follower-port COM7 --leader-port COM8
"""

from __future__ import annotations

import argparse
import os
import platform
import re
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


def calibration_path(kind: str, robot_type: str, calibration_id: str) -> str:
    return os.path.join(
        os.path.expanduser("~"),
        ".cache",
        "huggingface",
        "lerobot",
        "calibration",
        kind,
        robot_type,
        f"{calibration_id}.json",
    )


def sanitize_id(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    clean = clean.strip("._-")
    if not clean:
        raise ValueError("arm-set-id cannot be empty")
    return clean


def print_calibration_status(follower_id: str, leader_id: str) -> None:
    follower_calibration = calibration_path("robots", "so_follower", follower_id)
    leader_calibration = calibration_path("teleoperators", "so_leader", leader_id)

    print("Calibration ids:")
    print(f"  follower: {follower_id}")
    print(f"  leader:   {leader_id}")
    print()
    print("Calibration files:")
    print(f"  follower: {follower_calibration}")
    print(f"  leader:   {leader_calibration}")
    print()

    missing = []
    if not os.path.exists(follower_calibration):
        missing.append("follower")
    if not os.path.exists(leader_calibration):
        missing.append("leader")

    if missing:
        print("Calibration note:")
        print("  One or more calibration files do not exist yet.")
        print("  LeRobot should ask you to calibrate this arm set.")
        print("  This is normal for a different physical arm set or a new computer.")
        print("  Use a unique --arm-set-id for each different physical arm set.")
        print()


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
    print("  4. Motor setup is complete.")
    print("  5. This arm set uses its own calibration id.")
    print()
    print(f"Starting in {seconds} seconds. Press Ctrl+C to cancel.")
    for remaining in range(seconds, 0, -1):
        print(f"  {remaining}...")
        time.sleep(1)


def build_command(args: argparse.Namespace, passthrough: list[str], teleoperate_cli: str) -> list[str]:
    cmd = [
        teleoperate_cli,
        f"--fps={args.fps}",
        "--robot.type=so101_follower",
        f"--robot.port={args.follower_port}",
        f"--robot.id={args.follower_id}",
        f"--robot.disable_torque_on_disconnect={str(args.disable_torque_on_disconnect).lower()}",
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
    parser.add_argument("--arm-set-id", help="Unique id for this physical arm set, e.g. lab01 or classroom_arm_03")
    parser.add_argument("--follower-port", help="Follower arm USB port, e.g. COM4")
    parser.add_argument("--leader-port", help="Leader arm USB port, e.g. COM5")
    parser.add_argument("--follower-id", help="Advanced: explicit calibration id for follower arm")
    parser.add_argument("--leader-id", help="Advanced: explicit calibration id for leader arm")
    parser.add_argument("--fps", type=int, default=10, help="Teleoperation loop FPS. Use 10 for teaching stability.")
    parser.add_argument(
        "--disable-torque-on-disconnect",
        action="store_true",
        help="Ask LeRobot to disable follower torque on disconnect. Off by default to avoid extra serial writes after a communication error.",
    )
    parser.add_argument("--no-countdown", action="store_true", help="Skip safety countdown")

    args, passthrough = parser.parse_known_args()

    if not args.arm_set_id and not (args.follower_id and args.leader_id):
        parser.error("provide --arm-set-id, or provide both --follower-id and --leader-id")

    if args.arm_set_id:
        arm_set_id = sanitize_id(args.arm_set_id)
        args.follower_id = args.follower_id or f"{arm_set_id}_follower"
        args.leader_id = args.leader_id or f"{arm_set_id}_leader"

    teleoperate_cli = require_lerobot_cli()
    print_calibration_status(args.follower_id, args.leader_id)
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
    print("If LeRobot asks to calibrate, follow the prompts carefully.")
    print("If it asks whether to use an existing calibration file, press ENTER.")
    print("Type c only when you intentionally want to recalibrate this exact arm set.")
    print()

    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        print()
        print("Teleoperation stopped.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
