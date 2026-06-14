"""
ble_receiver.py - Receive ECG packets over BLE (Nordic UART Service) using bleak.

The firmware/BLE module exposes a Nordic UART Service (NUS); this client
subscribes to the TX characteristic notifications, runs the bytes through the
same PacketStream parser used by the UART path, and bridges to the dashboard
WebSocket.

Usage:
  python ble_receiver.py --name BioSigSoC
  python ble_receiver.py --address AA:BB:CC:DD:EE:FF
"""

from __future__ import annotations

import argparse
import asyncio
import json

from packet_parser import PacketStream

try:
    from bleak import BleakClient, BleakScanner
except Exception:  # pragma: no cover
    BleakClient = None
    BleakScanner = None

try:
    import websockets
except Exception:  # pragma: no cover
    websockets = None

# Nordic UART Service UUIDs
NUS_TX_CHAR = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # device -> host notify


class BLEBridge:
    def __init__(self):
        self.stream = PacketStream()
        self.clients: set = set()

    async def ws_handler(self, ws):
        self.clients.add(ws)
        try:
            async for _ in ws:
                pass
        finally:
            self.clients.discard(ws)

    async def push(self, pkt):
        if not self.clients:
            return
        msg = json.dumps({"v": round(pkt.voltage_mv, 4), "seq": pkt.seq,
                          "stats": self.stream.stats()})
        await asyncio.gather(*[c.send(msg) for c in self.clients],
                             return_exceptions=True)

    def make_notify_handler(self, loop):
        def handler(_char, data: bytearray):
            for pkt in self.stream.feed(bytes(data)):
                asyncio.run_coroutine_threadsafe(self.push(pkt), loop)
        return handler


async def run(args):
    if BleakClient is None:
        raise RuntimeError("bleak not installed: pip install bleak")

    bridge = BLEBridge()
    loop = asyncio.get_event_loop()

    if websockets is not None:
        await websockets.serve(bridge.ws_handler, "localhost", 8765)
        print("[ws] serving ws://localhost:8765")

    address = args.address
    if address is None:
        print(f"[ble] scanning for '{args.name}' ...")
        dev = await BleakScanner.find_device_by_name(args.name, timeout=10.0)
        if dev is None:
            raise RuntimeError(f"device '{args.name}' not found")
        address = dev.address

    print(f"[ble] connecting to {address}")
    async with BleakClient(address) as client:
        await client.start_notify(NUS_TX_CHAR, bridge.make_notify_handler(loop))
        print("[ble] subscribed; streaming...")
        while client.is_connected:
            await asyncio.sleep(1.0)
            s = bridge.stream.stats()
            print(f"[stats] total={s['total']} dropped={s['dropped']} "
                  f"errors={s['errors']} loss={s['loss_pct']}%")


def main():
    ap = argparse.ArgumentParser(description="ECG BLE receiver")
    ap.add_argument("--name", default="BioSigSoC", help="BLE advertised name")
    ap.add_argument("--address", help="BLE MAC/UUID (skip scan)")
    args = ap.parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\n[ble] stopped")


if __name__ == "__main__":
    main()
