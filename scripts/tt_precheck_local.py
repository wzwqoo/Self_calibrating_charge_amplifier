#!/usr/bin/env python3
"""Local re-implementation of the TT precheck gates that do not need the
full tt-support-tools install, run against gds/ + lef/ + info.yaml.

Logic mirrors TinyTapeout/tt-support-tools precheck/precheck.py and
precheck/tech_data.py as of 2026-08-04:
  * boundary_check   - one top cell, prBoundary covers the template DIEAREA,
                       nothing outside it
  * forbidden layers - met5 (TT's power grid owns it)
  * cell_name_check  - no '#' or '/' in any cell name
  * analog_pin_check - metal adjacent to ua[n] iff n < analog_pins AND the
                       pinout description is non-empty
  * power_pin_check  - VGND/VDPWR in Verilog and LEF, correct USE class,
                       VAPWR present iff uses_vapwr

This does not replace the real precheck (no magic/KLayout DRC decks here);
it catches the structural failures early, before a submission round-trip.
"""
import os, re, sys

import gdstk
import yaml

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOP = "tt_um_wzw_qamp"
GDS = os.path.join(HERE, "gds", f"{TOP}.gds")
LEF = os.path.join(HERE, "lef", f"{TOP}.lef")
VER = os.path.join(HERE, "src", "project.v")
YAML = os.path.join(HERE, "info.yaml")
DEF = os.path.join(HERE, "tt_analog_1x2.def")

MET4 = (71, 20)
VIA3 = (70, 44)
MET5 = [(72, 20), (72, 5), (72, 16)]
PRBOUNDARY = (235, 4)

fails, passes = [], []


def check(name, ok, detail=""):
    (passes if ok else fails).append(f"{name}: {detail}")
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def analog_pin_rects(uses_vapwr):
    """tech_data.analog_pin_rects for sky130A."""
    for n in range(8):
        x1 = (136.17 if uses_vapwr else 151.81) - 19.32 * n
        yield ((x1, 0.0), (x1 + 0.9, 1.0))


def main():
    cfg = yaml.safe_load(open(YAML))
    proj, pinout = cfg["project"], cfg.get("pinout", {})
    analog_pins = proj.get("analog_pins", 0)
    uses_vapwr = bool(proj.get("uses_vapwr", proj.get("uses_3v3", False)))

    print(f"tiles={proj['tiles']}  analog_pins={analog_pins}  "
          f"uses_vapwr={uses_vapwr}  top={proj['top_module']}\n")
    check("top_module starts with tt_um_", proj["top_module"].startswith("tt_um_"))
    check("top_module matches GDS filename", proj["top_module"] == TOP)
    if uses_vapwr and analog_pins == 0:
        check("VAPWR needs >=1 analog pin", False)

    lib = gdstk.read_gds(GDS)
    tops = lib.top_level()
    check("GDS top level unique", len(tops) == 1,
          f"{[c.name for c in tops]}")
    top = tops[0]

    # --- boundary --------------------------------------------------------
    die = re.search(r"DIEAREA \( 0 0 \) \( (\d+) (\d+) \)", open(DEF).read())
    dw, dh = int(die.group(1)) / 1000, int(die.group(2)) / 1000
    bb = top.bounding_box()
    (x0, y0), (x1, y1) = bb
    check("bbox == DIEAREA", abs(x0) < 1e-6 and abs(y0) < 1e-6
          and abs(x1 - dw) < 1e-3 and abs(y1 - dh) < 1e-3,
          f"{x1-x0:.2f} x {y1-y0:.2f} um vs {dw} x {dh}")

    layers = set(lib.layers_and_datatypes()) | set(lib.layers_and_texttypes())
    check("prBoundary present", PRBOUNDARY in layers)
    bad = [l for l in MET5 if l in layers]
    check("no forbidden met5 layers", not bad, str(bad))

    # --- cell names ------------------------------------------------------
    badnames = [n for n in gdstk.read_rawcells(GDS) if "#" in n or "/" in n]
    check("no '#' or '/' in cell names", not badnames, str(badnames[:4]))

    # --- analog pins -----------------------------------------------------
    flat = top.copy("_flat")
    flat.flatten()
    m4 = [p for p in flat.polygons if (p.layer, p.datatype) == MET4]
    v3 = [p for p in flat.polygons if (p.layer, p.datatype) == VIA3]
    for n, rect in enumerate(analog_pin_rects(uses_vapwr)):
        pr = gdstk.rectangle(*rect)
        ring = gdstk.boolean(gdstk.offset(pr, 0.5), gdstk.offset(pr, 0.1), "not")
        connected = bool(gdstk.boolean(m4, ring, "and")) or \
                    bool(gdstk.boolean(v3, pr, "and"))
        want_cnt = n < analog_pins
        want_doc = bool(pinout.get(f"ua[{n}]", ""))
        ok = (connected == want_cnt) and (connected == want_doc)
        check(f"ua[{n}]", ok,
              f"metal={connected} analog_pins says {want_cnt} "
              f"description says {want_doc}")

    # --- power pins ------------------------------------------------------
    for path, label in ((VER, "Verilog"), (LEF, "LEF")):
        s = open(path).read().replace("VPWR", "VDPWR")
        if label == "Verilog":
            s = re.sub(r"//.*", "", s)
            s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
        for pwr, want in (("VGND", True), ("VDPWR", True), ("VAPWR", uses_vapwr)):
            check(f"{label} {pwr}", (pwr in s) == want,
                  f"present={pwr in s} expected={want}")

    lef_s = open(LEF).read().replace("VPWR", "VDPWR")
    for pin, use in (("VDPWR", "USE POWER"), ("VGND", "USE GROUND")):
        m = re.search(rf"^\s*PIN {pin}\s*([\s\S]+?(?=^\s*END {pin}))",
                      lef_s, re.M)
        check(f"LEF {pin} {use}", bool(m) and use in m.group(1))

    print(f"\n{len(passes)} passed, {len(fails)} failed")
    if fails:
        for f in fails:
            print("  FAIL", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
