/*
 * packet.c - Binary packet framing for BLE/UART transmission.
 *
 * 10-byte packet:
 *   [0]=0xAA [1]=0x55 [2..3]=int16 sample LE [4..7]=uint32 seq LE
 *   [8]=CRC-8 over bytes [2..7] (poly 0x07) [9]=0xFF
 * 10 bytes * 500 sps = 5000 B/s = 40 kbps, well within 115200 baud.
 */
#include "packet.h"
#include "uart_tx.h"

static uint8_t crc8_table[256];

void Packet_Init(void)
{
    for (int i = 0; i < 256; i++) {
        uint8_t crc = (uint8_t)i;
        for (int b = 0; b < 8; b++)
            crc = (crc & 0x80) ? (uint8_t)((crc << 1) ^ CRC8_POLY)
                               : (uint8_t)(crc << 1);
        crc8_table[i] = crc;
    }
}

uint8_t CRC8_Compute(const uint8_t *data, uint8_t len)
{
    uint8_t crc = 0x00;
    for (uint8_t i = 0; i < len; i++)
        crc = crc8_table[crc ^ data[i]];
    return crc;
}

void Packet_Send(int16_t sample, uint32_t seq_num)
{
    uint8_t pkt[PACKET_SIZE];
    pkt[0] = START_BYTE_1;
    pkt[1] = START_BYTE_2;
    pkt[2] = (uint8_t)(sample & 0xFF);
    pkt[3] = (uint8_t)((sample >> 8) & 0xFF);
    pkt[4] = (uint8_t)(seq_num & 0xFF);
    pkt[5] = (uint8_t)((seq_num >> 8) & 0xFF);
    pkt[6] = (uint8_t)((seq_num >> 16) & 0xFF);
    pkt[7] = (uint8_t)((seq_num >> 24) & 0xFF);
    pkt[8] = CRC8_Compute(&pkt[2], 6);
    pkt[9] = END_BYTE;

    UART_TX_Push(pkt, PACKET_SIZE);   /* non-blocking, circular buffer */
}
