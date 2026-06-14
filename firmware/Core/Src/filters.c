/*
 * filters.c - Runtime helpers for the generated coefficient tables.
 *
 * The coefficient *data* lives in the auto-generated filters.h. This file
 * provides a tiny region-selection helper: in 60 Hz mains regions the 60 Hz
 * notch dominates, in 50 Hz regions the 50 Hz notch does. Both run in the
 * cascade regardless; this just lets the host configure which is emphasized.
 */
#include "filters.h"

typedef enum { MAINS_60HZ = 0, MAINS_50HZ = 1 } mains_region_t;

static mains_region_t g_region = MAINS_60HZ;

void Filters_SetRegion(int is_50hz) { g_region = is_50hz ? MAINS_50HZ : MAINS_60HZ; }
int  Filters_GetRegion(void)        { return (int)g_region; }
