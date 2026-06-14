#ifndef PACKET_H
#define PACKET_H

#include <stdint.h>

#define PACKET_SIZE     10
#define START_BYTE_1    0xAA
#define START_BYTE_2    0x55
#define END_BYTE        0xFF
#define CRC8_POLY       0x07

void    Packet_Init(void);                          /* build CRC-8 table */
uint8_t CRC8_Compute(const uint8_t *data, uint8_t len);
void    Packet_Send(int16_t sample, uint32_t seq_num);

#endif /* PACKET_H */
