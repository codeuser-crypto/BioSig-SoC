# ARM GCC cross-compiler Makefile for STM32F411 (BioSig SoC firmware)
#
# Requires: arm-none-eabi-gcc toolchain, CMSIS core + CMSIS-DSP headers/libs.
# Place CMSIS under firmware/CMSIS (Include, DSP/Include, Device/...) and a
# linker script STM32F411RETX_FLASH.ld in this directory.

CC      = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE    = arm-none-eabi-size

CFLAGS  = -mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard
CFLAGS += -mthumb -O2 -Wall -Wextra -ffunction-sections -fdata-sections
CFLAGS += -DSTM32F411xE -DARM_MATH_CM4 -D__FPU_PRESENT=1
CFLAGS += -ICore/Inc -ICMSIS/Include -ICMSIS/DSP/Include
CFLAGS += -ICMSIS/Device/ST/STM32F4xx/Include

LDFLAGS = -TSTM32F411RETX_FLASH.ld --specs=nosys.specs -Wl,--gc-sections
LDFLAGS += -LCMSIS/DSP/Lib -larm_cortexM4lf_math

SRCS = Core/Src/main.c Core/Src/adc_dma.c Core/Src/dsp_pipeline.c \
       Core/Src/filters.c Core/Src/uart_tx.c Core/Src/packet.c \
       Core/Src/timing.c
ASM  = Core/Startup/startup_stm32f411.s

TARGET = biosignal_soc.elf

.PHONY: all clean flash

all: $(TARGET)

$(TARGET): $(SRCS) $(ASM)
	$(CC) $(CFLAGS) $(SRCS) $(ASM) $(LDFLAGS) -o $@
	$(SIZE) $@
	$(OBJCOPY) -O binary $@ biosignal_soc.bin

flash: biosignal_soc.bin
	st-flash write biosignal_soc.bin 0x08000000

clean:
	rm -f $(TARGET) biosignal_soc.bin
