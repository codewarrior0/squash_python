"""
Squash Client Library: Python (2.7/3.2)
=========================================================

This client library reports exceptions to Squash, the Squarish exception
reporting and management system.

Documentation
-------------

Comprehensive documentation is written in ReST-formatted comments
throughout the source. To view this documentation as an HTML site, run sphinx
with ``(cd doc; make html)``. If sphinx is not installed, run ``pip install sphinx``.
The starting HTML file is at ``doc/_build/html/index.html``.

For an overview of the various components of Squash, see the website
documentation at https://github.com/SquareSquash/web.

Compatibility
-------------

This library is compatible with projects written using Python 2.7 and above,
and Python 3.2 and above. It may also be compatible with Python 2.6 and Python 3.1, if
the `argparse` module is installed.

This library was created for use with Python 2.7. Patches to improve compatibility
with python 2.6 or python 3+ are welcome.

Requirements
------------

Requires `argparse` on certain older Python versions; see **Compatibility** above.

Usage
-----

Unpack the source distribution, then run ``python setup.py install`` to
install squash_python into your site-packages folder. Consider using
`virtualenv` beforehand to install it into a site-packages folder
specific to your project instead of the system-wide folder

Add the following code somewhere in your application that gets invoked on
startup, such as your app's `main` function::

    import squash_python

    client = squash_python.get_client()
    client.APIKey = "YOUR_API_KEY"
    client.environment = "production"
    client.host = "https://your.squash.host"
    client.revision = "GIT_REVISION_OF_RELEASED_PRODUCT"
    client.reportErrors()
    client.hook()

.. tip: Use ``git rev-parse`` to translate a commit-ish (such as a branch or tag name)
        into a commit ID for the `revision` field.

The `reportErrors` method loads any errors recorded from previous crashes and
transmits them to Squash. Errors are only removed from this queue when Squash
successfully receives them. Exceptions are transmitted to Squash using
JSON-over-HTTPS. A default API endpoint is pre-configured. (see `notifyPath`
below)

the `hook` method uses `sys.excepthook` to add the uncaught-exception handler
that allows Squash to record new crashes.

A third method `recordException` can be used to report non-fatal exceptions
caught by your application. Its arguments are the same as those provided by `sys.exc_info`
and accepted by `sys.excepthook`. Typical usage::

    client.reportException(*sys.exc_info())

Configuration
-------------

The squash_python module logs information about successes and failures
to the standard `logging` module. Failures are logged to WARN, successes
are logged to INFO, and plenty of other stuff is logged to DEBUG.
To quickly enable this module and see its output, use the following code::

    import logging
    logging.basicConfig(level=logging.DEBUG)

You can configure the client using the attributes of the
singleton instance returned by `squash_python.get_client()`.
The following attributes are available:

`host`:
  **Required.** The host on which Squash is running. e.g. "https://squash.example.com:3000"

`APIKey`:
  **Required.** The API key of the project that exceptions will be associated with.
  This configuration option is required. The value can be found by going to the
  project's home page on Squash.

`environment`:
  **Required.** The environment that exceptions will be associated with.
  This should be a string such as "development", "testing", or "production"

`revision`:
  **Required.** The revision of the Git repository that was compiled to make this
  build. This ought to be a commit ID (for git, a SHA-1 hash).

`build`:
  For released apps, the machine-readable build number or build identifer that matches the revision.

`version`:
  For released apps, the human-readable version number.

`disabled`:
  If `YES`, the Squash client will not report any errors.

`notifyPath`:
  The path to post new exception notifications to. By default it's
  set to `/api/1.0/notify`.

`timeout`:
  The amount of time to wait before giving up on transmitting an
  error. By default it's 15 seconds.

`ignoredExceptions`:
  A set of `Exception` names or `Exception` subclasses that
  will not be reported to Squash.

`handledSignals`:
  A set of signals (represented as a list of integers) that Squash
  will trap. By default it's `SIGABRT`, `SIGBUS`, `SIGFPE`, `SIGILL`, `SIGSEGV`,
  and `SIGTRAP`. (On win32, `SIGBUS` and `SIGTRAP` are not available; see :mod:`signal`)

`filterStrings`:
  Strings to remove from the exception's message.
  These keys might contain sensitive or personal information, for
  example. In addition, the location of the user's home folder is
  removed and replaced with ~

`args`:
  Dictionary of additional keys and values to add to each reported occurrence.

Command-Line Utilities
----------------------

The ``squash_python`` module also installs two command line scripts called ``squash_release``
and ``squash_tester``.

You *must* use ``squash_release`` to notify Squash of a new deployment. Run ``squash_release`` to
have it print its usage information.

You can use ``squash_tester`` to test your Squash integration, or as a template to integrating
Squash into your own project. The easiest way to use ``squash_tester`` is to
run the Squash web server locally on port 3000, and set the environment variable
``SQUASH_TESTER_API_KEY`` to the API key of a project you create in your local web
server. Once that is done, you may run ``squash_tester`` to report an uncaught exception, or
run `squash_tester -s` to report an unhandled signal.

If the server is running elsewhere, you may set the environment variable ``SQUASH_TESTER_HOST``
 to the method, host and port of the server (e.g. "https://squash.example.com:3000")

"""

