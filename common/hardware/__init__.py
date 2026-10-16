# Compatibility layer: the newer model stack imports openpilot.common.hardware,
# master-tici keeps these in openpilot.system.hardware.
from openpilot.system.hardware import HARDWARE, PC, TICI, AGNOS

COMMA_HARDWARE = TICI
