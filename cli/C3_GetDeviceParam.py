#!/usr/bin/env python3
import argparse
import logging
import sys
from c3 import C3
from c3.utils import C3DateTime


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
            print("Device:")
            print(repr(panel))

            params = panel.get_device_param(["~ZKFPVersion",
                                             "~SerialNumber",
                                             "LockCount",
                                             "ReaderCount",
                                             "AuxInCount",
                                             "AuxOutCount",
                                             "DateTime"])

            for k in params:
                if k == "DateTime":
                    print("- %s: %s" % (k, C3DateTime.from_value(int(params.get(k))).isoformat()))
                else:
                    print("- %s: %s" % (k, params.get(k)))
    except Exception as e:
        print(f"Parameter retrieval failed: {e}")
    finally:
        panel.disconnect()


if __name__ == "__main__":
    main()
