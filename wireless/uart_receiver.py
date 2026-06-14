"""
uart_receiver.py - Receive and decode ECG packets from the STM32 over UART/USB,
and re-broadcast each sample to web dashboard clients over a WebSocket.

Usage:
  python uart_receiver.py --port COM5 --baud 115200
  python uart_receiver.py --mock          # generate synthetic ECG, no hardware
  python uart_receiver.py --mock --no-ws  # mock + just print stats

Serial: 115200 8N1, no flow control, 100 ms read timeout.
WebSocket server: ws://localhost:8765  (dashboard connects here)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import time

from packet_parser import PacketStream, build_packet
from data_logger import DataLogger

try:
    import serial  # pyserial
except Exception:  # pragma: no cover
    serial = None

try:
    import websockets
except Exception:  # pragma: no cover
    websockets = None

SAMPLE_RATE = 500


class ECGReceiver:
    def __init__(self, logger: DataLogger | None = None):
        self.stream = PacketStream()
        self.clients: set = set()
        self.logger = logger
        self.last_rate_t = time.time()
        self.rate_count = 0
        self.sample_rate_est = 0.0

    async def broadcast(self, pkt):
        self.rate_count += 1
        now = time.time()
        if now - self.last_rate_t >= 1.0:
            self.sample_rate_est = self.rate_count / (now - self.last_rate_t)
            self.rate_count = 0
            self.last_rate_t = now
        if self.logger:
            self.logger.log(pkt.seq, pkt.sample, pkt.voltage_mv)
        if not self.clients:
            return
        msg = json.dumps({
            "v": round(pkt.voltage_mv, 4),
            "seq": pkt.seq,
            "stats": {**self.stream.stats(),
                      "sps": round(self.sample_rate_est, 1)},
        })
        await asyncio.gather(*[c.send(msg) for c in self.clients],
                             return_exceptions=True)

    async def ws_handler(self, ws):
        self.clients.add(ws)
        try:
            async for _ in ws:  # ignore inbound; keep connection open
                pass
        finally:
            self.clients.discard(ws)


async def serial_source(recv: ECGReceiver, port: str, baud: int):
    if serial is None:
        raise RuntimeError("pyserial not installed; use --mock")
    ser = serial.Serial(port, baud, timeout=0.1)
    print(f"[uart] reading {port} @ {baud}")
    loop = asyncio.get_event_loop()
    while True:
        data = await loop.run_in_executor(None, ser.read, 256)
        if data:
            for pkt in recv.stream.feed(data):
                await recv.broadcast(pkt)
        else:
            await asyncio.sleep(0.005)


async def mock_source(recv: ECGReceiver):
    """Generate a synthetic ECG, encode to packets, feed the same parser."""
    print("[mock] generating synthetic ECG @ 500 sps")
    seq = 0
    t = 0.0
    dt = 1.0 / SAMPLE_RATE
    rr = 60.0 / 72.0
    while True:
        phase = (t % rr)
        # crude PQRST in Q15 units
        r = 26000 * math.exp(-0.5 * ((phase - 0.0) / 0.012) ** 2)
        p = 2000 * math.exp(-0.5 * ((phase - (rr - 0.16)) / 0.025) ** 2)
        tw = 5000 * math.exp(-0.5 * ((phase - 0.22) / 0.06) ** 2)
        noise = int(150 * math.sin(2 * math.pi * 60 * t))
        sample = int(max(-32768, min(32767, r + p + tw + noise)))
        for pkt in recv.stream.feed(build_packet(sample, seq)):
            await recv.broadcast(pkt)
        seq += 1
        t += dt
        await asyncio.sleep(dt)


async def stats_printer(recv: ECGReceiver):
    while True:
        await asyncio.sleep(2.0)
        s = recv.stream.stats()
        print(f"[stats] total={s['total']} dropped={s['dropped']} "
              f"errors={s['errors']} loss={s['loss_pct']}% "
              f"sps={recv.sample_rate_est:.0f} clients={len(recv.clients)}")


async def main_async(args):
    logger = None
    if args.log:
        logger = DataLogger()
        print(f"[log] writing {logger.path}")
    recv = ECGReceiver(logger=logger)

    tasks = [asyncio.create_task(stats_printer(recv))]

    if not args.no_ws:
        if websockets is None:
            print("[warn] websockets not installed; running without WS server")
        else:
            server = await websockets.serve(recv.ws_handler, "localhost", 8765)
            print("[ws] serving ws://localhost:8765")
            tasks.append(asyncio.create_task(asyncio.Future()))  # keep alive
            _ = server

    if args.mock:
        tasks.append(asyncio.create_task(mock_source(recv)))
    else:
        tasks.append(asyncio.create_task(serial_source(recv, args.port, args.baud)))

    try:
        await asyncio.gather(*tasks)
    finally:
        if logger:
            logger.close()


def main():
    ap = argparse.ArgumentParser(description="ECG UART receiver + WS bridge")
    ap.add_argument("--port", default="COM5", help="serial port (e.g. COM5, /dev/ttyUSB0)")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--mock", action="store_true", help="synthetic source, no hardware")
    ap.add_argument("--no-ws", action="store_true", help="disable WebSocket server")
    ap.add_argument("--log", action="store_true", help="log samples to CSV")
    args = ap.parse_args()
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\n[uart] stopped")


if __name__ == "__main__":
    main()
