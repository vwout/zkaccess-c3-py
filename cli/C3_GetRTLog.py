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
    args = parser.parse_args()

    print("Connecting to %s" % args.host)
    panel = C3(args.host)
    panel.log.addHandler(logging.StreamHandler(sys.stdout))
    panel.log.setLevel(logging.DEBUG)

    if panel.connect():
        try:
            while True:
                last_record_is_status = False

                records = panel.get_rt_log()
                for record in records:
                    print(repr(record))
                    if isinstance(record, rtlog.DoorAlarmStatusRecord):
                        last_record_is_status = True

                if last_record_is_status:
                    time.sleep(10)
        except KeyboardInterrupt:
            pass

    panel.disconnect()


if __name__ == "__main__":
    main()
