import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime
from dataclasses import dataclass


def today_iso() -> str:
    return date.today().isoformat()


def parse_iso_date(s: str) -> date:
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()


def add_months(d: date, months: int) -> date:
    # Safe month-add without external deps
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    # clamp day to end of month
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    day = min(d.day, last_day)
    return date(year, month, day)


def compute_status(balance: float, expires_on: date | None, voided: bool = False) -> str:
    if voided:
        return "Voided"
    if balance <= 0:
        return "Redeemed"
    if expires_on is not None and date.today() > expires_on:
        return "Expired"
    return "Active"


@dataclass
class CardRow:
    code: str
    issued_on: date
    expires_on: date | None
    initial_value: float
    balance: float
    voided: bool = False


class GiftCardUI(tk.Tk):
    """
    FRONTEND-ONLY UI.
    - No real backend connectivity
    - Keeps a local in-memory list ONLY to populate the table visually
    """
    def __init__(self):
        super().__init__()
        self.title("Company Gift Cards (Frontend Only)")
        self.geometry("1050x640")
        self.minsize(950, 560)

        # UI-only demo storage (not your real backend)
        self._cards: dict[str, CardRow] = {}

        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=0)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        self._build_left(root)
        self._build_right(root)

        self.table.bind("<Double-1>", self.on_row_double_click)

        self._seed_demo()
        self.refresh_table()

    # ---------------- UI BUILD ----------------
    def _build_left(self, parent: ttk.Frame):
        left = ttk.Frame(parent)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 10))

        form = ttk.LabelFrame(left, text="Issue / Manage card", padding=10)
        form.grid(row=0, column=0, sticky="ew")
        form.columnconfigure(1, weight=1)

        self.var_code = tk.StringVar()
        self.var_initial = tk.StringVar()
        self.var_issued_on = tk.StringVar(value=today_iso())

        self.var_never_expires = tk.BooleanVar(value=False)
        self.var_expires_months = tk.StringVar(value="12")

        # Redeem amount input (for later)
        self.var_redeem_amount = tk.StringVar(value="")

        ttk.Label(form, text="Card code").grid(row=0, column=0, sticky="w", pady=4)
        self.entry_code = ttk.Entry(form, textvariable=self.var_code, width=28)
        self.entry_code.grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Initial value").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.var_initial).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Issued on (YYYY-MM-DD)").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.var_issued_on).grid(row=2, column=1, sticky="ew", pady=4)

        # Expiry policy
        expiry_frame = ttk.Frame(form)
        expiry_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        expiry_frame.columnconfigure(1, weight=1)

        ttk.Checkbutton(
            expiry_frame,
            text="Never expires",
            variable=self.var_never_expires,
            command=self._toggle_expiry_inputs
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(expiry_frame, text="Expires in (months):").grid(row=1, column=0, sticky="w", pady=4)
        self.entry_expires_months = ttk.Entry(expiry_frame, textvariable=self.var_expires_months, width=10)
        self.entry_expires_months.grid(row=1, column=1, sticky="w", pady=4)

        ttk.Separator(form).grid(row=4, column=0, columnspan=2, sticky="ew", pady=10)

        ttk.Label(form, text="Redeem amount").grid(row=5, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.var_redeem_amount).grid(row=5, column=1, sticky="ew", pady=4)

        # Outputs
        out = ttk.LabelFrame(left, text="Output (calculated)", padding=10)
        out.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        out.columnconfigure(1, weight=1)

        self.var_out_balance = tk.StringVar(value="—")
        self.var_out_status = tk.StringVar(value="—")
        self.var_out_expires_on = tk.StringVar(value="—")
        self.var_out_message = tk.StringVar(value="Ready.")

        ttk.Label(out, text="Balance:").grid(row=0, column=0, sticky="w")
        ttk.Label(out, textvariable=self.var_out_balance).grid(row=0, column=1, sticky="w")

        ttk.Label(out, text="Status:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(out, textvariable=self.var_out_status).grid(row=1, column=1, sticky="w", pady=(6, 0))

        ttk.Label(out, text="Expires on:").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Label(out, textvariable=self.var_out_expires_on).grid(row=2, column=1, sticky="w", pady=(6, 0))

        ttk.Label(out, text="Message:").grid(row=3, column=0, sticky="nw", pady=(8, 0))
        ttk.Label(out, textvariable=self.var_out_message, wraplength=280).grid(
            row=3, column=1, sticky="w", pady=(8, 0)
        )

        # Actions (UI only)
        actions = ttk.LabelFrame(left, text="Actions (UI only)", padding=10)
        actions.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        actions.columnconfigure(0, weight=1)

        ttk.Button(actions, text="Issue / Save", command=self.on_issue_clicked).grid(row=0, column=0, sticky="ew", pady=4)
        ttk.Button(actions, text="Lookup", command=self.on_lookup_clicked).grid(row=1, column=0, sticky="ew", pady=4)
        ttk.Button(actions, text="Redeem", command=self.on_redeem_clicked).grid(row=2, column=0, sticky="ew", pady=4)
        ttk.Button(actions, text="Void", command=self.on_void_clicked).grid(row=3, column=0, sticky="ew", pady=4)

        ttk.Separator(actions).grid(row=4, column=0, sticky="ew", pady=10)

        ttk.Button(actions, text="Export CSV (table only)", command=self.on_export_clicked).grid(row=5, column=0, sticky="ew", pady=4)
        ttk.Button(actions, text="Clear form", command=self.clear_form).grid(row=6, column=0, sticky="ew", pady=4)

        self._toggle_expiry_inputs()

    def _build_right(self, parent: ttk.Frame):
        right = ttk.Frame(parent)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        top = ttk.Frame(right)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Search:").grid(row=0, column=0, sticky="w")
        self.var_search = tk.StringVar()
        ttk.Entry(top, textvariable=self.var_search).grid(row=0, column=1, sticky="ew", padx=(6, 6))
        ttk.Button(top, text="Apply", command=self.refresh_table).grid(row=0, column=2, sticky="e")
        ttk.Button(top, text="Reset", command=self.on_search_reset).grid(row=0, column=3, sticky="e", padx=(6, 0))

        table_frame = ttk.Frame(right)
        table_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        cols = ("code", "issued_on", "expires_on", "balance", "status")
        self.table = ttk.Treeview(table_frame, columns=cols, show="headings")
        headers = {
            "code": "Card Code",
            "issued_on": "Issued On",
            "expires_on": "Expires On",
            "balance": "Balance",
            "status": "Status",
        }
        widths = {"code": 260, "issued_on": 120, "expires_on": 120, "balance": 120, "status": 120}
        for c in cols:
            self.table.heading(c, text=headers[c])
            self.table.column(c, width=widths[c], anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=vsb.set)

        self.table.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        log_frame = ttk.LabelFrame(right, text="Log", padding=6)
        log_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)

        self.log = tk.Text(log_frame, height=7, wrap="word")
        self.log.grid(row=0, column=0, sticky="ew")
        self.log.configure(state="disabled")

    # ---------------- helpers ----------------
    def log_line(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _toggle_expiry_inputs(self):
        disabled = self.var_never_expires.get()
        state = "disabled" if disabled else "normal"
        self.entry_expires_months.configure(state=state)

    def clear_form(self):
        self.var_code.set("")
        self.var_initial.set("")
        self.var_issued_on.set(today_iso())
        self.var_never_expires.set(False)
        self.var_expires_months.set("12")
        self.var_redeem_amount.set("")
        self._toggle_expiry_inputs()

        self.var_out_balance.set("—")
        self.var_out_status.set("—")
        self.var_out_expires_on.set("—")
        self.var_out_message.set("Ready.")

        self.entry_code.focus_set()
        self.log_line("Cleared form (UI).")

    def _calc_expires_on(self, issued_on: date) -> date | None:
        if self.var_never_expires.get():
            return None
        raw = self.var_expires_months.get().strip()
        months = int(raw) if raw else 12
        if months < 0:
            months = 0
        return add_months(issued_on, months)

    def _update_outputs_from_card(self, card: CardRow):
        expires_str = card.expires_on.isoformat() if card.expires_on else "Never"
        status = compute_status(card.balance, card.expires_on, card.voided)
        self.var_out_balance.set(f"{card.balance:.2f}")
        self.var_out_expires_on.set(expires_str)
        self.var_out_status.set(status)

    def _seed_demo(self):
        c1 = CardRow(code="GC-0001", issued_on=date.today(), expires_on=add_months(date.today(), 12),
                    initial_value=100.0, balance=75.0)
        c2 = CardRow(code="GC-0002", issued_on=date.today(), expires_on=None,
                    initial_value=50.0, balance=0.0)
        c3 = CardRow(code="GC-0003", issued_on=add_months(date.today(), -14), expires_on=add_months(date.today(), -2),
                    initial_value=25.0, balance=25.0)
        self._cards[c1.code] = c1
        self._cards[c2.code] = c2
        self._cards[c3.code] = c3
        self.log_line("Loaded demo cards (UI only).")

    # ---------------- table ----------------
    def refresh_table(self):
        for item in self.table.get_children():
            self.table.delete(item)

        q = self.var_search.get().strip().lower()
        for code, card in sorted(self._cards.items()):
            status = compute_status(card.balance, card.expires_on, card.voided)
            expires_str = card.expires_on.isoformat() if card.expires_on else "Never"
            if q and q not in code.lower() and q not in status.lower():
                continue
            self.table.insert("", "end", values=(
                code,
                card.issued_on.isoformat(),
                expires_str,
                f"{card.balance:.2f}",
                status
            ))

        self.var_out_message.set("Table refreshed (UI).")
        self.log_line("Refreshed table (UI).")

    def on_search_reset(self):
        self.var_search.set("")
        self.refresh_table()

    def _get_selected_code(self) -> str | None:
        sel = self.table.selection()
        if not sel:
            return None
        values = self.table.item(sel[0], "values")
        return values[0] if values else None

    # ---------------- actions (UI only) ----------------
    def on_issue_clicked(self):
        # UI-only: create/update local demo record so you can see the flow.
        code = self.var_code.get().strip()
        if not code:
            messagebox.showerror("Validation", "Card code is required.")
            return

        try:
            initial = float(self.var_initial.get().strip())
            if initial < 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Validation", "Initial value must be a non-negative number.")
            return

        try:
            issued_on = parse_iso_date(self.var_issued_on.get())
        except Exception:
            messagebox.showerror("Validation", "Issued on must be YYYY-MM-DD.")
            return

        expires_on = self._calc_expires_on(issued_on)

        card = CardRow(
            code=code,
            issued_on=issued_on,
            expires_on=expires_on,
            initial_value=initial,
            balance=initial,
            voided=False
        )

        self._cards[code] = card  # UI-only store
        self._update_outputs_from_card(card)

        self.var_out_message.set("UI: Issued/Saved (local table only).")
        self.log_line(f"Issue/Save clicked -> code={code}, initial={initial:.2f}, expires={expires_on or 'Never'}")

        self.refresh_table()

    def on_lookup_clicked(self):
        code = self.var_code.get().strip() or self._get_selected_code()
        if not code:
            messagebox.showinfo("Lookup", "Enter a card code or select a row.")
            return

        card = self._cards.get(code)
        if not card:
            self.var_out_message.set("UI: Card not found (local demo list).")
            self.log_line(f"Lookup -> not found: {code}")
            return

        self._update_outputs_from_card(card)
        self.var_out_message.set("UI: Loaded card (local demo list).")
        self.log_line(f"Lookup -> found: {code}")

    def on_redeem_clicked(self):
        # UI-only: subtract redeem amount from local demo record
        code = self.var_code.get().strip() or self._get_selected_code()
        if not code:
            messagebox.showinfo("Redeem", "Enter a card code or select a row.")
            return

        card = self._cards.get(code)
        if not card:
            messagebox.showerror("Redeem", "Card not found (UI demo).")
            return

        try:
            amt = float(self.var_redeem_amount.get().strip())
            if amt <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Redeem", "Redeem amount must be a positive number.")
            return

        # UI-only logic (so you can see behavior)
        card.balance = max(0.0, card.balance - amt)
        self._update_outputs_from_card(card)
        self.var_out_message.set("UI: Redeemed (local table only).")
        self.log_line(f"Redeem clicked -> code={code}, amount={amt:.2f}, new_balance={card.balance:.2f}")
        self.refresh_table()

    def on_void_clicked(self):
        code = self.var_code.get().strip() or self._get_selected_code()
        if not code:
            messagebox.showinfo("Void", "Enter a card code or select a row.")
            return
        card = self._cards.get(code)
        if not card:
            messagebox.showerror("Void", "Card not found (UI demo).")
            return
        card.voided = True
        self._update_outputs_from_card(card)
        self.var_out_message.set("UI: Voided (local table only).")
        self.log_line(f"Void clicked -> code={code}")
        self.refresh_table()

    def on_export_clicked(self):
        if not self.table.get_children():
            messagebox.showinfo("Export", "Nothing to export.")
            return

        path = filedialog.asksaveasfilename(
            title="Export CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not path:
            return

        try:
            import csv
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["code", "issued_on", "expires_on", "balance", "status"])
                for iid in self.table.get_children():
                    writer.writerow(self.table.item(iid, "values"))
        except Exception as e:
            messagebox.showerror("Export failed", str(e))
            return

        self.var_out_message.set("UI: Exported table to CSV.")
        self.log_line(f"Exported CSV -> {path}")

    def on_row_double_click(self, _event=None):
        sel = self.table.selection()
        if not sel:
            return
        values = self.table.item(sel[0], "values")
        if not values:
            return
        code, issued_on, expires_on, balance, status = values

        self.var_code.set(code)
        self.var_issued_on.set(issued_on)
        self.var_initial.set(balance)  # just to populate a field; not meaningful for real backend
        self.var_out_balance.set(balance)
        self.var_out_status.set(status)
        self.var_out_expires_on.set(expires_on)

        self.var_out_message.set("UI: Loaded row into form.")
        self.log_line(f"Loaded row -> {code}")


if __name__ == "__main__":
    GiftCardUI().mainloop()