from __future__ import absolute_import, division, print_function, unicode_literals
import codecs
from datetime import datetime
import json
import logging
import signal
import os
import platform
import sys
try:
    import urllib2 as urlerror
except ImportError:
    import urllib.error as urlerror

import uuid

from squash_python.occurrence import Occurrence
from squash_python.uploader import SquashUploader

log = logging.getLogger(__name__)

_client = None


def get_client():
    """
    Return the shared `SquashClient` instance.
    """
    global _client
    if _client is None:
        _client = SquashClient()
    return _client


class SquashClient(object):
    APIKey = NotImplemented
    environment = NotImplemented
    host = NotImplemented
    revision = NotImplemented

    version = None
    build = None

    def __init__(self):
        if sys.platform == "win32":
            # Not all signals are available on win32 - see `signal.signal`
            self.handledSignals = [
                signal.SIGABRT,
                signal.SIGFPE,
                signal.SIGILL,
                signal.SIGSEGV,
            ]
        else:
            self.handledSignals = [
                signal.SIGABRT,
                signal.SIGBUS,
                signal.SIGFPE,
                signal.SIGILL,
                signal.SIGSEGV,
                signal.SIGTRAP,
            ]

        self.ignoredExceptions = set()
        self.filterStrings = []
        self.old_handlers = {}
        self.notifyPath = "/api/1.0/notify"
        self.timeout = 15
        self.disabled = False
        self.args = {}

    def hook(self):
        """
        Install the client's exception hook and signal handlers.
        """
        if not (self.revision):
            raise ValueError("SquashClient needs a revision.")
        if not (self.APIKey):
            raise ValueError("SquashClient needs an APIKey.")
        if not (self.host):
            raise ValueError("SquashClient needs a host.")
        if not (self.environment):
            raise ValueError("SquashClient needs an environment.")

        self.old_excepthook = sys.excepthook
        sys.excepthook = self.excepthook

        for signum in self.handledSignals:
            self.old_handlers[signum] = signal.signal(signum, self.sighandler)

    def recordException(self, exc_type, exc_value, exc_traceback):
        """
        Given the three values passed into :func:`sys.excepthook` or obtainable from :func:`sys.exc_info`,
        record an occurrence of the exception.

        This may be called by the application to report a nonfatal exception.
        """
        if self.disabled:
            return

        if exc_type.__name__ in self.ignoredExceptions or exc_type in self.ignoredExceptions:
            return

        occ = Occurrence.from_exception(exc_type, exc_value, exc_traceback)
        self.record(occ)

    def excepthook(self, exc_type, exc_value, exc_traceback):
        """
        From :func:`sys.excepthook`:

        When an exception is raised and uncaught, the interpreter calls sys.excepthook with three arguments,
        the exception class, exception instance, and a traceback object.
        """

        self.recordException(exc_type, exc_value, exc_traceback)

        self.old_excepthook(exc_type, exc_value, exc_traceback)

    def recordSignal(self, sig_num, sig_frame):
        """
        Given the two values passed into a `signal` handler, record an occurence of the signal.
        """
        if self.disabled:
            return

        occ = Occurrence.from_signal(sig_num, sig_frame)
        self.record(occ)

    def sighandler(self, sig_num, sig_frame):
        """
        From :func:`signal.signal`:

        The handler is called with two arguments: the signal number and the current stack frame ([...] see the
        attribute descriptions in the :mod:`inspect` module)

        """

        # Reset the signal handlers so signals raised during dump will terminate the process

        for signum, func in self.old_handlers.items():
            signal.signal(signum, func)

        self.recordSignal(sig_num, sig_frame)

        # Reraise the signal
        os.kill(os.getpid(), sig_num)

    def record(self, occ):
        """
        Saves the given occurrence to a file. The file is placed within a subfolder of `self.occurrence_folder`
        (by default "~/.SquashOccurrences") named with the app's API key.
        """
        args = occ.args

        message = args['message']

        # Remove filtered strings from exception message.
        for filter in self.filterStrings:
            message = message.replace(filter, '[REDACTED]')
            message = message.replace(repr(filter), '[REDACTED]') # OSErrors often format an included pathname using %r

        # Also remove home folder path.
        message = message.replace(os.path.expanduser('~'), '~')
        message = message.replace(repr(os.path.expanduser('~')), '~')

        args['message'] = message

        args.update({
            # Required fields
            'api_key':self.APIKey,
            'environment':self.environment,
            'UUID': str(uuid.uuid1()),
            'client': "squash_python",
            'occurred_at': datetime.now().isoformat(),
            'revision': self.revision,

            # Additional fields
            'arguments': sys.argv,
            'env_vars': dict(os.environ),
            'pid': os.getpid(),

            'device_id': hex(hash(platform.node())), # Hash of machine name - should be good ehough
            'device_type': platform.processor(), # "Intel64 Family 6 Model 30 Stepping 5, GenuineIntel"
            'operating_system': platform.system(), # "Windows"
            'os_version': platform.release(), # "7"
            'os_build': platform.version(), # "6.1.7601"

            #'physical_memory': #needs platform code

            'architecture': platform.machine(),
            'process_path': sys.executable,
        })

        if self.version:
            args['version'] = self.version
        if self.build:
            args['build'] = self.build

        args.update(self.args)
        filename = os.path.join(self.get_occurrence_folder(), args['UUID'])
        log.debug("Saving occurrence to %s", filename)

        with codecs.open(filename, "wb", encoding="utf-8") as f:
            f.write(occ.dump())

    def reportErrors(self):
        """
        Loads all saved occurrences from the folder, reports them, and deletes them one by one.
        """
        if self.disabled:
            return

        occs = []
        folder = self.get_occurrence_folder()
        uploader = SquashUploader(self.host, timeout=self.timeout)

        for filename in os.listdir(folder):
            path = os.path.join(folder, filename)

            try:
                log.debug("Reporting occurrence from %s", filename)
                with open(path, "rb") as f:
                    args = json.loads(f.read().decode('utf-8'))
                uploader.transmit(self.notifyPath, args)

            except urlerror.HTTPError as e:
                if e.code == 403: # Wrong API key
                    log.warn("Error: 403 Forbidden (Server refused API key). Aborting.")
                    break
                elif e.code == 422: # Something wrong with JSON data
                    log.warn("Error: 422 Unprocessable Entity (See Squash server error logs, exception UUID is %(UUID)s)", kw=args)
                else: # 500 Internal Server Error
                    log.warn("Error: %s (UUID %(UUID)s", e, kw=args)
                    log.warn("Data: \n%s\n", e.fp.read())

            except urlerror.URLError as e:
                if hasattr(e.args[0], 'errno') and e.args[0].errno == 10061: # socket.error: No server running here
                    log.warn("No server responded at %s. Aborting.", self.host)
                    break
                else:
                    log.warn("URLError: %s", e)

            except Exception as e:
                log.warn("%s while sending exception %s..." % (e, filename[:8]))

            os.unlink(path)

        return occs

    occurrence_folder = os.path.expanduser("~/.SquashOccurrences")

    def get_occurrence_folder(self):
        folder = os.path.join(self.occurrence_folder, self.APIKey)
        if not os.path.exists(folder):
            os.makedirs(folder)
        return folder
