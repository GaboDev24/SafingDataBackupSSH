"""
SafingData — Sistema de Diseño Táctico adaptado a Tkinter.
Soporta modo Oscuro (SpiderWeb Tactical) y modo Claro.
El tema se controla a través de ThemeManager (singleton `theme`).
"""

# ──────────────────────────────────────────────────────────────
# Paleta Oscura (SpiderWeb Tactical — original)
# ──────────────────────────────────────────────────────────────
C_DARK = {
    "bg":        "#000000",
    "bg2":       "#0a0a0a",
    "bg3":       "#111111",
    "bg4":       "#181818",
    "bg_input":  "#0d0d0d",
    "fg":        "#F5F5F5",
    "fg2":       "#999999",
    "fg3":       "#555555",
    "fg_dim":    "#333333",
    "red":       "#A30000",
    "red_hi":    "#CC0000",
    "red_dim":   "#5A0000",
    "red_glow":  "#3D0000",
    "green":     "#22c55e",
    "yellow":    "#f59e0b",
    "blue":      "#38bdf8",
    "danger":    "#ef4444",
    "border":    "#2A0000",
    "border2":   "#1A0000",
    "border_hi": "#A30000",
    "select":    "#1E0000",
    "hover":     "#160000",
}

# ──────────────────────────────────────────────────────────────
# Paleta Clara
# ──────────────────────────────────────────────────────────────
C_LIGHT = {
    "bg":        "#F7F7F8",
    "bg2":       "#EBEBED",
    "bg3":       "#FFFFFF",
    "bg4":       "#E0E0E3",
    "bg_input":  "#FAFAFA",
    "fg":        "#111111",
    "fg2":       "#444444",
    "fg3":       "#888888",
    "fg_dim":    "#BBBBBB",
    "red":       "#A30000",
    "red_hi":    "#CC0000",
    "red_dim":   "#E8B4B4",
    "red_glow":  "#F5DCDC",
    "green":     "#16a34a",
    "yellow":    "#d97706",
    "blue":      "#0284c7",
    "danger":    "#dc2626",
    "border":    "#E8C4C4",
    "border2":   "#F0D8D8",
    "border_hi": "#A30000",
    "select":    "#FAE8E8",
    "hover":     "#FDF1F1",
}

# ──────────────────────────────────────────────────────────────
# Fuentes
# ──────────────────────────────────────────────────────────────
F = {
    "xs":       ("Courier New", 7),
    "sm":       ("Courier New", 8),
    "base":     ("Courier New", 9),
    "md":       ("Courier New", 10),
    "lg":       ("Courier New", 11, "bold"),
    "xl":       ("Courier New", 13, "bold"),
    "title":    ("Courier New", 16, "bold"),
    "huge":     ("Courier New", 22, "bold"),
    "label":    ("Courier New", 8),
    "mono":     ("Courier New", 9),
}


# ──────────────────────────────────────────────────────────────
# ThemeManager — singleton de tema activo
# ──────────────────────────────────────────────────────────────

class ThemeManager:
    """
    Gestiona el tema activo (oscuro / claro / auto).
    Uso:
        from .styles import theme, C, F
        C["bg"]  →  siempre devuelve el color del tema activo.
    """
    DARK  = "dark"
    LIGHT = "light"
    AUTO  = "auto"

    def __init__(self) -> None:
        self._mode: str = self.AUTO
        self._palette: dict = C_DARK
        self._prev_palette: dict = C_DARK   # paleta anterior al último cambio
        self._callbacks: list = []

    # ── Detección del sistema ────────────────────────────────
    @staticmethod
    def _system_is_dark() -> bool:
        """Detecta si el sistema usa tema oscuro, sin requerir darkdetect."""
        # 1) darkdetect (pip install darkdetect)
        try:
            import darkdetect  # type: ignore
            return darkdetect.isDark() is not False
        except ImportError:
            pass
        # 2) GNOME / gsettings
        try:
            import subprocess
            out = subprocess.check_output(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                stderr=subprocess.DEVNULL, timeout=1,
            ).decode().strip()
            return "dark" in out.lower()
        except Exception:
            pass
        # 3) KDE / kreadconfig5
        try:
            import subprocess
            out = subprocess.check_output(
                ["kreadconfig5", "--group", "General", "--key", "ColorScheme"],
                stderr=subprocess.DEVNULL, timeout=1,
            ).decode().strip().lower()
            return "dark" in out
        except Exception:
            pass
        # 4) Por defecto: oscuro (diseño original)
        return True

    # ── API pública ───────────────────────────────────────────
    def set_mode(self, mode: str) -> None:
        """Establece "dark", "light" o "auto" y notifica los callbacks."""
        self._mode = mode
        self._recalc()

    def get_mode(self) -> str:
        return self._mode

    def is_dark(self) -> bool:
        return self._palette is C_DARK

    def palette(self) -> dict:
        return self._palette

    def prev_palette(self) -> dict:
        """Paleta que estaba activa ANTES del último cambio de tema."""
        return self._prev_palette

    def register_callback(self, fn) -> None:
        """Registra una función sin argumentos llamada al cambiar tema."""
        if fn not in self._callbacks:
            self._callbacks.append(fn)

    def unregister_callback(self, fn) -> None:
        self._callbacks = [f for f in self._callbacks if f is not fn]

    def _recalc(self) -> None:
        self._prev_palette = self._palette   # guardar antes de cambiar
        if self._mode == self.LIGHT:
            self._palette = C_LIGHT
        elif self._mode == self.DARK:
            self._palette = C_DARK
        else:  # AUTO
            self._palette = C_DARK if self._system_is_dark() else C_LIGHT
        # Actualizar el alias global C en-lugar (los importadores existentes
        # siguen usando el mismo objeto dict y verán los colores nuevos)
        C.clear()
        C.update(self._palette)
        for fn in list(self._callbacks):
            try:
                fn()
            except Exception:
                pass


