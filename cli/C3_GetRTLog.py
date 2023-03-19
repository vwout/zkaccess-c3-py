#!/usr/bin/env python3
import argparse
import logging
import sys
import time
from c3 import C3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('host', help='C3 panel IP address or host name')
    args = parser.parse_args()

    print("Connecting to %s" % args.host)
    panel = C3()
    panel.log.addHandler(logging.StreamHandler(sys.stdout))
    panel.log.setLevel(logging.DEBUG)

    if panel.connect(args.host):
        while True:
            records = panel.get_rt_log()
            for record in records:
                print(repr(record))

            time.sleep(2)

    panel.disconnect()


if __name__ == "__main__":
    main()
