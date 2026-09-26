import tkinter as tk
root = tk.Tk()
f = tk.Frame(root, bg="#0a0a0a")
lbl = tk.Label(root, bg="#0a0a0a", fg="#F5F5F5")
print(f.cget("bg"))
print(lbl.cget("bg"))
print(lbl.cget("fg"))
