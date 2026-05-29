"""
FBC Securities — Order Management System  v2
─────────────────────────────────────────────────────────────
v2 changes:
  - Counter is now free-text (user types it manually)
  - Custodians: FBC, CABS, CBZ, STANBIC only
  - Shares entry: two modes — No. of Shares OR Total Amount
  - Limit price field: no "optional" hint, plain label
  - Today's date auto-stamped and shown on every order card
  - Detail dialog is scrollable — all fields always visible
  - Partial fill: remainder order stays TAKEN by same dealer
    (no longer goes back to PENDING with no dealer)
  - Order card redesigned: cleaner layout, date prominent
"""

import os, sys, json, threading, uuid as _uuid
import urllib.request, subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date

# ════════════════════════════════════════════════════════════════════════════
#  AUTO-UPDATE
# ════════════════════════════════════════════════════════════════════════════
VERSION       = 2
GITHUB_USER   = "Anashe-Masomeke"
GITHUB_REPO   = "fbc-order-manager"
GITHUB_BRANCH = "main"
EXE_NAME      = "FBC-Order-Manager.exe"

_EXE = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/latest/download/{EXE_NAME}"
_VER = (f"https://raw.githubusercontent.com/"
        f"{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/version.txt")

def _remote_ver():
    try:
        with urllib.request.urlopen(_VER, timeout=6) as r:
            return int(r.read().decode().strip())
    except Exception:
        return -1

def check_and_apply_update():
    rv = _remote_ver()
    if rv <= VERSION:
        return
    root = tk.Tk(); root.withdraw()
    ok = messagebox.askyesno(
        "FBC Order Manager — Update Available",
        f"New version available (v{rv}).\nYour version: v{VERSION}\n\nDownload and install now?",
        icon="info")
    root.destroy()
    if not ok: return
    current_exe  = os.path.abspath(sys.argv[0])
    exe_dir      = os.path.dirname(current_exe)
    downloads    = os.path.join(os.path.expanduser("~"), "Downloads")
    save_dir     = downloads if os.path.isdir(downloads) else os.environ.get("TEMP", exe_dir)
    new_exe_path = os.path.join(save_dir, f"FBC-Order-Manager-v{rv}.exe")
    bat_path     = os.path.join(save_dir, "_fbc_om_updater.bat")
    prog = tk.Tk(); prog.title("Downloading…"); prog.resizable(False, False)
    prog.attributes("-topmost", True)
    w, h = 420, 100
    prog.geometry(f"{w}x{h}+{(prog.winfo_screenwidth()-w)//2}+{(prog.winfo_screenheight()-h)//2}")
    tk.Label(prog, text=f"Downloading FBC Order Manager v{rv}…",
             font=("Segoe UI", 10, "bold"), pady=10).pack()
    bar = ttk.Progressbar(prog, mode="indeterminate", length=360)
    bar.pack(padx=30); bar.start(12)
    lbl = tk.Label(prog, text="Starting…", font=("Segoe UI", 8), fg="#607080")
    lbl.pack(pady=4)
    prog.update(); err = [None]
    def _dl():
        try:
            dl = 0
            with urllib.request.urlopen(_EXE, timeout=180) as r:
                with open(new_exe_path, "wb") as f:
                    while True:
                        chunk = r.read(65536)
                        if not chunk: break
                        f.write(chunk); dl += len(chunk)
                        try: lbl.config(text=f"Downloaded: {dl//1024:,} KB")
                        except: pass
            if os.path.getsize(new_exe_path) < 2*1024*1024:
                os.remove(new_exe_path); raise Exception("Download incomplete.")
            with open(bat_path, "w") as f:
                f.write("\n".join(["@echo off", "ping 127.0.0.1 -n 6 > nul",
                    f'start "" "{new_exe_path}"', "ping 127.0.0.1 -n 2 > nul",
                    'del "%~f0"', ""]))
        except Exception as e:
            err[0] = str(e)
            for fp in [new_exe_path, bat_path]:
                try: os.remove(fp)
                except: pass
        finally:
            try: prog.after(0, prog.quit)
            except: pass
    t = threading.Thread(target=_dl, daemon=True)
    t.start(); prog.mainloop(); prog.destroy(); t.join()
    if err[0]:
        r2 = tk.Tk(); r2.withdraw()
        messagebox.showerror("Update Failed", err[0]); r2.destroy(); return
    subprocess.Popen(["cmd.exe", "/c", bat_path],
                     creationflags=subprocess.CREATE_NO_WINDOW, close_fds=True)
    sys.exit(0)

# ════════════════════════════════════════════════════════════════════════════
#  COLOURS & CONSTANTS
# ════════════════════════════════════════════════════════════════════════════
FBC_DARK    = "#003B6F"
FBC_MID     = "#0066B3"
FBC_ACCENT  = "#00A3E0"
BG          = "#F0F4F8"
CARD_BG     = "#FFFFFF"
SEP_CLR     = "#D0DAE8"
SIDEBAR_BG  = "#001F3F"
SIDEBAR_TXT = "#B0C8E8"
WHITE       = "#FFFFFF"

S_PENDING   = ("#FFF8E7", "#B45309", "#FBC02D")
S_TAKEN     = ("#EAF4FB", "#0066B3", "#00A3E0")
S_EXECUTED  = ("#F0FFF4", "#1A6B3A", "#4CAF50")
S_PARTIAL   = ("#F3E8FF", "#6B21A8", "#A855F7")
S_CANCELLED = ("#F5F5F5", "#757575", "#9E9E9E")

AGING_OK_BG      = "#EAF7EF"; AGING_OK_CLR      = "#1A6B3A"
AGING_WARN_BG    = "#FFF8E7"; AGING_WARN_CLR    = "#B45309"
AGING_OVERDUE_BG = "#FFF0F0"; AGING_OVERDUE_CLR = "#B71C1C"

OVERDUE_DAYS  = 2

STATE_FILE    = os.path.join(os.path.expanduser("~"), ".fbc_orders.json")
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".fbc_orders_settings.json")
SHEET_NAME    = "FBC_Orders"

COL_HEADERS = [
    "id", "order_type", "client_name", "client_address", "csd_no", "custodian",
    "instruction_by", "num_shares", "counter", "limit_price", "exchange",
    "entered_by", "entered_datetime", "order_date", "status",
    "taken_by", "taken_datetime",
    "executed_by", "executed_datetime", "shares_executed", "execution_price",
    "cancel_reason", "notes", "partial_of", "amount_mode", "total_amount"
]

CUSTODIANS = ["FBC", "CABS", "CBZ", "STANBIC"]

# ════════════════════════════════════════════════════════════════════════════
#  SETTINGS
# ════════════════════════════════════════════════════════════════════════════
def load_settings():
    try:
        with open(SETTINGS_FILE) as f: return json.load(f)
    except:
        return {"dealer_name": "", "sheet_id": "", "key_file": ""}

def save_settings(s):
    with open(SETTINGS_FILE, "w") as f: json.dump(s, f, indent=2)

# ════════════════════════════════════════════════════════════════════════════
#  GOOGLE SHEETS BACKEND
# ════════════════════════════════════════════════════════════════════════════
def _row_to_order(row):
    def g(i, d=""):
        return row[i] if i < len(row) else d
    def si(v, d=0):
        try: return int(v or d)
        except: return d
    return {
        "id":                g(0),
        "order_type":        g(1),
        "client_name":       g(2),
        "client_address":    g(3),
        "csd_no":            g(4),
        "custodian":         g(5),
        "instruction_by":    g(6),
        "num_shares":        si(g(7, "0")),
        "counter":           g(8),
        "limit_price":       g(9),
        "exchange":          g(10),
        "entered_by":        g(11),
        "entered_datetime":  g(12),
        "order_date":        g(13),
        "status":            g(14, "PENDING"),
        "taken_by":          g(15),
        "taken_datetime":    g(16),
        "executed_by":       g(17),
        "executed_datetime": g(18),
        "shares_executed":   si(g(19, "0")),
        "execution_price":   g(20),
        "cancel_reason":     g(21),
        "notes":             g(22),
        "partial_of":        g(23),
        "amount_mode":       g(24, "SHARES"),
        "total_amount":      g(25),
    }

def _order_to_row(o):
    return [
        o.get("id", ""),              o.get("order_type", ""),
        o.get("client_name", ""),     o.get("client_address", ""),
        o.get("csd_no", ""),          o.get("custodian", ""),
        o.get("instruction_by", ""),  str(o.get("num_shares", 0)),
        o.get("counter", ""),         o.get("limit_price", ""),
        o.get("exchange", ""),        o.get("entered_by", ""),
        o.get("entered_datetime", ""),o.get("order_date", ""),
        o.get("status", "PENDING"),
        o.get("taken_by", ""),        o.get("taken_datetime", ""),
        o.get("executed_by", ""),     o.get("executed_datetime", ""),
        str(o.get("shares_executed", 0)), o.get("execution_price", ""),
        o.get("cancel_reason", ""),   o.get("notes", ""),
        o.get("partial_of", ""),      o.get("amount_mode", "SHARES"),
        o.get("total_amount", ""),
    ]

def _open_worksheet(key_file, sheet_id):
    import gspread
    from google.oauth2.service_account import Credentials
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    creds  = Credentials.from_service_account_file(key_file, scopes=SCOPES)
    gc     = gspread.authorize(creds)
    sh     = gc.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(SHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=SHEET_NAME, rows=2000, cols=len(COL_HEADERS))
        ws.append_row(COL_HEADERS)
    existing = ws.row_values(1)
    if not existing:
        ws.insert_row(COL_HEADERS, 1)
    elif len(existing) < len(COL_HEADERS):
        for i, h in enumerate(COL_HEADERS[len(existing):], start=len(existing)+1):
            ws.update_cell(1, i, h)
    return ws

