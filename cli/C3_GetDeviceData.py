#!/usr/bin/env python3
import argparse
import logging
import sys

from c3 import C3
from c3.utils import C3DateTime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('host', help='C3 panel IP address or host name')
    parser.add_argument('--password', help='Password')
    parser.add_argument('--table', help='Table to request')
    parser.add_argument('--field', nargs='+', help='Field name(s) to request')
    args = parser.parse_args()

    print("Connecting to %s" % args.host)
    panel = C3(args.host)
    panel.log.addHandler(logging.StreamHandler(sys.stdout))
    panel.log.setLevel(logging.DEBUG)

    try:
        if panel.connect(args.password):
            print("Device:")
            print(repr(panel))

            data = panel.get_device_data(args.table, args.field)
            for record in data:
                first = True
                for (field_name, field_value) in record.items():
                    print("%s %s: %s" % ("-" if first else " ", field_name, str(field_value)))
                    first = False

    except Exception as e:
        print(f"Parameter retrieval failed: {e}")
    finally:
        panel.disconnect()


if __name__ == "__main__":
    main()
