"""Unit tests for the packet framing / CRC layer (packet_parser.py)."""
import struct

from packet_parser import (
    PacketStream,
    build_packet,
    crc8,
    parse_packet,
    PACKET_SIZE,
)


def test_valid_roundtrip():
    raw = build_packet(1234, 42)
    assert len(raw) == PACKET_SIZE
    pkt = parse_packet(raw)
    assert pkt is not None
    assert pkt.sample == 1234
    assert pkt.seq == 42


def test_negative_sample_roundtrip():
    raw = build_packet(-2000, 7)
    pkt = parse_packet(raw)
    assert pkt.sample == -2000


def test_crc_single_bit_error_detected():
    raw = bytearray(build_packet(100, 1))
    raw[3] ^= 0x01  # flip a bit in the sample high byte
    assert parse_packet(bytes(raw)) is None


def test_corrupt_start_byte_rejected():
    raw = bytearray(build_packet(100, 1))
    raw[0] = 0x00
    assert parse_packet(bytes(raw)) is None


def test_corrupt_end_byte_rejected():
    raw = bytearray(build_packet(100, 1))
    raw[9] = 0x00
    assert parse_packet(bytes(raw)) is None


def test_sequence_rollover():
    raw = build_packet(5, 0xFFFFFFFF)
    pkt = parse_packet(raw)
    assert pkt.seq == 0xFFFFFFFF


def test_batch_no_false_positives():
    stream = PacketStream()
    blob = b"".join(build_packet(i % 1000, i) for i in range(1000))
    got = list(stream.feed(blob))
    assert len(got) == 1000
    assert stream.errors == 0
    assert stream.dropped == 0
    assert [p.seq for p in got] == list(range(1000))


def test_dropped_packet_counted():
    stream = PacketStream()
    list(stream.feed(build_packet(0, 10)))
    # skip seq 11, 12 -> next is 13 -> 2 dropped
    list(stream.feed(build_packet(0, 13)))
    assert stream.dropped == 2


def test_resync_after_garbage():
    stream = PacketStream()
    garbage = b"\x12\x34\x56"
    good = build_packet(99, 1)
    got = list(stream.feed(garbage + good))
    assert len(got) == 1
    assert got[0].sample == 99


def test_split_packet_across_feeds():
    stream = PacketStream()
    raw = build_packet(77, 5)
    assert list(stream.feed(raw[:4])) == []
    got = list(stream.feed(raw[4:]))
    assert len(got) == 1
    assert got[0].sample == 77


def test_crc8_matches_reference_poly():
    # CRC-8 of a known payload (poly 0x07, init 0)
    payload = struct.pack("<hI", 0, 0)
    assert crc8(payload) == 0
