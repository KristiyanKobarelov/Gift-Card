# ui.py (clean base)
# Frontend-first Tkinter UI for Gift Card management.
# - Full name (BG) -> split into first/last -> create_code(first,last,sheet)
# - Manual code override: if Code is entered, it is used
# - Defaults: Issued = today, Expires = today + default months (12)
# - Prints payloads to console + UI log
# - Demo in-memory store for table/results while you build

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dataclasses import dataclass
from datetime import date, datetime
import calendar
import csv
from typing import Callable, Optional

# Try import your existing generator
try:
    from Functions.code_generator import create_code  # expects create_code(first_name, last_name, sheet)
except Exception as e:
    create_code = None
    _CREATE_CODE_IMPORT_ERROR = e
else:
    _CREATE_CODE_IMPORT_ERROR = None


# -------------------------
# Helpers
# -------------------------
def today_iso() -> str:
    return date.today().isoformat()


def parse_iso_date(s: str) -> date:
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()


def add_months(d: date, months: int) -> date:
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(d.day, last_day)
    return date(year, month, day)


def compute_status(balance: float, expires_on: date) -> str:
    if balance <= 0:
        return "Redeemed"
    if date.today() > expires_on:
        return "Expired"
    return "Active"


@dataclass
class CardRecord:
    code: str
    issued_on: date
    expires_on: date
    initial_value: float
    balance: float
    name_bg: str


class MissingInfoDialog(tk.Toplevel):
    """Modal dialog asking only for missing fields."""

    def __init__(self, parent: tk.Tk, title: str, fields: list[tuple[str, tk.StringVar]]):
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
        ttk.Button(btns, text="Cancel", command=self._cancel).pack(side="right", padx=(6, 0))
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


