# Plotter Studio

Turn any image into clean vector art and pen-plotter G-code.

**Open an image → it traces it in high quality (potrace) → preview the toolpath → export a crisp mm-unit SVG and G-code** (G0/G1 with pen up/down on Z), sized to your bed.

Built for GRBL-style pen plotters (defaults match an 80×80 mm bed, pen up `Z5` / down `Z0`), but bed size, pen heights, and feeds are all editable in the app.

---

## Quick start (recommended)

No Python knowledge needed. The launcher sets everything up on first run.

- **macOS / Linux:** double-click **`run.command`** (or run `./run.command` in a terminal).
- **Windows:** double-click **`run.bat`**.

The first launch creates a private environment, installs the two Python packages, and makes sure `potrace` is present (macOS uses Homebrew; Windows downloads it automatically). Every launch after that opens instantly.

> macOS may say `run.command` "cannot be opened because it is from an unidentified developer." Right-click it → **Open** once to allow it.

---

## Using it

1. **Open image** (PNG/JPG/BMP/…). High-contrast line art or solid shapes trace best.
2. Adjust **Threshold / Despeckle / Smoothing** (it re-traces live) and **Invert** for light-on-dark art.
3. Set **bed size**, **art size**, **pen Z heights**, and **feeds**.
4. **Rotate / Flip** if needed; the preview shows the exact toolpath (ink in blue, pen-up travel dashed).
5. **Export SVG** (for Rayforge / LightBurn / Inkscape) or **Export G-code** (stream in UGS).

An out-of-bounds warning appears if the art would exceed the bed's soft limits.

---

## Manual install (alternative)

```bash
pip install -r requirements.txt      # pillow + svgpathtools
# potrace:  macOS: brew install potrace | Windows: winget install potrace | Linux: sudo apt install potrace
python plotter_studio.py
```

## Build a standalone app (no Python on the target machine)

Bundles Python **and** potrace into one double-click app:

```bash
./build_macos.sh        # -> dist/PlotterStudio.app
build_windows.bat       # -> dist\PlotterStudio.exe
```

---

## Notes

- **Quality** comes from [potrace](https://potrace.sourceforge.net/); the app keeps it as the tracing engine on purpose.
- If a traced **circle plots as an oval**, that's an X/Y steps-per-mm mismatch in the *plotter firmware*, not the trace.
- The engine (`core.py`) is importable and headless-testable: `vectorize`, `compute_fit`, `to_bed`, `build_gcode`, `build_svg`.

MIT licensed.
