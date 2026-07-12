"""
SafingData — Panel de progreso y log de transferencia tipo terminal.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from .styles import C, F


class ProgressPanel(ttk.Frame):
    """Panel inferior con barra de progreso y log tipo terminal."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, style="Card.TFrame", **kwargs)
        self._build()

    def _build(self) -> None:
        self.configure(padding=(16, 12))

        # ── Header del panel ───────────────────────────────────
        header = ttk.Frame(self, style="Card.TFrame")
        header.pack(fill="x", pady=(0, 8))

        ttk.Label(
            header,
            text="▶  TRANSFER LOG",
            style="CardRed.TLabel",
            font=F["sm"],
        ).pack(side="left")

        self._status_lbl = ttk.Label(
            header,
            text="IDLE",
            style="CardDim.TLabel",
            font=F["sm"],
        )
        self._status_lbl.pack(side="right")

        # ── Barra de progreso ──────────────────────────────────
        bar_frame = ttk.Frame(self, style="Card.TFrame")
        bar_frame.pack(fill="x", pady=(0, 4))

        self._progress_var = tk.DoubleVar(value=0.0)
        self._progress_bar = ttk.Progressbar(
            bar_frame,
            variable=self._progress_var,
            maximum=100,
            style="Red.Horizontal.TProgressbar",
            length=100,
        )
        self._progress_bar.pack(fill="x", side="left", expand=True)

        self._pct_lbl = ttk.Label(
            bar_frame,
            text="  0%",
            style="CardDim.TLabel",
            font=F["sm"],
            width=5,
        )
        self._pct_lbl.pack(side="right")

        # ── Etiqueta de archivo actual ─────────────────────────
        self._file_lbl = ttk.Label(
            self,
            text="",
            style="CardDim.TLabel",
            font=F["sm"],
        )
        self._file_lbl.pack(fill="x", pady=(0, 8))

        # ── Log de texto tipo terminal ─────────────────────────
        log_outer = tk.Frame(self, bg=C["bg_input"], highlightbackground=C["border"], highlightthickness=1)
        log_outer.pack(fill="both", expand=True)

        self._log_text = tk.Text(
            log_outer,
            bg=C["bg_input"],
            fg=C["fg"],
            font=F["mono"],
            height=10,
            wrap="word",
            state="disabled",
            insertbackground=C["red"],
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=8,
            cursor="arrow",
        )

        scroll = ttk.Scrollbar(log_outer, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=scroll.set)

        scroll.pack(side="right", fill="y")
        self._log_text.pack(side="left", fill="both", expand=True)

        # Tags de color para el log
        self._log_text.tag_configure("info",    foreground=C["fg2"])
        self._log_text.tag_configure("success", foreground=C["green"])
        self._log_text.tag_configure("error",   foreground=C["danger"])
        self._log_text.tag_configure("warning", foreground=C["yellow"])
        self._log_text.tag_configure("cmd",     foreground=C["red"])
        self._log_text.tag_configure("ts",      foreground=C["fg3"])

    # ──────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────

    def log(self, message: str, level: str = "info") -> None:
        """Escribe un mensaje en el log. level: info | success | error | warning | cmd"""
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")

        self._log_text.configure(state="normal")
        self._log_text.insert("end", f"[{ts}] ", "ts")
        self._log_text.insert("end", f"{message}\n", level)
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def set_progress(self, percent: float, filename: str = "", status: str = "") -> None:
        """Actualiza la barra de progreso (0-100)."""
        clamped = max(0.0, min(100.0, percent))
        self._progress_var.set(clamped)
        self._pct_lbl.configure(text=f"{clamped:5.1f}%")
        if filename:
            self._file_lbl.configure(text=f"  {filename}")
        if status:
            self._status_lbl.configure(text=status)

    def set_status(self, status: str, color: str = "dim") -> None:
        colors = {"dim": C["fg2"], "ok": C["green"], "err": C["danger"], "busy": C["yellow"]}
        self._status_lbl.configure(
            text=status,
            foreground=colors.get(color, C["fg2"]),
        )

    def clear_progress(self) -> None:
        self._progress_var.set(0)
        self._pct_lbl.configure(text="  0%")
        self._file_lbl.configure(text="")

    def clear_log(self) -> None:
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.configure(state="disabled")
