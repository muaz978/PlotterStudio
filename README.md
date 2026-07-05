# Plotter Studio

Turn any image into clean vector art and pen-plotter G-code.

**Open an image → it traces it in high quality (potrace) → preview the toolpath → export a crisp mm-unit SVG and G-code** (G0/G1 with pen up/down on Z), sized to your bed.

Built for GRBL-style pen plotters (defaults match an 80×80 mm bed, pen up `Z5` / down `Z0`), but bed size, pen heights, and feeds are all editable in the app.

---

## Download (no setup)

Grab a ready-to-run build from the [**Releases**](https://github.com/muaz978/PlotterStudio/releases) page:

- **macOS** — download `PlotterStudio-macOS.zip`, unzip, open `PlotterStudio.app`. First launch: right-click → **Open** (it's unsigned).
- **Windows** — download `PlotterStudio-Windows.zip`, unzip, run `PlotterStudio.exe`.
  - Windows SmartScreen may show a blue **"Windows protected your PC"** box because the app is new and unsigned (not because it's unsafe). Click **More info → Run anyway**.
  - To silence it entirely on your PC: right-click the ZIP → **Properties** → tick **Unblock** → OK, *then* extract.
  - Prefer to verify the download first? Compare its SHA-256 to the `.sha256` file on the release: `Get-FileHash PlotterStudio-Windows.zip -Algorithm SHA256`.

`potrace` is bundled inside both, so there's nothing else to install.

> **Why the warning?** The app isn't code-signed (a signing certificate for Windows costs money, and free options require an approved open-source signing program). The SHA-256 checksums on each release let you confirm the download is authentic in the meantime.

---

## Quick start (from source)

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
