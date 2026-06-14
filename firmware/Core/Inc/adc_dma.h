#ifndef ADC_DMA_H
#define ADC_DMA_H

#include <stdint.h>

#define ADC_BUF_SIZE    256          /* total circular DMA buffer (samples) */
#define ADC_BLOCK_SIZE  128          /* one half = one DSP block */
#define ADC_SAMPLE_RATE 500U         /* Hz */
#define SYSTEM_CLOCK    168000000UL

extern volatile uint16_t adc_dma_buf[ADC_BUF_SIZE];
extern volatile uint8_t  dsp_buf_ready;   /* 0=none, 1=first half, 2=second half */

void ADC_DMA_Init(void);

#endif /* ADC_DMA_H */
