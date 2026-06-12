"""Persistent record streams for the PC integration service.

The first backend is JSON Lines: one append-only file per protocol message
type. It keeps raw and derived records separate without adding dependencies to
the early service refactor; an Excel backend can be added behind the same
interface later.
"""

import io
import json
import os

from protocol import (
    CONTROL_COMMAND,
    CONTROL_STATUS,
    SENSOR_DATA,
    SLEEP_RESULT,
    ProtocolError,
    decode_message,
    validate_message,
)


RECORD_TYPES = (SENSOR_DATA, SLEEP_RESULT, CONTROL_COMMAND, CONTROL_STATUS)


class JsonlRecordStorage(object):
    """Append validated protocol messages to four JSONL record streams."""

    def __init__(self, base_dir):
        self.base_dir = os.path.abspath(base_dir)
        if not os.path.isdir(self.base_dir):
            os.makedirs(self.base_dir)

    def append_record(self, message):
        validate_message(message)
        return self.append(message["type"], message)

    def append(self, record_type, message):
        if record_type not in RECORD_TYPES:
            raise ProtocolError("unknown record type: {0}".format(record_type))
        validate_message(message, expected_type=record_type)

        path = self.path_for(record_type)
        with io.open(path, "a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(message, ensure_ascii=False, sort_keys=True) + "\n"
            )
        return path

    def append_sensor_data(self, message):
        return self.append(SENSOR_DATA, message)

    def append_sleep_result(self, message):
        return self.append(SLEEP_RESULT, message)

    def append_control_command(self, message):
        return self.append(CONTROL_COMMAND, message)

    def append_control_status(self, message):
        return self.append(CONTROL_STATUS, message)

    def read_records(self, record_type):
        if record_type not in RECORD_TYPES:
            raise ProtocolError("unknown record type: {0}".format(record_type))
        path = self.path_for(record_type)
        if not os.path.exists(path):
            return []

        records = []
        with io.open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(decode_message(line, validate=True))
        for record in records:
            validate_message(record, expected_type=record_type)
        return records

    def path_for(self, record_type):
        if record_type not in RECORD_TYPES:
            raise ProtocolError("unknown record type: {0}".format(record_type))
        return os.path.join(self.base_dir, "{0}.jsonl".format(record_type))


def default_record_dir(base_dir="records"):
    return os.path.abspath(base_dir)
