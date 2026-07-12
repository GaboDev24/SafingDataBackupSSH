"""
SafingData — Ventana principal de la aplicación.
Diseño táctico SpiderWeb: fondo negro, acento rojo #A30000, monoespaciada.
"""

import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk, filedialog
from typing import Optional

from .styles import C, F, apply_ttk_style
from .file_selector import FileSelector, _fmt_size
from .progress_panel import ProgressPanel

# Importaciones del backend (al nivel del proyecto)
_APP_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_APP_DIR))

import app.config as cfg_module
import app.scheduler as sched
import app.storage as storage_mod
from app.backup import SSHBackupClient

VERSION = "1.0.0"


class AppWindow:
    """Ventana principal de SafingData."""

    def __init__(self) -> None:
        self._cfg = cfg_module.load_config()
        self._client = SSHBackupClient()
        self._backup_thread: Optional[threading.Thread] = None
        self._is_busy = False
        self._disk_info: dict = {"total": 0, "used": 0, "free": 0}
        self._remote_base_abs: str = ""

        self._root = tk.Tk()
        self._root.title("SafingData — Backup SSH Portable")
        self._root.configure(bg=C["bg"])
        self._root.minsize(960, 700)
        self._root.geometry("1100x760")
        self._root.resizable(True, True)

        # Icono
        try:
            self._root.iconbitmap(default="")
        except Exception:
            pass

        # Estilo ttk
        self._style = ttk.Style()
        apply_ttk_style(self._style)

        # Construir la UI
        self._build_ui()

        # Recargar estado de backups
        self._root.after(200, self._refresh_backup_list)

        # Cargar selección previa
        if self._cfg.get("selected_paths"):
            self._root.after(300, lambda: self._file_selector.set_paths(self._cfg["selected_paths"]))

    # ──────────────────────────────────────────────────────────
    # Construcción de la UI
    # ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self._build_header()
        self._build_body()
        self._build_footer()

    def _build_header(self) -> None:
        """Barra superior estilo terminal con dots macOS."""
        header = tk.Frame(self._root, bg=C["bg2"], pady=0)
        header.pack(fill="x", side="top")

        # Línea borde rojo en la parte inferior del header
        tk.Frame(self._root, bg=C["red"], height=1).pack(fill="x", side="top")

        inner = tk.Frame(header, bg=C["bg2"], padx=16, pady=10)
        inner.pack(fill="x")

        # ── Dots macOS ──────────────────────────────────────────
        dots_frame = tk.Frame(inner, bg=C["bg2"])
        dots_frame.pack(side="left", padx=(0, 16))
        for color in ("#ff5f57", "#febc2e", "#28c840"):
            dot = tk.Canvas(dots_frame, width=10, height=10, bg=C["bg2"], highlightthickness=0)
            dot.create_oval(1, 1, 9, 9, fill=color, outline="")
            dot.pack(side="left", padx=2)

        # ── Título ──────────────────────────────────────────────
        tk.Label(
            inner,
            text="SAFINGDATA",
            bg=C["bg2"],
            fg=C["red"],
            font=F["xl"],
        ).pack(side="left")

        tk.Label(
            inner,
            text="  //  SSH BACKUP SYSTEM",
            bg=C["bg2"],
            fg=C["fg3"],
            font=F["base"],
        ).pack(side="left")

        # ── Estado conexión ────────────────────────────────────
        conn_frame = tk.Frame(inner, bg=C["bg2"])
        conn_frame.pack(side="right")

        self._conn_dot = tk.Canvas(conn_frame, width=8, height=8, bg=C["bg2"], highlightthickness=0)
        self._conn_dot.create_oval(1, 1, 7, 7, fill=C["fg3"], outline="", tags="dot")
        self._conn_dot.pack(side="left", padx=(0, 6))

        self._conn_lbl = tk.Label(
            conn_frame,
            text="DESCONECTADO",
            bg=C["bg2"],
            fg=C["fg3"],
            font=F["sm"],
        )
        self._conn_lbl.pack(side="left", padx=(0, 16))

        # Botón conectar/desconectar
        self._btn_conn = tk.Button(
            conn_frame,
            text="CONECTAR",
            command=self._toggle_connection,
            bg=C["red"],
            fg=C["fg"],
            font=F["sm"],
            relief="flat",
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            activebackground=C["red_hi"],
            activeforeground=C["fg"],
        )
        self._btn_conn.pack(side="left", padx=(0, 8))

        # Botón configuración
        tk.Button(
            conn_frame,
            text="⚙",
            command=self._open_settings,
            bg=C["bg4"],
            fg=C["fg2"],
            font=F["base"],
            relief="flat",
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            activebackground=C["bg3"],
            activeforeground=C["fg"],
        ).pack(side="left")

    def _build_body(self) -> None:
        """Cuerpo principal: dos columnas + panel inferior."""
        body = tk.Frame(self._root, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=12, pady=10)

        # ── Columna izquierda: selector de archivos ────────────
        left = tk.Frame(body, bg=C["bg"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        # Borde decorativo
        left_border = tk.Frame(left, bg=C["border"], bd=0)
        left_border.pack(fill="both", expand=True)

        self._file_selector = FileSelector(
            left_border,
            on_change=self._on_selection_change,
        )
        self._file_selector.pack(fill="both", expand=True, padx=1, pady=1)

        # ── Columna derecha: info + backups ────────────────────
        right_outer = tk.Frame(body, bg=C["bg"], width=360)
        right_outer.pack(side="right", fill="both", padx=(6, 0))
        right_outer.pack_propagate(False)

        right_canvas = tk.Canvas(right_outer, bg=C["bg"], highlightthickness=0)
        right_scrollbar = ttk.Scrollbar(right_outer, orient="vertical", command=right_canvas.yview)
        
        right = tk.Frame(right_canvas, bg=C["bg"])
        right.bind(
            "<Configure>",
            lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all"))
        )
        
        right_canvas.create_window((0, 0), window=right, anchor="nw", width=340)
        right_canvas.configure(yscrollcommand=right_scrollbar.set)
        
        right_scrollbar.pack(side="right", fill="y")
        right_canvas.pack(side="left", fill="both", expand=True)

        # Habilitar scroll con la rueda del ratón en el panel derecho
        def _on_mousewheel(event):
            right_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        def _bind_mousewheel(event):
            right_canvas.bind_all("<MouseWheel>", _on_mousewheel)
            
        def _unbind_mousewheel(event):
            right_canvas.unbind_all("<MouseWheel>")
            
        right_canvas.bind("<Enter>", _bind_mousewheel)
        right_canvas.bind("<Leave>", _unbind_mousewheel)

        self._build_right_panel(right)

        # ── Panel inferior: progreso y log ─────────────────────
        bottom_outer = tk.Frame(self._root, bg=C["border"], pady=1)
        bottom_outer.pack(fill="x", side="bottom", padx=12, pady=(0, 8))

        self._progress = ProgressPanel(bottom_outer)
        self._progress.pack(fill="both", expand=True)

        # Log inicial
        self._progress.log("SafingData iniciado.", "info")
        self._progress.log(f"Servidor: {self._cfg['host']}:{self._cfg['port']}", "info")
        self._progress.log("Conecta para comenzar.", "info")

    def _build_right_panel(self, parent: tk.Frame) -> None:
        """Panel derecho con info de espacio y lista de backups."""
        # ── Card: Servidor ─────────────────────────────────────
        self._build_server_card(parent)

        # ── Separador ─────────────────────────────────────────
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", pady=8)

        # ── Card: Espacio ─────────────────────────────────────
        self._build_space_card(parent)

        # ── Separador ─────────────────────────────────────────
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", pady=8)

        # ── Card: Botón backup ────────────────────────────────
        self._build_action_card(parent)

        # ── Separador ─────────────────────────────────────────
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", pady=8)

        # ── Card: Backups activos ─────────────────────────────
        self._build_backups_card(parent)

    def _build_server_card(self, parent: tk.Frame) -> None:
        card = tk.Frame(parent, bg=C["bg3"], bd=0)
        card.pack(fill="x", padx=2)
        tk.Frame(card, bg=C["border"], height=1).pack(fill="x")
        inner = tk.Frame(card, bg=C["bg3"], padx=14, pady=10)
        inner.pack(fill="x")

        tk.Label(inner, text="◈ SERVIDOR SSH", bg=C["bg3"], fg=C["red"], font=F["sm"]).pack(anchor="w")

        info_frame = tk.Frame(inner, bg=C["bg3"])
        info_frame.pack(fill="x", pady=(6, 0))

        rows = [
            ("HOST", self._cfg["host"]),
            ("PUERTO", str(self._cfg["port"])),
            ("USUARIO", self._cfg["user"]),
        ]
        for label, value in rows:
            row = tk.Frame(info_frame, bg=C["bg3"])
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"{label:<8}", bg=C["bg3"], fg=C["fg3"], font=F["sm"]).pack(side="left")
            tk.Label(row, text=value, bg=C["bg3"], fg=C["fg"], font=F["base"]).pack(side="left")

        tk.Frame(card, bg=C["border"], height=1).pack(fill="x")

    def _build_space_card(self, parent: tk.Frame) -> None:
        card = tk.Frame(parent, bg=C["bg3"], bd=0)
        card.pack(fill="x", padx=2)
        tk.Frame(card, bg=C["border"], height=1).pack(fill="x")
        inner = tk.Frame(card, bg=C["bg3"], padx=14, pady=10)
        inner.pack(fill="x")

        header_row = tk.Frame(inner, bg=C["bg3"])
        header_row.pack(fill="x")
        tk.Label(header_row, text="◈ ESPACIO REMOTO", bg=C["bg3"], fg=C["red"], font=F["sm"]).pack(side="left")

        info = tk.Frame(inner, bg=C["bg3"])
        info.pack(fill="x", pady=(8, 6))

        # Total disponible
        self._space_avail_lbl = tk.Label(
            info, text="—", bg=C["bg3"], fg=C["fg"], font=F["lg"]
        )
        self._space_avail_lbl.pack(anchor="w")

        self._space_desc_lbl = tk.Label(
            info, text="disponible (total − 20 GB reserva)", bg=C["bg3"], fg=C["fg3"], font=F["sm"]
        )
        self._space_desc_lbl.pack(anchor="w")

        # Barra de espacio (Canvas)
        bar_outer = tk.Frame(inner, bg=C["bg_input"], height=8)
        bar_outer.pack(fill="x", pady=(8, 4))
        bar_outer.pack_propagate(False)

        self._space_canvas = tk.Canvas(
            bar_outer, bg=C["bg_input"], height=8, highlightthickness=0
        )
        self._space_canvas.pack(fill="both", expand=True)

        # Detalle
        detail_row = tk.Frame(inner, bg=C["bg3"])
        detail_row.pack(fill="x")

        self._space_used_lbl = tk.Label(
            detail_row, text="usado: —", bg=C["bg3"], fg=C["fg3"], font=F["sm"]
        )
        self._space_used_lbl.pack(side="left")

        self._space_total_lbl = tk.Label(
            detail_row, text="total: —", bg=C["bg3"], fg=C["fg3"], font=F["sm"]
        )
        self._space_total_lbl.pack(side="right")

        # Tamaño selección local
        sep2 = tk.Frame(inner, bg=C["border2"], height=1)
        sep2.pack(fill="x", pady=(8, 4))

        sel_row = tk.Frame(inner, bg=C["bg3"])
        sel_row.pack(fill="x")
        tk.Label(sel_row, text="SELECCIÓN LOCAL:", bg=C["bg3"], fg=C["fg3"], font=F["sm"]).pack(side="left")
        self._sel_size_lbl = tk.Label(sel_row, text="0 B", bg=C["bg3"], fg=C["fg"], font=F["base"]).pack(side="right")
        self._sel_size_var = tk.StringVar(value="0 B")
        tk.Label(sel_row, textvariable=self._sel_size_var, bg=C["bg3"], fg=C["fg"], font=F["base"]).pack(side="right")

        tk.Frame(card, bg=C["border"], height=1).pack(fill="x")

    def _build_action_card(self, parent: tk.Frame) -> None:
        card = tk.Frame(parent, bg=C["bg3"], bd=0)
        card.pack(fill="x", padx=2)
        tk.Frame(card, bg=C["border"], height=1).pack(fill="x")
        inner = tk.Frame(card, bg=C["bg3"], padx=14, pady=12)
        inner.pack(fill="x")

        self._btn_backup = tk.Button(
            inner,
            text="▶  INICIAR BACKUP COMPLETO",
            command=self._start_backup,
            bg=C["red"],
            fg=C["fg"],
            font=F["md"],
            relief="flat",
            bd=0,
            padx=14,
            pady=10,
            cursor="hand2",
            activebackground=C["red_hi"],
            activeforeground=C["fg"],
            disabledforeground=C["fg3"],
            state="disabled",
        )
        self._btn_backup.pack(fill="x")

        self._btn_cancel = tk.Button(
            inner,
            text="◼  CANCELAR",
            command=self._cancel_backup,
            bg=C["bg4"],
            fg=C["danger"],
            font=F["base"],
            relief="flat",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            activebackground=C["red_glow"],
            activeforeground=C["danger"],
            state="disabled",
        )
        self._btn_cancel.pack(fill="x", pady=(6, 0))

        tk.Frame(card, bg=C["border"], height=1).pack(fill="x")

    def _build_backups_card(self, parent: tk.Frame) -> None:
        card = tk.Frame(parent, bg=C["bg3"], bd=0)
        card.pack(fill="both", expand=True, padx=2)
        tk.Frame(card, bg=C["border"], height=1).pack(fill="x")

        header = tk.Frame(card, bg=C["bg2"], padx=14, pady=8)
        header.pack(fill="x")
        tk.Label(header, text="◈ BACKUPS ACTIVOS", bg=C["bg2"], fg=C["red"], font=F["sm"]).pack(side="left")
        self._backup_count_lbl = tk.Label(header, text="0", bg=C["bg2"], fg=C["fg3"], font=F["sm"])
        self._backup_count_lbl.pack(side="right")

        tk.Frame(card, bg=C["border"], height=1).pack(fill="x")

        # Treeview de backups
        tree_frame = tk.Frame(card, bg=C["bg3"])
        tree_frame.pack(fill="both", expand=True)

        self._backup_tree = ttk.Treeview(
            tree_frame,
            columns=("name", "date", "size", "remaining"),
            show="headings",
            selectmode="browse",
            height=6,
        )
        self._backup_tree.heading("name", text="NOMBRE", anchor="w")
        self._backup_tree.heading("date", text="FECHA", anchor="w")
        self._backup_tree.heading("size", text="TAMAÑO", anchor="e")
        self._backup_tree.heading("remaining", text="ESTADO", anchor="e")

        self._backup_tree.column("name", width=120, minwidth=100)
        self._backup_tree.column("date", width=120, minwidth=100)
        self._backup_tree.column("size", width=80, minwidth=60, anchor="e")
        self._backup_tree.column("remaining", width=90, minwidth=70, anchor="e")

        scroll_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self._backup_tree.yview)
        scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=self._backup_tree.xview)
        self._backup_tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self._backup_tree.pack(side="left", fill="both", expand=True)

        # Tags
        self._backup_tree.tag_configure("ok",      foreground=C["green"])
        self._backup_tree.tag_configure("warning", foreground=C["yellow"])
        self._backup_tree.tag_configure("expired", foreground=C["danger"])
        self._backup_tree.tag_configure("deleted", foreground=C["fg3"])

        # Botones de acción sobre backups
        btn_row = tk.Frame(card, bg=C["bg3"], padx=10, pady=8)
        btn_row.pack(fill="x")

        btn_cfg = dict(
            relief="flat", bd=0, padx=8, pady=5, cursor="hand2", font=F["sm"]
        )

        self._btn_download = tk.Button(
            btn_row,
            text="⬇ Descargar",
            command=self._download_backup,
            bg=C["bg4"], fg=C["blue"],
            activebackground=C["bg3"], activeforeground=C["blue"],
            state="disabled",
            **btn_cfg,
        )
        self._btn_download.pack(side="left", padx=(0, 4))

        self._btn_delete_bk = tk.Button(
            btn_row,
            text="✕ Eliminar",
            command=self._delete_backup,
            bg=C["bg4"], fg=C["danger"],
            activebackground=C["red_glow"], activeforeground=C["danger"],
            state="disabled",
            **btn_cfg,
        )
        self._btn_delete_bk.pack(side="left")

        tk.Frame(card, bg=C["border"], height=1).pack(fill="x")

        # Activar/desactivar botones según selección
        self._backup_tree.bind("<<TreeviewSelect>>", self._on_backup_selected)

    def _build_footer(self) -> None:
        foot = tk.Frame(self._root, bg=C["bg2"], pady=6)
        tk.Frame(self._root, bg=C["border"], height=1).pack(fill="x", side="bottom")
        foot.pack(fill="x", side="bottom")

        inner = tk.Frame(foot, bg=C["bg2"], padx=16)
        inner.pack(fill="x")

        tk.Label(
            inner,
            text=f"SafingData v{VERSION}  //  SSH Backup Portable",
            bg=C["bg2"],
            fg=C["fg3"],
            font=F["sm"],
        ).pack(side="left")

        # Pulse dot de estado
        self._pulse_canvas = tk.Canvas(inner, width=8, height=8, bg=C["bg2"], highlightthickness=0)
        self._pulse_canvas.create_oval(1, 1, 7, 7, fill=C["fg3"], outline="", tags="dot")
        self._pulse_canvas.pack(side="right", padx=(6, 0))

        self._footer_status = tk.Label(
            inner,
            text="offline",
            bg=C["bg2"],
            fg=C["fg3"],
            font=F["sm"],
        )
        self._footer_status.pack(side="right")

    # ──────────────────────────────────────────────────────────
    # Conexión SSH
    # ──────────────────────────────────────────────────────────

    def _toggle_connection(self) -> None:
        if self._client.connected:
            self._disconnect()
        else:
            self._prompt_connect()

    def _prompt_connect(self) -> None:
        """Solicita la contraseña y conecta."""
        if self._is_busy:
            return

        # Diálogo simple de contraseña
        pwd = simpledialog.askstring(
            "Autenticación SSH",
            f"Contraseña para {self._cfg['user']}@{self._cfg['host']}:{self._cfg['port']}",
            show="*",
            parent=self._root,
        )
        if not pwd:
            return

        self._set_ui_state("connecting")
        self._progress.log(f"Conectando a {self._cfg['host']}:{self._cfg['port']}...", "cmd")

        def _do_connect() -> None:
            try:
                self._client.connect(
                    self._cfg["host"],
                    self._cfg["port"],
                    self._cfg["user"],
                    pwd,
                )
                self._remote_base_abs = self._client.resolve_remote_base(
                    self._cfg["remote_base"]
                )
                disk = self._client.get_disk_info()
                self._root.after(0, lambda: self._on_connected(disk))
            except Exception as exc:
                self._root.after(0, lambda: self._on_connect_failed(str(exc)))

        t = threading.Thread(target=_do_connect, daemon=True)
        t.start()

    def _on_connected(self, disk: dict) -> None:
        self._disk_info = disk
        self._set_ui_state("connected")
        self._update_space_display()
        self._progress.log("Conexión establecida exitosamente.", "success")
        self._progress.log(f"Directorio remoto: {self._remote_base_abs}", "info")
        self._refresh_backup_list()

    def _on_connect_failed(self, error: str) -> None:
        self._set_ui_state("disconnected")
        self._progress.log(f"Error de conexión: {error}", "error")
        messagebox.showerror("Error de Conexión", f"No se pudo conectar:\n\n{error}", parent=self._root)

    def _disconnect(self) -> None:
        self._client.disconnect()
        self._set_ui_state("disconnected")
        self._progress.log("Desconectado del servidor.", "info")

    # ──────────────────────────────────────────────────────────
    # Estado de la UI
    # ──────────────────────────────────────────────────────────

    def _set_ui_state(self, state: str) -> None:
        """state: connecting | connected | disconnected | busy"""
        if state == "connecting":
            self._conn_dot.itemconfigure("dot", fill=C["yellow"])
            self._conn_lbl.configure(text="CONECTANDO...", fg=C["yellow"])
            self._btn_conn.configure(text="...", state="disabled")
            self._btn_backup.configure(state="disabled")
            self._footer_status.configure(text="conectando...", fg=C["yellow"])
            self._pulse_canvas.itemconfigure("dot", fill=C["yellow"])

        elif state == "connected":
            self._conn_dot.itemconfigure("dot", fill=C["green"])
            self._conn_lbl.configure(text="CONECTADO", fg=C["green"])
            self._btn_conn.configure(text="DESCONECTAR", state="normal",
                                     bg=C["bg4"], fg=C["fg2"],
                                     activebackground=C["bg3"])
            self._btn_backup.configure(state="normal")
            self._footer_status.configure(text="conectado", fg=C["green"])
            self._pulse_canvas.itemconfigure("dot", fill=C["green"])
            self._btn_download.configure(state="normal")
            self._btn_delete_bk.configure(state="normal")

        elif state == "disconnected":
            self._conn_dot.itemconfigure("dot", fill=C["fg3"])
            self._conn_lbl.configure(text="DESCONECTADO", fg=C["fg3"])
            self._btn_conn.configure(text="CONECTAR", state="normal",
                                     bg=C["red"], fg=C["fg"],
                                     activebackground=C["red_hi"])
            self._btn_backup.configure(state="disabled")
            self._footer_status.configure(text="offline", fg=C["fg3"])
            self._pulse_canvas.itemconfigure("dot", fill=C["fg3"])
            self._btn_download.configure(state="disabled")
            self._btn_delete_bk.configure(state="disabled")

        elif state == "busy":
            self._btn_backup.configure(state="disabled")
            self._btn_conn.configure(state="disabled")
            self._btn_cancel.configure(state="normal")
            self._file_selector.set_enabled(False)
            self._btn_download.configure(state="disabled")
            self._btn_delete_bk.configure(state="disabled")

        elif state == "idle_connected":
            self._btn_backup.configure(state="normal")
            self._btn_conn.configure(state="normal")
            self._btn_cancel.configure(state="disabled")
            self._file_selector.set_enabled(True)
            self._btn_download.configure(state="normal")
            self._btn_delete_bk.configure(state="normal")

    # ──────────────────────────────────────────────────────────
    # Backup
    # ──────────────────────────────────────────────────────────

    def _start_backup(self) -> None:
        if self._is_busy or not self._client.connected:
            return

        paths = self._file_selector.get_paths()
        if not paths:
            messagebox.showwarning(
                "Sin selección",
                "Selecciona al menos un archivo o carpeta antes de iniciar el backup.",
                parent=self._root,
            )
            return

        # Verificar espacio
        local_size = self._file_selector.get_total_size()
        ok, available, msg = storage_mod.check_quota(
            self._disk_info.get("total", 0),
            self._disk_info.get("used", 0),
            local_size,
        )
        if not ok:
            messagebox.showerror("Espacio insuficiente", msg, parent=self._root)
            return

        # ID del backup = timestamp
        default_backup_id = datetime.now().strftime("backup_%Y%m%d_%H%M%S")
        backup_id = simpledialog.askstring(
            "Nombre del Backup",
            "Introduce un nombre para el backup (sin espacios ni caracteres especiales):",
            initialvalue=default_backup_id,
            parent=self._root,
        )
        if not backup_id:
            return

        # Confirmar
        confirm = messagebox.askyesno(
            "Confirmar Backup",
            f"Se subirán {_fmt_size(local_size)} al servidor.\n\n"
            f"Espacio disponible: {_fmt_size(available)}\n\n"
            f"¿Continuar?",
            parent=self._root,
        )
        if not confirm:
            return

        # Guardar selección en config
        self._cfg["selected_paths"] = paths
        cfg_module.save_config(self._cfg)

        self._is_busy = True
        self._set_ui_state("busy")
        self._progress.clear_log()
        self._progress.set_progress(0, "", "SUBIENDO...")
        self._progress.set_status("SUBIENDO...", "busy")

        self._backup_thread = threading.Thread(
            target=self._run_backup,
            args=(backup_id, paths, local_size),
            daemon=True,
        )
        self._backup_thread.start()

    def _run_backup(self, backup_id: str, paths: list, total_size: int) -> None:
        remote_dest = f"{self._remote_base_abs}/{backup_id}"

        self._root.after(0, lambda: self._progress.log(f"Backup ID: {backup_id}", "cmd"))
        self._root.after(0, lambda: self._progress.log(f"Destino: {remote_dest}", "info"))
        self._root.after(0, lambda: self._progress.log(
            f"Total a subir: {_fmt_size(total_size)}", "info"
        ))

        import time
        start_time = time.time()
        
        uploaded_bytes = 0
        upload_errors = []
        
        tracked_uploaded = 0
        last_transferred = 0
        current_file = ""

        def _progress_cb(filename: str, transferred: int, total: int) -> None:
            nonlocal tracked_uploaded, last_transferred, current_file
            
            if filename != current_file:
                tracked_uploaded += last_transferred
                current_file = filename
                last_transferred = 0

            last_transferred = transferred
            global_transferred = tracked_uploaded + transferred

            if total > 0:
                global_pct = min(99, global_transferred / max(total_size, 1) * 100)
                
                elapsed = time.time() - start_time
                if elapsed > 0 and global_transferred > 0:
                    speed = global_transferred / elapsed
                    remaining_bytes = max(0, total_size - global_transferred)
                    eta_seconds = remaining_bytes / speed
                    
                    h = int(eta_seconds // 3600)
                    m = int((eta_seconds % 3600) // 60)
                    s = int(eta_seconds % 60)
                    if h > 0:
                        eta_str = f"{h:02d}:{m:02d}:{s:02d}"
                    else:
                        eta_str = f"{m:02d}:{s:02d}"
                else:
                    eta_str = "--:--"

                self._root.after(0, lambda p=global_pct, f=filename, e=eta_str:
                    self._progress.set_progress(p, f"  {f} | ETA: {e}", "SUBIENDO...")
                )

        try:
            for path in paths:
                if self._client._cancel_flag.is_set():
                    break
                p = Path(path)
                self._root.after(0, lambda n=p.name: self._progress.log(f"→ {n}", "cmd"))
                try:
                    self._client.upload_path(path, remote_dest, _progress_cb)
                    size = storage_mod.get_local_size([path])
                    uploaded_bytes += size
                    self._root.after(0, lambda n=p.name, s=size:
                        self._progress.log(f"  ✓ {n} ({_fmt_size(s)})", "success")
                    )
                except InterruptedError:
                    break
                except Exception as exc:
                    upload_errors.append(str(exc))
                    self._root.after(0, lambda e=str(exc), n=p.name:
                        self._progress.log(f"  ✗ {n}: {e}", "error")
                    )

            cancelled = self._client._cancel_flag.is_set()
            if cancelled:
                self._root.after(0, lambda: self._on_backup_cancelled(backup_id, remote_dest))
            elif upload_errors and uploaded_bytes == 0:
                self._root.after(0, lambda: self._on_backup_failed(upload_errors))
            else:
                self._root.after(0, lambda: self._on_backup_complete(
                    backup_id, paths, uploaded_bytes, upload_errors
                ))
        except Exception as exc:
            self._root.after(0, lambda e=str(exc): self._on_backup_failed([e]))

    def _on_backup_complete(
        self, backup_id: str, paths: list, size: int, errors: list
    ) -> None:
        self._is_busy = False
        self._progress.set_progress(100, "", "COMPLETADO")
        self._progress.set_status("COMPLETADO", "ok")
        self._progress.log(f"Backup completado: {_fmt_size(size)} subidos.", "success")
        if errors:
            self._progress.log(f"  {len(errors)} error(s) ignorado(s).", "warning")

        sched.record_backup(backup_id, paths, size)
        self._refresh_backup_list()
        self._set_ui_state("idle_connected")
        self._refresh_disk_info()

        messagebox.showinfo(
            "Backup completado",
            f"El backup se completó exitosamente.\n\n"
            f"ID: {backup_id}\n"
            f"Tamaño: {_fmt_size(size)}\n\n"
            f"Puedes descargarlo desde la lista de backups.",
            parent=self._root,
        )

    def _on_backup_failed(self, errors: list) -> None:
        self._is_busy = False
        self._progress.set_status("ERROR", "err")
        self._progress.log(f"Backup fallido: {errors[0]}", "error")
        self._set_ui_state("idle_connected")
        messagebox.showerror("Error en backup", f"El backup falló:\n\n{errors[0]}", parent=self._root)

    def _on_backup_cancelled(self, backup_id: str, remote_dest: str) -> None:
        self._is_busy = False
        self._progress.set_status("CANCELADO", "err")
        self._progress.log("Backup cancelado por el usuario. Limpiando...", "warning")
        # Limpiar lo que se subió parcialmente
        try:
            self._client.delete_remote_path(remote_dest)
            self._progress.log("Archivos parciales eliminados.", "info")
        except Exception:
            pass
        self._client._cancel_flag.clear()
        self._set_ui_state("idle_connected")

    def _cancel_backup(self) -> None:
        if self._is_busy:
            self._client.cancel()
            self._btn_cancel.configure(state="disabled")
            self._progress.log("Cancelando backup...", "warning")

    # ──────────────────────────────────────────────────────────
    # Gestión de backups guardados
    # ──────────────────────────────────────────────────────────

    def _refresh_backup_list(self) -> None:
        """Actualiza la lista de backups en el panel derecho."""
        self._backup_tree.delete(*self._backup_tree.get_children())
        backups = sched.get_all_backups()
        active = [b for b in backups if not b["deleted"]]
        self._backup_count_lbl.configure(text=str(len(active)))

        for b in backups:
            if b["deleted"]:
                continue
            date_str = b["created_at"].strftime("%d/%m/%y %H:%M")
            size_str = _fmt_size(b["size_bytes"])

            self._backup_tree.insert(
                "", "end",
                iid=b["id"],
                values=(b["id"], date_str, size_str, "GUARDADO"),
                tags=("ok",),
            )

    def _on_backup_selected(self, _event=None) -> None:
        selected = self._backup_tree.selection()
        state = "normal" if selected and self._client.connected else "disabled"
        self._btn_download.configure(state=state)
        self._btn_delete_bk.configure(state=state)

    def _download_backup(self) -> None:
        selected = self._backup_tree.selection()
        if not selected or not self._client.connected:
            return

        backup_id = selected[0]
        
        # Obtener tamaño total para calcular progreso global
        backups = sched.get_all_backups()
        target_backup = next((b for b in backups if b["id"] == backup_id), None)
        total_size = target_backup["size_bytes"] if target_backup else 1

        dest = filedialog.askdirectory(
            title="Selecciona dónde guardar el backup",
            parent=self._root,
        )
        if not dest:
            return

        remote_path = f"{self._remote_base_abs}/{backup_id}"
        self._set_ui_state("busy")
        self._progress.clear_log()
        self._progress.log(f"Descargando backup {backup_id}...", "cmd")
        self._progress.log(f"Total a descargar: {_fmt_size(total_size)}", "info")
        self._progress.set_status("DESCARGANDO...", "busy")

        def _do_download() -> None:
            import time
            start_time = time.time()
            downloaded_bytes = 0
            last_transferred = 0
            current_file = ""

            def _progress_cb(filename: str, transferred: int, total: int) -> None:
                nonlocal downloaded_bytes, last_transferred, current_file

                if filename != current_file:
                    downloaded_bytes += last_transferred
                    current_file = filename
                    last_transferred = 0

                last_transferred = transferred
                global_transferred = downloaded_bytes + transferred

                global_pct = min(99, global_transferred / max(total_size, 1) * 100)
                
                elapsed = time.time() - start_time
                if elapsed > 0 and global_transferred > 0:
                    speed = global_transferred / elapsed
                    remaining_bytes = max(0, total_size - global_transferred)
                    eta_seconds = remaining_bytes / speed
                    
                    h = int(eta_seconds // 3600)
                    m = int((eta_seconds % 3600) // 60)
                    s = int(eta_seconds % 60)
                    if h > 0:
                        eta_str = f"{h:02d}:{m:02d}:{s:02d}"
                    else:
                        eta_str = f"{m:02d}:{s:02d}"
                else:
                    eta_str = "--:--"

                self._root.after(0, lambda p=global_pct, f=filename, e=eta_str:
                    self._progress.set_progress(p, f"  {f} | ETA: {e}", "DESCARGANDO...")
                )

            try:
                self._client.download_path(remote_path, dest, progress_cb=_progress_cb)
                self._root.after(0, lambda: self._on_download_complete(backup_id, dest))
            except Exception as exc:
                self._root.after(0, lambda e=str(exc): self._on_download_failed(e))

        threading.Thread(target=_do_download, daemon=True).start()

    def _on_download_complete(self, backup_id: str, dest: str) -> None:
        self._progress.log(f"Descarga completada en: {dest}", "success")
        self._progress.set_status("COMPLETADO", "ok")
        self._set_ui_state("idle_connected")
        messagebox.showinfo(
            "Descarga completa",
            f"El backup se descargó en:\n{dest}/{backup_id}",
            parent=self._root,
        )

    def _on_download_failed(self, error: str) -> None:
        self._progress.log(f"Error en descarga: {error}", "error")
        self._progress.set_status("ERROR", "err")
        self._set_ui_state("idle_connected")
        messagebox.showerror("Error de descarga", f"No se pudo descargar:\n\n{error}", parent=self._root)

    def _delete_backup(self) -> None:
        selected = self._backup_tree.selection()
        if not selected or not self._client.connected:
            return

        backup_id = selected[0]
        confirm = messagebox.askyesno(
            "Eliminar backup",
            f"¿Eliminar permanentemente el backup:\n{backup_id}?\n\n"
            f"Esta acción no se puede deshacer.\n"
            f"Asegúrate de haber descargado los datos si los necesitas.",
            icon="warning",
            parent=self._root,
        )
        if not confirm:
            return

        self._progress.log(f"Eliminando backup {backup_id}...", "cmd")
        remote_path = f"{self._remote_base_abs}/{backup_id}"

        def _do_delete() -> None:
            try:
                self._client.delete_remote_path(remote_path)
                sched.mark_deleted(backup_id)
                self._root.after(0, lambda: self._on_delete_complete(backup_id))
            except Exception as exc:
                self._root.after(0, lambda e=str(exc): self._progress.log(
                    f"Error al eliminar: {e}", "error"
                ))

        threading.Thread(target=_do_delete, daemon=True).start()

    def _on_delete_complete(self, backup_id: str) -> None:
        self._progress.log(f"Backup {backup_id} eliminado.", "success")
        self._refresh_backup_list()
        self._refresh_disk_info()

    # ──────────────────────────────────────────────────────────
    # Actualización de espacio
    # ──────────────────────────────────────────────────────────

    def _refresh_disk_info(self) -> None:
        if not self._client.connected:
            return

        def _do() -> None:
            try:
                disk = self._client.get_disk_info()
                self._root.after(0, lambda d=disk: self._on_disk_info(d))
            except Exception:
                pass

        threading.Thread(target=_do, daemon=True).start()

    def _on_disk_info(self, disk: dict) -> None:
        self._disk_info = disk
        self._update_space_display()

    def _update_space_display(self) -> None:
        total = self._disk_info.get("total", 0)
        used = self._disk_info.get("used", 0)
        reserve = 20 * 1024 ** 3
        available = max(0, total - reserve - used)

        self._space_avail_lbl.configure(text=_fmt_size(available))
        self._space_used_lbl.configure(text=f"usado: {_fmt_size(used)}")
        self._space_total_lbl.configure(text=f"total: {_fmt_size(total)}")

        # Dibujar barra
        w = self._space_canvas.winfo_width()
        if w <= 1:
            w = 280

        self._space_canvas.delete("all")
        if total > 0:
            used_pct = min(1.0, used / total)
            reserve_pct = min(1.0, reserve / total)
            avail_pct = max(0, 1.0 - used_pct - reserve_pct)

            x0 = 0
            # Segmento usado (rojo)
            x1 = int(w * used_pct)
            if x1 > 0:
                self._space_canvas.create_rectangle(x0, 0, x1, 8, fill=C["red"], outline="")
            # Segmento disponible (verde)
            x2 = int(w * (used_pct + avail_pct))
            if x2 > x1:
                self._space_canvas.create_rectangle(x1, 0, x2, 8, fill=C["green"], outline="")
            # Segmento reserva sistema (gris oscuro)
            if x2 < w:
                self._space_canvas.create_rectangle(x2, 0, w, 8, fill=C["fg3"], outline="")

    # ──────────────────────────────────────────────────────────
    # Callbacks
    # ──────────────────────────────────────────────────────────

    def _on_selection_change(self) -> None:
        size = self._file_selector.get_total_size()
        self._sel_size_var.set(_fmt_size(size))

    # ──────────────────────────────────────────────────────────
    # Configuración
    # ──────────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        """Abre el diálogo de configuración SSH."""
        dlg = tk.Toplevel(self._root)
        dlg.title("Configuración SSH")
        dlg.configure(bg=C["bg"])
        dlg.resizable(False, False)
        dlg.grab_set()

        # Centrar
        dlg.geometry("420x320")
        dlg.update_idletasks()
        x = self._root.winfo_x() + (self._root.winfo_width() - 420) // 2
        y = self._root.winfo_y() + (self._root.winfo_height() - 320) // 2
        dlg.geometry(f"420x320+{x}+{y}")

        # Borde
        tk.Frame(dlg, bg=C["border"], height=2).pack(fill="x")
        header = tk.Frame(dlg, bg=C["bg2"], pady=10, padx=16)
        header.pack(fill="x")
        tk.Label(header, text="◈ CONFIGURACIÓN SSH", bg=C["bg2"], fg=C["red"], font=F["sm"]).pack(side="left")
        tk.Frame(dlg, bg=C["border"], height=1).pack(fill="x")

        form = tk.Frame(dlg, bg=C["bg"], padx=20, pady=16)
        form.pack(fill="both", expand=True)

        fields = [
            ("HOST",    "host",         self._cfg["host"]),
            ("PUERTO",  "port",         str(self._cfg["port"])),
            ("USUARIO", "user",         self._cfg["user"]),
            ("DIR REMOTO", "remote_base", self._cfg["remote_base"]),
        ]

        entries = {}
        for label, key, default in fields:
            row = tk.Frame(form, bg=C["bg"])
            row.pack(fill="x", pady=4)
            tk.Label(row, text=f"{label:<12}", bg=C["bg"], fg=C["fg3"], font=F["sm"]).pack(side="left")
            e = tk.Entry(
                row,
                bg=C["bg_input"],
                fg=C["fg"],
                insertbackground=C["red"],
                relief="flat",
                bd=4,
                font=F["base"],
            )
            e.insert(0, default)
            e.pack(side="left", fill="x", expand=True)
            entries[key] = e

        tk.Frame(dlg, bg=C["border"], height=1).pack(fill="x")
        btn_row = tk.Frame(dlg, bg=C["bg2"], pady=10, padx=16)
        btn_row.pack(fill="x")

        def _save() -> None:
            self._cfg["host"] = entries["host"].get().strip()
            self._cfg["port"] = int(entries["port"].get().strip() or "22")
            self._cfg["user"] = entries["user"].get().strip()
            self._cfg["remote_base"] = entries["remote_base"].get().strip()
            cfg_module.save_config(self._cfg)
            dlg.destroy()
            # Actualizar labels
            self._progress.log("Configuración guardada.", "success")

        tk.Button(
            btn_row, text="GUARDAR",
            command=_save,
            bg=C["red"], fg=C["fg"],
            font=F["md"], relief="flat", bd=0,
            padx=16, pady=6, cursor="hand2",
            activebackground=C["red_hi"],
        ).pack(side="right")

        tk.Button(
            btn_row, text="Cancelar",
            command=dlg.destroy,
            bg=C["bg4"], fg=C["fg2"],
            font=F["base"], relief="flat", bd=0,
            padx=12, pady=6, cursor="hand2",
            activebackground=C["bg3"],
        ).pack(side="right", padx=(0, 8))

    # ──────────────────────────────────────────────────────────
    # Ejecutar
    # ──────────────────────────────────────────────────────────

    def run(self) -> None:
        """Inicia el loop principal de Tkinter."""
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._root.mainloop()

    def _on_close(self) -> None:
        if self._is_busy:
            confirm = messagebox.askyesno(
                "Backup en progreso",
                "Hay un backup en curso. ¿Salir de todas formas?\nEl proceso se cancelará.",
                parent=self._root,
            )
            if not confirm:
                return
            self._client.cancel()
        if self._client.connected:
            self._client.disconnect()
        self._root.destroy()
