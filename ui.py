# ui.py — Gift Card Manager (Опция A: Functions + SheetStub) + Smart Flow + Mark Used (в таб "Използвай")
# UI на български. Работи без Google чрез SheetStub, но използва реалните Functions/*.
# После за Google: само сменяш self.sheet = SheetStub() -> self.sheet = get_google_sheet()

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date, timedelta
import csv
import io
import contextlib
from typing import Optional, List, Tuple

# --- Реалните ти функции ---
from Functions.code_generator import create_code
from Functions.add import add_gift_card
from Functions.print_info import print_info
from Functions.use_portion import use_portion
from Functions.remove import gift_card_used, remove_gift_card


# ------------------------------------------------------------
# 1) SheetStub (gspread-like) — методите, които Functions ползват
# ------------------------------------------------------------
class SheetStub:
    class Cell:
        def __init__(self, row: int, col: int, value):
            self.row = row
            self.col = col
            self.value = value

    def __init__(self):
        # Всеки ред: [код, дата_добавяне, сума/баланс, име, дата_used]
        self._rows: List[List] = []

    def append_row(self, values, value_input_option=None):
        row = list(values)
        while len(row) < 5:
            row.append("")
        self._rows.append(row)

    def col_values(self, col: int):
        idx = col - 1
        out = []
        for r in self._rows:
            out.append("" if idx >= len(r) else str(r[idx]))
        return out

    def find(self, value: str):
        value = str(value).strip()
        for i, r in enumerate(self._rows, start=1):  # 1-based rows
            if len(r) > 0 and str(r[0]).strip() == value:
                return SheetStub.Cell(row=i, col=1, value=r[0])
        return None

    def cell(self, row: int, col: int):
        r = self._rows[row - 1]
        idx = col - 1
        val = "" if idx >= len(r) else r[idx]
        return SheetStub.Cell(row=row, col=col, value=val)

    def update_cell(self, row: int, col: int, value):
        r = self._rows[row - 1]
        idx = col - 1
        while len(r) <= idx:
            r.append("")
        r[idx] = value

    def delete_rows(self, row_index: int):
        del self._rows[row_index - 1]

    # UI helper (не е gspread)
    def get_all_rows(self) -> List[List]:
        return list(self._rows)


