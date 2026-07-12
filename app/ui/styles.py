"""
SafingData — Sistema de Diseño Táctico adaptado a Tkinter.
Basado en DESIGN.md del proyecto SpiderWeb.
Tema: negro / rojo #A30000 / fuente monoespaciada.
"""

# ──────────────────────────────────────────────────────────────
# Paleta de colores (SpiderWeb Tactical)
# ──────────────────────────────────────────────────────────────
C = {
    # Fondos
    "bg":        "#000000",
    "bg2":       "#0a0a0a",
    "bg3":       "#111111",
    "bg4":       "#181818",
    "bg_input":  "#0d0d0d",

    # Texto
    "fg":        "#F5F5F5",
    "fg2":       "#999999",
    "fg3":       "#555555",
    "fg_dim":    "#333333",

    # Acento principal
    "red":       "#A30000",
    "red_hi":    "#CC0000",
    "red_dim":   "#5A0000",
    "red_glow":  "#3D0000",   # muy oscuro, simula glow

    # Estados
    "green":     "#22c55e",
    "yellow":    "#f59e0b",
    "blue":      "#38bdf8",
    "danger":    "#ef4444",

    # Bordes
    "border":    "#2A0000",
    "border2":   "#1A0000",
    "border_hi": "#A30000",

    # Selección / hover
    "select":    "#1E0000",
    "hover":     "#160000",
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
# Helpers
# ──────────────────────────────────────────────────────────────
def apply_ttk_style(style) -> None:
    """Aplica el tema táctico a todos los widgets ttk."""
    try:
        import tkinter.ttk as ttk
        style.theme_use("clam")
    except Exception:
        return

    # Frame general
    style.configure("TFrame", background=C["bg"])
    style.configure("Card.TFrame", background=C["bg3"])
    style.configure("Dark.TFrame", background=C["bg2"])
    style.configure("Header.TFrame", background=C["bg2"])

    # Labels
    style.configure(
        "TLabel",
        background=C["bg"],
        foreground=C["fg"],
        font=F["md"],
    )
    style.configure(
        "Dim.TLabel",
        background=C["bg"],
        foreground=C["fg2"],
        font=F["base"],
    )
    style.configure(
        "Muted.TLabel",
        background=C["bg"],
        foreground=C["fg3"],
        font=F["sm"],
    )
    style.configure(
        "Title.TLabel",
        background=C["bg"],
        foreground=C["fg"],
        font=F["xl"],
    )
    style.configure(
        "Red.TLabel",
        background=C["bg"],
        foreground=C["red"],
        font=F["base"],
    )
    style.configure(
        "Green.TLabel",
        background=C["bg"],
        foreground=C["green"],
        font=F["base"],
    )
    style.configure(
        "Card.TLabel",
        background=C["bg3"],
        foreground=C["fg"],
        font=F["md"],
    )
    style.configure(
        "CardDim.TLabel",
        background=C["bg3"],
        foreground=C["fg2"],
        font=F["sm"],
    )
    style.configure(
        "CardRed.TLabel",
        background=C["bg3"],
        foreground=C["red"],
        font=F["base"],
    )
    style.configure(
        "CardGreen.TLabel",
        background=C["bg3"],
        foreground=C["green"],
        font=F["base"],
    )
    style.configure(
        "CardYellow.TLabel",
        background=C["bg3"],
        foreground=C["yellow"],
        font=F["base"],
    )

    # Buttons
    style.configure(
        "Red.TButton",
        background=C["red"],
        foreground=C["fg"],
        font=F["md"],
        borderwidth=0,
        focuscolor=C["red"],
        relief="flat",
    )
    style.map(
        "Red.TButton",
        background=[("active", C["red_hi"]), ("disabled", C["red_dim"])],
        foreground=[("disabled", C["fg3"])],
    )
    style.configure(
        "Ghost.TButton",
        background=C["bg3"],
        foreground=C["fg2"],
        font=F["base"],
        borderwidth=1,
        relief="flat",
    )
    style.map(
        "Ghost.TButton",
        background=[("active", C["bg4"])],
        foreground=[("active", C["fg"])],
    )
    style.configure(
        "Danger.TButton",
        background=C["danger"],
        foreground=C["fg"],
        font=F["md"],
        borderwidth=0,
        relief="flat",
    )
    style.map(
        "Danger.TButton",
        background=[("active", "#cc0000")],
    )

    # Scrollbar
    style.configure(
        "TScrollbar",
        background=C["bg3"],
        troughcolor=C["bg"],
        bordercolor=C["border"],
        arrowcolor=C["fg3"],
        gripcount=0,
        relief="flat",
        borderwidth=0,
    )
    style.map(
        "TScrollbar",
        background=[("active", C["red_dim"])],
    )

    # Progressbar
    style.configure(
        "Red.Horizontal.TProgressbar",
        background=C["red"],
        troughcolor=C["bg3"],
        borderwidth=0,
        thickness=6,
    )

    # Separator
    style.configure(
        "TSeparator",
        background=C["border"],
    )

    # Treeview
    style.configure(
        "Treeview",
        background=C["bg3"],
        foreground=C["fg"],
        fieldbackground=C["bg3"],
        borderwidth=0,
        font=F["base"],
        rowheight=26,
    )
    style.configure(
        "Treeview.Heading",
        background=C["bg2"],
        foreground=C["red"],
        font=F["sm"],
        borderwidth=0,
        relief="flat",
    )
    style.map(
        "Treeview",
        background=[("selected", C["red_dim"])],
        foreground=[("selected", C["fg"])],
    )
    style.map(
        "Treeview.Heading",
        background=[("active", C["bg3"])],
    )

    # Entry
    style.configure(
        "TEntry",
        fieldbackground=C["bg_input"],
        foreground=C["fg"],
        insertcolor=C["red"],
        borderwidth=1,
        relief="flat",
        font=F["md"],
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", C["red"]), ("!focus", C["border"])],
    )

    # Notebook
    style.configure(
        "TNotebook",
        background=C["bg"],
        borderwidth=0,
    )
    style.configure(
        "TNotebook.Tab",
        background=C["bg3"],
        foreground=C["fg2"],
        font=F["base"],
        padding=[12, 6],
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", C["bg"])],
        foreground=[("selected", C["red"])],
    )
