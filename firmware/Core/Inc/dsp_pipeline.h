#ifndef DSP_PIPELINE_H
#define DSP_PIPELINE_H

#include <stdint.h>

extern volatile uint32_t pipeline_cycles;   /* DSP duration in CPU cycles */
extern volatile uint32_t sample_counter;    /* monotonic sample sequence */
extern volatile float    heart_rate_bpm;    /* updated by R-peak detector */

void DSP_Pipeline_Init(void);
void DSP_Pipeline_Process(const uint16_t *adc_buf, uint8_t buf_half);

#endif /* DSP_PIPELINE_H */