class GiftCardUI(tk.Tk):
    """
    Frontend-first UI. Uses demo in-memory store + prints payloads.
    Later you’ll replace store_* methods with Google Sheets calls.
    """

    class SheetStub:
        """
        Adapter passed to create_code(first,last,sheet).
        We expose multiple method names because we don't know what create_code calls.
        """

        def __init__(self, code_exists: Callable[[str], bool]):
            self._code_exists = code_exists

        # common names
        def code_exists(self, code: str) -> bool:
            return self._code_exists(code)

        def exists(self, code: str) -> bool:
            return self._code_exists(code)

        def has_code(self, code: str) -> bool:
            return self._code_exists(code)

        # common "find" styles
        def find_code(self, code: str):
            return code if self._code_exists(code) else None

        def find(self, code: str):
            return code if self._code_exists(code) else None

    def __init__(self):
        super().__init__()
        self.title("Gift Card Manager")
        self.geometry("1100x700")
        self.minsize(980, 600)

        # demo store
        self._demo_cards: dict[str, CardRecord] = {}

        # outputs
        self.var_message = tk.StringVar(value="Ready.")
        self.var_status = tk.StringVar(value="—")
        self.var_balance = tk.StringVar(value="—")
        self.var_expires_on_out = tk.StringVar(value="—")

        self._build_menu()
        self._build_layout()

        self._seed_demo()
        self.refresh_results()

        if create_code is None:
            self.var_message.set("WARNING: code_generator.py не се импортва (Generate/Issue ще дадат грешка).")
            self.log_line(f"[WARN] code_generator import error: {_CREATE_CODE_IMPORT_ERROR}")

    # -------------------------
    # UI build
    # -------------------------
    def _build_menu(self):
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Export results to CSV…", command=self.export_results_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Reset dates to defaults", command=self.reset_dates)
        tools_menu.add_command(label="Clear all fields", command=self.clear_all_fields)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def _build_layout(self):
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=0)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        # LEFT
        left = ttk.Frame(root)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        left.rowconfigure(1, weight=1)

        self.nb = ttk.Notebook(left)
        self.nb.grid(row=0, column=0, sticky="n")

        self._build_tab_issue()
        self._build_tab_redeem()
        self._build_tab_lookup()
        self._build_tab_settings()

        out = ttk.LabelFrame(left, text="Output", padding=10)
        out.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        out.columnconfigure(1, weight=1)

        ttk.Label(out, text="Status:").grid(row=0, column=0, sticky="w")
        ttk.Label(out, textvariable=self.var_status).grid(row=0, column=1, sticky="w")

        ttk.Label(out, text="Balance:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(out, textvariable=self.var_balance).grid(row=1, column=1, sticky="w", pady=(6, 0))

        ttk.Label(out, text="Expires on:").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Label(out, textvariable=self.var_expires_on_out).grid(row=2, column=1, sticky="w", pady=(6, 0))

        ttk.Label(out, text="Message:").grid(row=3, column=0, sticky="nw", pady=(10, 0))
        ttk.Label(out, textvariable=self.var_message, wraplength=340).grid(row=3, column=1, sticky="w", pady=(10, 0))

        # RIGHT
        right = ttk.Frame(root)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        header = ttk.Frame(right)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        ttk.Label(header, text="Results").grid(row=0, column=0, sticky="w")

        self.var_search = tk.StringVar()
        ttk.Entry(header, textvariable=self.var_search).grid(row=0, column=1, sticky="ew", padx=(10, 6))
        ttk.Button(header, text="Refresh", command=self.refresh_results).grid(row=0, column=2)
        ttk.Button(header, text="Clear", command=self.clear_search).grid(row=0, column=3, padx=(6, 0))

        table_frame = ttk.Frame(right)
        table_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        cols = ("code", "issued_on", "expires_on", "name_bg", "balance", "status")
        self.table = ttk.Treeview(table_frame, columns=cols, show="headings")
        headings = {
            "code": "Code",
            "issued_on": "Issued",
            "expires_on": "Expires",
            "name_bg": "Име",
            "balance": "Balance",
            "status": "Status",
        }
        widths = {"code": 240, "issued_on": 110, "expires_on": 110, "name_bg": 260, "balance": 110, "status": 110}
        for c in cols:
            self.table.heading(c, text=headings[c])
            self.table.column(c, width=widths[c], anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=vsb.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.table.bind("<Double-1>", self.on_table_double_click)

        log_frame = ttk.LabelFrame(right, text="Log", padding=6)
        log_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        self.log = tk.Text(log_frame, height=7, wrap="word")
        self.log.grid(row=0, column=0, sticky="ew")
        self.log.configure(state="disabled")

    def _build_tab_issue(self):
        tab = ttk.Frame(self.nb, padding=10)
        self.nb.add(tab, text="Issue")
        tab.columnconfigure(1, weight=1)

        self.var_code = tk.StringVar()
        self.var_initial_value = tk.StringVar()
        self.var_name_bg = tk.StringVar()
        self.var_issued_on = tk.StringVar(value=today_iso())
        self.var_expires_on = tk.StringVar(value=add_months(date.today(), 12).isoformat())

        ttk.Label(tab, text="Card code (optional override)").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(tab, textvariable=self.var_code).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(tab, text="Initial value").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(tab, textvariable=self.var_initial_value).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(tab, text="Name (in Cyrillic)").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(tab, textvariable=self.var_name_bg).grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(tab, text="Issued on (YYYY-MM-DD)").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(tab, textvariable=self.var_issued_on).grid(row=3, column=1, sticky="ew", pady=4)

        ttk.Label(tab, text="Expires on (YYYY-MM-DD)").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Entry(tab, textvariable=self.var_expires_on).grid(row=4, column=1, sticky="ew", pady=4)

        btns = ttk.Frame(tab)
        btns.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        btns.columnconfigure(0, weight=1)
        ttk.Button(btns, text="Generate code", command=self.on_generate_code).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(btns, text="Issue / Create", command=self.on_issue).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        ttk.Label(tab, text="Tip: Leave code empty to auto-generate. If you type a code, it overrides generation.").grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )

    def _build_tab_redeem(self):
        tab = ttk.Frame(self.nb, padding=10)
        self.nb.add(tab, text="Redeem")
        tab.columnconfigure(1, weight=1)

        self.var_redeem_code = tk.StringVar()
        self.var_redeem_amount = tk.StringVar()

        ttk.Label(tab, text="Card code").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(tab, textvariable=self.var_redeem_code).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(tab, text="Redeem amount").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(tab, textvariable=self.var_redeem_amount).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Button(tab, text="Redeem", command=self.on_redeem).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    def _build_tab_lookup(self):
        tab = ttk.Frame(self.nb, padding=10)
        self.nb.add(tab, text="Lookup")
        tab.columnconfigure(1, weight=1)

        self.var_lookup_code = tk.StringVar()

        ttk.Label(tab, text="Card code").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(tab, textvariable=self.var_lookup_code).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Button(tab, text="Lookup", command=self.on_lookup).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    def _build_tab_settings(self):
        tab = ttk.Frame(self.nb, padding=10)
        self.nb.add(tab, text="Settings")
        tab.columnconfigure(1, weight=1)

        self.var_default_expiry_months = tk.StringVar(value="12")

        ttk.Label(tab, text="Default expiry (months)").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(tab, textvariable=self.var_default_expiry_months).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Button(tab, text="Apply defaults to Issue tab", command=self.reset_dates).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0)
        )

        ttk.Label(tab, text="Defaults affect only auto-filled dates. You can still override Issued/Expires.").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )

    # -------------------------
    # UX helpers
    # -------------------------
    def log_line(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def show_about(self):
        messagebox.showinfo(
            "About",
            "Gift Card Manager (frontend-first)\n\n"
            "Currently uses demo in-memory store + prints payloads.\n"
            "Next step: connect Google Sheets + replace store_*."
        )

    def clear_outputs(self):
        self.var_status.set("—")
        self.var_balance.set("—")
        self.var_expires_on_out.set("—")

    def set_outputs_from_card(self, card: CardRecord):
        self.var_status.set(compute_status(card.balance, card.expires_on))
        self.var_balance.set(f"{card.balance:.2f}")
        self.var_expires_on_out.set(card.expires_on.isoformat())

    def _safe_float(self, s: str) -> Optional[float]:
        try:
            return float(s.strip())
        except Exception:
            return None

    def _safe_int(self, s: str, default: int) -> int:
        try:
            return int(s.strip())
        except Exception:
            return default

    def _ensure_fields(self, title: str, required: list[tuple[str, tk.StringVar]]) -> bool:
        missing = [(label, var) for (label, var) in required if not var.get().strip()]
        if not missing:
            return True
        dlg = MissingInfoDialog(self, title=title, fields=missing)
        self.wait_window(dlg)
        return dlg.ok

    # -------------------------
    # Defaults / clearing
    # -------------------------
    def reset_dates(self):
        self.var_issued_on.set(today_iso())
        months = self._safe_int(self.var_default_expiry_months.get(), 12)
        if months < 0:
            months = 0
        if months > 120:
            months = 120
        self.var_expires_on.set(add_months(date.today(), months).isoformat())
        self.var_message.set("Reset dates to defaults.")
        self.log_line("Reset dates to defaults.")

    def clear_all_fields(self):
        self.var_code.set("")
        self.var_initial_value.set("")
        self.var_name_bg.set("")
        self.var_lookup_code.set("")
        self.var_redeem_code.set("")
        self.var_redeem_amount.set("")
        self.reset_dates()
        self.clear_outputs()
        self.var_message.set("Cleared fields.")
        self.log_line("Cleared fields.")

    def clear_search(self):
        self.var_search.set("")
        self.refresh_results()

    # -------------------------
    # Name split
    # -------------------------
    def split_full_name_bg(self, full_name: str) -> tuple[str, str]:
        parts = [p for p in full_name.strip().split() if p]
        if len(parts) < 2:
            return "", ""
        first_name = parts[0]
        last_name = " ".join(parts[1:])
        return first_name, last_name

    # -------------------------
    # Store (demo) + code exists
    # -------------------------
    def code_exists(self, code: str) -> bool:
        return code in self._demo_cards

    def store_create_card(self, card: CardRecord) -> None:
        self._demo_cards[card.code] = card

    def store_get_card(self, code: str) -> Optional[CardRecord]:
        return self._demo_cards.get(code)

    def store_redeem(self, code: str, amount: float) -> Optional[CardRecord]:
        card = self._demo_cards.get(code)
        if not card:
            return None
        card.balance = max(0.0, card.balance - amount)
        return card

    def store_search(self, query: str) -> list[CardRecord]:
        q = query.strip().lower()
        if not q:
            return list(self._demo_cards.values())
        out: list[CardRecord] = []
        for c in self._demo_cards.values():
            status = compute_status(c.balance, c.expires_on).lower()
            if q in c.code.lower() or q in c.name_bg.lower() or q in status:
                out.append(c)
        return out

    # -------------------------
    # Actions
    # -------------------------
    def on_generate_code(self):
        if create_code is None:
            messagebox.showerror("Missing code_generator", f"code_generator.py import error:\n{_CREATE_CODE_IMPORT_ERROR}")
            return

        ok = self._ensure_fields("Missing info for code generation", [("Име (на кирилица)", self.var_name_bg)])
        if not ok:
            return

        full_name = self.var_name_bg.get().strip()
        first_name, last_name = self.split_full_name_bg(full_name)
        if not first_name or not last_name:
            messagebox.showerror("Invalid name", "Моля въведи поне име и фамилия (напр. Иван Иванов).")
            return

        sheet_stub = self.SheetStub(self.code_exists)

        try:
            code = create_code(first_name, last_name, sheet_stub)
        except Exception as e:
            messagebox.showerror("create_code() error", str(e))
            return

        self.var_code.set(str(code))

        payload = {
            "action": "generate_code",
            "full_name_bg": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "suggested_code": str(code),
        }
        print("[UI]", payload)
        self.log_line(f"[UI] {payload}")
        self.var_message.set("Generated code (printed to console).")

    def on_issue(self):
        if create_code is None:
            messagebox.showerror("Missing code_generator", f"code_generator.py import error:\n{_CREATE_CODE_IMPORT_ERROR}")
            return

        ok = self._ensure_fields(
            "Missing info to issue card",
            [
                ("Initial value", self.var_initial_value),
                ("Име (на кирилица)", self.var_name_bg),
                ("Issued on (YYYY-MM-DD)", self.var_issued_on),
                ("Expires on (YYYY-MM-DD)", self.var_expires_on),
            ],
        )
        if not ok:
            return

        amount = self._safe_float(self.var_initial_value.get())
        if amount is None or amount < 0:
            messagebox.showerror("Invalid amount", "Initial value must be a non-negative number.")
            return

        try:
            issued_on = parse_iso_date(self.var_issued_on.get())
        except Exception:
            messagebox.showerror("Invalid date", "Issued on must be YYYY-MM-DD.")
            return

        try:
            expires_on = parse_iso_date(self.var_expires_on.get())
        except Exception:
            messagebox.showerror("Invalid date", "Expires on must be YYYY-MM-DD.")
            return

        if expires_on < issued_on:
            messagebox.showerror("Invalid dates", "Expires on cannot be before Issued on.")
            return

        full_name = self.var_name_bg.get().strip()
        first_name, last_name = self.split_full_name_bg(full_name)
        if not first_name or not last_name:
            messagebox.showerror("Invalid name", "Моля въведи поне име и фамилия (напр. Иван Иванов).")
            return

        manual_code = self.var_code.get().strip().upper()
        if manual_code:
            code = manual_code
        else:
            sheet_stub = self.SheetStub(self.code_exists)
            try:
                code = str(create_code(first_name, last_name, sheet_stub))
            except Exception as e:
                messagebox.showerror("create_code() error", str(e))
                return
            self.var_code.set(code)

        payload = {
            "action": "issue",
            "code": code,
            "manual_code_override": bool(manual_code),
            "initial_value": float(amount),
            "issued_on": issued_on.isoformat(),
            "expires_on": expires_on.isoformat(),
            "full_name_bg": full_name,
            "first_name": first_name,
            "last_name": last_name,
        }
        print("[UI]", payload)
        self.log_line(f"[UI] {payload}")
        self.var_message.set("Issue clicked (printed to console).")

        # demo: add to local table so you see the flow
        card = CardRecord(
            code=code,
            issued_on=issued_on,
            expires_on=expires_on,
            initial_value=float(amount),
            balance=float(amount),
            name_bg=full_name,
        )
        self.store_create_card(card)
        self.set_outputs_from_card(card)
        self.refresh_results()

    def on_lookup(self):
        ok = self._ensure_fields("Missing info for lookup", [("Card code", self.var_lookup_code)])
        if not ok:
            return

        code = self.var_lookup_code.get().strip().upper()
        payload = {"action": "lookup", "code": code}
        print("[UI]", payload)
        self.log_line(f"[UI] {payload}")
        self.var_message.set("Lookup clicked (printed to console).")

        card = self.store_get_card(code)
        if card:
            self.set_outputs_from_card(card)
            self._select_code_in_table(code)
        else:
            self.clear_outputs()

    def on_redeem(self):
        ok = self._ensure_fields(
            "Missing info for redeem",
            [
                ("Card code", self.var_redeem_code),
                ("Redeem amount", self.var_redeem_amount),
            ],
        )
        if not ok:
            return

        code = self.var_redeem_code.get().strip().upper()
        amt = self._safe_float(self.var_redeem_amount.get())
        if amt is None or amt <= 0:
            messagebox.showerror("Invalid amount", "Redeem amount must be a positive number.")
            return

        payload = {"action": "redeem", "code": code, "amount": float(amt)}
        print("[UI]", payload)
        self.log_line(f"[UI] {payload}")
        self.var_message.set("Redeem clicked (printed to console).")

        card = self.store_get_card(code)
        if not card:
            self.clear_outputs()
            return

        if compute_status(card.balance, card.expires_on) == "Expired":
            messagebox.showerror("Cannot redeem", f"Card {code} is expired.")
            return

        updated = self.store_redeem(code, float(amt))
        if updated:
            self.set_outputs_from_card(updated)
            self.refresh_results()

    # -------------------------
    # Results / export
    # -------------------------
    def refresh_results(self):
        for iid in self.table.get_children():
            self.table.delete(iid)

        rows = self.store_search(self.var_search.get())

        for c in sorted(rows, key=lambda r: (r.expires_on, r.code)):
            status = compute_status(c.balance, c.expires_on)
            self.table.insert(
                "",
                "end",
                values=(c.code, c.issued_on.isoformat(), c.expires_on.isoformat(), c.name_bg, f"{c.balance:.2f}", status),
            )

        self.var_message.set("Results refreshed.")
        self.log_line("Results refreshed.")

    def on_table_double_click(self, _event=None):
        sel = self.table.selection()
        if not sel:
            return
        values = self.table.item(sel[0], "values")
        if not values:
            return
        code = str(values[0])

        self.var_code.set(code)
        self.var_lookup_code.set(code)
        self.var_redeem_code.set(code)

        card = self.store_get_card(code)
        if card:
            self.var_name_bg.set(card.name_bg)
            self.var_issued_on.set(card.issued_on.isoformat())
            self.var_expires_on.set(card.expires_on.isoformat())
            self.var_initial_value.set(f"{card.initial_value:.2f}")
            self.set_outputs_from_card(card)
            self.var_message.set("Loaded from results.")
            self.log_line(f"Loaded from results -> {code}")

    def _select_code_in_table(self, code: str):
        for iid in self.table.get_children():
            vals = self.table.item(iid, "values")
            if vals and str(vals[0]) == code:
                self.table.selection_set(iid)
                self.table.see(iid)
                return

    def export_results_csv(self):
        if not self.table.get_children():
            messagebox.showinfo("Export", "No results to export.")
            return

        path = filedialog.asksaveasfilename(
            title="Export results to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["code", "issued_on", "expires_on", "name_bg", "balance", "status"])
                for iid in self.table.get_children():
                    w.writerow(self.table.item(iid, "values"))
        except Exception as e:
            messagebox.showerror("Export failed", str(e))
            return

        self.var_message.set("Exported results to CSV.")
        self.log_line(f"Exported CSV -> {path}")

    # -------------------------
    # Demo seed
    # -------------------------
    def _seed_demo(self):
        expires = add_months(date.today(), 12)
        c1 = CardRecord(code="CRDEMO0001", issued_on=date.today(), expires_on=expires, initial_value=100.0, balance=100.0, name_bg="Иван Иванов")
        c2 = CardRecord(code="CRDEMO0002", issued_on=date.today(), expires_on=expires, initial_value=50.0, balance=0.0, name_bg="Мария Петрова")
        self._demo_cards[c1.code] = c1
        self._demo_cards[c2.code] = c2
        self.log_line("Loaded demo cards (UI-only).")


# IMPORTANT:
# Do NOT call mainloop() here.
# main.py should contain:
#   from ui import GiftCardUI
#   if __name__ == "__main__":
#       GiftCardUI().mainloop()