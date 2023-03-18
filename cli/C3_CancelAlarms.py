#!/usr/bin/env python3

from c3 import C3
from c3 import controldevice
import argparse
import logging
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('host', help='C3 panel IP address or host name')
    args = parser.parse_args()

    print("Connecting to %s" % args.host)
    panel = C3()
    panel.log.addHandler(logging.StreamHandler(sys.stdout))
    panel.log.setLevel(logging.DEBUG)

    if panel.connect(args.host):
        panel.control_device(controldevice.ControlDeviceCancelAlarms())

    panel.disconnect()


if __name__ == "__main__":
    main()