# ── Singleton + alias mutable global ─────────────────────────
theme = ThemeManager()

# C es un dict mutable compartido; siempre refleja la paleta activa.
# Importar con `from .styles import C` es seguro: es el mismo objeto.
C: dict = {}
C.update(C_DARK)  # valor inicial antes de que set_mode() lo recalcule


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def apply_ttk_style(style) -> None:
    """Aplica el tema táctico a todos los widgets ttk (usa la paleta activa C)."""
    try:
        style.theme_use("clam")
    except Exception:
        return
    _configure_ttk(style, C)


def _configure_ttk(style, p: dict) -> None:
    """Configura todos los estilos ttk con la paleta `p`."""

    # Frame
    style.configure("TFrame",        background=p["bg"])
    style.configure("Card.TFrame",   background=p["bg3"])
    style.configure("Dark.TFrame",   background=p["bg2"])
    style.configure("Header.TFrame", background=p["bg2"])

    # Labels
    style.configure("TLabel",            background=p["bg"],  foreground=p["fg"],     font=F["md"])
    style.configure("Dim.TLabel",        background=p["bg"],  foreground=p["fg2"],    font=F["base"])
    style.configure("Muted.TLabel",      background=p["bg"],  foreground=p["fg3"],    font=F["sm"])
    style.configure("Title.TLabel",      background=p["bg"],  foreground=p["fg"],     font=F["xl"])
    style.configure("Red.TLabel",        background=p["bg"],  foreground=p["red"],    font=F["base"])
    style.configure("Green.TLabel",      background=p["bg"],  foreground=p["green"],  font=F["base"])
    style.configure("Card.TLabel",       background=p["bg3"], foreground=p["fg"],     font=F["md"])
    style.configure("CardDim.TLabel",    background=p["bg3"], foreground=p["fg2"],    font=F["sm"])
    style.configure("CardRed.TLabel",    background=p["bg3"], foreground=p["red"],    font=F["base"])
    style.configure("CardGreen.TLabel",  background=p["bg3"], foreground=p["green"],  font=F["base"])
    style.configure("CardYellow.TLabel", background=p["bg3"], foreground=p["yellow"], font=F["base"])

    # Buttons
    style.configure(
        "Red.TButton",
        background=p["red"], foreground="#FFFFFF", font=F["md"],
        borderwidth=0, focuscolor=p["red"], relief="flat",
    )
    style.map(
        "Red.TButton",
        background=[("active", p["red_hi"]), ("disabled", p["red_dim"])],
        foreground=[("active", "#FFFFFF"), ("disabled", p["fg3"])],
    )
    style.configure(
        "Ghost.TButton",
        background=p["bg3"], foreground=p["fg2"], font=F["base"],
        borderwidth=1, relief="flat",
    )
    style.map(
        "Ghost.TButton",
        background=[("active", p["bg4"])],
        foreground=[("active", p["fg"])],
    )
    style.configure(
        "Danger.TButton",
        background=p["danger"], foreground=p["fg"], font=F["md"],
        borderwidth=0, relief="flat",
    )
    style.map("Danger.TButton", background=[("active", p["red_hi"])])

    # Scrollbar
    style.configure(
        "TScrollbar",
        background=p["bg3"], troughcolor=p["bg"],
        bordercolor=p["border"], arrowcolor=p["fg3"],
        gripcount=0, relief="flat", borderwidth=0,
    )
    style.map("TScrollbar", background=[("active", p["red_dim"])])

    # Progressbar
    style.configure(
        "Red.Horizontal.TProgressbar",
        background=p["red"], troughcolor=p["bg3"],
        borderwidth=0, thickness=6,
    )

    # Separator
    style.configure("TSeparator", background=p["border"])

    # Treeview
    style.configure(
        "Treeview",
        background=p["bg3"], foreground=p["fg"],
        fieldbackground=p["bg3"], borderwidth=0,
        font=F["base"], rowheight=26,
    )
    style.configure(
        "Treeview.Heading",
        background=p["bg2"], foreground=p["red"],
        font=F["sm"], borderwidth=0, relief="flat",
    )
    style.map(
        "Treeview",
        background=[("selected", p["red_dim"])],
        foreground=[("selected", p["fg"])],
    )
    style.map("Treeview.Heading", background=[("active", p["bg3"])])

    # Entry
    style.configure(
        "TEntry",
        fieldbackground=p["bg_input"], foreground=p["fg"],
        insertcolor=p["red"], borderwidth=1, relief="flat", font=F["md"],
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", p["red"]), ("!focus", p["border"])],
    )

    # Notebook
    style.configure("TNotebook", background=p["bg"], borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background=p["bg3"], foreground=p["fg2"],
        font=F["base"], padding=[12, 6],
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", p["bg"])],
        foreground=[("selected", p["red"])],
    )

    # Combobox
    style.configure(
        "TCombobox",
        fieldbackground=p["bg_input"], foreground=p["fg"],
        background=p["bg3"], bordercolor=p["border"],
        arrowcolor=p["fg3"],
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", p["bg_input"])],
        foreground=[("readonly", p["fg"])],
        bordercolor=[("focus", p["red"])],
    )
