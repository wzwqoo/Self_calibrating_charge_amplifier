# Self-calibrating charge amplifier

Tiny Tapeout sky130 analog project — a charge amplifier that measures its own
scale, instead of asking you to trust it.

![layout](docs/tt_um_wzw_qamp.png)

| | |
| --- | --- |
| top module | `tt_um_wzw_qamp` |
| tiles | 1×2 — 161.00 × 225.76 µm |
| analog pins | 2 — `ua[0]` VOUT, `ua[1]` SENSE (summing node — do not drive) |
| digital pins | 13 in, 0 out |
| supply | 1.8 V `VDPWR` only |

## How it works

A single-ended OTA integrates charge onto a 500 fF feedback cap. Two knobs on
the same summing node let the chip calibrate itself:

- **`qdac`** — a 6-bit split-capacitor DAC drops a *known* charge onto the
  virtual ground, `Q = C_sel · ΔV`. ΔV is selectable, so one array does two
  jobs: a 1.00 V step is the coarse calibration, a 204 mV step is the fine
  offset trim. Both are taps on one resistor divider off the supply, so ΔV is
  a **ratio**, not a rail — which is what makes the charge actually known.
- **`leakdac`** — a subthreshold current source giving 1 nA / 100 pA / 10 pA,
  for emulating sensor leakage.

`qdac` pins the absolute charge scale; `leakdac` then rides on that calibrated
scale to give an absolute current. The output is the whole ramp on `ua[0]` —
there's no on-chip comparator — so the measurement protocol lives in MCU
firmware and can change after tapeout.

See [docs/info.md](docs/info.md) for the pinout and test procedure.

## Status

Physical verification is clean: TT precheck 23/23, magic DRC 0 (full rule set),
KLayout FEOL/BEOL/offgrid 0, antenna 0, netgen LVS matches on every cell and
the top. 

Circuit simulation: the bias core starts at all five corners, the amplifier has
66 dB gain and 75° phase margin, and the measurement noise floor is 0.025 pA
against a 10 pA smallest range. The charge DAC delivers 211.3 fC full scale at
DNL 0.095 LSB, and that figure moves by 0.002 % across five corners and
−40…125 °C.
