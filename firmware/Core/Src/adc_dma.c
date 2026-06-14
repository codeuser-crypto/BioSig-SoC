/*
 * adc_dma.c - Register-level ADC1 + DMA2 Stream0 configuration (pure CMSIS).
 * Target: STM32F411RE, 168 MHz Cortex-M4.
 *
 *  - ADC1 channel 0 (PA0), 12-bit, right-aligned, single conversion per trigger
 *  - External trigger: TIM2 TRGO rising edge at exactly 500 Hz
 *  - DMA2 Stream0 Channel0: periph->memory, circular, 16-bit, half-word
 *  - Buffer: adc_dma_buf[256]; half/complete IRQ -> double-buffered DSP blocks
 *  - VDDA = 3.3 V, VREF+ = 3.0 V (REF3030 external reference)
 */
#include "stm32f4xx.h"
#include "adc_dma.h"
#include "dsp_pipeline.h"

volatile uint16_t adc_dma_buf[ADC_BUF_SIZE];
volatile uint8_t  dsp_buf_ready = 0;

void ADC_DMA_Init(void)
{
    /* Step 1: clocks */
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_DMA2EN;
    RCC->APB2ENR |= RCC_APB2ENR_ADC1EN;
    RCC->APB1ENR |= RCC_APB1ENR_TIM2EN;

    /* Step 2: PA0 analog mode (MODER=11), no pull */
    GPIOA->MODER  |= (3U << (0 * 2));
    GPIOA->PUPDR  &= ~(3U << (0 * 2));

    /* Step 3: TIM2 TRGO at 500 Hz. APB1 timer clock = 84 MHz*2 = 168 MHz.
     * PSC=167 -> 1 MHz, ARR=1999 -> 1 MHz/2000 = 500 Hz. */
    TIM2->PSC  = 167U;
    TIM2->ARR  = 1999U;
    TIM2->CR2 &= ~TIM_CR2_MMS;
    TIM2->CR2 |= TIM_CR2_MMS_1;          /* MMS=010: TRGO on update event */

    /* Step 4: ADC1 */
    ADC->CCR  &= ~ADC_CCR_ADCPRE;
    ADC->CCR  |= ADC_CCR_ADCPRE_0;       /* /4 -> 42 MHz ADC clock */
    ADC1->CR1  = 0;                      /* 12-bit (RES=00), scan off */
    ADC1->CR2  = 0;
    ADC1->CR2 |= (6U << ADC_CR2_EXTSEL_Pos);  /* EXTSEL=0110 TIM2 TRGO */
    ADC1->CR2 |= ADC_CR2_EXTEN_0;        /* rising edge */
    ADC1->CR2 |= ADC_CR2_DMA | ADC_CR2_DDS;   /* DMA + continuous requests */
    ADC1->SMPR2 = (4U << (3 * 0));       /* ch0 sample time = 84 cycles */
    ADC1->SQR1  = 0;                     /* 1 conversion */
    ADC1->SQR3  = 0;                     /* rank1 = channel 0 */

    /* Step 5: DMA2 Stream0 Channel0 */
    DMA2_Stream0->CR = 0;
    while (DMA2_Stream0->CR & DMA_SxCR_EN) { /* wait disabled */ }
    DMA2_Stream0->CR |= (0U << DMA_SxCR_CHSEL_Pos);    /* channel 0 */
    DMA2_Stream0->CR |= DMA_SxCR_MINC;                 /* mem increment */
    DMA2_Stream0->CR |= DMA_SxCR_PSIZE_0;              /* periph 16-bit */
    DMA2_Stream0->CR |= DMA_SxCR_MSIZE_0;              /* mem 16-bit */
    DMA2_Stream0->CR |= DMA_SxCR_CIRC;                 /* circular */
    /* DIR=00 periph->mem (default) */
    DMA2_Stream0->CR |= DMA_SxCR_HTIE | DMA_SxCR_TCIE; /* half + complete IRQ */
    DMA2_Stream0->NDTR = ADC_BUF_SIZE;
    DMA2_Stream0->PAR  = (uint32_t)&ADC1->DR;
    DMA2_Stream0->M0AR = (uint32_t)adc_dma_buf;

    /* Step 6: NVIC */
    NVIC_SetPriority(DMA2_Stream0_IRQn, 5);
    NVIC_EnableIRQ(DMA2_Stream0_IRQn);

    /* Step 7: enable DMA, ADC, then start the trigger timer */
    DMA2_Stream0->CR |= DMA_SxCR_EN;
    ADC1->CR2 |= ADC_CR2_ADON;
    TIM2->CR1 |= TIM_CR1_CEN;
}

/* DMA2 Stream0 IRQ: signal which half of the buffer just filled. */
void DMA2_Stream0_IRQHandler(void)
{
    if (DMA2->LISR & DMA_LISR_HTIF0) {
        DMA2->LIFCR = DMA_LIFCR_CHTIF0;
        dsp_buf_ready = 1;                 /* first half ready */
    }
    if (DMA2->LISR & DMA_LISR_TCIF0) {
        DMA2->LIFCR = DMA_LIFCR_CTCIF0;
        dsp_buf_ready = 2;                 /* second half ready */
    }
}
