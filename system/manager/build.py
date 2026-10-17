#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

# NOTE: Do NOT import anything here that needs be built (e.g. params)
from openpilot.common.basedir import BASEDIR
from openpilot.common.spinner import Spinner
from openpilot.common.text_window import TextWindow
from openpilot.common.swaglog import cloudlog, add_file_handler
from openpilot.system.hardware import HARDWARE, AGNOS
from openpilot.system.version import get_build_metadata

MAX_CACHE_SIZE = 4e9 if "CI" in os.environ else 2e9
CACHE_DIR = Path("/data/scons_cache" if AGNOS else "/tmp/scons_cache")

TOTAL_SCONS_NODES = 3800
MAX_BUILD_PROGRESS = 100

SUBMODULE_MARKERS = {
  "panda": "panda/__init__.py",
  "opendbc_repo": "opendbc_repo/opendbc/__init__.py",
  "msgq_repo": "msgq_repo/msgq/__init__.py",
  "rednose_repo": "rednose_repo/rednose/__init__.py",
  "teleoprtc_repo": "teleoprtc_repo/teleoprtc/__init__.py",
  "tinygrad_repo": "tinygrad_repo/tinygrad/__init__.py",
}
LFS_FILES = ("selfdrive/modeld/models/driving_supercombo.onnx", "selfdrive/modeld/models/dmonitoring_model.onnx")

def check_sources() -> list[str]:
  # a fresh clone without submodules / LFS objects fails deep inside scons with a confusing error, so say what is missing up front
  problems = []
  for name, marker in SUBMODULE_MARKERS.items():
    if not (Path(BASEDIR) / marker).exists():
      problems.append(f"submodule {name} is empty: run `git submodule update --init --recursive`")
  for rel in LFS_FILES:
    f = Path(BASEDIR) / rel
    if not f.exists() or f.stat().st_size < 1024:
      problems.append(f"{rel} is a git-lfs pointer, not the real file: run `git lfs pull`")
  return problems

def build(spinner: Spinner, dirty: bool = False, minimal: bool = False) -> None:
  problems = check_sources()
  if problems:
    msg = "cannot build, the checkout is incomplete\n \n" + "\n".join(problems)
    add_file_handler(cloudlog)
    cloudlog.error(msg)
    spinner.close()
    if not os.getenv("CI"):
      with TextWindow(msg) as t:
        t.wait_for_exit()
    exit(1)

  env = os.environ.copy()
  env['SCONS_PROGRESS'] = "1"
  if AGNOS:
    # the venv's capnp (1.0.1) does not match the headers in /usr/local (1.0.2), so build with the system tools
    capnp_sys = Path("/tmp/capnp_sys")
    capnp_sys.mkdir(exist_ok=True)
    for tool in ("capnp", "capnpc", "capnpc-c++"):
      src = Path("/usr/local/bin") / tool
      if src.exists():
        (capnp_sys / tool).unlink(missing_ok=True)
        (capnp_sys / tool).symlink_to(src)
    env['PATH'] = f"{capnp_sys}:{env['PATH']}"
  nproc = os.cpu_count()
  if nproc is None:
    nproc = 2

  extra_args = ["--minimal"] if minimal else []

  if AGNOS:
    HARDWARE.set_power_save(False)
    os.sched_setaffinity(0, range(8))  # ensure we can use the isolcpus cores

  # building with all cores can result in using too
  # much memory, so retry with less parallelism
  compile_output: list[bytes] = []
  for n in (nproc, nproc/2, 1):
    compile_output.clear()
    scons: subprocess.Popen = subprocess.Popen(["scons", f"-j{int(n)}", "--cache-populate", *extra_args], cwd=BASEDIR, env=env, stderr=subprocess.PIPE)
    assert scons.stderr is not None

    # Read progress from stderr and update spinner
    while scons.poll() is None:
      try:
        line = scons.stderr.readline()
        if line is None:
          continue
        line = line.rstrip()

        prefix = b'progress: '
        if line.startswith(prefix):
          i = int(line[len(prefix):])
          spinner.update_progress(MAX_BUILD_PROGRESS * min(1., i / TOTAL_SCONS_NODES), 100.)
        elif len(line):
          compile_output.append(line)
          print(line.decode('utf8', 'replace'))
      except Exception:
        pass

    if scons.returncode == 0:
      break

  if scons.returncode != 0:
    # Read remaining output
    if scons.stderr is not None:
      compile_output += scons.stderr.read().split(b'\n')

    # Build failed log errors
    error_s = b"\n".join(compile_output).decode('utf8', 'replace')
    add_file_handler(cloudlog)
    cloudlog.error("scons build failed\n" + error_s)

    # Show TextWindow
    spinner.close()
    if not os.getenv("CI"):
      with TextWindow("openpilot failed to build\n \n" + error_s) as t:
        t.wait_for_exit()
    exit(1)

  # enforce max cache size
  cache_files = [f for f in CACHE_DIR.rglob('*') if f.is_file()]
  cache_files.sort(key=lambda f: f.stat().st_mtime)
  cache_size = sum(f.stat().st_size for f in cache_files)
  for f in cache_files:
    if cache_size < MAX_CACHE_SIZE:
      break
    cache_size -= f.stat().st_size
    f.unlink()


if __name__ == "__main__":
  spinner = Spinner()
  spinner.update_progress(0, 100)
  build_metadata = get_build_metadata()
  build(spinner, build_metadata.openpilot.is_dirty, minimal = AGNOS)
