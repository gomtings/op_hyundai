# Compatibility layer: the newer model stack imports openpilot.common.hardware,
# master-tici keeps these in openpilot.system.hardware.
#
# Loaded lazily on purpose: SConscripts import openpilot.common.hardware.usb while parsing, and
# openpilot.system.hardware pulls in modules that are only built later in the same SCons run.
_NAMES = ("HARDWARE", "PC", "TICI", "AGNOS")


def __getattr__(name):
  if name == "COMMA_HARDWARE":
    from openpilot.system.hardware import TICI
    return TICI
  if name in _NAMES:
    import openpilot.system.hardware as _hw
    return getattr(_hw, name)
  raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
