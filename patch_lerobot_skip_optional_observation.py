#!/usr/bin/env python3
"""
Patch LeRobot teleoperation to continue if optional follower observation fails.

For SO-101 leader/follower teaching teleoperation, the loop reads follower
Present_Position before reading the leader action. LeRobot's own comment says
this observation is not really needed unless visualization or processors use it.

On some Windows + Feetech setups, follower sync_read can intermittently fail with:

    Failed to sync read 'Present_Position' ... There is no status packet!

This patch catches that optional observation failure, uses an empty observation,
and continues sending leader actions to the follower.
"""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path


PATCH_MARKER = "# SO-ARM101 local patch: continue without optional follower observation"

ORIGINAL = '''        # Get robot observation
        # Not really needed for now other than for visualization
        # teleop_action_processor can take None as an observation
        # given that it is the identity processor as default
        obs = robot.get_observation()

        if robot.name == "unitree_g1":
            teleop.send_feedback(obs)
'''

PATCHED = '''        # Get robot observation
        # Not really needed for now other than for visualization
        # teleop_action_processor can take None as an observation
        # given that it is the identity processor as default
        # SO-ARM101 local patch: continue without optional follower observation
        try:
            obs = robot.get_observation()
        except ConnectionError as exc:
            print(f"Warning: skipped optional robot observation after communication error: {exc}")
            obs = {}

        if robot.name == "unitree_g1":
            teleop.send_feedback(obs)
'''


def find_teleoperate_path() -> Path:
    spec = importlib.util.find_spec("lerobot.scripts.lerobot_teleoperate")
    if spec is None or spec.origin is None:
        raise RuntimeError("Could not find lerobot.scripts.lerobot_teleoperate")
    return Path(spec.origin)


def main() -> int:
    path = find_teleoperate_path()
    text = path.read_text(encoding="utf-8")

    if PATCH_MARKER in text:
        print(f"Optional-observation patch already applied: {path}")
        return 0

    if ORIGINAL not in text:
        print(f"ERROR: expected teleop observation block was not found in {path}")
        print("LeRobot may have changed. Patch not applied.")
        return 1

    backup_path = path.with_suffix(path.suffix + ".soarm101-obs.bak")
    if not backup_path.exists():
        shutil.copy2(path, backup_path)

    path.write_text(text.replace(ORIGINAL, PATCHED), encoding="utf-8")
    print(f"Applied optional-observation patch: {path}")
    print(f"Backup: {backup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
