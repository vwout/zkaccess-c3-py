#!/usr/bin/env python3
import argparse
import logging
import sys

from c3 import C3, controldevice


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('host', help='C3 panel IP address or host name')
    parser.add_argument('--password', help='Password')
    args = parser.parse_args()

    print("Connecting to %s" % args.host)
    panel = C3(args.host)
    panel.log.addHandler(logging.StreamHandler(sys.stdout))
    panel.log.setLevel(logging.DEBUG)

    try:
        if panel.connect(args.password):
            panel.control_device(controldevice.ControlDeviceCancelAlarms())
    except Exception as e:
        print(f"Cancel alarms faied: {e}")
    finally:
        panel.disconnect()


if __name__ == "__main__":
    main()
