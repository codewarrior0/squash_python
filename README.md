
Squash Client Library: Python (2.7/3.2)
=========================================================

This client library reports exceptions to Squash, the Squarish exception
reporting and management system.

Documentation
-------------

Comprehensive documentation is written in ReST-formatted comments
throughout the source. To view this documentation as an HTML site, run sphinx
with `(cd doc; make html)`. If sphinx is not installed, run `pip install sphinx`.
The starting HTML file is at `doc/_build/html/index.html`.

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

Unpack the source distribution, then run `python setup.py install` to
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

.. tip: Use `git rev-parse` to translate a commit-ish (such as a branch or tag name)
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
  build. This ought to be a commit's SHA-1 hash, but
  any commit-ish that can identify a revision is accepted.

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

The `squash_python` module also installs two command line scripts called `squash_release`
and `squash_tester`.

You *must* use `squash_release` to notify Squash of a new deployment. Run `squash_release` to
have it print its usage information.

You can use `squash_tester` to test your Squash integration, or as a template to integrating
Squash into your own project. The easiest way to use `squash_tester` is to
run the Squash web server locally on port 3000, and set the environment variable
`SQUASH_TESTER_API_KEY` to the API key of a project you create in your local web
server. Once that is done, you may run `squash_tester` to report an uncaught exception, or
run `squash_tester signal` to report an unhandled signal.

If the server is running elsewhere, you may set the environment variable SQUASH_TESTER_HOST
 to the method, host and port of the server (e.g. "https://squash.example.com:3000")


