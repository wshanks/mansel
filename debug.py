'Debugging tools'
import sys

from PyQt5.QtCore import pyqtRemoveInputHook
from pudb import set_trace


def debug_trace():  # pragma: no cover
    '''Set a tracepoint in the Python debugger that works with Qt'''
    sys.stdin = open('/dev/tty')
    pyqtRemoveInputHook()
    set_trace()
