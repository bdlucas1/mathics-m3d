#!/usr/bin/env bash
set -euo pipefail

#
# via ChatGPT
#

############################################
# Resolve the directory this script lives in
############################################

SCRIPT_SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SCRIPT_SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SCRIPT_SOURCE")" && pwd)"
  SCRIPT_SOURCE="$(readlink "$SCRIPT_SOURCE")"
  [[ "$SCRIPT_SOURCE" != /* ]] && SCRIPT_SOURCE="$DIR/$SCRIPT_SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SCRIPT_SOURCE")" && pwd)"

APP_DIR="$SCRIPT_DIR"
VENV_DIR="$APP_DIR/.venv"
M3D_PY="$APP_DIR/m3d.py"
#TMPDIR="${TMPDIR:-/tmp}"
TMPDIR=/tmp

############################################
# Activate .venv next to m3d.py, if present
############################################

if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
else
  echo "Warning: .venv not found at '$VENV_DIR' (continuing without it)" >&2
fi

# After activation, use whatever 'python' now points to, unless overridden
PYTHON_BIN="${PYTHON:-python}"

if [ ! -f "$M3D_PY" ]; then
  echo "Error: m3d.py not found at '$M3D_PY'" >&2
  exit 1
fi

############################################
# Start m3d.py detached with logging
############################################

# Temp log name; rename after we have the PID
log_tmp="$TMPDIR/m3d-$$.log"

# IMPORTANT: we do *not* cd; so any filenames in "$@"
# are resolved relative to the caller's original CWD.
# We invoke m3d.py via its absolute path.
nohup "$PYTHON_BIN" -u "$M3D_PY" "$@" >>"$log_tmp" 2>&1 &

pid=$!

# Final log name with the real PID
log="$TMPDIR/m3d-${pid}.log"
mv "$log_tmp" "$log" 2>/dev/null || log="$log_tmp"

# Detach the job from the shell (if interactive and disown exists)
if command -v disown >/dev/null 2>&1; then
  disown "$pid" 2>/dev/null || true
fi

echo "Panel server started using:"
echo "  Script dir: $APP_DIR"
echo "  m3d.py:     $M3D_PY"
echo "  PID:        $pid"
echo "  Log:        $log"
