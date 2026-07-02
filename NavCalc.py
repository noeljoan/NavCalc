#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NavCalc - V.F.R. Navigation Preparation Calculator
====================================================
(c) 2026 N. Joan
This version reproduces the classic wind-triangle calculation used in
VFR flight planning: from the magnetic heading, the distance, the
aircraft's true airspeed and the wind (direction + speed), it computes
the drift angle, the compensated magnetic heading, the crosswind /
headwind-tailwind components, the ground speed and the flight times.

This calculator is only an aid for flight-planning preparation.
It is the pilot's responsibility to verify the consistency of the
results.
"""

import math
import tkinter as tk

BLUE_FIELD = "#dbe9ff"      # light blue background for required fields (as in the original)
DARK_BLUE = "#1f3a5f"
WHITE = "#ffffff"
GREY_RESULT = "#f2f2f2"
GREEN_OK = "#2e7d32"
RED_ERR = "#c62828"

FONT_LABEL = ("Segoe UI", 10)
FONT_ENTRY = ("Segoe UI", 11, "bold")
FONT_TITLE = ("Segoe UI", 13, "bold")
FONT_RESULT_LABEL = ("Segoe UI", 10)
FONT_RESULT_VALUE = ("Segoe UI", 12, "bold")


def normalize_0_360(angle: float) -> float:
    return angle % 360.0


def normalize_180(angle: float) -> float:
    """Reduces an angle to the interval ]-180, 180]."""
    a = angle % 360.0
    if a > 180.0:
        a -= 360.0
    return a


class NavCalcApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NavCalc - V.F.R. Navigation Calculator - (c) 2026 N. Joan")
        self.configure(bg=WHITE)
        self.resizable(False, False)

        self._build_layout()
        self._reset_results()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_layout(self):
        pad = 12

        header = tk.Frame(self, bg=DARK_BLUE)
        header.pack(fill="x")
        tk.Label(
            header,
            text="NavCalc - V.F.R. Navigation Calculator",
            font=FONT_TITLE,
            fg=WHITE,
            bg=DARK_BLUE,
            pady=10,
        ).pack()

        main = tk.Frame(self, bg=WHITE, padx=pad, pady=pad)
        main.pack(fill="both", expand=True)

        # ---------------- Left column: inputs ----------------
        frame_input = tk.LabelFrame(
            main, text=" Flight Data ", font=FONT_LABEL, bg=WHITE,
            fg=DARK_BLUE, padx=10, pady=10
        )
        frame_input.grid(row=0, column=0, sticky="n", padx=(0, 12))

        self.var_rm = tk.StringVar()
        self.var_dist = tk.StringVar()
        self.var_vp = tk.StringVar()
        self.var_wd = tk.StringVar()
        self.var_vw = tk.StringVar()

        # NOTE: each field now consumes 1 or 2 grid rows (label+entry row,
        # plus an optional sub-text row). self._row tracks the next free
        # grid row so fields never overlap other widgets (this was the
        # bug in the previous version: "Wind direction" was silently
        # rendered on top of the "Calculate" button).
        self._row = 0
        self._field(frame_input, "Magnetic Heading (MH) [°]", self.var_rm)
        self._field(frame_input, "Distance between points [km/NM]", self.var_dist)
        self._field(frame_input, "Aircraft true airspeed (TAS)", self.var_vp)
        self._field(frame_input, "Wind direction (from) [°]", self.var_wd)
        self._field(frame_input, "Wind speed", self.var_vw)

        tk.Label(
            frame_input,
            text="All fields on blue background must\nbe filled in.",
            font=("Segoe UI", 8, "italic"),
            fg="#555555",
            bg=WHITE,
            justify="left",
        ).grid(row=self._row, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self._row += 1

        btn = tk.Button(
            frame_input,
            text="Calculate  (OK)",
            font=("Segoe UI", 11, "bold"),
            bg=DARK_BLUE,
            fg=WHITE,
            activebackground="#2c5288",
            activeforeground=WHITE,
            relief="flat",
            padx=14,
            pady=6,
            command=self.on_calculate,
        )
        btn.grid(row=self._row, column=0, columnspan=2, pady=(14, 0), sticky="we")
        self._row += 1

        btn_reset = tk.Button(
            frame_input,
            text="Clear",
            font=("Segoe UI", 9),
            bg="#e0e0e0",
            relief="flat",
            command=self.on_clear,
        )
        btn_reset.grid(row=self._row, column=0, columnspan=2, pady=(6, 0), sticky="we")
        self._row += 1

        # ---------------- Right column: results ----------------
        frame_results = tk.LabelFrame(
            main, text=" Results ", font=FONT_LABEL, bg=WHITE,
            fg=DARK_BLUE, padx=10, pady=10
        )
        frame_results.grid(row=0, column=1, sticky="n")

        self.lbl_vt = self._result(frame_results, 0, "Crosswind component (XWC)")
        self.lbl_ve_title, self.lbl_ve = self._result(
            frame_results, 1, "Effective wind (EW)", dynamic_title=True
        )
        self.lbl_drift = self._result(frame_results, 2, "Drift angle")
        self.lbl_hdg = self._result(frame_results, 3, "Compensated magnetic heading (CMH)")
        self.lbl_vs = self._result(frame_results, 4, "Ground speed (GS)")
        self.lbl_tsv = self._result(frame_results, 5, "Time without wind (TWW)")
        self.lbl_tc = self._result(frame_results, 6, "Corrected time (CT)")

        self.lbl_error = tk.Label(
            frame_results, text="", font=("Segoe UI", 9, "bold"),
            fg=RED_ERR, bg=WHITE, wraplength=280, justify="left"
        )
        self.lbl_error.grid(row=8, column=0, columnspan=2, sticky="w", pady=(10, 0))

        footer = tk.Label(
            self,
            text="NavCalc v1.0.0 (2026) by Noel Joan\n"
                 "This calculator is only an aid for flight-planning preparation;\n"
                 "it is the pilot's responsibility to verify the consistency of the results.",
            font=("Segoe UI", 8),
            fg="#777777",
            bg=WHITE,
            justify="center",
        )
        footer.pack(pady=(0, 10))

    def _field(self, parent, label, var, sub_text=None):
        """Adds a label+entry row (and an optional sub-text row) at the
        next free grid row, then advances the row counter accordingly."""
        row = self._row
        tk.Label(parent, text=label, font=FONT_LABEL, bg=WHITE, anchor="w",
                 justify="left", wraplength=220).grid(row=row, column=0, sticky="w", pady=(6, 0))
        entry = tk.Entry(parent, textvariable=var, font=FONT_ENTRY, width=10,
                          bg=BLUE_FIELD, relief="solid", bd=1, justify="center")
        entry.grid(row=row, column=1, sticky="e", pady=(6, 0), padx=(10, 0))
        self._row += 1

        if sub_text:
            tk.Label(parent, text=sub_text, font=("Segoe UI", 8, "italic"),
                      fg="#777777", bg=WHITE, justify="left").grid(
                row=self._row, column=0, columnspan=2, sticky="w"
            )
            self._row += 1

        return entry

    def _result(self, parent, row, label, dynamic_title=False):
        lbl_title = tk.Label(parent, text=label, font=FONT_RESULT_LABEL, bg=WHITE,
                              anchor="w", wraplength=200, justify="left")
        lbl_title.grid(row=row, column=0, sticky="w", pady=4)
        lbl_value = tk.Label(parent, text="—", font=FONT_RESULT_VALUE, bg=GREY_RESULT,
                              width=10, relief="solid", bd=1)
        lbl_value.grid(row=row, column=1, sticky="e", pady=4, padx=(10, 0))
        if dynamic_title:
            return lbl_title, lbl_value
        return lbl_value

    # ------------------------------------------------------------------
    # Calculation logic (wind triangle)
    # ------------------------------------------------------------------
    def on_clear(self):
        for v in (self.var_rm, self.var_dist, self.var_vp, self.var_wd, self.var_vw):
            v.set("")
        self._reset_results()
        self.lbl_error.config(text="")

    def _reset_results(self):
        for lbl in (self.lbl_vt, self.lbl_ve, self.lbl_drift, self.lbl_hdg,
                    self.lbl_vs, self.lbl_tsv, self.lbl_tc):
            lbl.config(text="—", fg="black")
        self.lbl_ve_title.config(text="Effective wind (Ew)")

    def _read_float(self, var, field_name):
        txt = var.get().strip().replace(",", ".")
        if txt == "":
            raise ValueError(f"Field \u00ab {field_name} \u00bb must be filled in.")
        try:
            return float(txt)
        except ValueError:
            raise ValueError(f"Field \u00ab {field_name} \u00bb must be a number.")

    def on_calculate(self):
        self.lbl_error.config(text="")
        self._reset_results()
        try:
            rm = self._read_float(self.var_rm, "Magnetic route")
            dist = self._read_float(self.var_dist, "Distance")
            vp = self._read_float(self.var_vp, "True airspeed")
            wd = self._read_float(self.var_wd, "Wind direction")
            vw = self._read_float(self.var_vw, "Wind speed")

            if vp <= 0:
                raise ValueError("The aircraft's true airspeed must be positive.")
            if dist <= 0:
                raise ValueError("The distance must be positive.")
            if vw < 0:
                raise ValueError("The wind speed cannot be negative.")

            result = self._compute_triangle(rm, dist, vp, wd, vw)
            self._show_results(result)

        except ValueError as e:
            self.lbl_error.config(text=str(e))
        except ZeroDivisionError:
            self.lbl_error.config(text="Zero or negative ground speed: the headwind\n"
                                        "exceeds the aircraft's true airspeed.")

    def _compute_triangle(self, rm, dist, vp, wd, vw):
        """Classic wind-triangle calculation for VFR navigation."""
        alpha = normalize_180(wd - rm)          # wind angle relative to the route
        a_rad = math.radians(alpha)

        vt = vw * math.sin(a_rad)                # crosswind component (signed)
        ve = vw * math.cos(a_rad)                # effective wind (signed: + = headwind, - = tailwind)

        # drift angle: correction angle caused by the crosswind component
        ratio = vt / vp if vp else 0.0
        ratio = max(-1.0, min(1.0, ratio))
        drift = math.degrees(math.asin(ratio))

        heading = normalize_0_360(rm + drift)    # compensated magnetic heading (CMH)
        vs = vp * math.cos(math.radians(drift)) - ve   # ground speed

        tsv = dist / vp * 60.0                   # time without wind (minutes)
        tc = dist / vs * 60.0 if vs > 0 else None  # corrected time (minutes)

        return dict(alpha=alpha, vt=vt, ve=ve, drift=drift, heading=heading, vs=vs,
                    tsv=tsv, tc=tc)

    def _show_results(self, r):
        self.lbl_vt.config(text=f"{abs(r['vt']):.1f}")

        if r["ve"] >= 0:
            self.lbl_ve_title.config(text="Effective wind\n(headwind component)")
        else:
            self.lbl_ve_title.config(text="Effective wind\n(tailwind component)")
        self.lbl_ve.config(text=f"{abs(r['ve']):.1f}")

        side = "R" if r["drift"] >= 0 else "L"  # Right / Left
        self.lbl_drift.config(text=f"{abs(r['drift']):.1f}\u00b0 {side}")

        self.lbl_hdg.config(text=f"{r['heading']:03.0f}\u00b0")

        self.lbl_vs.config(text=f"{r['vs']:.1f}")

        self.lbl_tsv.config(text=self._fmt_minutes(r["tsv"]))

        if r["tc"] is None:
            self.lbl_tc.config(text="---", fg=RED_ERR)
            self.lbl_error.config(
                text="Warning: the headwind exceeds the aircraft's true\n"
                     "airspeed, ground speed is zero or negative."
            )
        else:
            self.lbl_tc.config(text=self._fmt_minutes(r["tc"]), fg=GREEN_OK)

    @staticmethod
    def _fmt_minutes(total_minutes):
        h = int(total_minutes // 60)
        m = int(round(total_minutes % 60))
        if m == 60:
            h += 1
            m = 0
        if h > 0:
            return f"{h} h {m:02d} min"
        return f"{m} min"


if __name__ == "__main__":
    app = NavCalcApp()
    app.mainloop()
