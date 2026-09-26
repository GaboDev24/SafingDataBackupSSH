import sys
import tkinter as tk
from app.ui.styles import theme, C
from app.config import save_config, load_config
cfg = load_config()
cfg["theme"] = "light"
save_config(cfg)
print("Config saved as light.")
