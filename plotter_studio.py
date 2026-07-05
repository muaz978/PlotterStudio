#!/usr/bin/env python3
"""
Plotter Studio -- image -> high-quality vector -> SVG + plotter G-code.

A small, clean desktop app (Windows / macOS / Linux). Open an image, it traces
it with potrace, previews the toolpath live, and exports a clean mm-unit SVG and
G-code (G0/G1 + pen up/down on Z) sized to your bed.

Run:  python plotter_studio.py     (or double-click run.command / run.bat)
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import core

try:
    from PIL import Image, ImageTk
except Exception:
    Image = ImageTk = None

# ---- palette ----
BG     = "#f4f5f7"
PANEL  = "#ffffff"
INK    = "#1f2430"
MUTE   = "#8a90a0"
ACCENT = "#2d7dd2"
ACC_HI = "#256bb5"
BED    = "#fbf7ef"
LINE   = "#15305b"
TRAVEL = "#d9b48a"


class PlotterStudio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Plotter Studio")
        self.geometry("1040x700")
        self.minsize(940, 620)
        self.configure(bg=BG)

        # state
        self.image_path = None
        self.loops_raw = None     # traced (image space)
        self.loops_t = None       # + rotate/flip
        self.loops_mm = None      # fitted to bed
        self.fit = None
        self.rotate = 0
        self.flip_h = False
        self.flip_v = False
        self.thumb = None
        self._trace_job = None
        self.last_dir = os.path.expanduser("~")

        self._init_style()
        self._build_menu()
        self._build_ui()
        self._report_env()
        self.bind("<Configure>", lambda e: self._draw() if e.widget is self else None)

    # ---------------------------------------------------------------- style
    def _init_style(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        base = ("Segoe UI" if sys.platform.startswith("win")
                else "SF Pro Text" if sys.platform == "darwin" else "DejaVu Sans")
        self.option_add("*Font", (base, 11))
        st.configure(".", background=BG, foreground=INK)
        st.configure("TFrame", background=BG)
        st.configure("Card.TFrame", background=PANEL)
        st.configure("Toolbar.TFrame", background=PANEL)
        st.configure("TLabel", background=BG, foreground=INK)
        st.configure("Card.TLabel", background=PANEL, foreground=INK)
        st.configure("Muted.TLabel", background=PANEL, foreground=MUTE)
        st.configure("H.TLabel", background=PANEL, foreground=INK, font=(base, 11, "bold"))
        st.configure("Title.TLabel", background=PANEL, foreground=INK, font=(base, 15, "bold"))
        st.configure("TCheckbutton", background=PANEL)
        st.configure("TLabelframe", background=PANEL, foreground=MUTE, borderwidth=0)
        st.configure("TLabelframe.Label", background=PANEL, foreground=MUTE)
        st.configure("TButton", padding=6)
        st.configure("Accent.TButton", padding=7, foreground="#fff",
                     background=ACCENT, borderwidth=0)
        st.map("Accent.TButton", background=[("active", ACC_HI), ("pressed", ACC_HI)])
        st.configure("Tool.TButton", padding=6)
        st.configure("TScale", background=PANEL)
        st.configure("TEntry", fieldbackground="#fff")

    # ---------------------------------------------------------------- menu
    def _build_menu(self):
        m = tk.Menu(self)
        fm = tk.Menu(m, tearoff=0)
        fm.add_command(label="Open image…", accelerator="Ctrl+O", command=self.open_image)
        fm.add_separator()
        fm.add_command(label="Export SVG…", command=self.export_svg)
        fm.add_command(label="Export G-code…", accelerator="Ctrl+S", command=self.export_gcode)
        fm.add_separator()
        fm.add_command(label="Quit", command=self.destroy)
        m.add_cascade(label="File", menu=fm)
        hm = tk.Menu(m, tearoff=0)
        hm.add_command(label="About", command=self._about)
        m.add_cascade(label="Help", menu=hm)
        self.config(menu=m)
        self.bind_all("<Control-o>", lambda e: self.open_image())
        self.bind_all("<Control-s>", lambda e: self.export_gcode())
        if sys.platform == "darwin":
            self.bind_all("<Command-o>", lambda e: self.open_image())
            self.bind_all("<Command-s>", lambda e: self.export_gcode())

    # ---------------------------------------------------------------- layout
    def _build_ui(self):
        # toolbar
        tb = ttk.Frame(self, style="Toolbar.TFrame", padding=(12, 8))
        tb.pack(fill="x")
        ttk.Label(tb, text="✦ Plotter Studio", style="Title.TLabel").pack(side="left")
        ttk.Button(tb, text="Export G-code", style="Accent.TButton",
                   command=self.export_gcode).pack(side="right")
        ttk.Button(tb, text="Export SVG", style="Tool.TButton",
                   command=self.export_svg).pack(side="right", padx=(0, 8))
        ttk.Separator(tb, orient="vertical").pack(side="right", fill="y", padx=10)
        ttk.Button(tb, text="Flip V", style="Tool.TButton",
                   command=lambda: self._flip("v")).pack(side="right", padx=2)
        ttk.Button(tb, text="Flip H", style="Tool.TButton",
                   command=lambda: self._flip("h")).pack(side="right", padx=2)
        ttk.Button(tb, text="Rotate 90°", style="Tool.TButton",
                   command=self._rotate).pack(side="right", padx=2)
        ttk.Button(tb, text="Open image", style="Tool.TButton",
                   command=self.open_image).pack(side="right", padx=(0, 8))
        ttk.Separator(self, orient="horizontal").pack(fill="x")

        body = ttk.Frame(self, padding=0); body.pack(fill="both", expand=True)

        # left controls (card)
        left = ttk.Frame(body, style="Card.TFrame", padding=14, width=300)
        left.pack(side="left", fill="y"); left.pack_propagate(False)
        self._build_controls(left)

        # right preview
        right = ttk.Frame(body, padding=(12, 12)); right.pack(side="right", fill="both", expand=True)
        self.info = ttk.Label(right, text="Open an image to begin", style="TLabel", foreground=MUTE)
        self.info.pack(anchor="w", pady=(0, 6))
        self.canvas = tk.Canvas(right, bg=BED, highlightthickness=1, highlightbackground="#d7dae0")
        self.canvas.pack(fill="both", expand=True)

        # status bar
        self.status = ttk.Label(self, text="Ready", anchor="w", padding=(12, 5),
                                background=PANEL, foreground=INK)
        self.status.pack(fill="x", side="bottom")

    def _slider(self, parent, label, frm, to, val, integer, cb):
        wrap = ttk.Frame(parent, style="Card.TFrame"); wrap.pack(fill="x", pady=(6, 0))
        head = ttk.Frame(wrap, style="Card.TFrame"); head.pack(fill="x")
        ttk.Label(head, text=label, style="Card.TLabel").pack(side="left")
        vlbl = ttk.Label(head, text="", style="Muted.TLabel"); vlbl.pack(side="right")
        var = (tk.IntVar if integer else tk.DoubleVar)(value=val)

        def on(_=None):
            v = var.get()
            vlbl.config(text=str(int(v)) if integer else "%.2f" % v)
            cb()
        s = ttk.Scale(wrap, from_=frm, to=to, variable=var, command=lambda e: on())
        s.pack(fill="x")
        on()
        return var

    def _field(self, parent, label, val):
        fr = ttk.Frame(parent, style="Card.TFrame"); fr.pack(fill="x", pady=3)
        ttk.Label(fr, text=label, style="Card.TLabel", width=15).pack(side="left")
        var = tk.DoubleVar(value=val)
        e = ttk.Entry(fr, textvariable=var, width=8)
        e.pack(side="right")
        e.bind("<Return>", lambda ev: self._refit_draw())
        e.bind("<FocusOut>", lambda ev: self._refit_draw())
        return var

    def _build_controls(self, p):
        ttk.Label(p, text="TRACE", style="H.TLabel").pack(anchor="w")
        self.v_thresh = self._slider(p, "Threshold", 1, 254, 128, True, self._schedule_trace)
        self.v_desp = self._slider(p, "Despeckle", 0, 40, 8, True, self._schedule_trace)
        self.v_smooth = self._slider(p, "Smoothing", 0.0, 1.334, 1.2, False, self._schedule_trace)
        self.v_invert = tk.BooleanVar(value=False)
        ttk.Checkbutton(p, text="Invert (light art on dark)", variable=self.v_invert,
                        command=self._schedule_trace).pack(anchor="w", pady=(6, 0))

        ttk.Label(p, text="SIZE & BED  (mm)", style="H.TLabel").pack(anchor="w", pady=(16, 0))
        self.v_bedw = self._field(p, "Bed width", 80.0)
        self.v_bedh = self._field(p, "Bed height", 80.0)
        self.v_size = self._field(p, "Art longest side", 60.0)

        ttk.Label(p, text="PEN & FEEDS", style="H.TLabel").pack(anchor="w", pady=(16, 0))
        self.v_penup = self._field(p, "Pen up Z", 5.0)
        self.v_pendn = self._field(p, "Pen down Z", 0.0)
        self.v_fdraw = self._field(p, "Draw feed", 150)
        self.v_ftrav = self._field(p, "Travel feed", 250)

        self.v_travel = tk.BooleanVar(value=True)
        ttk.Checkbutton(p, text="Show travel moves", variable=self.v_travel,
                        command=self._draw).pack(anchor="w", pady=(16, 0))
        ttk.Button(p, text="Re-trace", style="Accent.TButton",
                   command=self.trace).pack(fill="x", pady=(16, 0))

    # ---------------------------------------------------------------- env
    def _report_env(self):
        d = core.deps_status()
        missing = [k for k, v in d.items() if not v]
        if missing:
            self._set("Missing: " + ", ".join(missing) + "  —  see README to install", True)
            if "potrace" in missing:
                self.after(300, lambda: messagebox.showwarning(
                    "potrace not found",
                    "Plotter Studio needs the free 'potrace' tracer.\n\n"
                    "macOS:    brew install potrace\n"
                    "Windows:  winget install potrace\n"
                    "Linux:    sudo apt install potrace\n\n"
                    "Install it, then reopen the app."))
        else:
            self._set("Ready — open an image (Ctrl+O)")

    # ---------------------------------------------------------------- actions
    def _set(self, text, err=False):
        self.status.config(text=text, foreground="#b00020" if err else INK)

    def open_image(self):
        p = filedialog.askopenfilename(
            title="Open image", initialdir=self.last_dir,
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff"),
                       ("All files", "*.*")])
        if not p:
            return
        self.image_path = p
        self.last_dir = os.path.dirname(p)
        self.rotate, self.flip_h, self.flip_v = 0, False, False
        self._load_thumb(p)
        self.trace()

    def _load_thumb(self, path):
        if Image is None:
            return
        try:
            im = Image.open(path).convert("RGB")
            im.thumbnail((150, 150))
            self.thumb = ImageTk.PhotoImage(im)
        except Exception:
            self.thumb = None

    def _schedule_trace(self):
        if not self.image_path:
            return
        if self._trace_job:
            self.after_cancel(self._trace_job)
        self._trace_job = self.after(450, self.trace)

    def trace(self):
        self._trace_job = None
        if not self.image_path:
            messagebox.showinfo("Plotter Studio", "Open an image first."); return
        try:
            self._set("Tracing…"); self.update_idletasks()
            self.loops_raw = core.vectorize(
                self.image_path,
                threshold=int(self.v_thresh.get()),
                invert=bool(self.v_invert.get()),
                despeckle=int(self.v_desp.get()),
                alphamax=float(self.v_smooth.get()))
            if not self.loops_raw:
                self._set("No shapes found — adjust threshold or toggle Invert.", True)
                self.loops_mm = None; self._draw(); return
            self._refit_draw()
        except Exception as ex:
            messagebox.showerror("Trace failed", str(ex))
            self._set(str(ex), True)

    def _refit(self):
        if not self.loops_raw:
            return
        self.loops_t = core.transform_loops(self.loops_raw, self.rotate, self.flip_h, self.flip_v)
        self.fit = core.compute_fit(self.loops_t, float(self.v_size.get()))
        self.loops_mm = core.to_bed(self.loops_t, self.fit,
                                    float(self.v_bedw.get()), float(self.v_bedh.get()))

    def _refit_draw(self):
        try:
            self._refit()
        except Exception:
            return
        self._draw()
        if self.loops_mm:
            s = core.stats(self.loops_mm)
            oob = core.out_of_bounds(self.loops_mm, self.v_bedw.get(), self.v_bedh.get())
            mins = s["draw_mm"] / max(1, int(self.v_fdraw.get()))
            self.info.config(
                text="%d contours · %.0f mm of ink · ~%.1f min%s"
                     % (s["contours"], s["draw_mm"], mins, "  ·  OUT OF BOUNDS" if oob else ""),
                foreground="#b00020" if oob else MUTE)
            self._set("Traced %d contours · %.1f × %.1f mm"
                      % (s["contours"], self.fit["w"], self.fit["h"]),
                      err=oob)

    def _rotate(self):
        self.rotate = (self.rotate + 90) % 360
        self._refit_draw()

    def _flip(self, axis):
        if axis == "h":
            self.flip_h = not self.flip_h
        else:
            self.flip_v = not self.flip_v
        self._refit_draw()

    # ---------------------------------------------------------------- preview
    def _draw(self):
        c = self.canvas; c.delete("all")
        cw, ch = c.winfo_width(), c.winfo_height()
        if cw < 10:
            return
        bw, bh = float(self.v_bedw.get()), float(self.v_bedh.get())
        pad = 26
        s = min((cw - 2 * pad) / bw, (ch - 2 * pad) / bh)
        ox, oy = (cw - bw * s) / 2, (ch - bh * s) / 2

        def px(x, y):
            return (ox + x * s, oy + (bh - y) * s)

        # bed + grid
        x0, y0 = px(0, bh); x1, y1 = px(bw, 0)
        c.create_rectangle(x0, y0, x1, y1, fill=BED, outline="#c9ccd3")
        step = 10
        gx = step
        while gx < bw:
            a, _ = px(gx, 0); c.create_line(a, y0, a, y1, fill="#ece7dc")
            gx += step
        gy = step
        while gy < bh:
            _, b = px(0, gy); c.create_line(x0, b, x1, b, fill="#ece7dc")
            gy += step

        if not self.loops_mm:
            c.create_text((x0 + x1) / 2, (y0 + y1) / 2, text="Trace preview appears here",
                          fill=MUTE); self._thumb(); return

        # travel moves
        if self.v_travel.get():
            prev = None
            for lp in self.loops_mm:
                if prev:
                    ax, ay = px(*prev); bx, by = px(*lp[0])
                    c.create_line(ax, ay, bx, by, fill=TRAVEL, dash=(3, 3))
                prev = lp[0]
        # ink
        for lp in self.loops_mm:
            flat = []
            for x, y in lp:
                a, b = px(x, y); flat += [a, b]
            if len(flat) >= 4:
                c.create_line(*flat, fill=LINE, width=1.4)
        self._thumb()

    def _thumb(self):
        if self.thumb:
            self.canvas.create_image(self.canvas.winfo_width() - 12, 12,
                                     anchor="ne", image=self.thumb)

    # ---------------------------------------------------------------- export
    def export_svg(self):
        if not self.loops_t or not self.fit:
            messagebox.showinfo("Plotter Studio", "Trace an image first."); return
        p = filedialog.asksaveasfilename(
            defaultextension=".svg", initialdir=self.last_dir,
            initialfile=self._base() + ".svg", filetypes=[("SVG", "*.svg")])
        if not p:
            return
        open(p, "w").write(core.build_svg(self.loops_t, self.fit))
        self.last_dir = os.path.dirname(p)
        self._set("Saved SVG → " + p)

    def export_gcode(self):
        if not self.loops_mm:
            messagebox.showinfo("Plotter Studio", "Trace an image first."); return
        if core.out_of_bounds(self.loops_mm, self.v_bedw.get(), self.v_bedh.get()):
            if not messagebox.askyesno(
                    "Out of bounds",
                    "Some moves fall outside the bed and may be refused by the "
                    "firmware's soft limits. Export anyway?"):
                return
        p = filedialog.asksaveasfilename(
            defaultextension=".gcode", initialdir=self.last_dir,
            initialfile=self._base() + ".gcode",
            filetypes=[("G-code", "*.gcode *.nc *.txt")])
        if not p:
            return
        open(p, "w").write(core.build_gcode(
            self.loops_mm, float(self.v_penup.get()), float(self.v_pendn.get()),
            int(self.v_fdraw.get()), int(self.v_ftrav.get())))
        self.last_dir = os.path.dirname(p)
        self._set("Saved G-code → " + p)

    def _base(self):
        return os.path.splitext(os.path.basename(self.image_path or "art"))[0]

    def _about(self):
        messagebox.showinfo(
            "About Plotter Studio",
            "Plotter Studio\n\nImage → high-quality vector → SVG + plotter G-code.\n"
            "Tracing by potrace. Built for GRBL-style pen plotters.")


def main():
    if Image is None:
        # PIL missing: still start so the status bar/README can guide the user
        pass
    PlotterStudio().mainloop()


if __name__ == "__main__":
    main()
