from __future__ import absolute_import, division, print_function, unicode_literals
import json
import logging
import os
from traceback import extract_tb
import sys
import signal

log = logging.getLogger(__name__)


def relpath(path):
    """ If possible, transform path by making it relative to the folder containing the starting script """
    path = os.path.abspath(path)
    dirname = os.path.dirname(os.path.abspath(sys.argv[0]))
    if path.startswith(dirname):
        return os.path.relpath(path, dirname)
    return path

def get_exc_backtrace(exc_traceback):
    """
    Transform the python traceback object into a list of dicts in the format
    expected by the notify API. This adjusts any absolute paths in the filenames
    into paths relative to the folder containing the starting script (argv[0])

    Python tracebacks have the most recent call last, but Squash expects it to be
    first so we reverse the traceback.
    """
    backtrace = []
    for filename, lineno, name, line in reversed(extract_tb(exc_traceback)):
        backtrace.append({
            "file":relpath(filename),
            "line":lineno,
            "symbol":name,
        })

    return backtrace

def get_frames(sig_frame, limit=None):
    n = 0

    while sig_frame is not None and (limit is None or n < limit):
        lineno = sig_frame.f_lineno
        co = sig_frame.f_code
        filename = co.co_filename
        name = co.co_name
        yield(filename, lineno, name)
        sig_frame = sig_frame.f_back
        n = n+1

def get_signal_backtrace(sig_frame):
    backtrace = []
    for filename, lineno, name in get_frames(sig_frame):
        backtrace.append({
            "file":relpath(filename),
            "line":lineno,
            "symbol":name,

        })

    return backtrace

signal_names = {
    signal.SIGABRT:"SIGABRT (Aborted)",
    signal.SIGFPE:"SIGFPS (Floating-point Exception)",
    signal.SIGILL:"SIGILL (Illegal Instruction)",
    signal.SIGSEGV:"SIGSEGV (Segmentation Violation)",

}
if sys.platform != "win32":
    signal_names.update({
        signal.SIGBUS:"SIGBUS (Bus Error)",
        signal.SIGTRAP:"SIGTRAP (Debugger Trap)",
    })

class Occurrence(object):

    @classmethod
    def from_exception(cls, exc_type, exc_value, exc_traceback):
        args = {
            'message': str(exc_value),
            'class_name': exc_type.__name__,
            'backtraces': [{
                "name": "Crashed Thread",
                "faulted": True,
                "backtrace": get_exc_backtrace(exc_traceback),
            }],
        }
        return cls(args)

    @classmethod
    def from_signal(cls, sig_num, sig_frame):
        message = signal_names.get(sig_num, "Signal %d" % sig_num)
        args = {
            'message': message,
            'class_name': message,
            'backtraces': [{
                "name": "Crashed Thread",
                "faulted": True,
                "backtrace": get_signal_backtrace(sig_frame),
            }],
        }
        return cls(args)

    def __init__(self, args):
        self.args = args

    def dump(self):
        return json.dumps(self.args, indent=1)




