#!/usr/bin/env python3
"""
Patch LeRobot SO-101 leader/follower reads to retry transient serial failures.

The default LeRobot SO-101 teleop loop reads Present_Position with zero retries.
On Windows + USB serial + Feetech buses, the first sync read after calibration can
occasionally fail with:

    Failed to sync read 'Present_Position' ... after 1 tries

This patch changes those SO-101 reads to use num_retry=5.
"""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path


PATCH_MARKER = "# SO-ARM101 local patch: retry Present_Position sync reads"


def module_path(module_name: str) -> Path:
    spec = importlib.util.find_spec(module_name)
    if spec is None or spec.origin is None:
        raise RuntimeError(f"Could not find {module_name}")
    return Path(spec.origin)


def patch_file(path: Path, original: str, patched: str, label: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if PATCH_MARKER in text:
        print(f"{label} retry patch already applied: {path}")
        return False

    if original not in text:
        raise RuntimeError(f"Expected block not found in {path}")

    backup_path = path.with_suffix(path.suffix + ".soarm101-retry.bak")
    if not backup_path.exists():
        shutil.copy2(path, backup_path)

    path.write_text(text.replace(original, patched), encoding="utf-8")
    print(f"Applied {label} retry patch: {path}")
    print(f"Backup: {backup_path}")
    return True


def main() -> int:
    follower_path = module_path("lerobot.robots.so_follower.so_follower")
    leader_path = module_path("lerobot.teleoperators.so_leader.so_leader")

    follower_original = '''        obs_dict = self.bus.sync_read("Present_Position")
        obs_dict = {f"{motor}.pos": val for motor, val in obs_dict.items()}
'''
    follower_patched = '''        # SO-ARM101 local patch: retry Present_Position sync reads
        obs_dict = self.bus.sync_read("Present_Position", num_retry=5)
        obs_dict = {f"{motor}.pos": val for motor, val in obs_dict.items()}
'''

    leader_original = '''        action = self.bus.sync_read("Present_Position")
        action = {f"{motor}.pos": val for motor, val in action.items()}
'''
    leader_patched = '''        # SO-ARM101 local patch: retry Present_Position sync reads
        action = self.bus.sync_read("Present_Position", num_retry=5)
        action = {f"{motor}.pos": val for motor, val in action.items()}
'''

    patch_file(follower_path, follower_original, follower_patched, "follower")
    patch_file(leader_path, leader_original, leader_patched, "leader")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
