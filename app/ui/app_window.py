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

VERSION = "1.1.0"

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def get_asset_path(filename: str) -> Path:
    """Retorna la ruta absoluta de un archivo de asset (logo, icon, banner)."""
    candidates = []
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            candidates.append(Path(getattr(sys, '_MEIPASS')) / filename)
        candidates.append(Path(sys.executable).parent / filename)
    candidates.append(_APP_DIR / filename)
    candidates.append(Path.cwd() / filename)

    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


class AppWindow:
    """Ventana principal de SafingData."""

    def __init__(self) -> None:
        self._cfg = cfg_module.load_config()
        self._client = SSHBackupClient()
        self._backup_thread: Optional[threading.Thread] = None
        self._is_busy = False
        self._is_connecting = False
        self._disk_info: dict = {"total": 0, "used": 0, "free": 0}
        self._remote_base_abs: str = ""

        self._root = tk.Tk()
        self._root.title("SafingData — Backup SSH Portable")
        self._root.configure(bg=C["bg"])
        self._root.minsize(960, 700)
        self._root.geometry("1100x760")
        self._root.resizable(True, True)

        # Ocultar ventana principal durante la pantalla de bienvenida (splash)
        self._root.withdraw()

        # Icono ejecutable/ventana
        icon_path = get_asset_path("icono.ico")
        if icon_path.exists():
            try:
                self._root.iconbitmap(str(icon_path))
            except Exception:
                pass
            try:
                if HAS_PIL:
                    ico_img = ImageTk.PhotoImage(Image.open(icon_path))
                    self._root.iconphoto(True, ico_img)
                    self._icon_ref = ico_img
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

        # Lanzar splash screen (banner.png) por 2 segundos
        self._show_splash()

    # ──────────────────────────────────────────────────────────
    # Helper: máquina activa
    # ──────────────────────────────────────────────────────────

    def _machine(self) -> dict:
        """Retorna el dict de la máquina SSH actualmente activa."""
        return cfg_module.get_active_machine(self._cfg)

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

        # ── Logo ────────────────────────────────────────────────
        logo_path = get_asset_path("logo.png")
        if logo_path.exists():
            try:
                if HAS_PIL:
                    pil_logo = Image.open(logo_path)
                    pil_logo = pil_logo.resize((30, 30), Image.Resampling.LANCZOS)
                    self._header_logo_img = ImageTk.PhotoImage(pil_logo)
                else:
                    raw_logo = tk.PhotoImage(file=str(logo_path))
                    sub = max(1, raw_logo.width() // 30)
                    self._header_logo_img = raw_logo.subsample(sub, sub)

                logo_lbl = tk.Label(inner, image=self._header_logo_img, bg=C["bg2"], bd=0)
                logo_lbl.pack(side="left", padx=(0, 10))
            except Exception as e:
                print(f"Error cargando logo.png: {e}")

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
        m = self._machine()
        self._progress.log(f"Perfil activo: {m.get('name', '—')}", "info")
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

        # ── Encabezado con botón mostrar/ocultar ──────────────
        header_row = tk.Frame(inner, bg=C["bg3"])
        header_row.pack(fill="x")
        tk.Label(
            header_row, text="◈ SERVIDOR SSH",
            bg=C["bg3"], fg=C["red"], font=F["sm"],
        ).pack(side="left")

        self._srv_revealed = False
        self._srv_toggle_btn = tk.Button(
            header_row, text="mostrar",
            command=self._toggle_server_reveal,
            bg=C["bg3"], fg=C["fg3"], font=F["xs"],
            relief="flat", bd=0, padx=4, pady=0,
            cursor="hand2",
            activebackground=C["bg3"], activeforeground=C["fg2"],
        )
        self._srv_toggle_btn.pack(side="right")

        info_frame = tk.Frame(inner, bg=C["bg3"])
        info_frame.pack(fill="x", pady=(6, 0))

        machine = self._machine()
        alias = machine.get("name", "—")
        host  = machine.get("host", "—")
        user  = machine.get("user", "—")

        # PERFIL — siempre visible, en rojo
        row_p = tk.Frame(info_frame, bg=C["bg3"])
        row_p.pack(fill="x", pady=1)
        tk.Label(row_p, text=f"{'PERFIL':<8}", bg=C["bg3"], fg=C["fg3"], font=F["sm"]).pack(side="left")
        self._srv_alias_lbl = tk.Label(row_p, text=alias, bg=C["bg3"], fg=C["red"], font=F["base"])
        self._srv_alias_lbl.pack(side="left")

        # HOST — enmascarado por defecto
        row_h = tk.Frame(info_frame, bg=C["bg3"])
        row_h.pack(fill="x", pady=1)
        tk.Label(row_h, text=f"{'HOST':<8}", bg=C["bg3"], fg=C["fg3"], font=F["sm"]).pack(side="left")
        self._srv_host_lbl = tk.Label(row_h, text="••••••••••", bg=C["bg3"], fg=C["fg2"], font=F["base"])
        self._srv_host_lbl.pack(side="left")

        # USUARIO — enmascarado por defecto
        row_u = tk.Frame(info_frame, bg=C["bg3"])
        row_u.pack(fill="x", pady=1)
        tk.Label(row_u, text=f"{'USUARIO':<8}", bg=C["bg3"], fg=C["fg3"], font=F["sm"]).pack(side="left")
        self._srv_user_lbl = tk.Label(row_u, text="••••••••••", bg=C["bg3"], fg=C["fg2"], font=F["base"])
        self._srv_user_lbl.pack(side="left")

        # JUMP HOST badge — visible solo si está configurado
        jump_host = machine.get("jump_host", "")
        self._srv_jump_row = tk.Frame(info_frame, bg=C["bg3"])
        self._srv_jump_row.pack(fill="x", pady=(4, 0))
        self._srv_jump_lbl = tk.Label(
            self._srv_jump_row,
            text=f"⇶ VIA JUMP HOST: {jump_host}" if jump_host else "",
            bg=C["bg3"], fg=C["yellow"], font=F["sm"],
        )
        self._srv_jump_lbl.pack(side="left")

        # Guardar valores reales para el toggle
        self._srv_raw = {"host": host, "user": user}

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
        if self._is_connecting:
            self._cancel_connect()
        elif self._client.connected:
            self._disconnect()
        else:
            self._prompt_connect()

    def _cancel_connect(self) -> None:
        """Aborta el intento de conexión en curso."""
        self._is_connecting = False
        self._client.disconnect()
        self._set_ui_state("disconnected")
        self._progress.log("Conexión cancelada por el usuario.", "warning")

    def _prompt_connect(self) -> None:
        """Solicita la contraseña y conecta usando la máquina activa.
        
        Si el usuario deja la contraseña en blanco, se intenta autenticación
        sin contraseña (agente SSH / Tailscale SSH / clave privada).
        Si cancela el diálogo, se aborta la conexión.
        """
        if self._is_busy or self._is_connecting:
            return

        m = self._machine()
        host      = m.get("host", "")
        port      = m.get("port", 22)
        user      = m.get("user", "")
        remote    = m.get("remote_base", "safingdata_backups")
        alias     = m.get("name", "—")
        jump_host = m.get("jump_host", "") or None
        jump_user = m.get("jump_user", "") or None

        pwd = simpledialog.askstring(
            "Autenticación SSH",
            f"[{alias}]  {user}@{host}:{port}\n\n"
            f"Contraseña SSH (déjala en blanco para usar\n"
            f"Tailscale SSH / clave privada / agente SSH):",
            show="*",
            parent=self._root,
        )
        # None = usuario canceló el diálogo → no conectar
        if pwd is None:
            return
        # Cadena vacía = autenticación sin contraseña (Tailscale / Keys)
        password = pwd if pwd else None

        auth_mode = "Tailscale/Clave" if password is None else "contraseña"
        jump_info = f" via Jump:{jump_host}" if jump_host else ""
        self._is_connecting = True
        self._set_ui_state("connecting")
        self._progress.log(f"Conectando a [{alias}] {host}:{port} ({auth_mode}{jump_info})...", "cmd")

        def _do_connect() -> None:
            try:
                self._client.connect(host, port, user, password,
                                     jump_host=jump_host, jump_user=jump_user)
                if not self._is_connecting:
                    self._client.disconnect()
                    return
                self._remote_base_abs = self._client.resolve_remote_base(remote)
                if not self._is_connecting:
                    self._client.disconnect()
                    return
                disk = self._client.get_disk_info()
                if not self._is_connecting:
                    self._client.disconnect()
                    return
                self._root.after(0, lambda: self._on_connected(disk))
            except Exception as exc:
                if self._is_connecting:
                    self._root.after(0, lambda: self._on_connect_failed(str(exc)))

        t = threading.Thread(target=_do_connect, daemon=True)
        t.start()

    def _on_connected(self, disk: dict) -> None:
        self._is_connecting = False
        self._disk_info = disk
        self._set_ui_state("connected")
        self._update_space_display()
        self._progress.log("Conexión establecida exitosamente.", "success")
        self._progress.log(f"Directorio remoto: {self._remote_base_abs}", "info")
        self._sync_backup_list()

    def _on_connect_failed(self, error: str) -> None:
        self._is_connecting = False
        self._set_ui_state("disconnected")
        self._progress.log(f"Error de conexión: {error}", "error")
        messagebox.showerror("Error de Conexión", f"No se pudo conectar:\n\n{error}", parent=self._root)

    def _disconnect(self) -> None:
        self._is_connecting = False
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
            self._btn_conn.configure(
                text="CANCELAR",
                state="normal",
                bg=C["bg4"],
                fg=C["danger"],
                activebackground=C["red_glow"],
                activeforeground=C["danger"],
            )
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

    def _sync_backup_list(self) -> None:
        """Sincroniza el registro local con los backups existentes en el servidor."""
        try:
            remote_ids = self._client.list_backups(self._remote_base_abs)
            imported = sched.sync_from_server(remote_ids)
            if imported > 0:
                self._progress.log(
                    f"Sincronizacion: {imported} backup(s) importado(s) del servidor.",
                    "success",
                )
            else:
                self._progress.log(
                    "Registro local sincronizado con el servidor.", "info"
                )
        except Exception as exc:
            self._progress.log(
                f"Advertencia: no se pudo sincronizar la lista de backups: {exc}",
                "warning",
            )
        finally:
            self._refresh_backup_list()

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
            size_str = _fmt_size(b["size_bytes"]) if b["size_bytes"] > 0 else "—"
            estado = "IMPORTADO" if b.get("imported") else "GUARDADO"
            tag = "warning" if b.get("imported") else "ok"

            self._backup_tree.insert(
                "", "end",
                iid=b["id"],
                values=(b["id"], date_str, size_str, estado),
                tags=(tag,),
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
    # Configuración — Gestor de máquinas SSH
    # ──────────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        """Gestor de múltiples máquinas SSH con nombre clave."""
        dlg = tk.Toplevel(self._root)
        dlg.title("Gestión de máquinas SSH")
        dlg.configure(bg=C["bg"])
        dlg.resizable(False, False)
        dlg.grab_set()

        # ── Centrar ────────────────────────────────────────────
        W, H = 500, 570
        dlg.geometry(f"{W}x{H}")
        dlg.update_idletasks()
        x = self._root.winfo_x() + (self._root.winfo_width() - W) // 2
        y = self._root.winfo_y() + (self._root.winfo_height() - H) // 2
        dlg.geometry(f"{W}x{H}+{x}+{y}")

        # ── Cabecera ───────────────────────────────────────────
        tk.Frame(dlg, bg=C["red"], height=2).pack(fill="x")
        header = tk.Frame(dlg, bg=C["bg2"], pady=12, padx=18)
        header.pack(fill="x")
        tk.Label(
            header, text="⚙  GESTIÓN DE MÁQUINAS SSH",
            bg=C["bg2"], fg=C["red"], font=F["md"],
        ).pack(side="left")
        tk.Label(
            header, text=f"v{VERSION}",
            bg=C["bg2"], fg=C["fg3"], font=F["sm"],
        ).pack(side="right")
        tk.Frame(dlg, bg=C["border"], height=1).pack(fill="x")

        # ── Selector de máquina ────────────────────────────────
        sel_bar = tk.Frame(dlg, bg=C["bg3"], padx=18, pady=10)
        sel_bar.pack(fill="x")
        tk.Label(sel_bar, text="MÁQUINA:", bg=C["bg3"], fg=C["fg3"], font=F["sm"]).pack(side="left", padx=(0, 8))

        machine_names = cfg_module.get_machine_names(self._cfg)
        active_name = self._cfg.get("active_machine", machine_names[0] if machine_names else "")
        selected_var = tk.StringVar(value=active_name)

        machine_combo = ttk.Combobox(
            sel_bar, textvariable=selected_var, values=machine_names,
            state="readonly", font=F["base"], width=22,
        )
        machine_combo.pack(side="left", padx=(0, 10))

        # Estado compartido del formulario
        entries: dict[str, tk.Entry] = {}
        port_ph: list[bool] = [False]   # [is_placeholder_active]

        def _make_entry(parent, label_text, hint_text, value, is_port=False):
            lbl_row = tk.Frame(parent, bg=C["bg"])
            lbl_row.pack(fill="x", pady=(8, 1))
            tk.Label(lbl_row, text=label_text, bg=C["bg"], fg=C["fg3"], font=F["sm"]).pack(side="left")
            tk.Label(lbl_row, text=hint_text, bg=C["bg"], fg=C["fg_dim"], font=F["xs"]).pack(side="right")

            border = tk.Frame(parent, bg=C["border"], padx=1, pady=1)
            border.pack(fill="x")

            e = tk.Entry(border, bg=C["bg_input"], fg=C["fg"],
                         insertbackground=C["red"], relief="flat", bd=4, font=F["base"])

            if is_port and (not value or value == "22"):
                e.insert(0, "22")
                e.configure(fg=C["fg3"])
                port_ph[0] = True

                def _fi(ev, en=e, b=border):
                    if port_ph[0]:
                        en.delete(0, "end")
                        en.configure(fg=C["fg"])
                        port_ph[0] = False
                    b.configure(bg=C["red"])

                def _fo(ev, en=e, b=border):
                    if not en.get().strip():
                        en.insert(0, "22")
                        en.configure(fg=C["fg3"])
                        port_ph[0] = True
                    b.configure(bg=C["border"])

                e.bind("<FocusIn>",  _fi)
                e.bind("<FocusOut>", _fo)
            else:
                e.insert(0, value or "")
                e.bind("<FocusIn>",  lambda ev, b=border: b.configure(bg=C["red"]))
                e.bind("<FocusOut>", lambda ev, b=border: b.configure(bg=C["border"]))

            e.pack(fill="x")
            return e

        # ── Formulario (dinámico) ──────────────────────────────
        tk.Frame(dlg, bg=C["border"], height=1).pack(fill="x")
        form = tk.Frame(dlg, bg=C["bg"], padx=20, pady=10)
        form.pack(fill="both", expand=True)

        def _build_form(machine: dict) -> None:
            for w in form.winfo_children():
                w.destroy()
            entries.clear()
            port_ph[0] = False
            port_val = machine.get("port", 22)
            port_str = str(port_val) if port_val != 22 else ""

            entries["name"]        = _make_entry(form, "NOMBRE CLAVE", "Alias único (ej: Casa, Trabajo, VPS)", machine.get("name", ""))
            entries["host"]        = _make_entry(form, "HOST / IP",    "Dirección o dominio del servidor SSH",  machine.get("host", ""))
            entries["port"]        = _make_entry(form, "PUERTO",       "Opcional — vacío = 22",                port_str, is_port=True)
            entries["user"]        = _make_entry(form, "USUARIO SSH",  "Nombre de usuario en el servidor",     machine.get("user", ""))
            entries["remote_base"] = _make_entry(form, "DIR. REMOTO",  "Carpeta base de backups en el servidor", machine.get("remote_base", "safingdata_backups"))
            # ── Separador sección Jump Host ──────────────────────────
            sep_frame = tk.Frame(form, bg=C["bg"])
            sep_frame.pack(fill="x", pady=(12, 0))
            tk.Label(
                sep_frame,
                text="⇶ JUMP HOST (opcional — para Tailscale sin cliente instalado)",
                bg=C["bg"], fg=C["yellow"], font=F["sm"],
            ).pack(side="left")
            tk.Frame(form, bg=C["border"], height=1).pack(fill="x", pady=(4, 0))
            entries["jump_host"] = _make_entry(form, "JUMP HOST",  "Host/IP del bastión con Tailscale (ej: bastion.mi.com)", machine.get("jump_host", ""))
            entries["jump_user"] = _make_entry(form, "JUMP USER",  "Usuario SSH en el bastión (vacío = mismo usuario)",      machine.get("jump_user", ""))

        def _get_values():
            name      = entries["name"].get().strip()
            host      = entries["host"].get().strip()
            pr        = entries["port"].get().strip()
            port      = 22 if (not pr or port_ph[0]) else (int(pr) if pr.isdigit() else 22)
            user      = entries["user"].get().strip()
            remote    = entries["remote_base"].get().strip()
            jump_host = entries["jump_host"].get().strip() if "jump_host" in entries else ""
            jump_user = entries["jump_user"].get().strip() if "jump_user" in entries else ""
            return name, host, port, user, remote, jump_host, jump_user

        # ── Barra de estado ────────────────────────────────────
        tk.Frame(dlg, bg=C["border"], height=1).pack(fill="x")
        status_bar = tk.Frame(dlg, bg=C["bg3"], padx=18, pady=8)
        status_bar.pack(fill="x")
        status_dot = tk.Canvas(status_bar, width=8, height=8, bg=C["bg3"], highlightthickness=0)
        status_dot.create_oval(1, 1, 7, 7, fill=C["fg3"], outline="", tags="dot")
        status_dot.pack(side="left", padx=(0, 6))
        status_lbl = tk.Label(status_bar, text="Sin verificar", bg=C["bg3"], fg=C["fg3"], font=F["sm"])
        status_lbl.pack(side="left")

        def _set_status(msg, color):
            status_dot.itemconfigure("dot", fill=color)
            status_lbl.configure(text=msg, fg=color)

        def _validate() -> bool:
            name, host, port, user, remote, jump_host, jump_user = _get_values()
            if not name:
                _set_status("NOMBRE CLAVE no puede estar vacío.", C["danger"])
                entries["name"].focus_set(); return False
            if not host:
                _set_status("HOST no puede estar vacío.", C["danger"])
                entries["host"].focus_set(); return False
            pr = entries["port"].get().strip()
            if pr and not port_ph[0] and not pr.isdigit():
                _set_status("PUERTO debe ser un número (ej: 22).", C["danger"])
                entries["port"].focus_set(); return False
            if not user:
                _set_status("USUARIO no puede estar vacío.", C["danger"])
                entries["user"].focus_set(); return False
            if not remote:
                _set_status("DIR. REMOTO no puede estar vacío.", C["danger"])
                entries["remote_base"].focus_set(); return False
            return True

        def _load_machine(name: str) -> None:
            m = next((x for x in self._cfg.get("machines", []) if x.get("name") == name), None)
            if m:
                _build_form(m)
                _set_status("Sin verificar", C["fg3"])

        # Cargar máquina inicial
        initial = next(
            (m for m in self._cfg.get("machines", []) if m.get("name") == active_name),
            self._cfg.get("machines", [{}])[0] if self._cfg.get("machines") else {},
        )
        _build_form(initial)

        machine_combo.bind("<<ComboboxSelected>>", lambda e: _load_machine(selected_var.get()))

        # ── Botón "+ Nueva" ────────────────────────────────────
        def _new_machine() -> None:
            new_name = simpledialog.askstring(
                "Nueva máquina",
                "Nombre clave para la nueva máquina SSH:\n(ej: Trabajo, VPS, Casa):",
                parent=dlg,
            )
            if not new_name or not new_name.strip():
                return
            new_name = new_name.strip()
            if new_name in cfg_module.get_machine_names(self._cfg):
                messagebox.showerror("Nombre duplicado", f"Ya existe '{new_name}'.", parent=dlg)
                return
            cfg_module.upsert_machine(self._cfg, {
                "name": new_name, "host": "", "port": 22, "user": "",
                "remote_base": "safingdata_backups", "jump_host": "", "jump_user": "",
            })
            names = cfg_module.get_machine_names(self._cfg)
            machine_combo["values"] = names
            selected_var.set(new_name)
            _load_machine(new_name)

        tk.Button(
            sel_bar, text="+ Nueva", command=_new_machine,
            bg=C["bg4"], fg=C["blue"], font=F["sm"], relief="flat", bd=0,
            padx=8, pady=4, cursor="hand2",
            activebackground=C["bg3"], activeforeground=C["blue"],
        ).pack(side="left")

        # ── Acciones ───────────────────────────────────────────

        def _test_connection() -> None:
            if not _validate():
                return
            name, host, port, user, remote, jump_host, jump_user = _get_values()
            pwd = simpledialog.askstring(
                "Contraseña SSH",
                f"[{name}]  {user}@{host}:{port}\n(solo para la prueba, no se guarda)",
                show="*", parent=dlg,
            )
            if not pwd:
                return
            btn_test.configure(state="disabled", text="Probando...")
            _set_status("Conectando...", C["yellow"])
            dlg.update()

            def _do_test():
                import paramiko
                try:
                    c = paramiko.SSHClient()
                    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    sock = None
                    if jump_host:
                        import paramiko as _pm
                        _jump_u = jump_user or user
                        proxy_cmd = (
                            f"ssh -o StrictHostKeyChecking=no "
                            f"-o UserKnownHostsFile=/dev/null "
                            f"-W {host}:{port} "
                            f"{_jump_u}@{jump_host}"
                        )
                        sock = _pm.ProxyCommand(proxy_cmd)
                    c.connect(hostname=host, port=port, username=user, password=pwd, timeout=8, sock=sock)
                    c.close()
                    msg = "✓  Conexión exitosa." + (f" (via {jump_host})" if jump_host else "")
                    dlg.after(0, lambda m=msg: (
                        _set_status(m, C["green"]),
                        btn_test.configure(state="normal", text="Probar conexión"),
                    ))
                except Exception as exc:
                    err = str(exc)
                    dlg.after(0, lambda e=err: (
                        _set_status(f"✗  {e[:52]}", C["danger"]),
                        btn_test.configure(state="normal", text="Probar conexión"),
                    ))

            threading.Thread(target=_do_test, daemon=True).start()

        def _delete_machine() -> None:
            current = selected_var.get()
            if len(self._cfg.get("machines", [])) <= 1:
                messagebox.showerror("No se puede eliminar", "Debes tener al menos una máquina configurada.", parent=dlg)
                return
            if not messagebox.askyesno("Eliminar máquina", f"¿Eliminar '{current}'?\n\nEsta acción no se puede deshacer.", icon="warning", parent=dlg):
                return
            cfg_module.delete_machine(self._cfg, current)
            cfg_module.save_config(self._cfg)
            names = cfg_module.get_machine_names(self._cfg)
            machine_combo["values"] = names
            new_active = self._cfg.get("active_machine", names[0] if names else "")
            selected_var.set(new_active)
            _load_machine(new_active)
            self._refresh_server_card()
            self._progress.log(f"Máquina '{current}' eliminada.", "warning")

        def _save() -> None:
            if not _validate():
                return
            old_name = selected_var.get()
            name, host, port, user, remote, jump_host, jump_user = _get_values()

            if name != old_name and name in cfg_module.get_machine_names(self._cfg):
                messagebox.showerror("Nombre duplicado", f"Ya existe '{name}'.", parent=dlg)
                return

            if name != old_name:
                cfg_module.delete_machine(self._cfg, old_name)

            cfg_module.upsert_machine(self._cfg, {
                "name": name, "host": host, "port": port, "user": user,
                "remote_base": remote, "jump_host": jump_host, "jump_user": jump_user,
            })
            cfg_module.set_active_machine(self._cfg, name)
            cfg_module.save_config(self._cfg)

            dlg.destroy()
            self._refresh_server_card()
            self._progress.log(f"Máquina '{name}' guardada y activada.", "success")
            self._progress.log(f"Servidor: {host}:{port}  usuario: {user}", "info")
            if jump_host:
                self._progress.log(f"Jump Host: {jump_host}", "info")
            if self._client.connected:
                self._disconnect()
                self._progress.log("Desconectado — reconecta con el nuevo servidor.", "warning")

        # ── Botones ────────────────────────────────────────────
        tk.Frame(dlg, bg=C["border"], height=1).pack(fill="x")
        btn_row = tk.Frame(dlg, bg=C["bg2"], pady=10, padx=16)
        btn_row.pack(fill="x")

        btn_test = tk.Button(
            btn_row, text="Probar conexión", command=_test_connection,
            bg=C["bg4"], fg=C["blue"], font=F["base"], relief="flat", bd=0,
            padx=12, pady=6, cursor="hand2",
            activebackground=C["bg3"], activeforeground=C["blue"],
        )
        btn_test.pack(side="left")

        tk.Button(
            btn_row, text="✕ Eliminar", command=_delete_machine,
            bg=C["bg4"], fg=C["danger"], font=F["base"], relief="flat", bd=0,
            padx=10, pady=6, cursor="hand2",
            activebackground=C["red_glow"], activeforeground=C["danger"],
        ).pack(side="left", padx=(8, 0))

        tk.Button(
            btn_row, text="Cancelar", command=dlg.destroy,
            bg=C["bg4"], fg=C["fg2"], font=F["base"], relief="flat", bd=0,
            padx=12, pady=6, cursor="hand2", activebackground=C["bg3"],
        ).pack(side="right", padx=(0, 8))

        tk.Button(
            btn_row, text="GUARDAR", command=_save,
            bg=C["red"], fg=C["fg"], font=F["md"], relief="flat", bd=0,
            padx=16, pady=6, cursor="hand2", activebackground=C["red_hi"],
        ).pack(side="right")

        dlg.bind("<Return>", lambda _: _save())
        dlg.bind("<Escape>", lambda _: dlg.destroy())

    def _toggle_server_reveal(self) -> None:
        """Alterna la visibilidad de host y usuario en el panel de servidor."""
        self._srv_revealed = not self._srv_revealed
        if self._srv_revealed:
            self._srv_toggle_btn.configure(text="ocultar", fg=C["red"])
            self._srv_host_lbl.configure(text=self._srv_raw.get("host", "—"))
            self._srv_user_lbl.configure(text=self._srv_raw.get("user", "—"))
        else:
            self._srv_toggle_btn.configure(text="mostrar", fg=C["fg3"])
            self._srv_host_lbl.configure(text="••••••••••")
            self._srv_user_lbl.configure(text="••••••••••")

    def _refresh_server_card(self) -> None:
        """Actualiza el panel de servidor con la máquina activa actual."""
        machine = self._machine()
        self._srv_raw = {"host": machine.get("host", "—"), "user": machine.get("user", "—")}

        if hasattr(self, "_srv_alias_lbl"):
            self._srv_alias_lbl.configure(text=machine.get("name", "—"))

        # Resetear siempre a estado oculto
        self._srv_revealed = False
        if hasattr(self, "_srv_toggle_btn"):
            self._srv_toggle_btn.configure(text="mostrar", fg=C["fg3"])
        if hasattr(self, "_srv_host_lbl"):
            self._srv_host_lbl.configure(text="••••••••••")
        if hasattr(self, "_srv_user_lbl"):
            self._srv_user_lbl.configure(text="••••••••••")

        # Actualizar badge de Jump Host
        if hasattr(self, "_srv_jump_lbl"):
            jh = machine.get("jump_host", "")
            self._srv_jump_lbl.configure(text=f"⇶ VIA JUMP HOST: {jh}" if jh else "")

    # ──────────────────────────────────────────────────────────
    # Splash Screen (Banner de inicio)
    # ──────────────────────────────────────────────────────────

    def _show_splash(self) -> None:
        """Muestra la ventana de bienvenida (banner.png) en medio de la pantalla por 2 segundos."""
        banner_path = get_asset_path("banner.png")
        if not banner_path.exists():
            self._center_and_show_main()
            return

        splash = tk.Toplevel(self._root)
        splash.overrideredirect(True)
        splash.attributes("-topmost", True)
        splash.configure(bg="#000000")

        # Icono del splash window
        icon_path = get_asset_path("icono.ico")
        if icon_path.exists():
            try:
                splash.iconbitmap(str(icon_path))
            except Exception:
                pass

        try:
            sw = splash.winfo_screenwidth()
            sh = splash.winfo_screenheight()

            if HAS_PIL:
                pil_banner = Image.open(banner_path)
                w, h = pil_banner.size

                # Si la pantalla es pequeña, escalar proporcionalmente
                if w > sw * 0.85 or h > sh * 0.85:
                    scale = min((sw * 0.85) / w, (sh * 0.85) / h)
                    w, h = int(w * scale), int(h * scale)
                    pil_banner = pil_banner.resize((w, h), Image.Resampling.LANCZOS)

                self._splash_img = ImageTk.PhotoImage(pil_banner)
            else:
                raw_banner = tk.PhotoImage(file=str(banner_path))
                w = raw_banner.width()
                h = raw_banner.height()
                self._splash_img = raw_banner

            banner_lbl = tk.Label(
                splash,
                image=self._splash_img,
                bg="#000000",
                bd=0,
                highlightthickness=0,
            )
            banner_lbl.pack()

            # Posicionar en el centro exacto de la pantalla
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2)
            splash.geometry(f"{w}x{h}+{x}+{y}")
            splash.update()

            def _finish_splash():
                try:
                    splash.destroy()
                except Exception:
                    pass
                self._center_and_show_main()

            # Ocultar splash y mostrar ventana principal tras 2000 ms (2 segundos)
            self._root.after(2000, _finish_splash)

        except Exception as e:
            print(f"Error en splash screen: {e}")
            try:
                splash.destroy()
            except Exception:
                pass
            self._center_and_show_main()

    def _center_and_show_main(self) -> None:
        """Centra la ventana principal en la pantalla y la hace visible."""
        self._root.update_idletasks()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        w, h = 1100, 760
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self._root.geometry(f"{w}x{h}+{x}+{y}")
        self._root.deiconify()
        self._root.lift()
        self._root.focus_force()

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
