#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IBAN -> (attempt) BIC lookup mit super simpler UI.
Constraints: nur python-stdnum, kein externes Bankverzeichnis.
Funktion: IBAN validieren, formatiert ausgeben, BIC nicht ableitbar.
"""

import sys
import tkinter as tk
from tkinter import ttk
import csv
import os

try:
    from stdnum import iban as std_iban
except Exception:
    print("Fehler: Das Paket 'python-stdnum' ist nicht installiert.\n"
          "Installiere es mit:\n\n    pip install python-stdnum\n")
    sys.exit(1)


APP_TITLE = "IBAN → BIC without leaking data externally :)"
APP_WIDTH = 640
APP_HEIGHT = 260

# 
# Globale Variable für BLZ->BIC Mapping
blz_bic_map = {}


def load_bundesbank_data(csv_path="blz.csv"):
    """
    Liest die Bankleitzahlen-Datei der Bundesbank ein und baut ein Mapping BLZ -> BIC.
    Erwartet CSV mit Spalten: Bankleitzahl;BIC;...
    """
    global blz_bic_map
    if not os.path.exists(csv_path):
        print(f"Hinweis: Bundesbank-Datei {csv_path} nicht gefunden. BIC-Suche deaktiviert.")
        return
    
    with open(csv_path, newline="", encoding="latin-1") as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            blz = row.get("Bankleitzahl", "").strip()
            bic = row.get("BIC", "").strip()
            if blz and bic:
                blz_bic_map[blz] = bic

    print(f"{len(blz_bic_map)} BLZ-Einträge geladen.")


iban_var = None
result_var = None


def normalize_iban(user_text: str) -> str:
    return "".join(ch for ch in (user_text or "").strip() if ch.isalnum())


def validate_iban(iban_raw: str):
    iban = normalize_iban(iban_raw)
    if not iban:
        return False, "", "Bitte eine IBAN eingeben."
    try:
        std_iban.validate(iban)
        return True, std_iban.compact(iban), None
    except Exception as ex:
        return False, iban, f"Ungültige IBAN: {ex}"


def get_bic_from_iban_placeholder(_iban: str):
    """
    Versuche, die BLZ aus der IBAN zu extrahieren und dann BIC aus Mapping zu holen.
    Funktioniert nur für deutsche IBANs (DEkk bbbb bbbb cccc cccc cc).
    """
    if not _iban.startswith("DE"):
        return None

    # Bei DE-IBAN: Stellen 5-12 sind die BLZ
    try:
        blz = _iban[4:12]
    except Exception:
        return None

    return blz_bic_map.get(blz)


def on_check():
    user_iban = iban_var.get()
    is_valid, compact, err = validate_iban(user_iban)
    if not is_valid:
        result_var.set(err)
        return

    formatted = std_iban.format(compact)
    bic = get_bic_from_iban_placeholder(compact)

    if bic:
        txt = f"✅ IBAN ist gültig.\nFormatiert: {formatted}\nBIC: {bic}"
    else:
        txt = (
            f"✅ IBAN ist gültig.\nFormatiert: {formatted}\n"
            "ℹ️ Keine BIC ermittelbar ohne Bankverzeichnis.\n"
            "Hinweis: Eine BIC lässt sich nicht direkt aus der IBAN ableiten."
        )
    result_var.set(txt)


def run_cli(args):
    if len(args) < 2:
        print("Verwendung: python iban_bic_gui.py <IBAN>")
        print("Ohne Argumente startet die GUI.")
        return

    test_iban = " ".join(args[1:])
    is_valid, compact, err = validate_iban(test_iban)
    if not is_valid:
        print(err)
        return

    formatted = std_iban.format(compact)
    bic = get_bic_from_iban_placeholder(compact)

    print("IBAN ist gültig.")
    print(f"Formatiert: {formatted}")
    if bic:
        print(f"BIC: {bic}")
    else:
        print("Keine BIC ermittelbar ohne Bankverzeichnis.")


def center_window(win, width, height):
    win.update_idletasks()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    x, y = int((sw/2) - (width/2)), int((sh/2) - (height/2))
    win.geometry(f"{width}x{height}+{x}+{y}")


def build_gui():
    root = tk.Tk()
    root.title(APP_TITLE)
    center_window(root, APP_WIDTH, APP_HEIGHT)
    root.resizable(False, False)

    # Create variables after root window is created
    global iban_var, result_var
    iban_var = tk.StringVar()
    result_var = tk.StringVar()

    frm = ttk.Frame(root, padding=16)
    frm.pack(fill="both", expand=True)

    lbl = ttk.Label(frm, text="IBAN einfügen und prüfen", font=("TkDefaultFont", 12, "bold"))
    lbl.pack(anchor="w", pady=(0, 8))

    entry = ttk.Entry(frm, textvariable=iban_var, width=60)
    entry.pack(fill="x", pady=(0, 8))
    entry.focus_set()
    entry.bind('<Return>', lambda event: on_check())

    btn_row = ttk.Frame(frm)
    btn_row.pack(fill="x", pady=(0, 8))

    ttk.Button(btn_row, text="Prüfen", command=on_check).pack(side="left")

    def clear():
        iban_var.set("")
        result_var.set("")
    ttk.Button(btn_row, text="Leeren", command=clear).pack(side="left", padx=(8, 0))

    result = tk.Text(frm, height=6, wrap="word")
    result.pack(fill="both", expand=True)
    result.configure(state="disabled")

    def update_result(*_):
        result.configure(state="normal")
        result.delete("1.0", "end")
        result.insert("1.0", result_var.get())
        result.configure(state="disabled")

    result_var.trace_add("write", update_result)

    foot = ttk.Label(
        frm,
        text=("Dieses Tool funktioniert nur mit deutschen IBANs."),
        wraplength=APP_WIDTH-32,
        foreground="gray"
    )
    foot.pack(anchor="w", pady=(8, 0))

    root.mainloop()


if __name__ == "__main__":
    # Bundesbank-Datei laden (erwarte blz.csv im selben Ordner)
    load_bundesbank_data("blz-aktuell-csv-data.csv")

    if len(sys.argv) > 1:
        run_cli(sys.argv)
    else:
        build_gui()
