#!/usr/bin/env python3
import argparse
import logging
import sys
import time

from c3 import C3, rtlog


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

                print(f"Door status: {[repr(panel.lock_status(i+1)) for i in range(panel.nr_of_locks)]}:")
                print(f"Aux status: {[repr(panel.aux_out_status(i+1)) for i in range(panel.nr_aux_out)]}:")

                if last_record_is_status:
                    time.sleep(9)

                print("-" * 25)

                time.sleep(1)
        except KeyboardInterrupt:
            pass

    panel.disconnect()


if __name__ == "__main__":
    main()