def test_sheets_connection(key_file, sheet_id):
    try: _open_worksheet(key_file, sheet_id); return True, ""
    except Exception as e: return False, str(e)

class SheetsDB:
    def __init__(self, key_file, sheet_id):
        self.key_file = key_file; self.sheet_id = sheet_id
        self._online = False; self._ws = None; self._lock = threading.Lock()
        self._connect()

    def _connect(self):
        try:
            self._ws = _open_worksheet(self.key_file, self.sheet_id)
            self._online = True; print("[SheetsDB] Connected OK")
        except Exception as e:
            self._online = False; print(f"[SheetsDB] Offline — {e}")

    def _reconnect_if_needed(self):
        if not self._online: self._connect()

    @property
    def online(self): return self._online

    def read_all(self):
        self._reconnect_if_needed()
        if self._online:
            try:
                with self._lock:
                    rows = self._ws.get_all_values()
                data = [r for r in rows if r and r[0] and r[0].strip().lower() != "id"]
                orders = [_row_to_order(r) for r in data]
                with open(STATE_FILE, "w") as f: json.dump(orders, f, indent=2)
                return orders
            except Exception as e:
                print(f"[SheetsDB] read failed: {e}"); self._online = False
        try:
            with open(STATE_FILE) as f: return json.load(f)
        except: return []

    def _find_row_num(self, order_id):
        try:
            col = self._ws.col_values(1)
            for i, v in enumerate(col):
                if v == order_id: return i + 1
        except: pass
        return None

    def append_order(self, order):
        self._reconnect_if_needed()
        if self._online:
            try:
                with self._lock:
                    self._ws.append_row(_order_to_row(order), value_input_option="RAW")
                return True
            except Exception as e:
                print(f"[SheetsDB] append failed: {e}"); self._online = False
        return False

    def update_order(self, order):
        self._reconnect_if_needed()
        if self._online:
            try:
                with self._lock:
                    rn = self._find_row_num(order["id"])
                    if rn:
                        cols = len(COL_HEADERS)
                        # Build column letter for end column
                        if cols <= 26:
                            end_col = chr(ord('A') + cols - 1)
                        else:
                            end_col = chr(ord('A') + (cols-1)//26 - 1) + chr(ord('A') + (cols-1)%26)
                        self._ws.update(
                            values=[_order_to_row(order)],
                            range_name=f"A{rn}:{end_col}{rn}",
                            value_input_option="RAW")
                return True
            except Exception as e:
                print(f"[SheetsDB] update failed: {e}"); self._online = False
        return False

    def delete_order(self, order_id):
        self._reconnect_if_needed()
        if self._online:
            try:
                with self._lock:
                    rn = self._find_row_num(order_id)
                    if rn: self._ws.delete_rows(rn)
                return True
            except Exception as e:
                print(f"[SheetsDB] delete failed: {e}"); self._online = False
        return False

# ════════════════════════════════════════════════════════════════════════════
#  LOCAL HELPERS
# ════════════════════════════════════════════════════════════════════════════
def new_id():
    return str(_uuid.uuid4())[:8].upper()

def load_orders_local():
    try:
        with open(STATE_FILE) as f: return json.load(f)
    except: return []

def save_orders_local(orders):
    with open(STATE_FILE, "w") as f: json.dump(orders, f, indent=2)

def days_since_str(dt_str):
    if not dt_str: return 0
    try:
        d = datetime.fromisoformat(dt_str).date()
        return (date.today() - d).days
    except:
        try: return (date.today() - datetime.strptime(dt_str[:10], "%Y-%m-%d").date()).days
        except: return 0

def hours_since_str(dt_str):
    if not dt_str: return 0
    try:
        dt = datetime.fromisoformat(dt_str)
        return int((datetime.now() - dt).total_seconds() // 3600)
    except: return 0

def aging_info(order):
    entered = order.get("entered_datetime", "")
    if not entered: return None
    hrs = hours_since_str(entered)
    days = hrs // 24
    if days >= OVERDUE_DAYS:
        return (f"⏰  OVERDUE — {days}d {hrs%24}h", AGING_OVERDUE_CLR, AGING_OVERDUE_BG)
    elif hrs >= 4:
        return (f"🕐  {days}d {hrs%24}h since entry", AGING_WARN_CLR, AGING_WARN_BG)
    else:
        return (f"🕐  {hrs}h since entry", AGING_OK_CLR, AGING_OK_BG)

def fmt_dt(dt_str):
    if not dt_str: return "—"
    try: return datetime.fromisoformat(dt_str).strftime("%d %b %Y  %H:%M")
    except: return dt_str[:16]

def fmt_date(d_str):
    if not d_str: return "—"
    try: return datetime.strptime(d_str, "%Y-%m-%d").strftime("%d %b %Y")
    except: return d_str

# ════════════════════════════════════════════════════════════════════════════
#  WIDGET HELPERS
# ════════════════════════════════════════════════════════════════════════════
def flat_entry(parent, var, width=None, **kw):
    e = tk.Entry(parent, textvariable=var, font=("Segoe UI", 10),
                 bg="#F7FAFC", fg="#1A2B3C", relief="flat",
                 highlightbackground=SEP_CLR, highlightthickness=1, **kw)
    if width: e.config(width=width)
    return e

def flat_text(parent, height=5, **kw):
    return tk.Text(parent, font=("Segoe UI", 10), bg="#F7FAFC", fg="#1A2B3C",
                   relief="flat", highlightbackground=SEP_CLR, highlightthickness=1,
                   height=height, wrap="word", **kw)

def card_frame(parent, bg=CARD_BG, **kw):
    return tk.Frame(parent, bg=bg, padx=14, pady=10,
                    highlightbackground=SEP_CLR, highlightthickness=1, **kw)

def section_lbl(parent, text, bg=BG):
    tk.Label(parent, text=text, bg=bg, fg=FBC_DARK,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(12, 3))

def make_combo(parent, var, values, **kw):
    c = ttk.Combobox(parent, textvariable=var, values=values,
                     font=("Segoe UI", 10), state="readonly", **kw)
    return c

def scrollable_body(window):
    """Returns (outer_frame, body_frame, canvas) — body is the scrollable content area."""
    outer = tk.Frame(window, bg=BG); outer.pack(fill="both", expand=True)
    canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
    sb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y"); canvas.pack(side="left", fill="both", expand=True)
    body = tk.Frame(canvas, bg=BG, padx=20, pady=6)
    cid = canvas.create_window((0, 0), window=body, anchor="nw")
    body.bind("<Configure>",
              lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>",
                lambda e: canvas.itemconfig(cid, width=e.width))
    canvas.bind_all("<MouseWheel>",
                    lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))
    return outer, body, canvas

# ════════════════════════════════════════════════════════════════════════════
#  SHEETS SETUP DIALOG
# ════════════════════════════════════════════════════════════════════════════
class SheetsSetupDialog(tk.Toplevel):
    def __init__(self, parent, settings, on_save):
        super().__init__(parent)
        self.settings = settings; self.on_save = on_save
        self.title("Google Sheets Setup")
        self.resizable(True, True); self.configure(bg=BG); self.grab_set()
        self._sid = tk.StringVar(value=settings.get("sheet_id", ""))
        self._key = tk.StringVar(value=settings.get("key_file", ""))
        self._build()
        self.update_idletasks()
        w, h = 580, 400
        px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(px,0)}+{max(10,py)}")

    def _build(self):
        tk.Frame(self, bg=FBC_ACCENT, height=4).pack(fill="x")
        hdr = tk.Frame(self, bg=FBC_DARK, pady=10); hdr.pack(fill="x")
        tk.Label(hdr, text="☁  Connect to Google Sheets", bg=FBC_DARK, fg=WHITE,
                 font=("Segoe UI", 12, "bold")).pack(padx=16, anchor="w")
        tk.Label(hdr, text="All dealers must use the same Sheet ID.",
                 bg=FBC_DARK, fg=SIDEBAR_TXT, font=("Segoe UI", 9)).pack(padx=16, anchor="w", pady=(0, 4))
        body = tk.Frame(self, bg=BG, padx=24, pady=16); body.pack(fill="both", expand=True)
        tk.Label(body, text="Google Sheet ID", bg=BG, fg=FBC_DARK,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(body, text="Long code between /d/ and /edit in the Sheet URL",
                 bg=BG, fg="#607080", font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 4))
        flat_entry(body, self._sid).pack(fill="x", ipady=6, pady=(0, 14))
        tk.Label(body, text="Service Account JSON Key File", bg=BG, fg=FBC_DARK,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(body, text=".json file from Google Cloud Console",
                 bg=BG, fg="#607080", font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 4))
        kr = tk.Frame(body, bg=BG); kr.pack(fill="x", pady=(0, 10))
        flat_entry(kr, self._key).pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 6))
        tk.Button(kr, text="📂 Browse", font=("Segoe UI", 9), bg=FBC_MID, fg=WHITE,
                  relief="flat", cursor="hand2", activebackground=FBC_DARK,
                  command=self._browse).pack(side="left")
        self._err = tk.Label(body, text="", bg=BG, fg="#B71C1C", font=("Segoe UI", 9))
        self._err.pack(anchor="w", pady=(0, 6))
        bb = tk.Frame(body, bg=BG); bb.pack(fill="x", pady=(4, 0))
        tk.Button(bb, text="Skip (offline mode)", font=("Segoe UI", 9), bg=BG, fg="#607080",
                  relief="flat", cursor="hand2", activebackground=SEP_CLR,
                  command=self._skip).pack(side="right", padx=(6, 0))
        tk.Button(bb, text="  ✅  Connect & Save  ", font=("Segoe UI", 10, "bold"),
                  bg=FBC_MID, fg=WHITE, relief="flat", cursor="hand2",
                  activebackground=FBC_DARK, command=self._save).pack(side="right")

    def _browse(self):
        p = filedialog.askopenfilename(title="Select JSON key",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if p: self._key.set(p)

    def _save(self):
        sid = self._sid.get().strip(); key = self._key.get().strip()
        if not sid: self._err.config(text="❌  Please enter Sheet ID."); return
        if not key: self._err.config(text="❌  Please select JSON key file."); return
        if not os.path.exists(key):
            self._err.config(text=f"❌  File not found: {key}"); return
        self._err.config(text="⏳  Testing connection…"); self.update()
        ok, err = test_sheets_connection(key, sid)
        if not ok:
            self._err.config(text=f"❌  {err[:100]}")
            messagebox.showerror("Connection Error", err, parent=self); return
        self.settings["sheet_id"] = sid; self.settings["key_file"] = key
        save_settings(self.settings); self.on_save(sid, key); self.destroy()

    def _skip(self): self.on_save("", ""); self.destroy()

# ════════════════════════════════════════════════════════════════════════════
#  LOGIN DIALOG
# ════════════════════════════════════════════════════════════════════════════
class LoginDialog(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FBC Order Manager — Sign In")
        self.resizable(False, False); self.configure(bg=SIDEBAR_BG)
        self.authenticated = False; self.dealer_name = ""
        self._settings = load_settings()
        self._build()
        self.update_idletasks()
        w = 400; sh = self.winfo_screenheight()
        h = min(self.winfo_reqheight() + 20, int(sh * 0.90))
        x = (self.winfo_screenwidth() - w) // 2; y = max(20, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build(self):
        hdr = tk.Frame(self, bg=FBC_MID, pady=20); hdr.pack(fill="x")
        tk.Label(hdr, text="FBC Securities", bg=FBC_DARK, fg=WHITE,
                 font=("Segoe UI", 18, "bold"), padx=16, pady=6).pack()
        tk.Label(hdr, text="Order Management System", bg=FBC_MID, fg=WHITE,
                 font=("Segoe UI", 11)).pack(pady=(2, 0))
        tk.Label(hdr, text=f"v{VERSION}", bg=FBC_MID, fg="#90CAF9",
                 font=("Segoe UI", 8)).pack()

        body = tk.Frame(self, bg=SIDEBAR_BG, padx=36, pady=20)
        body.pack(fill="both", expand=True)

        info = tk.Frame(body, bg="#0D2B4E", padx=14, pady=10,
                        highlightbackground=FBC_MID, highlightthickness=1)
        info.pack(fill="x", pady=(0, 18))
        tk.Label(info,
                 text="Your name is stamped on every order you enter\nand every order you take.",
                 bg="#0D2B4E", fg=SIDEBAR_TXT, font=("Segoe UI", 9), justify="left").pack(anchor="w")

        tk.Label(body, text="Your name", bg=SIDEBAR_BG, fg=SIDEBAR_TXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(body, text="e.g.  Anashe  or  Takudzwa  or  T. Moyo",
                 bg=SIDEBAR_BG, fg="#607080", font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 6))

        saved = self._settings.get("dealer_name", "").strip()
        self._name_var = tk.StringVar(value=saved)
        self._name_entry = tk.Entry(body, textvariable=self._name_var,
                                    font=("Segoe UI", 13),
                                    bg="#0D2B4E", fg=WHITE, insertbackground=WHITE,
                                    relief="flat", highlightbackground=FBC_MID,
                                    highlightthickness=1)
        self._name_entry.pack(fill="x", ipady=9, pady=(0, 4))
        self._name_entry.focus(); self._name_entry.select_range(0, "end")

        self._err = tk.Label(body, text="", bg=SIDEBAR_BG, fg="#FF6B6B", font=("Segoe UI", 9))
        self._err.pack(anchor="w", pady=(4, 0))

        tk.Button(body, text="  Enter System  ", command=self._go,
                  bg=FBC_ACCENT, fg=WHITE, relief="flat", font=("Segoe UI", 11, "bold"),
                  cursor="hand2", pady=11, activebackground=FBC_MID).pack(fill="x", pady=(14, 0))

        self._name_entry.bind("<Return>", lambda _: self._go())

        sid = self._settings.get("sheet_id", "")
        tk.Label(body,
                 text="☁  Cloud sync: configured" if sid else "⚠  Cloud sync: not configured yet",
                 bg=SIDEBAR_BG, fg="#6EE7B7" if sid else "#FFB347",
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(18, 0))

    def _go(self):
        name = self._name_var.get().strip()
        if not name: self._err.config(text="❌  Please enter your name."); return
        if len(name) < 2: self._err.config(text="❌  Name too short."); return
        self.dealer_name = name; self.authenticated = True
        save_settings({**self._settings, "dealer_name": name})
        self.destroy()

    def _close(self): self.authenticated = False; self.destroy()

# ════════════════════════════════════════════════════════════════════════════
#  NEW ORDER DIALOG  — v2: free-text counter, shares/amount toggle, date shown
# ════════════════════════════════════════════════════════════════════════════
class NewOrderDialog(tk.Toplevel):
    def __init__(self, parent, dealer_name, on_saved):
        super().__init__(parent)
        self.dealer_name = dealer_name; self.on_saved = on_saved
        self.title("New Order")
        self.resizable(False, False); self.configure(bg=BG); self.grab_set()
        self._build()
        self.update_idletasks()
        w, h = 660, 740
        px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(px,0)}+{max(py,0)}")
        self._canvas.yview_moveto(0)

    def _build(self):
        tk.Frame(self, bg=FBC_ACCENT, height=4).pack(fill="x")
        hdr = tk.Frame(self, bg=FBC_DARK, pady=10); hdr.pack(fill="x")
        tk.Label(hdr, text="📋  New Order Entry", bg=FBC_DARK, fg=WHITE,
                 font=("Segoe UI", 12, "bold")).pack(padx=16, anchor="w")
        today_str = date.today().strftime("%d %B %Y")
        tk.Label(hdr, text=f"Entered by: {self.dealer_name}   ·   Date: {today_str}",
                 bg=FBC_DARK, fg=SIDEBAR_TXT, font=("Segoe UI", 9)).pack(padx=16, anchor="w", pady=(0, 4))

        _, body, self._canvas = scrollable_body(self)

        # ── ORDER TYPE ────────────────────────────────────────────────────
        section_lbl(body, "ORDER TYPE")
        type_card = card_frame(body); type_card.pack(fill="x")
        self._order_type = tk.StringVar(value="BUY")
        row = tk.Frame(type_card, bg=CARD_BG); row.pack(anchor="w")
        self._buy_btn = tk.Button(row, text="  BUY  ", font=("Segoe UI", 12, "bold"),
                                  bg="#1A6B3A", fg=WHITE, relief="flat", cursor="hand2",
                                  activebackground="#145A32",
                                  command=lambda: self._set_type("BUY"))
        self._buy_btn.pack(side="left", padx=(0, 8), ipady=6, ipadx=4)
        self._sell_btn = tk.Button(row, text="  SELL  ", font=("Segoe UI", 12, "bold"),
                                   bg=BG, fg="#607080", relief="flat", cursor="hand2",
                                   activebackground=SEP_CLR,
                                   command=lambda: self._set_type("SELL"))
        self._sell_btn.pack(side="left", ipady=6, ipadx=4)
        self._type_hint = tk.Label(type_card, text="✅  BUY order selected",
                                   bg=CARD_BG, fg="#1A6B3A", font=("Segoe UI", 9))
        self._type_hint.pack(anchor="w", pady=(8, 0))

        # ── EXCHANGE ──────────────────────────────────────────────────────
        section_lbl(body, "EXCHANGE")
        exc_card = card_frame(body); exc_card.pack(fill="x")
        self._exchange = tk.StringVar(value="ZSE")
        er = tk.Frame(exc_card, bg=CARD_BG); er.pack(anchor="w")
        for val, txt in [("ZSE", "ZSE  (ZiG)"), ("VFEX", "VFEX  (USD)")]:
            tk.Radiobutton(er, text=txt, variable=self._exchange, value=val,
                           bg=CARD_BG, fg=FBC_DARK, selectcolor=CARD_BG,
                           font=("Segoe UI", 10), cursor="hand2",
                           activebackground=CARD_BG).pack(side="left", padx=(0, 20))

        # ── CLIENT DETAILS ────────────────────────────────────────────────
        section_lbl(body, "CLIENT DETAILS")
        cl_card = card_frame(body); cl_card.pack(fill="x")
        self._client_name     = tk.StringVar()
        self._client_address  = tk.StringVar()
        self._csd_no          = tk.StringVar()
        self._tel_no          = tk.StringVar()
        self._custodian       = tk.StringVar(value="FBC")
        self._instruction_by  = tk.StringVar(value="CLIENT")

        for lbl_txt, var in [
            ("Client name *",  self._client_name),
            ("Client address", self._client_address),
            ("CSD number *",   self._csd_no),
            ("Tel no.",        self._tel_no),
        ]:
            r = tk.Frame(cl_card, bg=CARD_BG); r.pack(fill="x", pady=3)
            tk.Label(r, text=lbl_txt, bg=CARD_BG, fg="#607080",
                     font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
            flat_entry(r, var).pack(side="left", fill="x", expand=True, ipady=5, padx=(4, 0))

        r = tk.Frame(cl_card, bg=CARD_BG); r.pack(fill="x", pady=3)
        tk.Label(r, text="Custodian", bg=CARD_BG, fg="#607080",
                 font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
        make_combo(r, self._custodian, CUSTODIANS).pack(side="left", ipady=3, padx=(4, 0))

        r = tk.Frame(cl_card, bg=CARD_BG); r.pack(fill="x", pady=3)
        tk.Label(r, text="Instruction by", bg=CARD_BG, fg="#607080",
                 font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
        make_combo(r, self._instruction_by,
                   ["CLIENT", "BROKER", "FUND MANAGER", "OTHER"]).pack(side="left", ipady=3, padx=(4, 0))

        # ── ORDER DETAILS ─────────────────────────────────────────────────
        section_lbl(body, "ORDER DETAILS")
        od_card = card_frame(body); od_card.pack(fill="x")

        # Counter — free text
        r = tk.Frame(od_card, bg=CARD_BG); r.pack(fill="x", pady=3)
        tk.Label(r, text="Counter *", bg=CARD_BG, fg="#607080",
                 font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
        self._counter = tk.StringVar()
        flat_entry(r, self._counter, width=24).pack(side="left", ipady=5, padx=(4, 0))
        tk.Label(r, text="e.g. BAT, PADENGA, ECONET",
                 bg=CARD_BG, fg="#A0B0C0", font=("Segoe UI", 8)).pack(side="left", padx=(8, 0))

        # Limit price — no hint
        r = tk.Frame(od_card, bg=CARD_BG); r.pack(fill="x", pady=3)
        tk.Label(r, text="Limit price *", bg=CARD_BG, fg="#607080",
                 font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
        self._limit_price = tk.StringVar()
        flat_entry(r, self._limit_price, width=14).pack(side="left", ipady=5, padx=(4, 0))

        # Shares vs Amount toggle
        tk.Frame(od_card, bg=SEP_CLR, height=1).pack(fill="x", pady=(10, 6))
        tk.Label(od_card, text="Quantity — choose one method:",
                 bg=CARD_BG, fg=FBC_DARK, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))

        self._qty_mode = tk.StringVar(value="SHARES")
        mode_row = tk.Frame(od_card, bg=CARD_BG); mode_row.pack(anchor="w", pady=(0, 8))
        tk.Radiobutton(mode_row, text="Enter number of shares",
                       variable=self._qty_mode, value="SHARES",
                       command=self._on_qty_mode,
                       bg=CARD_BG, fg=FBC_DARK, selectcolor=CARD_BG,
                       font=("Segoe UI", 10), cursor="hand2",
                       activebackground=CARD_BG).pack(side="left", padx=(0, 20))
        tk.Radiobutton(mode_row, text="Enter total amount",
                       variable=self._qty_mode, value="AMOUNT",
                       command=self._on_qty_mode,
                       bg=CARD_BG, fg=FBC_DARK, selectcolor=CARD_BG,
                       font=("Segoe UI", 10), cursor="hand2",
                       activebackground=CARD_BG).pack(side="left")

        # Shares entry row
        self._shares_row = tk.Frame(od_card, bg=CARD_BG); self._shares_row.pack(fill="x", pady=2)
        tk.Label(self._shares_row, text="No. of shares *", bg=CARD_BG, fg="#607080",
                 font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
        self._num_shares = tk.StringVar()
        flat_entry(self._shares_row, self._num_shares, width=14).pack(side="left", ipady=5, padx=(4, 0))

        # Amount entry row (hidden initially)
        self._amount_row = tk.Frame(od_card, bg=CARD_BG)
        tk.Label(self._amount_row, text="Total amount *", bg=CARD_BG, fg="#607080",
                 font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
        self._total_amount = tk.StringVar()
        flat_entry(self._amount_row, self._total_amount, width=14).pack(side="left", ipady=5, padx=(4, 0))
        self._currency_lbl = tk.Label(self._amount_row, text="ZiG",
                                      bg=CARD_BG, fg="#607080", font=("Segoe UI", 9))
        self._currency_lbl.pack(side="left", padx=(6, 0))

        # Exchange drives currency label
        self._exchange.trace_add("write", lambda *_: self._currency_lbl.config(
            text="ZiG" if self._exchange.get() == "ZSE" else "USD"))

        # ── NOTES ─────────────────────────────────────────────────────────
        section_lbl(body, "NOTES (optional)")
        nc = card_frame(body); nc.pack(fill="x")
        self._notes = flat_text(nc, height=3); self._notes.pack(fill="x")

        tk.Frame(body, bg=BG, height=10).pack()

        # ── BUTTONS ───────────────────────────────────────────────────────
        btn_bar = tk.Frame(self, bg=BG, padx=20, pady=10); btn_bar.pack(fill="x")
        tk.Button(btn_bar, text="Cancel", font=("Segoe UI", 10), bg=BG, fg="#607080",
                  relief="flat", cursor="hand2", command=self._close,
                  activebackground=SEP_CLR).pack(side="right", padx=(6, 0))
        tk.Button(btn_bar, text="  📋  Post Order  ", font=("Segoe UI", 10, "bold"),
                  bg=FBC_MID, fg=WHITE, relief="flat", cursor="hand2",
                  activebackground=FBC_DARK, command=self._save).pack(side="right")

    def _close(self):
        try: self._canvas.unbind_all("<MouseWheel>")
        except: pass
        self.destroy()

    def _set_type(self, t):
        self._order_type.set(t)
        if t == "BUY":
            self._buy_btn.config(bg="#1A6B3A", fg=WHITE)
            self._sell_btn.config(bg=BG, fg="#607080")
            self._type_hint.config(text="✅  BUY order selected", fg="#1A6B3A")
        else:
            self._sell_btn.config(bg="#B71C1C", fg=WHITE)
            self._buy_btn.config(bg=BG, fg="#607080")
            self._type_hint.config(text="🔴  SELL order selected", fg="#B71C1C")

    def _on_qty_mode(self):
        if self._qty_mode.get() == "SHARES":
            self._amount_row.pack_forget()
            self._shares_row.pack(fill="x", pady=2)
        else:
            self._shares_row.pack_forget()
            self._amount_row.pack(fill="x", pady=2)

    def _save(self):
        client  = self._client_name.get().strip()
        csd     = self._csd_no.get().strip()
        counter = self._counter.get().strip()
        limit   = self._limit_price.get().strip()
        mode    = self._qty_mode.get()

        if not client:
            messagebox.showwarning("Missing", "Please enter the client name.", parent=self); return
        if not csd:
            messagebox.showwarning("Missing", "Please enter the CSD number.", parent=self); return
        if not counter:
            messagebox.showwarning("Missing", "Please enter a counter (e.g. BAT).", parent=self); return
        if not limit:
            messagebox.showwarning("Missing", "Please enter the limit price.", parent=self); return

        shares = 0; total_amount = ""
        if mode == "SHARES":
            raw = self._num_shares.get().strip()
            if not raw:
                messagebox.showwarning("Missing", "Please enter number of shares.", parent=self); return
            try: shares = int(raw.replace(",", ""))
            except:
                messagebox.showwarning("Invalid", "Number of shares must be a whole number.", parent=self); return
            if shares <= 0:
                messagebox.showwarning("Invalid", "Shares must be greater than zero.", parent=self); return
        else:
            raw = self._total_amount.get().strip()
            if not raw:
                messagebox.showwarning("Missing", "Please enter the total amount.", parent=self); return
            try: float(raw.replace(",", ""))
            except:
                messagebox.showwarning("Invalid", "Total amount must be a number.", parent=self); return
            total_amount = raw
            shares = 0  # will be determined at execution

        now = datetime.now()
        order = {
            "id":                new_id(),
            "order_type":        self._order_type.get(),
            "client_name":       client,
            "client_address":    self._client_address.get().strip(),
            "csd_no":            csd,
            "custodian":         self._custodian.get(),
            "instruction_by":    self._instruction_by.get(),
            "num_shares":        shares,
            "counter":           counter.upper(),
            "limit_price":       limit,
            "exchange":          self._exchange.get(),
            "entered_by":        self.dealer_name,
            "entered_datetime":  now.isoformat(),
            "order_date":        date.today().isoformat(),
            "status":            "PENDING",
            "taken_by":          "",
            "taken_datetime":    "",
            "executed_by":       "",
            "executed_datetime": "",
            "shares_executed":   0,
            "execution_price":   "",
            "cancel_reason":     "",
            "notes":             self._notes.get("1.0", "end").strip(),
            "partial_of":        "",
            "amount_mode":       mode,
            "total_amount":      total_amount,
        }
        try: self._canvas.unbind_all("<MouseWheel>")
        except: pass
        self.on_saved(order)
        self.destroy()

# ════════════════════════════════════════════════════════════════════════════
#  EXECUTE ORDER DIALOG  — v2: amount mode awareness, remainder stays TAKEN
# ════════════════════════════════════════════════════════════════════════════
class ExecuteOrderDialog(tk.Toplevel):
    def __init__(self, parent, order, dealer_name, on_executed):
        super().__init__(parent)
        self.order = order; self.dealer_name = dealer_name; self.on_executed = on_executed
        self.title("Execute Order")
        self.resizable(False, False); self.configure(bg=BG); self.grab_set()
        self._build()
        self.update_idletasks()
        w, h = 520, 540
        px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(px,0)}+{max(py,0)}")

    def _build(self):
        ot = self.order["order_type"]
        colour = "#1A6B3A" if ot == "BUY" else "#B71C1C"
        tk.Frame(self, bg=colour, height=4).pack(fill="x")
        hdr = tk.Frame(self, bg=FBC_DARK, pady=10); hdr.pack(fill="x")
        tk.Label(hdr, text=f"✅  Execute {ot} Order — {self.order['counter']}",
                 bg=FBC_DARK, fg=WHITE, font=("Segoe UI", 11, "bold")).pack(padx=16, anchor="w")
        tk.Label(hdr, text=f"Client: {self.order['client_name']}  ·  CSD: {self.order['csd_no']}",
                 bg=FBC_DARK, fg=SIDEBAR_TXT, font=("Segoe UI", 9)).pack(padx=16, anchor="w", pady=(0, 4))

        body = tk.Frame(self, bg=BG, padx=24, pady=16); body.pack(fill="both", expand=True)

        # Summary strip
        summ = tk.Frame(body, bg="#EAF4FB", padx=12, pady=10,
                        highlightbackground="#90CAF9", highlightthickness=1)
        summ.pack(fill="x", pady=(0, 16))
        mode = self.order.get("amount_mode", "SHARES")
        if mode == "AMOUNT":
            qty_txt = f"Total amount: {self.order.get('total_amount', '?')}  {self.order['exchange']}"
        else:
            qty_txt = f"{self.order['num_shares']:,} shares"
        tk.Label(summ,
                 text=f"{ot}  {qty_txt}  {self.order['counter']}  [{self.order['exchange']}]",
                 bg="#EAF4FB", fg=FBC_DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(summ,
                 text=f"Limit: {self.order.get('limit_price','?')}   ·   Date: {fmt_date(self.order.get('order_date',''))}",
                 bg="#EAF4FB", fg="#607080", font=("Segoe UI", 9)).pack(anchor="w")

        # Full or partial
        tk.Label(body, text="Execution type", bg=BG, fg=FBC_DARK,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self._exec_type = tk.StringVar(value="FULL")
        er = tk.Frame(body, bg=BG); er.pack(anchor="w", pady=(4, 12))
        tk.Radiobutton(er, text="Full fill", variable=self._exec_type, value="FULL",
                       command=self._on_type, bg=BG, fg=FBC_DARK, selectcolor=BG,
                       font=("Segoe UI", 10), cursor="hand2",
                       activebackground=BG).pack(side="left", padx=(0, 20))
        tk.Radiobutton(er, text="Partial fill", variable=self._exec_type, value="PARTIAL",
                       command=self._on_type, bg=BG, fg=FBC_DARK, selectcolor=BG,
                       font=("Segoe UI", 10), cursor="hand2",
                       activebackground=BG).pack(side="left")

        # Shares executed
        r = tk.Frame(body, bg=BG); r.pack(fill="x", pady=(0, 8))
        tk.Label(r, text="Shares executed *", bg=BG, fg="#607080",
                 font=("Segoe UI", 9), width=20, anchor="w").pack(side="left")
        self._shares_exec = tk.StringVar(
            value=str(self.order["num_shares"]) if self.order["num_shares"] > 0 else "")
        self._shares_entry = flat_entry(r, self._shares_exec, width=14)
        self._shares_entry.pack(side="left", ipady=5, padx=(4, 0))

        # Execution price
        r = tk.Frame(body, bg=BG); r.pack(fill="x", pady=(0, 8))
        tk.Label(r, text="Execution price *", bg=BG, fg="#607080",
                 font=("Segoe UI", 9), width=20, anchor="w").pack(side="left")
        self._exec_price = tk.StringVar(value=self.order.get("limit_price", ""))
        flat_entry(r, self._exec_price, width=14).pack(side="left", ipady=5, padx=(4, 0))
        tk.Label(r, text=f"{'ZiG' if self.order['exchange'] == 'ZSE' else 'USD'} per share",
                 bg=BG, fg="#A0B0C0", font=("Segoe UI", 8)).pack(side="left", padx=(8, 0))

        # Notes
        tk.Label(body, text="Execution notes (optional)", bg=BG, fg="#607080",
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(8, 4))
        self._exec_notes = flat_text(body, height=3)
        self._exec_notes.pack(fill="x")

        self._err = tk.Label(body, text="", bg=BG, fg="#B71C1C", font=("Segoe UI", 9))
        self._err.pack(anchor="w", pady=(6, 0))

        btn_bar = tk.Frame(self, bg=BG, padx=20, pady=10); btn_bar.pack(fill="x")
        tk.Button(btn_bar, text="Cancel", font=("Segoe UI", 10), bg=BG, fg="#607080",
                  relief="flat", cursor="hand2", command=self.destroy,
                  activebackground=SEP_CLR).pack(side="right", padx=(6, 0))
        tk.Button(btn_bar, text="  ✅  Confirm Execution  ", font=("Segoe UI", 10, "bold"),
                  bg="#1A6B3A", fg=WHITE, relief="flat", cursor="hand2",
                  activebackground="#145A32", command=self._execute).pack(side="right")

    def _on_type(self):
        t = self._exec_type.get()
        if t == "FULL":
            if self.order["num_shares"] > 0:
                self._shares_exec.set(str(self.order["num_shares"]))
                self._shares_entry.config(state="disabled")
            else:
                self._shares_entry.config(state="normal")
        else:
            self._shares_entry.config(state="normal")
            self._shares_exec.set("")
            self._shares_entry.focus()

    def _execute(self):
        shares_raw = self._shares_exec.get().strip()
        price = self._exec_price.get().strip()
        if not shares_raw:
            self._err.config(text="❌  Enter shares executed."); return
        try: se = int(shares_raw.replace(",", ""))
        except:
            self._err.config(text="❌  Shares must be a whole number."); return
        if se <= 0:
            self._err.config(text="❌  Shares must be greater than zero."); return
        if self.order["num_shares"] > 0 and se > self.order["num_shares"]:
            self._err.config(
                text=f"❌  Cannot exceed ordered quantity ({self.order['num_shares']:,})."); return
        if not price:
            self._err.config(text="❌  Enter execution price."); return

        is_partial = (self._exec_type.get() == "PARTIAL")
        notes_extra = self._exec_notes.get("1.0", "end").strip()
        now = datetime.now().isoformat()

        self.order["executed_by"]       = self.dealer_name
        self.order["executed_datetime"] = now
        self.order["shares_executed"]   = se
        self.order["execution_price"]   = price
        self.order["status"]            = "PARTIAL" if is_partial else "EXECUTED"
        if notes_extra:
            existing = self.order.get("notes", "")
            self.order["notes"] = (existing + "\n" + notes_extra).strip()
        self.on_executed(self.order, is_partial)
        self.destroy()

# ════════════════════════════════════════════════════════════════════════════
#  CANCEL ORDER DIALOG
# ════════════════════════════════════════════════════════════════════════════
class CancelOrderDialog(tk.Toplevel):
    def __init__(self, parent, order, dealer_name, on_cancelled):
        super().__init__(parent)
        self.order = order; self.dealer_name = dealer_name; self.on_cancelled = on_cancelled
        self.title("Cancel Order")
        self.resizable(False, False); self.configure(bg=BG); self.grab_set()
        self._build()
        self.update_idletasks()
        w, h = 460, 380
        px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(px,0)}+{max(py,0)}")

    def _build(self):
        tk.Frame(self, bg="#B71C1C", height=4).pack(fill="x")
        hdr = tk.Frame(self, bg=FBC_DARK, pady=10); hdr.pack(fill="x")
        tk.Label(hdr, text=f"🚫  Cancel Order — {self.order['counter']}",
                 bg=FBC_DARK, fg=WHITE, font=("Segoe UI", 11, "bold")).pack(padx=16, anchor="w")
        shares_txt = (f"{self.order['num_shares']:,} shares" if self.order["num_shares"] > 0
                      else f"Amount: {self.order.get('total_amount','?')}")
        tk.Label(hdr,
                 text=f"{self.order['order_type']}  {shares_txt}  ·  {self.order['client_name']}",
                 bg=FBC_DARK, fg=SIDEBAR_TXT, font=("Segoe UI", 9)).pack(padx=16, anchor="w", pady=(0, 4))

        body = tk.Frame(self, bg=BG, padx=24, pady=16); body.pack(fill="both", expand=True)
        warn = tk.Frame(body, bg="#FFF0F0", padx=12, pady=10,
                        highlightbackground="#FFCDD2", highlightthickness=1)
        warn.pack(fill="x", pady=(0, 16))
        tk.Label(warn,
                 text="⚠  This will permanently cancel the order.\nReason is recorded in the audit trail.",
                 bg="#FFF0F0", fg="#B71C1C", font=("Segoe UI", 9), justify="left").pack(anchor="w")

        tk.Label(body, text="Cancellation reason *", bg=BG, fg=FBC_DARK,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")

        quick_frame = tk.Frame(body, bg=BG); quick_frame.pack(fill="x", pady=(6, 8))
        self._reason_var = tk.StringVar()
        for reason in ["Client withdrew instruction", "Limit not reached", "Duplicate order", "Other"]:
            tk.Button(quick_frame, text=reason, font=("Segoe UI", 8), bg=BG, fg=FBC_MID,
                      relief="flat", cursor="hand2", activebackground=SEP_CLR,
                      command=lambda r=reason: self._set_reason(r)).pack(side="left", padx=(0, 6))

        self._reason_txt = flat_text(body, height=4); self._reason_txt.pack(fill="x")
        self._err = tk.Label(body, text="", bg=BG, fg="#B71C1C", font=("Segoe UI", 9))
        self._err.pack(anchor="w", pady=(4, 0))

        btn_bar = tk.Frame(self, bg=BG, padx=20, pady=10); btn_bar.pack(fill="x")
        tk.Button(btn_bar, text="Back", font=("Segoe UI", 10), bg=BG, fg="#607080",
                  relief="flat", cursor="hand2", command=self.destroy,
                  activebackground=SEP_CLR).pack(side="right", padx=(6, 0))
        tk.Button(btn_bar, text="  🚫  Confirm Cancel  ", font=("Segoe UI", 10, "bold"),
                  bg="#B71C1C", fg=WHITE, relief="flat", cursor="hand2",
                  activebackground="#8B0000", command=self._cancel).pack(side="right")

    def _set_reason(self, r):
        self._reason_txt.delete("1.0", "end")
        self._reason_txt.insert("1.0", r)

    def _cancel(self):
        reason = self._reason_txt.get("1.0", "end").strip()
        if not reason:
            self._err.config(text="❌  Please provide a cancellation reason."); return
        self.order["status"]        = "CANCELLED"
        self.order["cancel_reason"] = reason
        self.on_cancelled(self.order)
        self.destroy()

# ════════════════════════════════════════════════════════════════════════════
#  ORDER DETAIL DIALOG  — v2: scrollable, all fields always visible
# ════════════════════════════════════════════════════════════════════════════
class OrderDetailDialog(tk.Toplevel):
    def __init__(self, parent, order):
        super().__init__(parent)
        self.order = order
        self.title(f"Order Detail — {order['id']}")
        self.resizable(True, True); self.configure(bg=BG); self.grab_set()
        self._build()
        self.update_idletasks()
        w, h = 540, 640
        px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(px,0)}+{max(py,0)}")

    def _build(self):
        ot  = self.order["order_type"]
        col = "#1A6B3A" if ot == "BUY" else "#B71C1C"
        tk.Frame(self, bg=col, height=4).pack(fill="x")
        hdr = tk.Frame(self, bg=FBC_DARK, pady=10); hdr.pack(fill="x")
        tk.Label(hdr, text=f"📋  Order {self.order['id']}  —  {ot}  {self.order['counter']}",
                 bg=FBC_DARK, fg=WHITE, font=("Segoe UI", 12, "bold")).pack(padx=16, anchor="w")
        tk.Label(hdr, text=f"Date: {fmt_date(self.order.get('order_date',''))}   ·   Entered: {fmt_dt(self.order.get('entered_datetime',''))}",
                 bg=FBC_DARK, fg=SIDEBAR_TXT, font=("Segoe UI", 9)).pack(padx=16, anchor="w", pady=(0, 4))

        # Scrollable body
        _, body, _ = scrollable_body(self)

        def divider():
            tk.Frame(body, bg=SEP_CLR, height=1).pack(fill="x", pady=8)

        def detail_row(label, value, bold=False):
            r = tk.Frame(body, bg=BG); r.pack(fill="x", pady=2)
            tk.Label(r, text=label, bg=BG, fg="#607080",
                     font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
            display = str(value) if value else "—"
            tk.Label(r, text=display, bg=BG, fg=FBC_DARK,
                     font=("Segoe UI", 9, "bold" if bold else "normal"),
                     anchor="w", wraplength=280, justify="left").pack(side="left", fill="x", expand=True)

        o = self.order
        mode = o.get("amount_mode", "SHARES")

        # ── Section: Order ─────────────────────────────────────────────────
        tk.Label(body, text="ORDER", bg=BG, fg=FBC_MID,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(8, 4))
        detail_row("Order ID",         o["id"],          bold=True)
        detail_row("Type",             o["order_type"],   bold=True)
        detail_row("Exchange",         o["exchange"])
        detail_row("Counter",          o["counter"],      bold=True)
        detail_row("Order date",       fmt_date(o.get("order_date", "")))
        if mode == "AMOUNT":
            detail_row("Total amount", f"{o.get('total_amount','?')}  {o['exchange']}")
            detail_row("Shares ordered", f"{o['num_shares']:,}" if o['num_shares'] > 0 else "TBD at execution")
        else:
            detail_row("Shares ordered", f"{o['num_shares']:,}")
        detail_row("Limit price",      o["limit_price"])

        divider()

        # ── Section: Client ────────────────────────────────────────────────
        tk.Label(body, text="CLIENT", bg=BG, fg=FBC_MID,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 4))
        detail_row("Client name",      o["client_name"],  bold=True)
        detail_row("Client address",   o["client_address"])
        detail_row("CSD number",       o["csd_no"])
        detail_row("Custodian",        o["custodian"])
        detail_row("Instruction by",   o["instruction_by"])

        divider()

        # ── Section: Workflow ──────────────────────────────────────────────
        tk.Label(body, text="WORKFLOW", bg=BG, fg=FBC_MID,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 4))
        detail_row("Entered by",       o["entered_by"])
        detail_row("Entered at",       fmt_dt(o["entered_datetime"]))
        detail_row("Status",           o["status"],       bold=True)
        detail_row("Taken by",         o["taken_by"])
        detail_row("Taken at",         fmt_dt(o["taken_datetime"]))
        detail_row("Executed by",      o["executed_by"])
        detail_row("Executed at",      fmt_dt(o["executed_datetime"]))
        detail_row("Shares executed",
                   f"{o['shares_executed']:,}" if o.get("shares_executed", 0) > 0 else "—")
        detail_row("Execution price",  o["execution_price"])

        if o.get("cancel_reason"):
            divider()
            tk.Label(body, text="CANCELLATION", bg=BG, fg="#B71C1C",
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 4))
            detail_row("Cancel reason",  o["cancel_reason"])

        if o.get("partial_of"):
            divider()
            detail_row("Remainder of",   f"#{o['partial_of']}")

        if o.get("notes"):
            divider()
            tk.Label(body, text="NOTES", bg=BG, fg=FBC_MID,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 4))
            tk.Label(body, text=o["notes"], bg=BG, fg=FBC_DARK,
                     font=("Segoe UI", 9), wraplength=460, justify="left").pack(anchor="w")

        tk.Frame(body, bg=BG, height=12).pack()

        # Close button inside the scrollable area so it's always reachable
        tk.Button(body, text="  Close  ", font=("Segoe UI", 10), bg=FBC_MID, fg=WHITE,
                  relief="flat", cursor="hand2", activebackground=FBC_DARK,
                  command=self.destroy, pady=6).pack(pady=(0, 12))

# ════════════════════════════════════════════════════════════════════════════
#  MAIN APP
# ════════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self, dealer_name, settings):
        super().__init__()
        self.dealer_name = dealer_name; self.settings = settings
        self.title(f"FBC Order Manager  v{VERSION}  —  {dealer_name}")
        self.state("zoomed"); self.configure(bg=BG)
        sid = settings.get("sheet_id", ""); key = settings.get("key_file", "")
        self.db = SheetsDB(key, sid) if (sid and key and os.path.exists(key)) else None
        self.orders = []; self._filter = "all"
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refresh())
        self._build()
        self._full_sync()
        self._schedule_auto_sync()

    def _build(self):
        # ── TOP BAR ───────────────────────────────────────────────────────
        top = tk.Frame(self, bg=FBC_DARK); top.pack(fill="x")
        tk.Frame(top, bg=FBC_ACCENT, width=6).pack(side="left", fill="y")
        tk.Label(top, text="📈  FBC Securities — Order Manager", bg=FBC_DARK, fg=WHITE,
                 font=("Segoe UI", 13, "bold"), pady=14, padx=16).pack(side="left")
        self._sync_lbl = tk.Label(top, text="", bg=FBC_DARK, font=("Segoe UI", 9))
        self._sync_lbl.pack(side="left", padx=10)

        tk.Button(top, text="  📋  New Order  ", font=("Segoe UI", 10, "bold"),
                  bg=FBC_ACCENT, fg=WHITE, relief="flat", cursor="hand2",
                  activebackground=FBC_MID, pady=8,
                  command=self._open_new_order).pack(side="right", padx=12, pady=6)
        tk.Button(top, text="☁  Sheets", font=("Segoe UI", 9), bg=FBC_DARK, fg=SIDEBAR_TXT,
                  relief="flat", cursor="hand2", activebackground=FBC_MID,
                  command=self._open_sheets_setup).pack(side="right", padx=4, pady=6)
        tk.Label(top, text=f"👤  {self.dealer_name}", bg=FBC_DARK, fg=SIDEBAR_TXT,
                 font=("Segoe UI", 9)).pack(side="right", padx=8)
        tk.Label(top, text=f"v{VERSION}", bg=FBC_DARK, fg="#2A5A8A",
                 font=("Segoe UI", 9)).pack(side="right", padx=6)

        # ── METRICS ───────────────────────────────────────────────────────
        metric_bg = tk.Frame(self, bg=SIDEBAR_BG, pady=10); metric_bg.pack(fill="x")
        mr = tk.Frame(metric_bg, bg=SIDEBAR_BG); mr.pack(padx=20)

        def mcard(label, colour):
            f = tk.Frame(mr, bg="#002855", padx=16, pady=10,
                         highlightbackground="#0A3A6A", highlightthickness=1)
            f.pack(side="left", padx=(0, 10))
            tk.Label(f, text=label, bg="#002855", fg=SIDEBAR_TXT,
                     font=("Segoe UI", 8)).pack(anchor="w")
            v = tk.Label(f, text="0", bg="#002855", fg=colour,
                         font=("Segoe UI", 20, "bold"))
            v.pack(anchor="w"); return v

        self._m_total     = mcard("Total orders",        FBC_ACCENT)
        self._m_pending   = mcard("Pending",             "#FBC02D")
        self._m_taken     = mcard("In progress",         "#00A3E0")
        self._m_executed  = mcard("Executed today",      "#4CAF50")
        self._m_partial   = mcard("Partial fills",       "#A855F7")
        self._m_overdue   = mcard(f"Overdue (>{OVERDUE_DAYS}d)", "#FF4444")
        self._m_cancelled = mcard("Cancelled",           "#9E9E9E")

        # ── SEARCH + TABS ─────────────────────────────────────────────────
        ctrl_row = tk.Frame(self, bg=BG, padx=20, pady=8); ctrl_row.pack(fill="x")

        search_frame = tk.Frame(ctrl_row, bg=BG); search_frame.pack(side="left", padx=(0, 16))
        tk.Label(search_frame, text="🔍", bg=BG, font=("Segoe UI", 10)).pack(side="left")
        se = flat_entry(search_frame, self._search_var, width=22)
        se.pack(side="left", ipady=4, padx=(4, 0))
        tk.Label(search_frame, text="Search client / counter / CSD",
                 bg=BG, fg="#A0B0C0", font=("Segoe UI", 8)).pack(side="left", padx=(6, 0))

        self._tabs = {}
        for key, label in [
            ("all", "All"), ("pending", "Pending"), ("taken", "In Progress"),
            ("executed", "Executed"), ("partial", "Partial"),
            ("overdue", "Overdue"), ("cancelled", "Cancelled")
        ]:
            b = tk.Button(ctrl_row, text=label, font=("Segoe UI", 9), relief="flat",
                          cursor="hand2", padx=10, pady=5,
                          command=lambda k=key: self._set_filter(k))
            b.pack(side="left", padx=(0, 3)); self._tabs[key] = b
        self._paint_tabs()

        tk.Frame(self, bg=SEP_CLR, height=1).pack(fill="x", padx=20)

        # ── ORDER LIST ────────────────────────────────────────────────────
        lo = tk.Frame(self, bg=BG); lo.pack(fill="both", expand=True, padx=20, pady=10)
        self._canvas = tk.Canvas(lo, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(lo, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); self._canvas.pack(side="left", fill="both", expand=True)
        self._inner = tk.Frame(self._canvas, bg=BG)
        self._inner_id = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._inner.bind("<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
            lambda e: self._canvas.itemconfig(self._inner_id, width=e.width))
        self._canvas.bind_all("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-1*(e.delta//120), "units"))

    def _paint_tabs(self):
        for k, b in self._tabs.items():
            if k == self._filter: b.config(bg=FBC_DARK, fg=WHITE)
            else: b.config(bg=BG, fg="#607080",
                           activebackground=SEP_CLR, activeforeground=FBC_DARK)

    def _set_filter(self, key):
        self._filter = key; self._paint_tabs(); self._refresh()

    def _update_sync_badge(self):
        if self.db and self.db.online:
            self._sync_lbl.config(text="☁  Live", fg="#6EE7B7")
        elif self.db:
            self._sync_lbl.config(text="⚠  Offline (local cache)", fg="#FFB347")
        else:
            self._sync_lbl.config(text="⚠  No sync configured", fg="#607080")

    def _full_sync(self):
        def _do():
            orders = self.db.read_all() if self.db else load_orders_local()
            self.after(0, lambda: self._apply_orders(orders))
        threading.Thread(target=_do, daemon=True).start()

    def _apply_orders(self, orders):
        self.orders = orders; self._update_sync_badge(); self._refresh()

    def _schedule_auto_sync(self):
        self._full_sync()
        self.after(20_000, self._schedule_auto_sync)

    def _refresh(self):
        orders = self.orders
        search = self._search_var.get().strip().lower()
        today  = date.today().isoformat()

        pending    = [o for o in orders if o["status"] == "PENDING"]
        taken      = [o for o in orders if o["status"] == "TAKEN"]
        executed   = [o for o in orders if o["status"] == "EXECUTED"]
        partial    = [o for o in orders if o["status"] == "PARTIAL"]
        cancelled  = [o for o in orders if o["status"] == "CANCELLED"]
        exec_today = [o for o in executed if o.get("executed_datetime", "")[:10] == today]
        overdue    = [o for o in pending + taken
                      if days_since_str(o.get("entered_datetime", "")) >= OVERDUE_DAYS]

        self._m_total.config(    text=str(len(orders)))
        self._m_pending.config(  text=str(len(pending)))
        self._m_taken.config(    text=str(len(taken)))
        self._m_executed.config( text=str(len(exec_today)))
        self._m_partial.config(  text=str(len(partial)))
        self._m_overdue.config(  text=str(len(overdue)))
        self._m_cancelled.config(text=str(len(cancelled)))

        if   self._filter == "pending":   visible = pending
        elif self._filter == "taken":     visible = taken
        elif self._filter == "executed":  visible = executed
        elif self._filter == "partial":   visible = partial
        elif self._filter == "overdue":   visible = overdue
        elif self._filter == "cancelled": visible = cancelled
        else:                             visible = orders

        if search:
            visible = [o for o in visible if
                       search in o.get("client_name",  "").lower() or
                       search in o.get("counter",      "").lower() or
                       search in o.get("csd_no",       "").lower() or
                       search in o.get("entered_by",   "").lower() or
                       search in o.get("id",           "").lower()]

        def sort_key(o):
            p = {"PENDING": 0, "TAKEN": 1, "PARTIAL": 2, "EXECUTED": 3, "CANCELLED": 4}
            return (p.get(o["status"], 5), o.get("entered_datetime", ""))
        visible = sorted(visible, key=sort_key)

        for w in self._inner.winfo_children(): w.destroy()
        if not visible:
            msg = ("No orders yet. Click '📋 New Order' to post the first order."
                   if self._filter == "all" else "No orders in this category.")
            tk.Label(self._inner, text=msg, bg=BG, fg="#8096B0",
                     font=("Segoe UI", 11), pady=40).pack()
            return
        for o in visible:
            self._order_card(self._inner, o)

    def _order_card(self, parent, o):
        status     = o["status"]
        is_overdue = (status in ("PENDING", "TAKEN") and
                      days_since_str(o.get("entered_datetime", "")) >= OVERDUE_DAYS)

        if is_overdue:
            cbg, cborder = "#FFF0F0", "#B71C1C"
        elif status == "PENDING":
            cbg, cborder = S_PENDING[0], "#FBC02D"
        elif status == "TAKEN":
            cbg, cborder = S_TAKEN[0], "#00A3E0"
        elif status == "EXECUTED":
            cbg, cborder = S_EXECUTED[0], "#4CAF50"
        elif status == "PARTIAL":
            cbg, cborder = S_PARTIAL[0], "#A855F7"
        else:
            cbg, cborder = S_CANCELLED[0], "#9E9E9E"

        card = tk.Frame(parent, bg=cbg, padx=14, pady=10,
                        highlightbackground=cborder, highlightthickness=1)
        card.pack(fill="x", pady=4)

        # LEFT: BUY / SELL badge
        ot         = o["order_type"]
        badge_col  = "#1A6B3A" if ot == "BUY" else "#B71C1C"
        tk.Label(card, text=ot, bg=badge_col, fg=WHITE,
                 font=("Segoe UI", 10, "bold"), padx=8, pady=12, width=5
                 ).pack(side="left", padx=(0, 12))

        # MIDDLE: info block
        info = tk.Frame(card, bg=cbg); info.pack(side="left", fill="x", expand=True)

        # Line 1 — counter · qty · exchange · ID
        mode = o.get("amount_mode", "SHARES")
        if mode == "AMOUNT" and not o["num_shares"]:
            qty_txt = f"Amount: {o.get('total_amount','?')}"
        else:
            qty_txt = f"{o['num_shares']:,} shares"

        tk.Label(info,
                 text=f"{o['counter']}  ·  {qty_txt}  ·  {o['exchange']}  ·  #{o['id']}",
                 bg=cbg, fg=FBC_DARK, font=("Segoe UI", 11, "bold")).pack(anchor="w")

        # Line 2 — client · CSD
        tk.Label(info,
                 text=f"Client: {o['client_name']}   ·   CSD: {o['csd_no']}",
                 bg=cbg, fg="#607080", font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))

        # Line 3 — date · entered by · limit
        order_date = fmt_date(o.get("order_date", "")) if o.get("order_date") else ""
        date_txt   = f"Date: {order_date}   ·   " if order_date else ""
        lp_txt     = f"Limit: {o['limit_price']}" if o.get("limit_price") else ""
        meta_parts = [p for p in [date_txt + f"By: {o['entered_by']}", lp_txt] if p]
        tk.Label(info,
                 text="   ·   ".join(meta_parts),
                 bg=cbg, fg="#607080", font=("Segoe UI", 8)).pack(anchor="w")

        # Status + aging badges
        badge_row = tk.Frame(info, bg=cbg); badge_row.pack(anchor="w", pady=(4, 0))

        if status == "PENDING":
            s_bg, s_fg = S_PENDING[0], S_PENDING[1]
            s_txt = "⏳  PENDING — awaiting dealer"
        elif status == "TAKEN":
            s_bg, s_fg = S_TAKEN[0], S_TAKEN[1]
            s_txt = f"🔵  IN PROGRESS — {o.get('taken_by','?')}  ·  {fmt_dt(o.get('taken_datetime',''))}"
        elif status == "EXECUTED":
            s_bg, s_fg = S_EXECUTED[0], S_EXECUTED[1]
            s_txt = (f"✅  EXECUTED  ·  {o.get('shares_executed',0):,} shares"
                     f" @ {o.get('execution_price','?')}  ·  by {o.get('executed_by','?')}")
        elif status == "PARTIAL":
            s_bg, s_fg = S_PARTIAL[0], S_PARTIAL[1]
            rem  = o["num_shares"] - o.get("shares_executed", 0)
            held = o.get("taken_by", "")
            rem_txt = f"  ·  {rem:,} remaining" if o["num_shares"] > 0 else ""
            held_txt = f"  ·  held by {held}" if held else ""
            s_txt = (f"⚡  PARTIAL  ·  {o.get('shares_executed',0):,} filled"
                     f"{rem_txt}  ·  by {o.get('executed_by','?')}{held_txt}")
        else:
            s_bg, s_fg = S_CANCELLED[0], S_CANCELLED[1]
            s_txt = f"🚫  CANCELLED  —  {o.get('cancel_reason','')[:60]}"

        tk.Label(badge_row, text=f"  {s_txt}  ", bg=s_bg, fg=s_fg,
                 font=("Segoe UI", 8, "bold"), padx=4, pady=2).pack(side="left")

        if status in ("PENDING", "TAKEN", "PARTIAL"):
            ag = aging_info(o)
            if ag:
                al, ac, ab = ag
                tk.Label(badge_row, text=f"  {al}  ", bg=ab, fg=ac,
                         font=("Segoe UI", 8), padx=4, pady=2).pack(side="left", padx=(6, 0))

        # RIGHT: action buttons
        right = tk.Frame(card, bg=cbg); right.pack(side="right", anchor="n", pady=(4, 0))

        tk.Button(right, text="📋 Detail", font=("Segoe UI", 8), bg=cbg, fg=FBC_MID,
                  relief="flat", cursor="hand2", activebackground=BG,
                  command=lambda ord=o: OrderDetailDialog(self, ord)
                  ).pack(side="top", pady=(0, 4))

        if status == "PENDING":
            tk.Button(right, text="  🤝  Take Order  ",
                      font=("Segoe UI", 9, "bold"),
                      bg=FBC_MID, fg=WHITE, relief="flat", cursor="hand2",
                      activebackground=FBC_DARK,
                      command=lambda ord=o: self._take_order(ord)
                      ).pack(side="top", pady=(0, 4), fill="x")
            tk.Button(right, text="🚫 Cancel", font=("Segoe UI", 8), bg=cbg, fg="#B71C1C",
                      relief="flat", cursor="hand2", activebackground=BG,
                      command=lambda ord=o: self._open_cancel(ord)
                      ).pack(side="top")

        elif status == "TAKEN":
            if o.get("taken_by") == self.dealer_name:
                tk.Button(right, text="  ✅  Execute  ",
                          font=("Segoe UI", 9, "bold"),
                          bg="#1A6B3A", fg=WHITE, relief="flat", cursor="hand2",
                          activebackground="#145A32",
                          command=lambda ord=o: self._open_execute(ord)
                          ).pack(side="top", pady=(0, 4), fill="x")
                tk.Button(right, text="↩ Release", font=("Segoe UI", 8), bg=cbg, fg="#607080",
                          relief="flat", cursor="hand2", activebackground=BG,
                          command=lambda ord=o: self._release_order(ord)
                          ).pack(side="top", pady=(0, 4))
                tk.Button(right, text="🚫 Cancel", font=("Segoe UI", 8), bg=cbg, fg="#B71C1C",
                          relief="flat", cursor="hand2", activebackground=BG,
                          command=lambda ord=o: self._open_cancel(ord)
                          ).pack(side="top")
            else:
                tk.Label(right, text=f"🔒 Taken by\n{o.get('taken_by','')}",
                         bg=cbg, fg=S_TAKEN[1], font=("Segoe UI", 8, "bold"),
                         justify="center").pack(side="top")

        elif status == "PARTIAL":
            # KEY FIX: dealer who executed the partial keeps ownership via taken_by
            can_execute = (o.get("taken_by") == self.dealer_name or
                           o.get("executed_by") == self.dealer_name)
            if can_execute:
                tk.Button(right, text="  ✅  Execute Remainder  ",
                          font=("Segoe UI", 9, "bold"),
                          bg="#6B21A8", fg=WHITE, relief="flat", cursor="hand2",
                          activebackground="#581C87",
                          command=lambda ord=o: self._open_execute(ord)
                          ).pack(side="top", fill="x", pady=(0, 4))
                tk.Button(right, text="🚫 Cancel Remainder", font=("Segoe UI", 8),
                          bg=cbg, fg="#B71C1C", relief="flat", cursor="hand2",
                          activebackground=BG,
                          command=lambda ord=o: self._open_cancel(ord)
                          ).pack(side="top")
            else:
                held = o.get("taken_by", o.get("executed_by", ""))
                tk.Label(right, text=f"🔒 Held by\n{held}",
                         bg=cbg, fg=S_PARTIAL[1], font=("Segoe UI", 8, "bold"),
                         justify="center").pack(side="top")

        if status in ("CANCELLED", "EXECUTED"):
            tk.Button(right, text="🗑", font=("Segoe UI", 10), bg=cbg, fg="#CBD5E1",
                      relief="flat", cursor="hand2", activebackground=BG,
                      command=lambda ord=o: self._delete(ord)
                      ).pack(side="top", pady=(4, 0))

    # ── ACTIONS ───────────────────────────────────────────────────────────
    def _take_order(self, order):
        if order["status"] != "PENDING":
            messagebox.showinfo("Already taken",
                                "This order has already been taken.", parent=self); return
        if not messagebox.askyesno("Take Order",
            f"Claim this order?\n\n"
            f"{order['order_type']}  {order['counter']}\n"
            f"Client: {order['client_name']}\n\n"
            f"Your name ({self.dealer_name}) will be stamped on this order.\n"
            f"Others will see it is in progress.",
            parent=self): return
        order["status"]       = "TAKEN"
        order["taken_by"]     = self.dealer_name
        order["taken_datetime"] = datetime.now().isoformat()
        self._persist(order)

    def _release_order(self, order):
        if not messagebox.askyesno("Release Order",
            "Release this order back to PENDING?\n\nOther dealers will be able to take it.",
            parent=self): return
        order["status"]         = "PENDING"
        order["taken_by"]       = ""
        order["taken_datetime"] = ""
        self._persist(order)

    def _open_execute(self, order):
        ExecuteOrderDialog(self, order, self.dealer_name, self._on_executed)

    def _on_executed(self, order, is_partial):
        """
        KEY FIX v2:
        When partial fill happens, the remainder order stays TAKEN by the same
        dealer (taken_by preserved). It does NOT go back to PENDING with no dealer.
        The dealer sees 'Execute Remainder' immediately on their screen.
        """
        if is_partial:
            now = datetime.now().isoformat()
            rem_shares = max(0, order["num_shares"] - order["shares_executed"])
            remainder = {
                **order,
                "id":                new_id(),
                "status":            "TAKEN",       # stays TAKEN, not PENDING
                "num_shares":        rem_shares,
                "shares_executed":   0,
                "execution_price":   "",
                "executed_by":       "",
                "executed_datetime": "",
                "cancel_reason":     "",
                "partial_of":        order["id"],
                "entered_datetime":  now,
                "order_date":        order.get("order_date", date.today().isoformat()),
                # taken_by stays the SAME dealer — they keep the order
                "taken_by":          order["taken_by"] or order["executed_by"],
                "taken_datetime":    order.get("taken_datetime", now),
                "notes":             (f"Remainder from partial fill of #{order['id']}\n"
                                      f"Previously filled: {order['shares_executed']:,} shares "
                                      f"@ {order['execution_price']}"),
            }
            self._persist(order)
            self._add_new(remainder)
        else:
            self._persist(order)

    def _open_cancel(self, order):
        CancelOrderDialog(self, order, self.dealer_name, self._on_cancelled)

    def _on_cancelled(self, order):
        self._persist(order)

    def _open_new_order(self):
        NewOrderDialog(self, self.dealer_name, self._add_new)

    def _add_new(self, order):
        def _do():
            if self.db: self.db.append_order(order)
            self.orders.append(order); save_orders_local(self.orders)
            self.after(0, self._refresh)
        threading.Thread(target=_do, daemon=True).start()

    def _persist(self, order):
        def _do():
            if self.db: self.db.update_order(order)
            save_orders_local(self.orders); self.after(0, self._refresh)
        threading.Thread(target=_do, daemon=True).start()

    def _delete(self, order):
        if not messagebox.askyesno("Delete",
            f"Permanently delete the record for {order['client_name']}?\n\nThis cannot be undone.",
            parent=self): return
        def _do():
            if self.db: self.db.delete_order(order["id"])
            if order in self.orders: self.orders.remove(order)
            save_orders_local(self.orders); self.after(0, self._refresh)
        threading.Thread(target=_do, daemon=True).start()

    def _open_sheets_setup(self):
        SheetsSetupDialog(self, self.settings, self._on_sheets_saved)

    def _on_sheets_saved(self, sid, key):
        if sid and key:
            self.settings["sheet_id"] = sid; self.settings["key_file"] = key
            self.db = SheetsDB(key, sid); self._full_sync()
        self._update_sync_badge()

# ════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    check_and_apply_update()

    login = LoginDialog(); login.mainloop()
    if not login.authenticated: sys.exit(0)

    settings = load_settings()

    if (not settings.get("sheet_id") or not settings.get("key_file")
            or not os.path.exists(settings.get("key_file", ""))):
        _tmp = tk.Tk(); _tmp.withdraw()
        _saved = {}
        def _on_setup(sid, key): _saved["sheet_id"] = sid; _saved["key_file"] = key
        dlg = SheetsSetupDialog(_tmp, settings, _on_setup)
        _tmp.wait_window(dlg); _tmp.destroy()
        if _saved: settings.update(_saved); save_settings(settings)

    settings = load_settings()
    app = App(dealer_name=login.dealer_name, settings=settings)
    app.mainloop()

