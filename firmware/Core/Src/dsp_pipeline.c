/*
 * dsp_pipeline.c - Real-time DSP on Cortex-M4 (CMSIS-DSP, Q15).
 *
 * Per 128-sample block (triggered on DMA half/complete):
 *   Stage 1: ADC counts -> Q15 (remove 2048 mid-rail bias, scale)
 *   Stage 2: 60 Hz IIR notch (Q15 biquad cascade)
 *   Stage 3: 50 Hz IIR notch (Q15 biquad cascade)
 *   Stage 4: 0.5-40 Hz bandpass FIR (128-tap Q15, SIMD via SMLAD)
 *   Stage 5: Pan-Tompkins R-peak detection -> heart_rate_bpm
 *   Stage 6: packetize + queue for UART/BLE TX
 *
 * Timing budget @168 MHz: ~132 us per block << 256 ms DMA refill. Measured
 * with DWT and stored in pipeline_cycles.
 */
#include "arm_math.h"
#include "filters.h"
#include "packet.h"
#include "dsp_pipeline.h"
#include "core_cm4.h"   /* DWT */

volatile uint32_t pipeline_cycles = 0;
volatile uint32_t sample_counter  = 0;
volatile float    heart_rate_bpm  = 0.0f;

#define BLOCK 128

static arm_fir_instance_q15 fir_bp_inst;
static q15_t fir_state[FIR_NUM_TAPS + BLOCK - 1];

static arm_biquad_casd_df1_inst_q15 notch_60hz_inst;
static arm_biquad_casd_df1_inst_q15 notch_50hz_inst;
static q15_t notch_60hz_state[4 * IIR_NUM_STAGES];
static q15_t notch_50hz_state[4 * IIR_NUM_STAGES];

static q15_t dsp_input_q15[BLOCK];
static q15_t dsp_after_notch[BLOCK];
static q15_t dsp_output_q15[BLOCK];

/* R-peak detector state (persists across blocks) */
static q15_t rp_prev[4] = {0, 0, 0, 0};
static float rp_integ = 0.0f;
static float rp_threshold = 0.0f;
static uint32_t rp_last_peak = 0;
static uint32_t rp_sample = 0;

void DSP_Pipeline_Init(void)
{
    arm_biquad_cascade_df1_init_q15(&notch_60hz_inst, IIR_NUM_STAGES,
                                    (q15_t *)notch_60hz_coeffs_q15,
                                    notch_60hz_state, IIR_POST_SHIFT);
    arm_biquad_cascade_df1_init_q15(&notch_50hz_inst, IIR_NUM_STAGES,
                                    (q15_t *)notch_50hz_coeffs_q15,
                                    notch_50hz_state, IIR_POST_SHIFT);
    arm_fir_init_q15(&fir_bp_inst, FIR_NUM_TAPS,
                     (q15_t *)fir_bp_coeffs_q15, fir_state, BLOCK);
}

static void detect_rpeaks(const q15_t *x, int n)
{
    for (int i = 0; i < n; i++) {
        /* derivative */
        float d = ((float)x[i] - (float)rp_prev[0]) * 0.25f;
        rp_prev[0] = rp_prev[1];
        rp_prev[1] = rp_prev[2];
        rp_prev[2] = rp_prev[3];
        rp_prev[3] = x[i];
        /* square + leaky moving integrator (~150 ms window) */
        float sq = d * d;
        rp_integ += (sq - rp_integ) / 75.0f;
        /* adaptive threshold */
        if (rp_integ > rp_threshold) rp_threshold = rp_integ;
        rp_threshold *= 0.9995f;       /* slow decay */

        rp_sample++;
        if (rp_integ > 0.5f * rp_threshold &&
            (rp_sample - rp_last_peak) > 100) {   /* 200 ms refractory @500Hz */
            if (rp_last_peak != 0) {
                float rr_s = (float)(rp_sample - rp_last_peak) / 500.0f;
                if (rr_s > 0.3f && rr_s < 2.0f)
                    heart_rate_bpm = 60.0f / rr_s;
            }
            rp_last_peak = rp_sample;
        }
    }
}

void DSP_Pipeline_Process(const uint16_t *adc_buf, uint8_t buf_half)
{
    uint32_t t_start = DWT->CYCCNT;
    const uint16_t *src = (buf_half == 1) ? adc_buf : adc_buf + BLOCK;

    /* Stage 1: ADC counts -> Q15 (remove 2048 mid-rail bias, <<3 scale) */
    for (int i = 0; i < BLOCK; i++) {
        int32_t val = ((int32_t)src[i] - 2048) << 3;
        if (val > 32767)  val = 32767;
        if (val < -32768) val = -32768;
        dsp_input_q15[i] = (q15_t)val;
    }

    /* Stage 2 & 3: notch 60 then 50 Hz */
    arm_biquad_cascade_df1_q15(&notch_60hz_inst, dsp_input_q15,
                               dsp_after_notch, BLOCK);
    arm_biquad_cascade_df1_q15(&notch_50hz_inst, dsp_after_notch,
                               dsp_after_notch, BLOCK);

    /* Stage 4: bandpass FIR */
    arm_fir_q15(&fir_bp_inst, dsp_after_notch, dsp_output_q15, BLOCK);

    /* Stage 5: R-peak detection */
    detect_rpeaks(dsp_output_q15, BLOCK);

    pipeline_cycles = DWT->CYCCNT - t_start;

    /* Stage 6: packetize + queue */
    for (int i = 0; i < BLOCK; i++)
        Packet_Send(dsp_output_q15[i], sample_counter++);
}
