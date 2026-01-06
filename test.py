import tkinter as tk
from tkinter import ttk, messagebox, filedialog


class GiftCardUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gift Card Manager (Frontend Only)")
        self.geometry("1000x620")
        self.minsize(900, 560)

        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=0)  # left panel
        root.columnconfigure(1, weight=1)  # right panel
        root.rowconfigure(0, weight=1)

        self._build_left(root)
        self._build_right(root)

        # bindings
        self.table.bind("<Double-1>", self.on_row_double_click)

        # optional: show the layout with a few demo rows (purely UI)
        self._load_demo_rows()

    # ---------------- UI BUILD ----------------
    def _build_left(self, parent: ttk.Frame):
        left = ttk.Frame(parent)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 10))

        # --- Form ---
        form = ttk.LabelFrame(left, text="Card details", padding=10)
        form.grid(row=0, column=0, sticky="ew")
        form.columnconfigure(1, weight=1)

        self.var_code = tk.StringVar()
        self.var_amount = tk.StringVar()
        self.var_store = tk.StringVar()
        self.var_status = tk.StringVar(value="Active")
        self.var_expiry = tk.StringVar()
        self.var_note = tk.StringVar()

        ttk.Label(form, text="Card code").grid(row=0, column=0, sticky="w", pady=4)
        self.entry_code = ttk.Entry(form, textvariable=self.var_code, width=28)
        self.entry_code.grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Amount").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.var_amount).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Store").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.var_store).grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Status").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Combobox(
            form,
            textvariable=self.var_status,
            values=["Active", "Redeemed", "Expired"],
            state="readonly"
        ).grid(row=3, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Expiry (optional)").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.var_expiry).grid(row=4, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Note (optional)").grid(row=5, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.var_note).grid(row=5, column=1, sticky="ew", pady=4)

        # --- Output fields ---
        out = ttk.LabelFrame(left, text="Output", padding=10)
        out.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        out.columnconfigure(1, weight=1)

        self.var_out_balance = tk.StringVar(value="—")
        self.var_out_message = tk.StringVar(value="Ready.")

        ttk.Label(out, text="Balance:").grid(row=0, column=0, sticky="w")
        ttk.Label(out, textvariable=self.var_out_balance).grid(row=0, column=1, sticky="w")

        ttk.Label(out, text="Message:").grid(row=1, column=0, sticky="nw", pady=(8, 0))
        ttk.Label(out, textvariable=self.var_out_message, wraplength=280).grid(
            row=1, column=1, sticky="w", pady=(8, 0)
        )

        # --- Actions ---
        actions = ttk.LabelFrame(left, text="Actions (UI only)", padding=10)
        actions.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        actions.columnconfigure(0, weight=1)

        ttk.Button(actions, text="Add / Save", command=self.on_save_clicked).grid(row=0, column=0, sticky="ew", pady=4)
        ttk.Button(actions, text="Check balance", command=self.on_check_balance_clicked).grid(row=1, column=0, sticky="ew", pady=4)
        ttk.Button(actions, text="Redeem", command=self.on_redeem_clicked).grid(row=2, column=0, sticky="ew", pady=4)
        ttk.Button(actions, text="Delete", command=self.on_delete_clicked).grid(row=3, column=0, sticky="ew", pady=4)

        ttk.Separator(actions).grid(row=4, column=0, sticky="ew", pady=10)

        ttk.Button(actions, text="Export CSV", command=self.on_export_clicked).grid(row=5, column=0, sticky="ew", pady=4)
        ttk.Button(actions, text="Clear form", command=self.clear_form).grid(row=6, column=0, sticky="ew", pady=4)

        # Small hint
        hint = ttk.Label(left, text="Tip: double-click a table row to load it into the form.")
        hint.grid(row=3, column=0, sticky="w", pady=(10, 0))

    def _build_right(self, parent: ttk.Frame):
        right = ttk.Frame(parent)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        # --- Search ---
        top = ttk.Frame(right)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Search:").grid(row=0, column=0, sticky="w")
        self.var_search = tk.StringVar()
        ttk.Entry(top, textvariable=self.var_search).grid(row=0, column=1, sticky="ew", padx=(6, 6))
        ttk.Button(top, text="Apply (UI)", command=self.on_search_clicked).grid(row=0, column=2, sticky="e")
        ttk.Button(top, text="Reset", command=self.on_search_reset).grid(row=0, column=3, sticky="e", padx=(6, 0))

        # --- Table ---
        table_frame = ttk.Frame(right)
        table_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        cols = ("code", "amount", "store", "status", "expiry")
        self.table = ttk.Treeview(table_frame, columns=cols, show="headings")
        headings = {
            "code": "Card Code",
            "amount": "Amount",
            "store": "Store",
            "status": "Status",
            "expiry": "Expiry",
        }
        widths = {
            "code": 260,
            "amount": 110,
            "store": 220,
            "status": 120,
            "expiry": 140,
        }
        for c in cols:
            self.table.heading(c, text=headings[c])
            self.table.column(c, width=widths[c], anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=vsb.set)

        self.table.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # --- Log ---
        log_frame = ttk.LabelFrame(right, text="Log", padding=6)
        log_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)

        self.log = tk.Text(log_frame, height=7, wrap="word")
        self.log.grid(row=0, column=0, sticky="ew")
        self.log.configure(state="disabled")

    # ---------------- UI helpers ----------------
    def log_line(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def clear_form(self):
        self.var_code.set("")
        self.var_amount.set("")
        self.var_store.set("")
        self.var_status.set("Active")
        self.var_expiry.set("")
        self.var_note.set("")
        self.var_out_balance.set("—")
        self.var_out_message.set("Ready.")
        self.entry_code.focus_set()
        self.log_line("Cleared form (UI).")

    def selected_row_values(self):
        sel = self.table.selection()
        if not sel:
            return None
        return self.table.item(sel[0], "values")

    def _load_demo_rows(self):
        # purely visual; delete these later if you want
        demo = [
            ("ABCD-1111", "50.00", "Amazon", "Active", "2026-12-31"),
            ("EFGH-2222", "0.00", "Steam", "Redeemed", ""),
            ("IJKL-3333", "25.00", "Apple", "Active", "2027-01-15"),
        ]
        for row in demo:
            self.table.insert("", "end", values=row)
        self.log_line("Loaded demo rows (UI only).")

    # ---------------- Button handlers (no backend) ----------------
    def on_save_clicked(self):
        # UI-only: show what would be sent to backend
        payload = {
            "code": self.var_code.get().strip(),
            "amount": self.var_amount.get().strip(),
            "store": self.var_store.get().strip(),
            "status": self.var_status.get().strip(),
            "expiry": self.var_expiry.get().strip(),
            "note": self.var_note.get().strip(),
        }
        self.var_out_message.set("UI: Save clicked (no backend connected).")
        self.log_line(f"Save clicked -> {payload}")

    def on_check_balance_clicked(self):
        code = self.var_code.get().strip()
        if not code:
            messagebox.showinfo("UI only", "Enter a card code (UI only).")
            return
        self.var_out_balance.set("—")
        self.var_out_message.set("UI: Check balance clicked (no backend).")
        self.log_line(f"Check balance clicked -> code={code}")

    def on_redeem_clicked(self):
        code = self.var_code.get().strip()
        if not code:
            messagebox.showinfo("UI only", "Enter a card code (UI only).")
            return
        self.var_out_message.set("UI: Redeem clicked (no backend).")
        self.log_line(f"Redeem clicked -> code={code}")

    def on_delete_clicked(self):
        values = self.selected_row_values()
        if not values:
            messagebox.showinfo("UI only", "Select a row to delete (UI only).")
            return
        code = values[0]
        if not messagebox.askyesno("UI only", f"Delete row for {code}? (UI only)"):
            return
        # UI-only: remove row from table (no backend)
        for item in self.table.selection():
            self.table.delete(item)
        self.var_out_message.set("UI: Deleted row (table only).")
        self.log_line(f"Deleted row from table -> code={code}")

    def on_export_clicked(self):
        # UI-only: export current table view to CSV (still frontend; no backend needed)
        path = filedialog.asksaveasfilename(
            title="Export CSV (UI only)",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                import csv
                writer = csv.writer(f)
                writer.writerow(["code", "amount", "store", "status", "expiry"])
                for iid in self.table.get_children():
                    writer.writerow(self.table.item(iid, "values"))
        except Exception as e:
            messagebox.showerror("Export failed", str(e))
            return

        self.var_out_message.set("UI: Exported table to CSV.")
        self.log_line(f"Exported table to CSV -> {path}")

    def on_search_clicked(self):
        # UI-only: no filtering logic; just show search text
        q = self.var_search.get().strip()
        self.var_out_message.set("UI: Search clicked (no filtering yet).")
        self.log_line(f"Search clicked -> query='{q}'")

    def on_search_reset(self):
        self.var_search.set("")
        self.var_out_message.set("UI: Search reset.")
        self.log_line("Search reset (UI).")

    def on_row_double_click(self, _event=None):
        values = self.selected_row_values()
        if not values:
            return
        code, amount, store, status, expiry = values
        self.var_code.set(code)
        self.var_amount.set(amount)
        self.var_store.set(store)
        self.var_status.set(status)
        self.var_expiry.set(expiry)
        self.var_out_message.set("UI: Loaded row into form.")
        self.log_line(f"Loaded row into form -> code={code}")


if __name__ == "__main__":
    GiftCardUI().mainloop()