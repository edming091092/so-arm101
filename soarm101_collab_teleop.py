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
