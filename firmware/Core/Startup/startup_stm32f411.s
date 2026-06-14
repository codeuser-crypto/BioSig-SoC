/* startup_stm32f411.s - Minimal vector table + reset handler (ARM GCC). */
  .syntax unified
  .cpu cortex-m4
  .fpu softvfp
  .thumb

.global g_pfnVectors
.global Default_Handler

/* Linker-provided symbols */
.word _sidata        /* start of .data init values in flash */
.word _sdata         /* start of .data in RAM */
.word _edata         /* end of .data in RAM */
.word _sbss          /* start of .bss */
.word _ebss          /* end of .bss */
.word _estack        /* top of stack */

  .section .text.Reset_Handler
  .weak Reset_Handler
  .type Reset_Handler, %function
Reset_Handler:
  ldr   sp, =_estack          /* set stack pointer */

  /* copy .data from flash to RAM */
  movs  r1, #0
  b     LoopCopyDataInit
CopyDataInit:
  ldr   r3, =_sidata
  ldr   r3, [r3, r1]
  str   r3, [r0, r1]
  adds  r1, r1, #4
LoopCopyDataInit:
  ldr   r0, =_sdata
  ldr   r3, =_edata
  adds  r2, r0, r1
  cmp   r2, r3
  bcc   CopyDataInit

  /* zero .bss */
  ldr   r2, =_sbss
  b     LoopFillZerobss
FillZerobss:
  movs  r3, #0
  str   r3, [r2], #4
LoopFillZerobss:
  ldr   r3, =_ebss
  cmp   r2, r3
  bcc   FillZerobss

  bl    SystemInit_Optional
  bl    main
LoopForever:
  b     LoopForever

  .weak SystemInit_Optional
  .thumb_func
SystemInit_Optional:
  bx lr

  .section .text.Default_Handler,"ax",%progbits
Default_Handler:
Infinite_Loop:
  b  Infinite_Loop
  .size Default_Handler, .-Default_Handler

/* Minimal vector table (extend as needed for full STM32F411 map) */
  .section .isr_vector,"a",%progbits
  .type g_pfnVectors, %object
g_pfnVectors:
  .word _estack
  .word Reset_Handler
  .word NMI_Handler
  .word HardFault_Handler
  .word MemManage_Handler
  .word BusFault_Handler
  .word UsageFault_Handler
  .word 0
  .word 0
  .word 0
  .word 0
  .word SVC_Handler
  .word DebugMon_Handler
  .word 0
  .word PendSV_Handler
  .word SysTick_Handler

  /* External interrupts (subset; others default) */
  .word 0    /* WWDG */
  /* ... reserved entries trimmed for brevity; real build uses CMSIS table */
  .word DMA2_Stream0_IRQHandler
  .word USART2_IRQHandler

/* Weak aliases to Default_Handler */
  .weak NMI_Handler
  .thumb_set NMI_Handler,Default_Handler
  .weak HardFault_Handler
  .thumb_set HardFault_Handler,Default_Handler
  .weak MemManage_Handler
  .thumb_set MemManage_Handler,Default_Handler
  .weak BusFault_Handler
  .thumb_set BusFault_Handler,Default_Handler
  .weak UsageFault_Handler
  .thumb_set UsageFault_Handler,Default_Handler
  .weak SVC_Handler
  .thumb_set SVC_Handler,Default_Handler
  .weak DebugMon_Handler
  .thumb_set DebugMon_Handler,Default_Handler
  .weak PendSV_Handler
  .thumb_set PendSV_Handler,Default_Handler
  .weak SysTick_Handler
  .thumb_set SysTick_Handler,Default_Handler
  .weak DMA2_Stream0_IRQHandler
  .thumb_set DMA2_Stream0_IRQHandler,Default_Handler
  .weak USART2_IRQHandler
  .thumb_set USART2_IRQHandler,Default_Handler
