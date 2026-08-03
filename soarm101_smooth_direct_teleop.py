#!/usr/bin/env python3
"""
Smooth direct SO-ARM101 / SO-101 leader-follower teleoperation.

This bypasses LeRobot's generic teleop loop for teaching use:
- no follower observation read
- no visualization
- no processor pipeline
- no repeated follower writes while the leader is idle

The goal is smoother classroom/demo control on Windows USB serial setups.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time

from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.teleoperators.so_leader.config_so_leader import SOLeaderTeleopConfig
from lerobot.teleoperators.so_leader.so_leader import SOLeader


def sanitize_id(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("._-")
    if not clean:
        raise ValueError("arm-set-id cannot be empty")
    return clean


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


def action_changed(current: dict[str, float], previous: dict[str, float] | None, deadband: float) -> bool:
    if previous is None:
        return True

    for key, value in current.items():
        old = previous.get(key)
        if old is None or abs(float(value) - float(old)) >= deadband:
            return True

    return False


def sleep_until_next(loop_start: float, fps: int) -> None:
    target_s = 1.0 / max(1, fps)
    elapsed = time.perf_counter() - loop_start
    remaining = target_s - elapsed
    if remaining > 0:
        time.sleep(remaining)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smooth direct SO-101 leader-follower teaching teleop.")
    parser.add_argument("--arm-set-id", required=True, help="Unique id for this physical arm set, e.g. lab01")
    parser.add_argument("--follower-port", required=True, help="Follower arm port, e.g. COM5")
    parser.add_argument("--leader-port", required=True, help="Leader arm port, e.g. COM4")
    parser.add_argument("--fps", type=int, default=20, help="Loop target FPS. Try 20 first, then 30 if stable.")
    parser.add_argument("--deadband", type=float, default=0.8, help="Minimum position change before writing again.")
    parser.add_argument("--stats-interval", type=float, default=2.0, help="Seconds between timing summaries.")
    args = parser.parse_args()

    arm_set_id = sanitize_id(args.arm_set_id)
    follower_id = f"{arm_set_id}_follower"
    leader_id = f"{arm_set_id}_leader"

    print("Smooth direct teleop")
    print(f"  follower: {follower_id} on {args.follower_port}")
    print(f"  leader:   {leader_id} on {args.leader_port}")
    print(f"  fps:      {args.fps}")
    print(f"  deadband: {args.deadband}")
    print()
    print("Calibration files:")
    print(f"  follower: {calibration_path('robots', 'so_follower', follower_id)}")
    print(f"  leader:   {calibration_path('teleoperators', 'so_leader', leader_id)}")
    print()

    leader = SOLeader(SOLeaderTeleopConfig(port=args.leader_port, id=leader_id))
    follower = SOFollower(
        SOFollowerRobotConfig(
            port=args.follower_port,
            id=follower_id,
            disable_torque_on_disconnect=False,
        )
    )

    previous_action: dict[str, float] | None = None
    loops = 0
    writes = 0
    last_stats = time.perf_counter()
    total_leader_ms = 0.0
    total_write_ms = 0.0

    try:
        print("Connecting leader...")
        leader.connect()
        print("Connecting follower...")
        follower.connect()
        print("Connected. Press Ctrl+C to stop.")
        print()

        while True:
            loop_start = time.perf_counter()

            read_start = time.perf_counter()
            action = leader.get_action()
            total_leader_ms += (time.perf_counter() - read_start) * 1000.0

            if action_changed(action, previous_action, args.deadband):
                write_start = time.perf_counter()
                follower.send_action(action)
                total_write_ms += (time.perf_counter() - write_start) * 1000.0
                previous_action = dict(action)
                writes += 1

            loops += 1
            now = time.perf_counter()
            if now - last_stats >= args.stats_interval:
                hz = loops / (now - last_stats)
                avg_read = total_leader_ms / max(1, loops)
                avg_write = total_write_ms / max(1, writes)
                print(
                    f"loop {hz:.1f} Hz | writes {writes} | "
                    f"leader read {avg_read:.1f} ms | follower write {avg_write:.1f} ms"
                )
                loops = 0
                writes = 0
                total_leader_ms = 0.0
                total_write_ms = 0.0
                last_stats = now

            sleep_until_next(loop_start, args.fps)

    except KeyboardInterrupt:
        print()
        print("Stopped by user.")
        return 130
    finally:
        for device_name, device in [("leader", leader), ("follower", follower)]:
            try:
                if device.is_connected:
                    device.disconnect()
            except Exception as exc:
                print(f"Warning: failed to disconnect {device_name}: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
