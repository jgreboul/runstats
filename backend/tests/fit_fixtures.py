from __future__ import annotations

import struct
from datetime import UTC, datetime

from fitparse.records import Crc

FIT_EPOCH = datetime(1989, 12, 31, tzinfo=UTC)


def build_activity_fit(
    *,
    start_time: datetime = datetime(2026, 6, 1, 14, 0, tzinfo=UTC),
    distance_meters: float = 10_000.0,
    duration_seconds: float = 1_800.0,
    include_optional: bool = True,
) -> bytes:
    data = bytearray()

    if include_optional:
        session_fields = [
            (2, 4, 0x86),
            (5, 1, 0x00),
            (6, 1, 0x00),
            (7, 4, 0x86),
            (8, 4, 0x86),
            (9, 4, 0x86),
            (11, 2, 0x84),
            (16, 1, 0x02),
            (17, 1, 0x02),
            (18, 1, 0x02),
            (22, 2, 0x84),
            (24, 1, 0x02),
        ]
        data.extend(_definition_message(0, 18, session_fields))
        data.extend(
            _data_message(
                0,
                "IBBIIIHBBBH B".replace(" ", ""),
                [
                    _fit_timestamp(start_time),
                    1,
                    0,
                    int(duration_seconds * 1000),
                    int(duration_seconds * 1000),
                    int(distance_meters * 100),
                    750,
                    145,
                    170,
                    168,
                    80,
                    32,
                ],
            )
        )
        data.extend(_lap_messages(start_time, duration_seconds, distance_meters))
    else:
        session_fields = [
            (2, 4, 0x86),
            (5, 1, 0x00),
            (7, 4, 0x86),
            (9, 4, 0x86),
        ]
        data.extend(_definition_message(0, 18, session_fields))
        data.extend(
            _data_message(
                0,
                "IBII",
                [
                    _fit_timestamp(start_time),
                    1,
                    int(duration_seconds * 1000),
                    int(distance_meters * 100),
                ],
            )
        )

    data.extend(_record_messages(start_time, duration_seconds, distance_meters))
    header = struct.pack("<BBHI4s", 14, 0x10, 2134, len(data), b".FIT")
    header += b"\x00\x00"
    checksum = Crc.calculate(header + data)
    return bytes(header + data + struct.pack("<H", checksum))


def _lap_messages(
    start_time: datetime,
    duration_seconds: float,
    distance_meters: float,
) -> bytes:
    lap_fields = [
        (2, 4, 0x86),
        (7, 4, 0x86),
        (8, 4, 0x86),
        (9, 4, 0x86),
        (15, 1, 0x02),
    ]
    half_duration = duration_seconds / 2.0
    half_distance = distance_meters / 2.0
    return b"".join(
        [
            _definition_message(1, 19, lap_fields),
            _data_message(
                1,
                "IIIIB",
                [
                    _fit_timestamp(start_time),
                    int(half_duration * 1000),
                    int(half_duration * 1000),
                    int(half_distance * 100),
                    140,
                ],
            ),
            _data_message(
                1,
                "IIIIB",
                [
                    _fit_timestamp(start_time) + int(half_duration),
                    int(half_duration * 1000),
                    int(half_duration * 1000),
                    int(half_distance * 100),
                    150,
                ],
            ),
        ]
    )


def _record_messages(
    start_time: datetime,
    duration_seconds: float,
    distance_meters: float,
) -> bytes:
    record_fields = [
        (253, 4, 0x86),
        (5, 4, 0x86),
        (78, 4, 0x86),
        (3, 1, 0x02),
        (4, 1, 0x02),
        (7, 2, 0x84),
        (73, 4, 0x86),
        (0, 4, 0x85),
        (1, 4, 0x85),
    ]
    start_timestamp = _fit_timestamp(start_time)
    middle_seconds = int(duration_seconds / 2.0)
    return b"".join(
        [
            _definition_message(2, 20, record_fields),
            _record_data(start_timestamp, 0.0, 0.0, 120),
            _record_data(
                start_timestamp + middle_seconds,
                distance_meters / 2.0,
                40.0,
                145,
            ),
            _record_data(
                start_timestamp + int(duration_seconds),
                distance_meters,
                80.0,
                155,
            ),
        ]
    )


def _record_data(
    timestamp: int,
    distance_meters: float,
    altitude_meters: float,
    heart_rate: int,
) -> bytes:
    return _data_message(
        2,
        "IIIBBHIii",
        [
            timestamp,
            int(distance_meters * 100),
            int((altitude_meters + 500) * 5),
            heart_rate,
            168,
            260,
            3100,
            505_314_000,
            -1_497_771_000,
        ],
    )


def _definition_message(
    local_message_number: int,
    global_message_number: int,
    fields: list[tuple[int, int, int]],
) -> bytes:
    payload = bytearray([0x40 | local_message_number, 0, 0])
    payload.extend(struct.pack("<HB", global_message_number, len(fields)))
    for field_number, size, base_type in fields:
        payload.extend(struct.pack("<BBB", field_number, size, base_type))
    return bytes(payload)


def _data_message(
    local_message_number: int,
    fmt: str,
    values: list[int],
) -> bytes:
    return bytes([local_message_number]) + struct.pack(f"<{fmt}", *values)


def _fit_timestamp(timestamp: datetime) -> int:
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return int((timestamp.astimezone(UTC) - FIT_EPOCH).total_seconds())
