"""
SafingData — Panel selector de archivos y carpetas.
Muestra un TreeView con los paths seleccionados y el tamaño acumulado.
"""

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from typing import Callable, List, Optional

from .styles import C, F


class FileSelector(ttk.Frame):
    """
    Panel izquierdo con árbol de archivos/carpetas seleccionados.
    Provee botones para agregar/quitar items y callback cuando cambia la selección.
    """

    def __init__(self, parent, on_change: Optional[Callable[[], None]] = None, **kwargs):
        super().__init__(parent, style="Card.TFrame", **kwargs)
        self._on_change = on_change
        self._paths: List[str] = []
        self._build()

    # ──────────────────────────────────────────────────────────
    # Construcción del panel
    # ──────────────────────────────────────────────────────────

    def _build(self) -> None:
        self.configure(padding=(0, 0))

        # ── Encabezado ─────────────────────────────────────────
        header = tk.Frame(self, bg=C["bg2"], pady=10, padx=14)
        header.pack(fill="x")

        tk.Label(
            header,
            text="◈  SELECCIÓN",
            bg=C["bg2"],
            fg=C["red"],
            font=F["sm"],
        ).pack(side="left")

        self._size_lbl = tk.Label(
            header,
            text="0 B",
            bg=C["bg2"],
            fg=C["fg3"],
            font=F["sm"],
        )
        self._size_lbl.pack(side="right")

        # Separador
        tk.Frame(self, bg=C["border"], height=1).pack(fill="x")

        # ── Toolbar de botones ─────────────────────────────────
        toolbar = tk.Frame(self, bg=C["bg3"], pady=6, padx=10)
        toolbar.pack(fill="x")

        btn_cfg = dict(
            bg=C["bg4"],
            fg=C["fg2"],
            font=F["sm"],
            relief="flat",
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            activebackground=C["red_dim"],
            activeforeground=C["fg"],
        )

        self._btn_file = tk.Button(
            toolbar,
            text="+ Archivo",
            command=self._add_file,
            **btn_cfg,
        )
        self._btn_file.pack(side="left", padx=(0, 4))

        self._btn_folder = tk.Button(
            toolbar,
            text="+ Carpeta",
            command=self._add_folder,
            **btn_cfg,
        )
        self._btn_folder.pack(side="left", padx=(0, 4))

        self._btn_remove = tk.Button(
            toolbar,
            text="✕ Quitar",
            command=self._remove_selected,
            bg=C["bg4"],
            fg=C["danger"],
            font=F["sm"],
            relief="flat",
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            activebackground="#3D0000",
            activeforeground=C["danger"],
        )
        self._btn_remove.pack(side="left")

        tk.Frame(self, bg=C["border2"], height=1).pack(fill="x")

        # ── Treeview ───────────────────────────────────────────
        tree_frame = tk.Frame(self, bg=C["bg3"])
        tree_frame.pack(fill="both", expand=True)

        self._tree = ttk.Treeview(
            tree_frame,
            columns=("type", "size"),
            show="tree headings",
            selectmode="browse",
        )

        self._tree.heading("#0", text="PATH", anchor="w")
        self._tree.heading("type", text="TIPO", anchor="w")
        self._tree.heading("size", text="TAMAÑO", anchor="e")

        self._tree.column("#0", width=220, minwidth=120)
        self._tree.column("type", width=70, minwidth=60)
        self._tree.column("size", width=90, minwidth=70, anchor="e")

        scroll_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self._tree.pack(side="left", fill="both", expand=True)

        # Tags de color para el tree
        self._tree.tag_configure("file",   foreground=C["fg"])
        self._tree.tag_configure("folder", foreground=C["blue"])
        self._tree.tag_configure("error",  foreground=C["danger"])

        # ── Placeholder cuando está vacío ───────────────────────
        self._empty_lbl = tk.Label(
            tree_frame,
            text="Sin archivos seleccionados.\nUsa los botones de arriba\npara agregar archivos o carpetas.",
            bg=C["bg3"],
            fg=C["fg3"],
            font=F["sm"],
            justify="center",
        )
        self._empty_lbl.place(relx=0.5, rely=0.5, anchor="center")

    # ──────────────────────────────────────────────────────────
    # Acciones de los botones
    # ──────────────────────────────────────────────────────────

    def _add_file(self) -> None:
        paths = filedialog.askopenfilenames(title="Seleccionar archivos")
        for p in paths:
            self._add_path(p)

    def _add_folder(self) -> None:
        path = filedialog.askdirectory(title="Seleccionar carpeta")
        if path:
            self._add_path(path)

    def _add_path(self, path: str) -> None:
        """Agrega un path si no está duplicado."""
        path = str(Path(path).resolve())
        if path in self._paths:
            return
        # Verificar que el path no esté ya cubierto por un padre
        for existing in self._paths:
            if path.startswith(existing + "/") or path.startswith(existing + "\\"):
                return  # ya cubierto
        self._paths.append(path)
        self._refresh_tree()
        if self._on_change:
            self._on_change()

    def _remove_selected(self) -> None:
        selected = self._tree.selection()
        if not selected:
            return
        iid = selected[0]
        # Solo removemos items raíz (los que están en self._paths)
        parent = self._tree.parent(iid)
        if parent:
            # Es un hijo → remover su raíz
            root = iid
            while self._tree.parent(root):
                root = self._tree.parent(root)
            iid = root
        item = self._tree.item(iid, "values")
        path = self._tree.item(iid, "text")
        if path and path in self._paths:
            self._paths.remove(path)
        elif iid in self._paths:
            self._paths.remove(iid)
        else:
            # Buscar por índice
            idx = int(iid) if iid.isdigit() else -1
            if 0 <= idx < len(self._paths):
                self._paths.pop(idx)
        self._refresh_tree()
        if self._on_change:
            self._on_change()

    # ──────────────────────────────────────────────────────────
    # Actualización del árbol
    # ──────────────────────────────────────────────────────────

    def _refresh_tree(self) -> None:
        """Reconstruye el TreeView con los paths actuales."""
        self._tree.delete(*self._tree.get_children())

        total_size = 0

        for i, path_str in enumerate(self._paths):
            p = Path(path_str)
            if not p.exists():
                self._tree.insert(
                    "", "end",
                    iid=str(i),
                    text=path_str,
                    values=("—", "NO EXISTE"),
                    tags=("error",),
                    open=False,
                )
                continue

            if p.is_file():
                size = p.stat().st_size
                total_size += size
                self._tree.insert(
                    "", "end",
                    iid=str(i),
                    text=path_str,
                    values=("archivo", _fmt_size(size)),
                    tags=("file",),
                )
            elif p.is_dir():
                dir_size = _dir_size(p)
                total_size += dir_size
                parent_iid = self._tree.insert(
                    "", "end",
                    iid=str(i),
                    text=path_str,
                    values=("carpeta", _fmt_size(dir_size)),
                    tags=("folder",),
                    open=False,
                )
                # Mostrar hasta 2 niveles de hijos
                _insert_children(self._tree, parent_iid, p, depth=0, max_depth=1)

        # Mostrar/ocultar placeholder
        if self._paths:
            self._empty_lbl.place_forget()
        else:
            self._empty_lbl.place(relx=0.5, rely=0.5, anchor="center")

        # Actualizar etiqueta de tamaño total
        self._size_lbl.configure(text=_fmt_size(total_size))

    # ──────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────

    def get_paths(self) -> List[str]:
        return list(self._paths)

    def set_paths(self, paths: List[str]) -> None:
        self._paths = [str(Path(p).resolve()) for p in paths if Path(p).exists()]
        self._refresh_tree()

    def get_total_size(self) -> int:
        total = 0
        for p_str in self._paths:
            p = Path(p_str)
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
            elif p.is_dir():
                total += _dir_size(p)
        return total

    def set_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self._btn_file.configure(state=state)
        self._btn_folder.configure(state=state)
        self._btn_remove.configure(state=state)


