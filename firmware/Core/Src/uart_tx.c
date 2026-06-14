/*
 * uart_tx.c - Interrupt-driven USART2 TX with a circular buffer.
 * USART2: PA2 (TX), PA3 (RX), AF7. Clocked from APB1 (42 MHz).
 * Never blocks: the DSP ISR pushes bytes; the TXE interrupt drains them.
 */
#include "stm32f4xx.h"
#include "uart_tx.h"

static uint8_t  tx_buf[TX_BUF_SIZE];
static volatile uint16_t tx_head = 0;   /* write index */
static volatile uint16_t tx_tail = 0;   /* read index  */

void UART_TX_Init(uint32_t baud)
{
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
    RCC->APB1ENR |= RCC_APB1ENR_USART2EN;

    /* PA2, PA3 to AF7 (USART2) */
    GPIOA->MODER &= ~((3U << (2 * 2)) | (3U << (3 * 2)));
    GPIOA->MODER |=  ((2U << (2 * 2)) | (2U << (3 * 2)));   /* alt func */
    GPIOA->AFR[0] |= (7U << (2 * 4)) | (7U << (3 * 4));

    /* baud: APB1 clock = 42 MHz; USARTDIV = fck / (16*baud) */
    USART2->BRR = (42000000UL + (baud / 2)) / baud;
    USART2->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_UE;

    NVIC_SetPriority(USART2_IRQn, 6);
    NVIC_EnableIRQ(USART2_IRQn);
}

int UART_TX_Push(const uint8_t *data, uint16_t len)
{
    int queued = 0;
    for (uint16_t i = 0; i < len; i++) {
        uint16_t next = (uint16_t)((tx_head + 1) % TX_BUF_SIZE);
        if (next == tx_tail) break;       /* buffer full: drop rest */
        tx_buf[tx_head] = data[i];
        tx_head = next;
        queued++;
    }
    USART2->CR1 |= USART_CR1_TXEIE;       /* enable TXE IRQ to start pump */
    return queued;
}

void UART_TX_PumpFromISR(void)
{
    if (USART2->SR & USART_SR_TXE) {
        if (tx_tail != tx_head) {
            USART2->DR = tx_buf[tx_tail];
            tx_tail = (uint16_t)((tx_tail + 1) % TX_BUF_SIZE);
        } else {
            USART2->CR1 &= ~USART_CR1_TXEIE;   /* nothing left: stop IRQ */
        }
    }
}

void USART2_IRQHandler(void)
{
    UART_TX_PumpFromISR();
}
