<!--
This file is used to generate your project datasheet.
-->

## How it works

This is a **charge amplifier that measures its own scale.** Most charge
amplifiers have a gain you must trust; this one carries the instrument that
calibrates it on the same die, and closes the loop on the demo board's MCU.
It is fully analog — there is no clocked logic anywhere on the tile.

**The core.** A single-ended OTA with its output integrating onto a 500 fF
MiM feedback cap, with a transmission-gate reset across it. The output appears
on `ua[0]`. **`ua[1]` is the summing node itself** — the virtual ground, held
at 0.90 V — so an external charge source can reach the one node where a charge
amplifier's gain is independent of the source's own capacitance. It is fenced
by grounded shields on both sides of the routing bus. The 0.90 V reference is
generated on chip, from two matched resistors across VDPWR.

**The sensor limit is a real spec, not a caution.** TT's analog path adds
~90 Ohm and <5 pF, and the summing node's own total is 0.4 pF, so anything you
hang on `ua[1]` adds directly to the noise gain `1 + Cin/Cf`. Measured charge
transfer: **0.997 at 1 pF, 0.989 at 10 pF, 0.958 at 47 pF** — a 47x change in
sensor capacitance moves the gain 4 %, which is the whole point of a charge
amplifier. Above ~100 pF it degrades fast, and at 1.4 nF (a PVDF film) the
transfer is 0.34 *and* the bandwidth collapses to 4.6 kHz. **Use a piezo MEMS
element, not a film.**

**Knob 1 — a known charge (`qdac`).** A 6-bit split-capacitor DAC (a 3-bit
MSB array of ≈27 fF units, a 3-bit LSB array behind a 28 fF bridge cap) has
its top plates on the virtual ground. Each bottom plate switches between a
stepped node `st` and VSS, so a code drops `Q = C_sel · ΔV` onto the summing
node — electrically indistinguishable from a real sensor event.

The trick is that **ΔV is selectable**, which makes one array do two jobs:

| strobe | `st` goes to | ΔV | what it is |
|---|---|---|---|
| `TRIGC` high | `vcal` | 1.00 V | **calibration** — large, known Q that pins the absolute charge scale |
| `TRIGT` high | `vtrim` | 204 mV | **offset trim** — same 64 codes, ~5× finer |
| `TRIGN` high | VSS | — | idle |

**All three strobes are active high**, and exactly one is asserted at a time.

Both step levels are taps on the same resistor divider off VDPWR, so ΔV is a
**resistor ratio times the supply** — not a rail, and not a threshold voltage.
That distinction is the whole calibration: the leg switches are NMOS, and an
NMOS can only pull a plate to `Vdd − Vt`, so stepping `st` to VDPWR would make
the delivered charge a function of `Vt`. Simulated over five corners and
−40…125 °C, a 1.8 V step moves the full-scale charge by **22.8 %**; the 1.0 V
tap moves it by **0.002 %**.

Full-scale is **211.3 fC** measured (213.8 fF of drawn array × `vcal` 1.0018 V
= 214.2 fC computed, 98.7 % of it) ≈ 0.42 V out, LSB ≈ 6.6 mV; the
trim step spans ≈ 43 fC ≈ 86 mV out, LSB ≈ 1.3 mV. On the parasitic
extraction of this layout, DNL over all 64 codes is **0.080 LSB**, INL 0.047,
monotonic. The bridge and LSB capacitors are sized against that extraction, so
the drawn array is deliberately not exactly binary. The whole extracted tile is
monotonic at every major code transition, with a worst DNL of 0.17 LSB.

`st` settles in 1.5–4.6 µs across five corners and −40…125 °C — the divider tap
is a 222 kΩ node with no local decoupling, so it droops during the fire and
recovers. The settled value is exact and the same everywhere to 0.16 %;
**wait ≥5 µs after the strobe before reading.** (Worst case is the fast-nfet /
slow-pfet corner at −40 °C, 4.58 µs. Reading at 3.4 µs there costs 0.1 %.)

