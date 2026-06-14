"""
packet_parser.py - Decode, CRC-verify, and sequence-check ECG packets.

Mirrors firmware/Core/Src/packet.c exactly so the same wire format is used on
both ends. Shared by uart_receiver.py, ble_receiver.py, and the unit tests.

PACKET FORMAT (10 bytes):
  [0] 0xAA  start1
  [1] 0x55  start2
  [2] sample low byte   (int16 LE, Q15 DSP output)
  [3] sample high byte
  [4..7] uint32 LE sequence number
  [8] CRC-8 over bytes [2..7], polynomial 0x07
  [9] 0xFF  end byte
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

PACKET_SIZE = 10
START_BYTE_1 = 0xAA
START_BYTE_2 = 0x55
END_BYTE = 0xFF
CRC8_POLY = 0x07

# DSP output Q15 -> mV. Q15 full scale (32768) maps to the +/-1.65 V ADC half
# window referred through the 5000x system gain back to the electrode.
# voltage_mv = sample * (3300 mV / 32768) / 5000
Q15_TO_MV = (3300.0 / 32768.0) / 5000.0


def crc8(data: bytes, poly: int = CRC8_POLY) -> int:
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ poly
            else:
                crc <<= 1
            crc &= 0xFF
    return crc


def build_packet(sample: int, seq: int) -> bytes:
    """Encode a packet (used by tests and the mock data source)."""
    payload = struct.pack("<hI", sample, seq & 0xFFFFFFFF)
    crc = crc8(payload)
    return bytes([START_BYTE_1, START_BYTE_2]) + payload + bytes([crc, END_BYTE])


@dataclass
class ParsedPacket:
    sample: int
    seq: int
    voltage_mv: float


def parse_packet(raw: bytes) -> ParsedPacket | None:
    """Parse a single 10-byte packet. Returns None if framing/CRC invalid."""
    if len(raw) != PACKET_SIZE:
        return None
    if raw[0] != START_BYTE_1 or raw[1] != START_BYTE_2 or raw[9] != END_BYTE:
        return None
    payload = raw[2:8]
    if crc8(payload) != raw[8]:
        return None
    sample, seq = struct.unpack("<hI", payload)
    return ParsedPacket(sample=sample, seq=seq, voltage_mv=sample * Q15_TO_MV)


class PacketStream:
    """Stateful byte-stream demuxer with sync hunting and stats tracking."""

    def __init__(self):
        self.buf = bytearray()
        self.last_seq: int | None = None
        self.total = 0
        self.dropped = 0
        self.errors = 0

    def feed(self, data: bytes):
        """Append bytes; yield ParsedPacket for each complete valid packet."""
        self.buf += data
        while len(self.buf) >= PACKET_SIZE:
            idx = self.buf.find(bytes([START_BYTE_1, START_BYTE_2]))
            if idx == -1:
                # No sync in buffer; keep only the last trailing byte that
                # could be a partial 0xAA.
                self.buf = self.buf[-1:]
                return
            if idx > 0:
                del self.buf[:idx]
            if len(self.buf) < PACKET_SIZE:
                return
            chunk = bytes(self.buf[:PACKET_SIZE])
            pkt = parse_packet(chunk)
            if pkt is None:
                # Bad CRC/framing: drop just the first sync byte and re-hunt.
                self.errors += 1
                del self.buf[:1]
                continue
            del self.buf[:PACKET_SIZE]
            self.total += 1
            if self.last_seq is not None:
                gap = (pkt.seq - self.last_seq - 1) & 0xFFFFFFFF
                if gap < 0x80000000:  # ignore implausible backward jumps
                    self.dropped += gap
            self.last_seq = pkt.seq
            yield pkt

    @property
    def loss_pct(self) -> float:
        denom = self.total + self.dropped
        return 100.0 * self.dropped / denom if denom else 0.0

    def stats(self) -> dict:
        return {
            "total": self.total,
            "dropped": self.dropped,
            "errors": self.errors,
            "loss_pct": round(self.loss_pct, 3),
        }
