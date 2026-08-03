#!/usr/bin/env python3
"""
Patch LeRobot's Feetech calibration writer for SO-ARM101/SO-101.

Some SO leader/follower calibration runs can produce range_min below 0 or
range_max above 4095 after homing offsets are applied. Feetech position-limit
registers are unsigned 12-bit values, so writing those values raises:

    ValueError: Negative values are not allowed

This patch clamps Min_Position_Limit and Max_Position_Limit to 0..4095 before
writing them to the motors and before caching/saving calibration.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path


PATCH_MARKER = "# SO-ARM101 local patch: clamp Feetech position limits"

ORIGINAL = '''    def write_calibration(self, calibration_dict: dict[str, MotorCalibration], cache: bool = True) -> None:
        for motor, calibration in calibration_dict.items():
            if self.protocol_version == 0:
                self.write("Homing_Offset", motor, calibration.homing_offset)
            self.write("Min_Position_Limit", motor, calibration.range_min)
            self.write("Max_Position_Limit", motor, calibration.range_max)

        if cache:
            self.calibration = calibration_dict
'''

PATCHED = '''    def write_calibration(self, calibration_dict: dict[str, MotorCalibration], cache: bool = True) -> None:
        # SO-ARM101 local patch: clamp Feetech position limits
        for motor, calibration in calibration_dict.items():
            if self.protocol_version == 0:
                self.write("Homing_Offset", motor, calibration.homing_offset)

            raw_min = int(calibration.range_min)
            raw_max = int(calibration.range_max)
            clamped_min = max(0, min(4095, raw_min))
            clamped_max = max(0, min(4095, raw_max))

            if clamped_min != raw_min or clamped_max != raw_max:
                print(
                    f"Clamped {motor} calibration range from "
                    f"[{raw_min}, {raw_max}] to [{clamped_min}, {clamped_max}]"
                )
                calibration.range_min = clamped_min
                calibration.range_max = clamped_max

            self.write("Min_Position_Limit", motor, calibration.range_min)
            self.write("Max_Position_Limit", motor, calibration.range_max)

        if cache:
            self.calibration = calibration_dict
'''


def find_feetech_path() -> Path:
    spec = importlib.util.find_spec("lerobot.motors.feetech.feetech")
    if spec is None or spec.origin is None:
        raise RuntimeError("Could not find lerobot.motors.feetech.feetech")
    return Path(spec.origin)


def main() -> int:
    feetech_path = find_feetech_path()
    text = feetech_path.read_text(encoding="utf-8")

    if PATCH_MARKER in text:
        print(f"Already patched: {feetech_path}")
        return 0

    if ORIGINAL not in text:
        print(f"ERROR: expected write_calibration block was not found in {feetech_path}")
        print("LeRobot may have changed. Patch not applied.")
        return 1

    backup_path = feetech_path.with_suffix(feetech_path.suffix + ".soarm101.bak")
    if not backup_path.exists():
        shutil.copy2(feetech_path, backup_path)

    feetech_path.write_text(text.replace(ORIGINAL, PATCHED), encoding="utf-8")
    print(f"Patched: {feetech_path}")
    print(f"Backup:  {backup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