**Knob 2 — a known leakage (`leakdac`).** A subthreshold NMOS current source
whose gate is tapped off a resistor divider, giving three decades — 1 nA,
100 pA, 10 pA — selected by `S0`/`S1`/`S2`. The taps were placed from an
*extracted* n·V_T of 38.1 mV, not the model's (whose prefactor was 2.8× off).
Driven into the 500 fF cap, those are ramps of 2 V/ms, 200 mV/ms and
20 mV/ms.

**Why both.** `qdac` fixes the absolute charge scale of the amplifier;
`leakdac` then rides on that calibrated scale to give an absolute current.
Neither alone is enough — the injector without the current source calibrates
gain but says nothing about the leakage floor, and the current source without
the injector has nothing to check itself against.

**What is not on this die.** The comparator and the single-slope counter were
moved off chip. `ua[0]` carries the *whole ramp* to the demo board's 12-bit
ADC rather than one threshold crossing, which costs nothing in area and means
**the measurement protocol is changeable after tapeout** — on a one-shot
shuttle that is worth a great deal. There is likewise no chopper: chopping is
already proven by the earlier 4×2 tile and would have cost ~90 µm of row that
this 1×2 does not have.

## How to test

Everything needs only the chip, a 1.8 V supply, and an MCU with an ADC and
13 GPIOs (an RP2040 was the target).

**1. Power-up and DC check.** `VDPWR` = 1.8 V, `ua[1]` open (or your sensor),
`ui[6]` (RST) high, and the step driver idle — `uio[1]` (TRIGN) **high**,
`ui[7]` (TRIGC) and `uio[0]` (TRIGT) **both low** (all three are active high).
Leave `S0`/`S1`/`S2` all low. `ua[0]` should sit at 0.90 V.

**2. Charge-injection transfer curve — the main self-test.** With RST
released, set a code on `ui[5:0]`, then drive TRIGN low and TRIGC high to
fire the calibration step. `ua[0]` should step down by `Q/Cf`. Return TRIGN
high and pulse RST between points. Sweep all 64 codes: they should fall on a
straight line whose slope gives the absolute fC-per-code, and hence `Cf`.
**The complements are generated on chip** — unlike the earlier 4×2 tile, you
do not need to drive them.

**3. Fine trim.** Repeat step 2 with TRIGT instead of TRIGC. Same codes,
~5× smaller steps — this is the offset knob.

**The trim is one-sided: calibrate at mid-code, not at code 0.** `st` steps
from VSS up to `vtrim`, so the array can only inject charge of one sign — code
0 is one *end* of the range, not its centre. Park the trim at code 32 when
measuring the nominal operating point; that leaves ±32 codes of correction in
either direction, which is ±28 mV referred to the amplifier input against a
simulated offset sigma of 7.2 mV (±3.9σ, 0 of 299 Monte Carlo draws outside).
Calibrating at code 0 gives you half a knob and a 50 % chance it points the
wrong way.

**4. Leakage ramp.** Assert exactly one of `S0`/`S1`/`S2`, release RST, and
sample `ua[0]` as it ramps. `I = Cf · dV/dt`, with `Cf` from step 2, so the
current comes out absolute. **Assert only one at a time** — the three taps
are independent pass transistors on one divider and asserting two shorts two
nodes of it together.

**5. The loop.** Steps 2 and 4 together are the point of the chip: run 2 to
calibrate the scale, run 4 to measure a current against that scale, and
repeat over temperature or supply to watch the calibration track.

## External hardware

- 1.8 V supply on `VDPWR`.
- **Nothing on `ua[1]` unless you want it.** It is the summing node: leave it
  open for self-test, or connect a piezo MEMS element (<10 pF) for sensing.
  Do **not** drive it — it is a virtual ground, not a reference input.
- **Average.** VCM is now an on-chip divider, so supply noise reaches the
  output at ~0.5x where an external reference filtered it away. It is
  uncorrelated shot to shot, so N readings average it down as 1/sqrt(N);
  N = 100 puts it well under the signal for every measurement below.
- An MCU with a 12-bit ADC on `ua[0]` and 13 GPIOs for `ui[7:0]` and
  `uio[4:0]`. The RP2040 on the TT demo board is sufficient and is where the
  digital half of the calibration loop lives.
