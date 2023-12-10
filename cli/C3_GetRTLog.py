#!/usr/bin/env python3
import argparse
import logging
import sys
import time
from c3 import C3
from c3 import rtlog


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('host', help='C3 panel IP address or host name')
    parser.add_argument('--password', help='Password')
    args = parser.parse_args()

    print("Connecting to %s" % args.host)
    panel = C3(args.host)
    panel.log.addHandler(logging.StreamHandler(sys.stdout))
    panel.log.setLevel(logging.DEBUG)

    if panel.connect(args.password):
        try:
            while True:
                last_record_is_status = False
                records = []

                if not panel.is_connected():
                    panel.connect(args.password)

                try:
                    records = panel.get_rt_log()
                except ConnectionError as ex:
                    print(f"Error retrieving RT logs: {ex}")
                    panel.disconnect()

                for record in records:
                    print(repr(record))
                    if isinstance(record, rtlog.DoorAlarmStatusRecord):
                        last_record_is_status = True

                if last_record_is_status:
                    time.sleep(9)

                time.sleep(1)
        except KeyboardInterrupt:
            pass

    panel.disconnect()


if __name__ == "__main__":
    main()
