/*
 * timing.c - Cycle-accurate timing via the DWT cycle counter.
 *   TIMING_Init() once; TIMING_GetCycles() reads CYCCNT; convert with
 *   TIMING_CyclesToUs() (168 MHz core).
 */
#include "stm32f4xx.h"
#include "core_cm4.h"
#include "timing.h"

void TIMING_Init(void)
{
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;   /* enable trace */
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;              /* enable cycle counter */
}

uint32_t TIMING_GetCycles(void) { return DWT->CYCCNT; }

float TIMING_CyclesToUs(uint32_t cycles) { return cycles / 168.0f; }
