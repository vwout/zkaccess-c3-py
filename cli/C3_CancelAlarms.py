#!/usr/bin/env python3
import argparse
import logging
import sys
from c3 import C3
from c3 import controldevice


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('host', help='C3 panel IP address or host name')
    args = parser.parse_args()

    print("Connecting to %s" % args.host)
    panel = C3(args.host)
    panel.log.addHandler(logging.StreamHandler(sys.stdout))
    panel.log.setLevel(logging.DEBUG)

    try:
        if panel.connect():
            panel.control_device(controldevice.ControlDeviceCancelAlarms())
    except Exception as e:
        print(f"Cancel alarms faied: {e}")
    finally:
        panel.disconnect()


if __name__ == "__main__":
    main()
