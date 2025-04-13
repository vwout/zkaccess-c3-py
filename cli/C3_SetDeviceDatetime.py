#!/usr/bin/env python3
import argparse
import logging
import sys
from datetime import datetime

from c3 import C3
from c3.utils import C3DateTime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("host", help="C3 panel IP address or host name")
    parser.add_argument("--password", help="Password")
    parser.add_argument(
        "--time",
        type=datetime.fromisoformat,
        help="Time to set as ISO format, e.g. YYYY-MM-DD HH:mm:ss (defaults to now)",
    )
    parser.add_argument(
        "--debug",
        action=argparse.BooleanOptionalAction,
        help="Enable verbose debug output",
    )
    args = parser.parse_args()

    print("Connecting to %s" % args.host)
    panel = C3(args.host)

    if args.debug:
        panel.log.addHandler(logging.StreamHandler(sys.stdout))
        panel.log.setLevel(logging.DEBUG)

    try:
        if panel.connect(args.password):
            print("Device:")
            print(repr(panel))

            panel.set_device_datetime(args.time or datetime.now())

            params = panel.get_device_param(["DateTime"])
            for k in params:
                if k == "DateTime":
                    print(
                        "- %s: %s"
                        % (k, C3DateTime.from_value(int(params.get(k))).isoformat())
                    )
    except Exception as e:
        print(f"Setting the date/time failed: {e}")
    finally:
        panel.disconnect()


if __name__ == "__main__":
    main()
