import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import pandas as pd

def select_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx"),("CSV files", "*.csv")])
    return file_path

select_file()
