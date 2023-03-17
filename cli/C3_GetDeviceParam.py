#!/usr/bin/env python3

from c3 import C3
from c3.utils import C3DateTime
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
        params = panel.get_device_param(["~SerialNumber",
                                         "LockCount",
                                         "ReaderCount",
                                         "AuxInCount",
                                         "AuxOutCount",
                                         "DateTime"])

        for k in params.keys():
            if k == "DateTime":
                print("- %s: %s" % (k, C3DateTime.from_value(int(params.get(k))).isoformat()))
            else:
                print("- %s: %s" % (k, params.get(k)))

    panel.disconnect()


if __name__ == "__main__":
    main()
