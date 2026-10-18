"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""


def set_pid_log_field(pid_log, name, value) -> None:
  # LateralTorqueState only has these fields in the newer cereal; skip them here to avoid a schema change
  if hasattr(pid_log, name):
    setattr(pid_log, name, value)
