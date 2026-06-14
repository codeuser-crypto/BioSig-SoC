#ifndef UART_TX_H
#define UART_TX_H

#include <stdint.h>

#define TX_BUF_SIZE   1024          /* circular TX buffer (bytes) */

void UART_TX_Init(uint32_t baud);   /* USART2 on PA2/PA3 */
int  UART_TX_Push(const uint8_t *data, uint16_t len);  /* returns bytes queued */
void UART_TX_PumpFromISR(void);     /* called from USART2 TXE/TC IRQ */

#endif /* UART_TX_H */
