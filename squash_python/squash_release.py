"""
    squash_release
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
from datetime import datetime
import os
import subprocess
import sys

import squash_python

import logging
logging.basicConfig(level=logging.INFO)

def main():
    argv = sys.argv
    parser = argparse.ArgumentParser(description="Notify a Squash server of a new deployment. This associates the version and/or build number with a Git revision ID")

    parser.add_argument('-o', '--open-timeout', type=int, dest='timeout', help="HTTP connection timeout", )
    parser.add_argument('-t', '--read-timeout', type=int, dest='timeout', help="HTTP connection timeout (same as -o, provided for compatibility)")
    #parser.add_argument('-k', '--[no-]skip-verification', help="Do not perform SSL peer verification")
    parser.add_argument('-p', '--project-dir', help="Specify a custom project directory to use for current revision (default current directory)")
    parser.add_argument('-r', '--revision', help="Specify a code revision that was deployed (default current revision)")
    parser.add_argument('-b', '--build', help="Specify a machine-readable build number that was deployed")
    parser.add_argument('-v', '--product-version', dest='version', help="Specify a human-readable version that was deployed. If not specified, use the build number.")
    parser.add_argument('host', help="The host and port of the machine running the Squash server")
    parser.add_argument('api_key', help="The API key for this project")
    parser.add_argument('environment', help="The name of the current deployment environment")

    parser.add_argument('-V', '--version', action='version', version="1.0.0")
    args = parser.parse_args(argv[1:])

    if args.project_dir is None:
        args.project_dir = os.getcwd()

    os.chdir(args.project_dir)

    if args.revision is None:
        args.revision = subprocess.check_output('git rev-parse HEAD'.split()).strip()

    uploader = squash_python.SquashUploader(args.host, timeout = args.timeout)
    uploader.transmit("/api/1.0/deploy.json",
                      {
                         'project'     : {'api_key' : args.api_key},
                         'environment' : {'name' : args.environment},
                         'deploy'      : {
                             'deployed_at' : datetime.now().isoformat(),
                             'revision'    : args.revision,
                             'build'       : args.build,
                             'version'     : args.version or args.build,
                         }
                     })

if __name__ == '__main__':
    main()
