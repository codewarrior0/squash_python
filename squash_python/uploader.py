"""
    uploader
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import json
try:
    import urllib2 as urlrequest
except ImportError:
    import urllib.request as urlrequest
import sys
import logging
log = logging.getLogger(__name__)

class SquashUploader(object):
    def __init__(self, host, timeout=None):
        """
        :param host: The host, port, and scheme of the Squash server (e.g. "https://squash.mycompany.com:3000")
        :type host: string
        :param timeout: Socket timeout in seconds. If none, uses :mod:`socket` default.
        """
        self.host = host
        self.timeout = timeout

    def transmit(self, location, args):
        """
        Convert the dictionary `args` into a json string and POST it to `location`. Raise `urllib2.HTTPError` if
        the HTTP server returns an error or `urllib2.URLError` if the connection failed.

        :param location: The path portion of the URL, with leading slash. (e.g. "/api/1.0/deploy.json")
        :type location: string

        :param args: The data to transmit. Will be json-encoded before being sent.
                     Any strings should either be `unicode` objects (`str` in python3)
                     or UTF-8 encoded `str` objects (`bytes` in python3)

        :type args: dict
        """
        args = dict(args)
        args['utf8'] = '\u2713'

        data = json.dumps(args)
        headers = { "Content-type": "application/json" ,
                    "Content-encoding": "utf-8",
                    "Accept-encoding": "utf-8",
                    }

        req = urlrequest.Request(self.host + location, data, headers)

        if self.timeout:
            response = urlrequest.urlopen(req, None, self.timeout)
        else:
            response = urlrequest.urlopen(req)

        code = response.code
        data = response.fp.read()

        log.info("Response status: %s\nResponse data: \n%s\n" % (code, data))


