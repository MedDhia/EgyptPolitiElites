import signal
import sys

from .cli import main

# Restore default SIGPIPE handling so that `politi sources | head` exits
# quietly instead of raising BrokenPipeError out of a print().
if hasattr(signal, "SIGPIPE"):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

sys.exit(main())
