# External imports
import argparse
import haml
import mako.template
import os
import tempfile
from bcbio import isatab

def get_arguments():
    args = argparse.ArgumentParser()
    args.add_argument(
        "my.isatab",
        type=file,
        help="The path to the ISA-TAB file."
        )
    args.add_argument(
        "output.html",
        type=argparse.FileType('w'),
        help="The path to the output HTML report file."
    )
    args.add_argument(
        '--verbose', '-v',
        action='store_true',
        help="Be verbose"
    )
    args.add_argument(
        '--debug', '-d', 
        action='store_true',
        help="Print debugging information"
    )
    args.parse_args()


def main(): 
    '''Run ISA-Report'''
    get_arguments()
    pass

if __name__ == '__main__':
    main()
