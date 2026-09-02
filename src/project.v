/*
 * Self-calibrating charge amplifier, for Tiny Tapeout sky130
 * (1x2 analog tile, 161.00 x 225.76 um).
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * This is a hard-macro analog submission: the GDS in gds/ is the design.
 * This stub exists only so the TT harness has a module to instantiate and
 * so precheck can confirm the power pins. There is no synthesisable logic
 * on this die and no clock of any kind - the only digital block, an
 * inverter strip, is purely combinational.
 *
 * Pinout
 *   ua[0]  VOUT     analog out  integrator output -> MCU ADC (12-bit)
 *   ua[1]  SENSE    analog in   summing node / virtual ground, 0.90 V.
 *                               Piezo MEMS sensor input, <10 pF; leave open
 *                               for self-test.  DO NOT DRIVE IT.  The 0.90 V
 *                               reference is generated on die by a divider
 *                               (integ_slim XRVA/XRVB) and is not pinned out.
 *   ui[0]  B0       in          charge-DAC code bit 0 (LSB)
 *   ui[1]  B1       in
 *   ui[2]  B2       in
 *   ui[3]  B3       in
 *   ui[4]  B4       in
 *   ui[5]  B5       in          charge-DAC code bit 5 (MSB)
 *   ui[6]  RST      in          integrator reset - hold high through power-up
 *   ui[7]  TRIGC    in          fire cal step,  ACTIVE HIGH (st -> vcal,
 *                               1.0018 V - a divider tap, NOT the 1.8 V rail)
 *   uio[0] TRIGT    in          fire trim step, ACTIVE HIGH (st -> vtrim,
 *                               0.2038 V - the same divider, 4.9x finer)
 *   uio[1] TRIGN    in          step pull-down, ACTIVE HIGH = idle (st -> VSS)
 *   uio[2] S0       in          leak DAC decade select, 1 nA
 *   uio[3] S1       in          leak DAC decade select, 100 pA
 *   uio[4] S2       in          leak DAC decade select, 10 pA
 *
 * All three strobes are ACTIVE HIGH and exactly one is asserted at a time.
 * Stepping `st` to the 1.8 V rail was the RETIRED behaviour: the leg switches
 * are NMOS, so a plate stops at Vdd - Vt and the delivered charge becomes a
 * function of a threshold - 22.8 % over corners and temperature, against
 * 0.002 % for the divider tap.  That change is the whole calibration.
 *
 * The b0..b5 complements are generated ON DIE by invstrip_v3, unlike V1
 * where the complements had to be driven from outside. Only b0..b5 are
 * needed on ui.
 *
 * S0/S1/S2 are three independent NMOS pass taps on one resistor divider.
 * They are one-hot BY CONVENTION ONLY - asserting two shorts two nodes of
 * the divider together. Firmware must enforce it.
 *
 * uo_out, uio_out and uio_oe are unused and are tied to VGND *in the GDS*
 * (a single met4 strap over the contiguous output pin block, dropped to the
 * VGND bus track). They are driven to 0 here as well so the Verilog view
 * agrees with the layout.
 *
 * uo_out[0] is included in that strap as of 2026-08-11. It had been left out
 * because the earlier tiles drove it with a comparator, which v3 moved off
 * chip; the strap now runs to x = 94.80 um and covers it. Verilog and layout
 * agree - all eight uo_out bits are 0 in both views.
 */

`default_nettype none

module tt_um_wzw_qamp (
    input  wire       VGND,
    input  wire       VDPWR,    // 1.8 V analog/core supply
    input  wire [7:0] ui_in,    // B0..B5, RST, TRIGC
    output wire [7:0] uo_out,   // unused - tied low
    input  wire [7:0] uio_in,   // [4:0] = TRIGT TRIGN S0 S1 S2
    output wire [7:0] uio_out,  // unused - tied low
    output wire [7:0] uio_oe,   // all inputs -> 0
    inout  wire [7:0] ua,       // ua[1:0] used; ua[7:2] unconnected
    input  wire       ena,
    input  wire       clk,      // unused - no clocked digital on this die
    input  wire       rst_n     // unused - integrator reset is ui_in[6]
);

  assign uo_out  = 8'b0;
  assign uio_out = 8'b0;
  assign uio_oe  = 8'b0;

  // Silence unused-input warnings without inferring logic.
  wire _unused = &{ena, clk, rst_n, ui_in, uio_in[7:5], 1'b0};

endmodule
