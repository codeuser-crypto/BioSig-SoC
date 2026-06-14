/*
 * main.c - BioSig SoC firmware entry point.
 *
 * Brings up the system clock, peripherals and DSP, then runs a tiny
 * super-loop: it sleeps in WFI and wakes on the DMA half/complete IRQ, which
 * flags a buffer half; the main loop runs the DSP block on that half and the
 * results are streamed out over USART2. Every 10 s a timing line is emitted.
 */
#include "stm32f4xx.h"
#include "adc_dma.h"
#include "dsp_pipeline.h"
#include "packet.h"
#include "uart_tx.h"
#include "timing.h"

#include <stdio.h>
#include <string.h>

static void SystemClock_Config(void);

int main(void)
{
    SystemClock_Config();
    TIMING_Init();
    Packet_Init();
    UART_TX_Init(115200);
    DSP_Pipeline_Init();
    ADC_DMA_Init();

    uint32_t last_report = TIMING_GetCycles();

    for (;;) {
        if (dsp_buf_ready) {
            uint8_t half = dsp_buf_ready;
            dsp_buf_ready = 0;
            DSP_Pipeline_Process((const uint16_t *)adc_dma_buf, half);
        }

        /* Periodic timing report (~every 10 s at 168 MHz). */
        uint32_t now = TIMING_GetCycles();
        if ((uint32_t)(now - last_report) > 1680000000UL) {
            last_report = now;
            char line[96];
            int dsp_us = (int)TIMING_CyclesToUs(pipeline_cycles);
            int n = snprintf(line, sizeof(line),
                             "TIMING: DSP=%dus HR=%d BPM BUDGET=256000us\r\n",
                             dsp_us, (int)heart_rate_bpm);
            if (n > 0) UART_TX_Push((const uint8_t *)line, (uint16_t)n);
        }

        __WFI();   /* sleep until next interrupt */
    }
}

/*
 * Configure for 168 MHz from a 8 MHz HSE (Nucleo MCO).
 * PLL: M=8, N=336, P=2 -> 168 MHz; Q=7 -> 48 MHz for USB.
 * Flash 5 wait states, APB1 /4 (42 MHz), APB2 /2 (84 MHz).
 */
static void SystemClock_Config(void)
{
    RCC->CR |= RCC_CR_HSEON;
    while (!(RCC->CR & RCC_CR_HSERDY)) { }

    FLASH->ACR = FLASH_ACR_PRFTEN | FLASH_ACR_ICEN | FLASH_ACR_DCEN |
                 FLASH_ACR_LATENCY_5WS;

    RCC->PLLCFGR = (8U)            |        /* PLLM = 8 */
                   (336U << 6)     |        /* PLLN = 336 */
                   (0U << 16)      |        /* PLLP = 2 (00) */
                   (RCC_PLLCFGR_PLLSRC_HSE) |
                   (7U << 24);              /* PLLQ = 7 */

    RCC->CR |= RCC_CR_PLLON;
    while (!(RCC->CR & RCC_CR_PLLRDY)) { }

    RCC->CFGR |= RCC_CFGR_PPRE1_DIV4 | RCC_CFGR_PPRE2_DIV2;
    RCC->CFGR |= RCC_CFGR_SW_PLL;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_PLL) { }

    SystemCoreClock = 168000000UL;
}
