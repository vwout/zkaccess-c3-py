#!/usr/bin/env python3
import argparse
import logging
import sys
from c3 import C3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--interface', help='IP address of the interface to look for devices on')
    args = parser.parse_args()

    C3.log.addHandler(logging.StreamHandler(sys.stdout))
    C3.log.setLevel(logging.DEBUG)
    devices = C3.discover(args.interface)
    for device in devices:
        print("Found device:")
        for k in device:
            print("- %s: %s" % (k, device.get(k)))


if __name__ == "__main__":
    main()
