#ifndef TIMING_H
#define TIMING_H

#include <stdint.h>

void     TIMING_Init(void);
uint32_t TIMING_GetCycles(void);
float    TIMING_CyclesToUs(uint32_t cycles);

#endif /* TIMING_H */
