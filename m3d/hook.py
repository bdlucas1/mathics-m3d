import sys
import traceback
import threading

def my_excepthook(exc_type, exc, tb):
    print("\n=== Uncaught exception (reversed stack via PYTHONPATH and ~/bin/sitecustomize.py) ===", file=sys.stderr)

    # Extract frames and reverse them
    frames = traceback.extract_tb(tb)
    for frame in reversed(frames):
        # This format matches traceback formatting but reversed:
        print(f'  File "{frame.filename}", line {frame.lineno}, in {frame.name}', file=sys.stderr)
        if frame.line:
            print(f"    {frame.line.strip()}", file=sys.stderr)

    # Print exception type + message
    print(f"{exc_type.__name__}: {exc}", file=sys.stderr)

sys.excepthook = my_excepthook

# Handle uncaught exceptions in threads (Python 3.8+)
try:
    def _thread_hook(args):
        my_excepthook(args.exc_type, args.exc_value, args.exc_traceback)
    threading.excepthook = _thread_hook
except Exception:
    pass
