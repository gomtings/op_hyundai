#!/usr/bin/env bash
# Manual update for the C3 (updates are disabled on the device):
# pull the branch, rebuild, and only keep `prebuilt` if the build succeeded.
# usage: bash /data/openpilot/scripts/update_op.sh [branch]   (default: current branch)
set -eu

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

BRANCH="${1:-$(git rev-parse --abbrev-ref HEAD)}"

# the venv's capnp (1.0.1) does not match /usr/local's (1.0.2), so build against the system one
mkdir -p /tmp/capnp_sys
for t in capnp capnpc capnpc-c++; do
  [ -x "/usr/local/bin/$t" ] && ln -sf "/usr/local/bin/$t" "/tmp/capnp_sys/$t"
done
export PATH="/tmp/capnp_sys:$PATH"

# tinygrad submodule lives under sunnypilot/tinygrad
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git merge --ff-only "origin/$BRANCH"
git submodule update --init --recursive

# drop prebuilt first so an interrupted build is rebuilt on the next boot instead of running stale binaries
rm -f prebuilt

if ! python3 system/manager/build.py; then
  echo "BUILD FAILED: prebuilt not created, the next boot will try to build again" >&2
  exit 1
fi

touch prebuilt
echo "update done on $BRANCH ($(git rev-parse --short HEAD)); reboot to apply"
