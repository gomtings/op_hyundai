#!/usr/bin/env python3
"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import json
import os

from openpilot.common.basedir import BASEDIR
from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog

CAR_LIST_JSON_OUT = os.path.join(BASEDIR, "sunnypilot", "selfdrive", "car", "car_list.json")


def update_car_list_param():
  try:
    with open(CAR_LIST_JSON_OUT) as f:
      current_car_list = json.load(f)

    params = Params()
    existing_car_list = params.get("CarList")
    if existing_car_list != current_car_list:
      params.put("CarList", current_car_list)
      cloudlog.warning("Updated CarList param with latest platform list")
    else:
      cloudlog.warning("CarList param is up to date, no need to update")
  except Exception as e:
    # CarList key not recognized by params system - likely params_keys.h not rebuilt
    # or params system not fully initialized. Skip update to prevent crash.
    cloudlog.error(f"Failed to update CarList param: {e}. Skipping CarList sync. "
                   "This may indicate params_keys.h needs to be rebuilt on device.")


if __name__ == "__main__":
  update_car_list_param()
