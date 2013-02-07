from __future__ import absolute_import, division, print_function, unicode_literals
import os
import subprocess
import sys
import signal
import time
import argparse

import squash_python

import logging
logging.basicConfig(level=logging.DEBUG)

class STBoomException(Exception):
    pass

class SquashTester(object):
    def main(self, argv):
        parser = argparse.ArgumentParser()

        parser.add_argument("-i", "--immediate", action="store_true",
                            help="""Send an occurrence for a non-fatal exception. The exception is sent immediately.
                            This is the default action.""")

        parser.add_argument("-c", "--crash", action="store_true", dest="hard",
                            help="""Send an occurrence for a fatal exception. The exception is written to disk
                            and sent the next time squash_tester is invoked. This overrides -i.""")

        parser.add_argument("-s", "--signal", action="store_true",
                            help="""Send an occurrence for an unhandled signal. The signal is handled as
                            with -c. This overrides -c and -i.""")

        parser.add_argument("-S", "--send", action="store_true", dest="send_only",
                            help="""Only send previously recorded exceptions.
                            """)

        parser.add_argument("-r", "--revision", action="store", dest='rev',
                            help="""Specify the Git revision to send with the exception. If not specified, uses
                            `git rev-parse HEAD` to get the revision from the current directory.""")

        parser.add_argument("-A", "--apikey",
                            help="""Specify the API key on the command line instead of through an environment variable.""")
        parser.add_argument("-e", "--env",
                            help="""Specify the name of the deployment environment to associate with this occurrence.
                            By default, uses "development".""")

        parser.epilog = "Before taking any other action, squash_tester reports all previously recorded errors."

        args = parser.parse_args(argv[1:])

        client = squash_python.get_client()
        client.APIKey = os.getenv('SQUASH_TESTER_API_KEY', args.apikey)
        if not client.APIKey:
            print("Error: Environment variable SQUASH_TESTER_API_KEY must be set.")
            parser.print_help()
            return -1

        client.environment = args.env or "development"
        client.host = os.getenv('SQUASH_TESTER_HOST', "http://localhost:3000")

        try:
            client.revision = args.rev or subprocess.check_output("git rev-parse HEAD".split()).strip().decode('ascii')
        except:
            print("Unable to determine source revision. Specify a revision with -r or chdir to a folder"
                  "containing a git repository. ")
            raise SystemExit


        print("Reporting errors to %s if needed, env=%s, apikey=%s..." % (client.host, client.environment, client.APIKey[:8]))
        client.reportErrors()
        client.hook()

        if args.signal:
            print("Raising SIGABRT...")
            os.kill(os.getpid(), signal.SIGABRT)
            print("Signal recorded. Run squash_tester again to send it.")
        elif args.hard:
            print("Raising exception...")
            raise_it()
            print("Exception recorded. Run squash_tester again to send it.")
        elif not args.send_only:
            print("Catching exception...", end="")
            try:
                raise_it()
            except Exception:
                client.excepthook(*sys.exc_info())
                print("Caught. Sending unsent errors...")
                client.reportErrors()
                print("Sent.")


def raise_it():
    raise STBoomException("At the boom the time will be %s seconds since the epoch. Boom!" % time.time())



def main():
    tester = SquashTester()
    tester.main(sys.argv)