# ------------------------------------------------------------
# 2) Helpers — stdout capture, парсване, статус, expiry
# ------------------------------------------------------------
def capture_stdout(fn, *args, **kwargs) -> str:
    """Хваща print() изхода от Functions и го връща като текст."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*args, **kwargs)
    return buf.getvalue().strip()


def safe_float(s: str) -> Optional[float]:
    try:
        return float(str(s).strip())
    except Exception:
        return None


def parse_bg_date(s: str) -> Optional[date]:
    """Очаква дата в формат dd.mm.yyyy"""
    try:
        return datetime.strptime(str(s).strip(), "%d.%m.%Y").date()
    except Exception:
        return None


def expiry_from_code(code: str) -> Optional[date]:
    """
    Код формат: CR + ddmmyy + инициали
    Пример: CR200127KP  -> expiry = 20.01.2027
    """
    try:
        code = str(code).strip()
        if len(code) < 8:
            return None
        ddmmyy = code[2:8]
        dd = int(ddmmyy[0:2])
        mm = int(ddmmyy[2:4])
        yy = int(ddmmyy[4:6])
        yyyy = 2000 + yy
        return date(yyyy, mm, dd)
    except Exception:
        return None


def fallback_expiry_from_added_date(date_added_str: str) -> Optional[date]:
    """
    Ако кодът не е по шаблон (пример CRDEMO0001),
    смятаме expiry от дата_добавяне + 365 дни.
    """
    d = parse_bg_date(date_added_str)
    if not d:
        return None
    return d + timedelta(days=365)


def get_expiry(code: str, date_added_str: str) -> Optional[date]:
    """Първо опитваме expiry от кода. Ако няма — fallback от дата + 365."""
    exp = expiry_from_code(code)
    if exp:
        return exp
    return fallback_expiry_from_added_date(date_added_str)


def is_expired(code: str, date_added_str: str) -> bool:
    exp = get_expiry(code, date_added_str)
    return exp is not None and date.today() > exp


def fmt_dd_mm_yy(d: Optional[date]) -> str:
    if not d:
        return "—"
    return d.strftime("%d-%m-%y")


def row_status(row: List) -> str:
    """
    Колони:
      1 code
      2 date_added
      3 amount/balance
      4 name
      5 used_date

    Статуси:
      - ИЗПОЛЗВАНА: ако има used_date (колона 5)
      - ИЗЧЕРПАНА: ако баланс <= 0
      - ИЗТЕКЛА: ако expiry (code или fallback) < днес
      - АКТИВНА: иначе
    """
    used = str(row[4]).strip() if len(row) >= 5 else ""
    if used:
        return "ИЗПОЛЗВАНА"

    bal = safe_float(row[2]) if len(row) >= 3 else None
    if bal is None:
        return "НЕИЗВЕСТНО"
    if bal <= 0:
        return "ИЗЧЕРПАНА"

    code = str(row[0]).strip() if len(row) >= 1 else ""
    date_added = str(row[1]).strip() if len(row) >= 2 else ""
    if is_expired(code, date_added):
        return "ИЗТЕКЛА"

    return "АКТИВНА"


# ------------------------------------------------------------
# 3) Smart Flow dialog — пита само за липсващите полета
# ------------------------------------------------------------
class MissingInfoDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, title: str, fields: List[Tuple[str, tk.StringVar]]):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self._ok = False

        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        first_entry = None
        for r, (label, var) in enumerate(fields):
            ttk.Label(container, text=label).grid(row=r, column=0, sticky="w", pady=4, padx=(0, 10))
            e = ttk.Entry(container, textvariable=var, width=34)
            e.grid(row=r, column=1, sticky="ew", pady=4)
            if first_entry is None:
                first_entry = e

        btns = ttk.Frame(container)
        btns.grid(row=len(fields), column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(btns, text="Отказ", command=self._cancel).pack(side="right", padx=(6, 0))
        ttk.Button(btns, text="OK", command=self._accept).pack(side="right")

        self.bind("<Return>", lambda _e: self._accept())
        self.bind("<Escape>", lambda _e: self._cancel())

        if first_entry is not None:
            first_entry.focus_set()

        # center on parent
        self.update_idletasks()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{px + (pw - w)//2}+{py + (ph - h)//2}")

    def _accept(self):
        self._ok = True
        self.destroy()

    def _cancel(self):
        self._ok = False
        self.destroy()

    @property
    def ok(self) -> bool:
        return self._ok


# ------------------------------------------------------------
# 4) Основен UI клас
# ------------------------------------------------------------
class GiftCardUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Управление на Подаръчни Карти")
        self.geometry("1200x760")
        self.minsize(1000, 640)

        # Опция A: локален SheetStub (по-късно ще стане Google sheet)
        self.sheet = SheetStub()

        # Панел "Информация"
        self.var_msg = tk.StringVar(value="Готово.")
        self.var_status = tk.StringVar(value="—")
        self.var_balance = tk.StringVar(value="—")
        self.var_used = tk.StringVar(value="—")
        self.var_expiry = tk.StringVar(value="—")

        # Search
        self.var_search = tk.StringVar()

        # Създай карта
        self.var_code = tk.StringVar()
        self.var_amount = tk.StringVar()
        self.var_name = tk.StringVar()

        # Използвай
        self.var_redeem_code = tk.StringVar()
        self.var_redeem_amount = tk.StringVar()

        # Търси
        self.var_lookup_code = tk.StringVar()

        self._build_menu()
        self._build_layout()

        self._seed_demo()
        self.refresh_results()

    # ---------------- UI build ----------------
    def _build_menu(self):
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Експорт в CSV…", command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Изход", command=self.destroy)
        menubar.add_cascade(label="Файл", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="За програмата", command=self.about)
        menubar.add_cascade(label="Помощ", menu=help_menu)

        self.config(menu=menubar)

    def _build_layout(self):
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=0)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        # LEFT: Tabs + Info
        left = ttk.Frame(root)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        left.rowconfigure(1, weight=1)

        self.nb = ttk.Notebook(left)
        self.nb.grid(row=0, column=0, sticky="n")

        self._build_tab_issue()
        self._build_tab_redeem()
        self._build_tab_lookup()

        out = ttk.LabelFrame(left, text="Информация", padding=10)
        out.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        out.columnconfigure(1, weight=1)

        ttk.Label(out, text="Статус:").grid(row=0, column=0, sticky="w")
        ttk.Label(out, textvariable=self.var_status).grid(row=0, column=1, sticky="w")

        ttk.Label(out, text="Баланс:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(out, textvariable=self.var_balance).grid(row=1, column=1, sticky="w", pady=(6, 0))

        ttk.Label(out, text="Валидна до:").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Label(out, textvariable=self.var_expiry).grid(row=2, column=1, sticky="w", pady=(6, 0))

        ttk.Label(out, text="Използвана:").grid(row=3, column=0, sticky="w", pady=(6, 0))
        ttk.Label(out, textvariable=self.var_used).grid(row=3, column=1, sticky="w", pady=(6, 0))

        ttk.Label(out, text="Съобщение:").grid(row=4, column=0, sticky="nw", pady=(10, 0))
        ttk.Label(out, textvariable=self.var_msg, wraplength=360).grid(row=4, column=1, sticky="w", pady=(10, 0))

        # RIGHT: Results + Log
        right = ttk.Frame(root)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        header = ttk.Frame(right)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        ttk.Label(header, text="Резултaти").grid(row=0, column=0, sticky="w")

        ttk.Entry(header, textvariable=self.var_search).grid(row=0, column=1, sticky="ew", padx=(10, 6))
        ttk.Button(header, text="Обнови", command=self.refresh_results).grid(row=0, column=2)
        ttk.Button(header, text="Изчисти", command=self.clear_search).grid(row=0, column=3, padx=(6, 0))

        table_frame = ttk.Frame(right)
        table_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        cols = ("code", "date_added", "expiry", "amount", "name", "used", "status")
        self.table = ttk.Treeview(table_frame, columns=cols, show="headings")

        headings = {
            "code": "Код",
            "date_added": "Дата",
            "expiry": "Валидна до",
            "amount": "Сума",
            "name": "Име",
            "used": "Използвана на",
            "status": "Статус",
        }
        widths = {"code": 240, "date_added": 110, "expiry": 110, "amount": 90, "name": 260, "used": 120, "status": 120}

        for c in cols:
            self.table.heading(c, text=headings[c])
            self.table.column(c, width=widths[c], anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=vsb.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.table.bind("<Double-1>", self.on_table_double_click)

        log_frame = ttk.LabelFrame(right, text="Лог", padding=6)
        log_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)

        self.log = tk.Text(log_frame, height=8, wrap="word")
        self.log.grid(row=0, column=0, sticky="ew")
        self.log.configure(state="disabled")

    def _build_tab_issue(self):
        tab = ttk.Frame(self.nb, padding=10)
        self.nb.add(tab, text="Създай карта")
        tab.columnconfigure(1, weight=1)

        ttk.Label(tab, text="Код (по желание)").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(tab, textvariable=self.var_code).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(tab, text="Сума").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(tab, textvariable=self.var_amount).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(tab, text="Име (на кирилица)").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(tab, textvariable=self.var_name).grid(row=2, column=1, sticky="ew", pady=4)

        btns = ttk.Frame(tab)
        btns.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        btns.columnconfigure(0, weight=1)

        ttk.Button(btns, text="Генерирай код", command=self.on_generate_code).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(btns, text="Създай", command=self.on_issue).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        actions = ttk.Frame(tab)
        actions.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        actions.columnconfigure(0, weight=1)

        ttk.Button(actions, text="Премахни по код", command=self.on_remove).grid(row=0, column=0, sticky="ew")

        ttk.Label(tab, text="Съвет: Ако оставиш кода празен, ще се генерира автоматично.").grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )

    def _build_tab_redeem(self):
        tab = ttk.Frame(self.nb, padding=10)
        self.nb.add(tab, text="Използвай")
        tab.columnconfigure(1, weight=1)

        ttk.Label(tab, text="Код").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(tab, textvariable=self.var_redeem_code).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(tab, text="Сума за приспадане").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(tab, textvariable=self.var_redeem_amount).grid(row=1, column=1, sticky="ew", pady=4)

        self.btn_redeem = ttk.Button(tab, text="Използвай", command=self.on_redeem)
        self.btn_redeem.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        ttk.Button(tab, text="Маркирай като използвана", command=self.on_mark_used).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0)
        )

    def _build_tab_lookup(self):
        tab = ttk.Frame(self.nb, padding=10)
        self.nb.add(tab, text="Търси")
        tab.columnconfigure(1, weight=1)

        ttk.Label(tab, text="Код").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(tab, textvariable=self.var_lookup_code).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Button(tab, text="Покажи", command=self.on_lookup).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    # ---------------- Smart Flow helper ----------------
    def ensure_fields(self, title: str, required: List[Tuple[str, tk.StringVar]]) -> bool:
        missing = [(label, var) for (label, var) in required if not var.get().strip()]
        if not missing:
            return True
        dlg = MissingInfoDialog(self, title=title, fields=missing)
        self.wait_window(dlg)
        return dlg.ok

    # ---------------- helpers ----------------
    def log_line(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def about(self):
        messagebox.showinfo(
            "За програмата",
            "Управление на подаръчни карти (тестов режим)\n\n"
            "В момента работи с локален SheetStub.\n"
            "Следваща стъпка: включване на Google Sheets."
        )

    def clear_search(self):
        self.var_search.set("")
        self.refresh_results()

    def split_name(self, full_name: str) -> tuple[str, str]:
        parts = [p for p in str(full_name).strip().split() if p]
        if len(parts) < 2:
            return "", ""
        return parts[0], " ".join(parts[1:])

    def update_info_from_code(self, code: str):
        code = str(code).strip()
        cell = self.sheet.find(code)
        if not cell:
            self.var_status.set("НЕ Е НАМЕРЕНА")
            self.var_balance.set("—")
            self.var_used.set("—")
            self.var_expiry.set("—")
            self.btn_redeem.state(["disabled"])
            return

        row = cell.row
        bal = safe_float(self.sheet.cell(row, 3).value)
        used_date = str(self.sheet.cell(row, 5).value).strip()
        date_added = str(self.sheet.cell(row, 2).value).strip()

        exp = get_expiry(code, date_added)
        expired = exp is not None and date.today() > exp

        self.var_balance.set("—" if bal is None else f"{bal:.2f}")
        self.var_used.set("ДА" if used_date else "НЕ")
        self.var_expiry.set(fmt_dd_mm_yy(exp))

        status = row_status([
            self.sheet.cell(row, 1).value,
            self.sheet.cell(row, 2).value,
            self.sheet.cell(row, 3).value,
            self.sheet.cell(row, 4).value,
            self.sheet.cell(row, 5).value,
        ])
        self.var_status.set(status)

        if used_date or (bal is not None and bal <= 0) or expired:
            self.btn_redeem.state(["disabled"])
        else:
            self.btn_redeem.state(["!disabled"])

    # ---------------- actions ----------------
    def on_generate_code(self):
        ok = self.ensure_fields("Липсва информация", [("Име (на кирилица)", self.var_name)])
        if not ok:
            return
        name = self.var_name.get().strip()
        first, last = self.split_name(name)
        if not first or not last:
            messagebox.showerror("Невалидно име", "Моля въведи поне име и фамилия.")
            return
        code = create_code(self.sheet, first, last)
        self.var_code.set(code)
        self.log_line(f"[UI] Генериран код: {code} за {name}")
        self.var_msg.set("Генериран код.")

    def on_issue(self):
        ok = self.ensure_fields("Липсва информация за създаване", [("Сума", self.var_amount), ("Име (на кирилица)", self.var_name)])
        if not ok:
            return
        amount = self.var_amount.get().strip()
        name = self.var_name.get().strip()

        amt = safe_float(amount)
        if amt is None or amt < 0:
            messagebox.showerror("Грешна сума", "Сумата трябва да е число (>= 0).")
            return

        first, last = self.split_name(name)
        if not first or not last:
            messagebox.showerror("Невалидно име", "Моля въведи поне име и фамилия.")
            return

        manual = self.var_code.get().strip()
        if manual:
            code = manual
        else:
            code = create_code(self.sheet, first, last)
            self.var_code.set(code)

        out = capture_stdout(add_gift_card, self.sheet, code, int(amt) if float(amt).is_integer() else amt, name)
        if out:
            self.log_line(out)

        self.var_msg.set("Картата е създадена.")
        self.refresh_results()
        self._select_in_table(code)
        self.update_info_from_code(code)
        self.var_lookup_code.set(code)
        self.var_redeem_code.set(code)

    def on_lookup(self):
        ok = self.ensure_fields("Липсва код за търсене", [("Код", self.var_lookup_code)])
        if not ok:
            return
        code = self.var_lookup_code.get().strip()
        out = capture_stdout(print_info, self.sheet, code)
        if out:
            self.log_line(out)
        self.var_msg.set("Проверка по код.")
        self.update_info_from_code(code)
        self._select_in_table(code)
        self.var_redeem_code.set(code)
        self.var_code.set(code)

    def on_redeem(self):
        ok = self.ensure_fields("Липсва информация за използване", [("Код", self.var_redeem_code), ("Сума за приспадане", self.var_redeem_amount)])
        if not ok:
            return
        code = self.var_redeem_code.get().strip()
        amount = self.var_redeem_amount.get().strip()

        amt = safe_float(amount)
        if amt is None or amt <= 0:
            messagebox.showerror("Грешна сума", "Сумата за приспадане трябва да е число (> 0).")
            return

        cell = self.sheet.find(code)
        date_added = ""
        if cell:
            date_added = str(self.sheet.cell(cell.row, 2).value).strip()

        if is_expired(code, date_added):
            messagebox.showerror("Изтекла карта", "Тази подаръчна карта е изтекла и не може да се използва.")
            return

        out = capture_stdout(use_portion, self.sheet, code, int(amt) if float(amt).is_integer() else amt)
        if out:
            self.log_line(out)

        cell = self.sheet.find(code)
        if cell:
            row = cell.row
            bal = safe_float(self.sheet.cell(row, 3).value)
            used_date = str(self.sheet.cell(row, 5).value).strip()
            if (bal is not None and bal <= 0) and not used_date:
                out2 = capture_stdout(gift_card_used, self.sheet, code)
                if out2:
                    self.log_line(out2)

        self.var_msg.set("Операцията 'Използвай' е изпълнена.")
        self.refresh_results()
        self._select_in_table(code)
        self.update_info_from_code(code)

    def on_mark_used(self):
        ok = self.ensure_fields("Липсва код", [("Код", self.var_redeem_code)])
        if not ok:
            return
        code = self.var_redeem_code.get().strip()
        if not code:
            return

        out = capture_stdout(gift_card_used, self.sheet, code)
        if out:
            self.log_line(out)

        self.var_msg.set("Маркирано като използвана (ако е намерена).")
        self.refresh_results()
        self._select_in_table(code)
        self.update_info_from_code(code)
        self.var_code.set(code)
        self.var_lookup_code.set(code)

    def on_remove(self):
        ok = self.ensure_fields("Липсва код за премахване", [("Код", self.var_code)])
        if not ok:
            return
        code = self.var_code.get().strip()
        if not code:
            return
        if not messagebox.askyesno("Потвърждение", f"Сигурен ли си, че искаш да премахнеш карта:\n{code}?"):
            return
        out = capture_stdout(remove_gift_card, self.sheet, code)
        if out:
            self.log_line(out)
        self.var_msg.set("Картата е премахната (ако е съществувала).")
        self.refresh_results()
        self.update_info_from_code(code)

    # ---------------- table ----------------
    def refresh_results(self):
        for iid in self.table.get_children():
            self.table.delete(iid)

        q = self.var_search.get().strip().lower()
        for row in self.sheet.get_all_rows():
            r = list(row)
            while len(r) < 5:
                r.append("")

            code = str(r[0]).strip()
            date_added = str(r[1]).strip()
            amount = str(r[2]).strip()
            name = str(r[3]).strip()
            used = str(r[4]).strip()
            status = row_status(r)

            exp = get_expiry(code, date_added)
            exp_str = fmt_dd_mm_yy(exp)

            blob = f"{code} {date_added} {exp_str} {amount} {name} {used} {status}".lower()
            if q and q not in blob:
                continue

            self.table.insert("", "end", values=(code, date_added, exp_str, amount, name, used, status))

        self.var_msg.set("Резултатите са обновени.")
        self.log_line("Резултатите са обновени.")

    def _select_in_table(self, code: str):
        code = str(code).strip()
        for iid in self.table.get_children():
            vals = self.table.item(iid, "values")
            if vals and str(vals[0]).strip() == code:
                self.table.selection_set(iid)
                self.table.see(iid)
                return

    def on_table_double_click(self, _event=None):
        sel = self.table.selection()
        if not sel:
            return
        vals = self.table.item(sel[0], "values")
        if not vals:
            return

        # code, date, expiry, amount, name, used, status
        code = str(vals[0]).strip()
        name = str(vals[4]).strip()

        self.var_lookup_code.set(code)
        self.var_redeem_code.set(code)
        self.var_code.set(code)
        self.var_name.set(name)

        self.update_info_from_code(code)
        self.var_msg.set("Заредено от таблицата.")
        self.log_line(f"Заредено от таблицата: {code}")

    # ---------------- export ----------------
    def export_csv(self):
        path = filedialog.asksaveasfilename(
            title="Експорт в CSV",
            defaultextension=".csv",
            filetypes=[("CSV файлове", "*.csv")],
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["code", "date_added", "expiry", "amount", "name", "used_date", "status"])
                for row in self.sheet.get_all_rows():
                    r = list(row)
                    while len(r) < 5:
                        r.append("")
                    code = str(r[0]).strip()
                    date_added = str(r[1]).strip()
                    exp = get_expiry(code, date_added)
                    exp_str = fmt_dd_mm_yy(exp)
                    w.writerow([r[0], r[1], exp_str, r[2], r[3], r[4], row_status(r)])
        except Exception as e:
            messagebox.showerror("Грешка", str(e))
            return

        self.var_msg.set("Експортът е готов.")
        self.log_line(f"Експорт в CSV: {path}")

    # ---------------- demo seed ----------------
    def _seed_demo(self):
        today = datetime.now().strftime("%d.%m.%Y")
        self.sheet.append_row(["CRDEMO0001", today, 100, "Иван Иванов", ""], value_input_option="USER_ENTERED")
        self.sheet.append_row(["CRDEMO0002", today, 50, "Мария Петрова", ""], value_input_option="USER_ENTERED")
        self.log_line("Заредени са тестови карти (SheetStub).")


# IMPORTANT:
# Do NOT call mainloop() here.
# main.py should contain:
#   from ui import GiftCardUI
#   if __name__ == "__main__":
#       GiftCardUI().mainloop()