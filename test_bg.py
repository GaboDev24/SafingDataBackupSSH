from app.ui.app_window import AppWindow
app = AppWindow()

def print_tree(w, indent=""):
    print(indent + str(w) + " (" + w.__class__.__name__ + ") -> bg=" + str(w.cget("bg") if hasattr(w, "cget") and "bg" in w.keys() else "N/A"))
    for c in w.winfo_children():
        print_tree(c, indent + "  ")

app._root.update_idletasks()
print_tree(app._root)