# ──────────────────────────────────────────────────────────────
# Helpers privados
# ──────────────────────────────────────────────────────────────

def _dir_size(path: Path) -> int:
    total = 0
    try:
        for f in path.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
    except PermissionError:
        pass
    return total


def _insert_children(
    tree: ttk.Treeview,
    parent_iid: str,
    directory: Path,
    depth: int,
    max_depth: int,
) -> None:
    if depth >= max_depth:
        return
    try:
        items = sorted(directory.iterdir(), key=lambda x: (x.is_file(), x.name))
    except PermissionError:
        return
    for item in items[:50]:  # máx 50 hijos visibles
        if item.is_file():
            try:
                size = item.stat().st_size
            except OSError:
                size = 0
            tree.insert(
                parent_iid, "end",
                text=item.name,
                values=("archivo", _fmt_size(size)),
                tags=("file",),
            )
        elif item.is_dir():
            child_iid = tree.insert(
                parent_iid, "end",
                text=item.name + "/",
                values=("carpeta", ""),
                tags=("folder",),
                open=False,
            )
            if depth + 1 < max_depth:
                _insert_children(tree, child_iid, item, depth + 1, max_depth)


def _fmt_size(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    elif b < 1024 ** 2:
        return f"{b / 1024:.1f} KB"
    elif b < 1024 ** 3:
        return f"{b / 1024 ** 2:.1f} MB"
    else:
        return f"{b / 1024 ** 3:.2f} GB"
