#!/usr/bin/env python3
import argparse
import logging
import sys
from c3 import C3
from c3 import consts
from c3 import controldevice


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('host', help='C3 panel IP address or host name')
    parser.add_argument('--output', choices=['door', 'aux'], required=True, help='Output is door or auxiliary')
    parser.add_argument('--number', type=int, required=True, help='Door or auxiliary output number')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--open', action="store_true", help='Set state to normal open')
    group.add_argument('--close', action="store_true", help='Set state to closed')
    parser.add_argument('--duration', type=int, help='Duration to (temporarily) open the door')
    args = parser.parse_args()

    duration = 0
    if args.open:
        duration = args.duration or 255  # Use default open when no duration is specified

    print("Connecting to %s" % args.host)
    panel = C3(args.host)
    panel.log.addHandler(logging.StreamHandler(sys.stdout))
    panel.log.setLevel(logging.DEBUG)

    try:
        if panel.connect():
            operation = controldevice.ControlDeviceOutput(args.number,
                                                          consts.ControlOutputAddress.AUX_OUTPUT if args.output == 'aux'
                                                          else consts.ControlOutputAddress.DOOR_OUTPUT, duration)
            panel.control_device(operation)
    except Exception as e:
        print(f"Parameter retrieval failed: {e}")
    finally:
        panel.disconnect()


if __name__ == "__main__":
    main()
