"""
GUI — CDA AI Transport System
Modern chatbot-style interface with full Task 5 support
FAST National University - SE4009
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, font as tkfont
import threading
import time

from task3_process_mining import load_log
from task4_analytics import compute_throughput_times, compute_transition_times, detect_bottlenecks
from task5_ai_planner import TripPlanner
from task5_ai_agent import RouteAIAgent


# ──────────────────────────────────────────────────────────
# COLOUR PALETTE
# ──────────────────────────────────────────────────────────
BG         = "#0F1117"   # dark background
SIDEBAR_BG = "#16181F"   # slightly lighter sidebar
CHAT_BG    = "#1A1D27"   # chat area
BUBBLE_BOT = "#252836"   # agent message bubble
BUBBLE_USR = "#2563EB"   # user message bubble (blue)
ACCENT     = "#3B82F6"   # primary accent
ACCENT2    = "#6366F1"   # secondary accent
TEXT_PRI   = "#F1F5F9"   # primary text
TEXT_SEC   = "#94A3B8"   # secondary text
TEXT_DIM   = "#475569"   # dimmed
INPUT_BG   = "#1E2130"   # input box bg
BORDER     = "#2D3148"   # border
SUCCESS    = "#22C55E"
WARNING    = "#F59E0B"
CHIP_BG    = "#252836"
CHIP_HVR   = "#2D3148"

FONT_FAMILY = "Segoe UI"


class RoundedFrame(tk.Canvas):
    """Canvas-backed rounded rectangle container."""
    def __init__(self, parent, bg, radius=12, **kwargs):
        super().__init__(parent, bg=parent["bg"] if "bg" in parent.keys() else BG,
                         highlightthickness=0, **kwargs)
        self._bg = bg
        self._r = radius
        self.bind("<Configure>", self._redraw)

    def _redraw(self, e=None):
        w, h, r = self.winfo_width(), self.winfo_height(), self._r
        self.delete("bg")
        self.create_rounded_rect(0, 0, w, h, r, fill=self._bg, tags="bg")
        self.lower("bg")

    def create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        pts = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r,
               x2,y2-r, x2,y2, x2-r,y2, x1+r,y2,
               x1,y2, x1,y2-r, x1,y1+r, x1,y1]
        return self.create_polygon(pts, smooth=True, **kwargs)


class App:

    SUGGESTIONS = [
        ("🗺  Khanna Pul → NUST",
         "I have to travel from Khanna Pul to NUST Metro Station — what are my options?"),
        ("🛑  Routes via Faizabad",
         "Which route goes through Faizabad?"),
        ("🕒  Last bus from H-9",
         "What time does the last bus leave from H-9?"),
        ("⏱  Khanna Pul → Faizabad time",
         "How long does it take to get from Khanna Pul to Faizabad?"),
        ("🔗  G-9 ↔ F-10 Markaz",
         "Do any routes connect G-9 Markaz to F-10 Markaz?"),
        ("🚌  Routes via G-9",
         "Which route goes through G-9 Markaz?"),
        ("⏱  PIMS → NUST time",
         "How long does it take to get from PIMS Hospital to NUST?"),
        ("🕒  Last bus from Sohan",
         "What time does the last bus leave from Sohan?"),
    ]

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("CDA AI Transport System")
        self.root.geometry("1100x720")
        self.root.minsize(820, 560)
        self.root.configure(bg=BG)

        self._typing = False

        # ── Load data ─────────────────────────────────────
        try:
            self.log = load_log("data/cda_event_log.xes")
            self.dfg = discover_process_map(self.log)
        except Exception:
            self.log = None
            self.dfg = None

        self.planner = TripPlanner(self.log, "data/routes.csv")
        self.agent   = RouteAIAgent(self.planner)

        self._build_ui()

    # ──────────────────────────────────────────────────────
    # TOP-LEVEL LAYOUT
    # ──────────────────────────────────────────────────────
    def _build_ui(self):
        # Main paned layout
        self.root.columnconfigure(0, minsize=220, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()

    # ──────────────────────────────────────────────────────
    # SIDEBAR
    # ──────────────────────────────────────────────────────
    def _build_sidebar(self):
        sb = tk.Frame(self.root, bg=SIDEBAR_BG, width=220)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.columnconfigure(0, weight=1)

        # Logo / brand
        logo_frame = tk.Frame(sb, bg=SIDEBAR_BG, pady=20)
        logo_frame.grid(row=0, column=0, sticky="ew")

        logo_icon = tk.Label(logo_frame, text="🚍", font=(FONT_FAMILY, 28),
                             bg=SIDEBAR_BG, fg=TEXT_PRI)
        logo_icon.pack()
        tk.Label(logo_frame, text="CDA Transit AI",
                 font=(FONT_FAMILY, 13, "bold"),
                 bg=SIDEBAR_BG, fg=TEXT_PRI).pack()
        tk.Label(logo_frame, text="Islamabad Bus Network",
                 font=(FONT_FAMILY, 8),
                 bg=SIDEBAR_BG, fg=TEXT_DIM).pack()

        tk.Frame(sb, bg=BORDER, height=1).grid(row=1, column=0, sticky="ew", padx=16)

        # Nav buttons
        nav = tk.Frame(sb, bg=SIDEBAR_BG, pady=10)
        nav.grid(row=2, column=0, sticky="ew")

        self._nav_btns = {}
        nav_items = [
            ("💬", "AI Chat",     self._show_chat),
            ("📊", "Analytics",   self._show_analytics),
            ("ℹ️",  "About",      self._show_about),
        ]
        for icon, label, cmd in nav_items:
            self._add_nav_btn(nav, icon, label, cmd)

        tk.Frame(sb, bg=BORDER, height=1).grid(row=3, column=0, sticky="ew", padx=16)

        # Quick queries label
        tk.Label(sb, text="QUICK QUERIES",
                 font=(FONT_FAMILY, 8, "bold"),
                 bg=SIDEBAR_BG, fg=TEXT_DIM).grid(row=4, column=0, sticky="w",
                                                   padx=16, pady=(14, 4))

        # Quick query buttons
        qf = tk.Frame(sb, bg=SIDEBAR_BG)
        qf.grid(row=5, column=0, sticky="ew", padx=8)

        for label, query in self.SUGGESTIONS:
            self._add_quick_btn(qf, label, query)

        # Status bar at bottom
        tk.Frame(sb, bg=BORDER, height=1).grid(row=6, column=0, sticky="ew",
                                                padx=16, pady=(10, 0))
        status_frame = tk.Frame(sb, bg=SIDEBAR_BG, pady=8)
        status_frame.grid(row=7, column=0, sticky="ew")
        self.status_dot = tk.Label(status_frame, text="●", fg=SUCCESS,
                                   bg=SIDEBAR_BG, font=(FONT_FAMILY, 9))
        self.status_dot.pack(side="left", padx=(12, 4))
        tk.Label(status_frame, text="System Ready",
                 font=(FONT_FAMILY, 9), bg=SIDEBAR_BG, fg=TEXT_SEC).pack(side="left")

    def _add_nav_btn(self, parent, icon, label, cmd):
        f = tk.Frame(parent, bg=SIDEBAR_BG, cursor="hand2")
        f.pack(fill="x", padx=8, pady=2)

        lbl = tk.Label(f, text=f"  {icon}  {label}",
                       font=(FONT_FAMILY, 10),
                       bg=SIDEBAR_BG, fg=TEXT_SEC,
                       anchor="w", padx=8, pady=6)
        lbl.pack(fill="x")

        def on_enter(e):
            f.config(bg=CHIP_HVR); lbl.config(bg=CHIP_HVR)
        def on_leave(e):
            f.config(bg=SIDEBAR_BG); lbl.config(bg=SIDEBAR_BG)
        def on_click(e):
            cmd()

        for w in (f, lbl):
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)

    def _add_quick_btn(self, parent, label, query):
        f = tk.Frame(parent, bg=SIDEBAR_BG, cursor="hand2")
        f.pack(fill="x", pady=1)

        lbl = tk.Label(f, text=f"  {label}",
                       font=(FONT_FAMILY, 8),
                       bg=SIDEBAR_BG, fg=TEXT_SEC,
                       anchor="w", pady=4, wraplength=180, justify="left")
        lbl.pack(fill="x", padx=4)

        def on_enter(e):
            f.config(bg=CHIP_HVR); lbl.config(bg=CHIP_HVR)
        def on_leave(e):
            f.config(bg=SIDEBAR_BG); lbl.config(bg=SIDEBAR_BG)
        def on_click(e):
            self._fill_and_send(query)

        for w in (f, lbl):
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)

    # ──────────────────────────────────────────────────────
    # MAIN CONTENT AREA
    # ──────────────────────────────────────────────────────
    def _build_main(self):
        self.main_frame = tk.Frame(self.root, bg=BG)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)

        self.chat_frame     = tk.Frame(self.main_frame, bg=BG)
        self.analytics_frame = tk.Frame(self.main_frame, bg=BG)
        self.about_frame    = tk.Frame(self.main_frame, bg=BG)

        for f in (self.chat_frame, self.analytics_frame, self.about_frame):
            f.grid(row=0, column=0, sticky="nsew")

        self._build_chat_panel()
        self._build_analytics_panel()
        self._build_about_panel()
        self._show_chat()

    # ──────────────────────────────────────────────────────
    # CHAT PANEL
    # ──────────────────────────────────────────────────────
    def _build_chat_panel(self):
        p = self.chat_frame
        p.columnconfigure(0, weight=1)
        p.rowconfigure(1, weight=1)

        # Header
        hdr = tk.Frame(p, bg=CHAT_BG, pady=14, padx=20)
        hdr.grid(row=0, column=0, sticky="ew")

        tk.Label(hdr, text="💬  AI Transit Agent",
                 font=(FONT_FAMILY, 14, "bold"),
                 bg=CHAT_BG, fg=TEXT_PRI).pack(side="left")
        tk.Label(hdr, text="Powered by CDA Route Data + Claude AI",
                 font=(FONT_FAMILY, 9),
                 bg=CHAT_BG, fg=TEXT_DIM).pack(side="right")
        tk.Frame(p, bg=BORDER, height=1).grid(row=0, column=0, sticky="sew")

        # Chat scroll area
        chat_outer = tk.Frame(p, bg=CHAT_BG)
        chat_outer.grid(row=1, column=0, sticky="nsew")
        chat_outer.rowconfigure(0, weight=1)
        chat_outer.columnconfigure(0, weight=1)

        self.chat_canvas = tk.Canvas(chat_outer, bg=CHAT_BG,
                                     highlightthickness=0, bd=0)
        self.chat_canvas.grid(row=0, column=0, sticky="nsew")

        scrollbar = tk.Scrollbar(chat_outer, orient="vertical",
                                  command=self.chat_canvas.yview,
                                  bg=CHAT_BG, troughcolor=CHAT_BG,
                                  activebackground=BORDER)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.chat_canvas.configure(yscrollcommand=scrollbar.set)

        self.chat_inner = tk.Frame(self.chat_canvas, bg=CHAT_BG)
        self.chat_window = self.chat_canvas.create_window((0, 0),
                                                           window=self.chat_inner,
                                                           anchor="nw")
        self.chat_inner.bind("<Configure>", self._on_chat_configure)
        self.chat_canvas.bind("<Configure>", self._on_canvas_configure)

        # Mouse wheel
        self.chat_canvas.bind_all("<MouseWheel>",
            lambda e: self.chat_canvas.yview_scroll(-1*(e.delta//120), "units"))

        # Bottom area: input + typing indicator
        bottom = tk.Frame(p, bg=BG, pady=12, padx=16)
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)

        self.typing_label = tk.Label(bottom, text="",
                                      font=(FONT_FAMILY, 9, "italic"),
                                      bg=BG, fg=TEXT_DIM)
        self.typing_label.grid(row=0, column=0, sticky="w", pady=(0, 4))

        # Input row
        input_row = tk.Frame(bottom, bg=INPUT_BG,
                              highlightbackground=BORDER,
                              highlightthickness=1)
        input_row.grid(row=1, column=0, sticky="ew")
        input_row.columnconfigure(0, weight=1)

        self.chat_entry = tk.Text(input_row,
                                   font=(FONT_FAMILY, 11),
                                   bg=INPUT_BG, fg=TEXT_PRI,
                                   insertbackground=ACCENT,
                                   relief="flat", bd=0,
                                   height=2, padx=14, pady=10,
                                   wrap="word")
        self.chat_entry.grid(row=0, column=0, sticky="ew")
        self.chat_entry.bind("<Return>",    self._on_enter_key)
        self.chat_entry.bind("<Shift-Return>", lambda e: None)  # allow newline

        send_btn = tk.Button(input_row, text="Send  ➤",
                             font=(FONT_FAMILY, 10, "bold"),
                             bg=ACCENT, fg="white",
                             relief="flat", bd=0,
                             padx=18, pady=14,
                             cursor="hand2",
                             activebackground=ACCENT2,
                             activeforeground="white",
                             command=self.send_message)
        send_btn.grid(row=0, column=1)
        self.send_btn = send_btn

        hint = tk.Label(bottom,
                        text="Press Enter to send  •  Shift+Enter for new line",
                        font=(FONT_FAMILY, 8),
                        bg=BG, fg=TEXT_DIM)
        hint.grid(row=2, column=0, sticky="w", pady=(4, 0))

        # Initial welcome message
        self.root.after(300, self._show_welcome)

    def _on_chat_configure(self, e):
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))

    def _on_canvas_configure(self, e):
        self.chat_canvas.itemconfig(self.chat_window, width=e.width)

    def _show_welcome(self):
        self._add_bot_message(
            "👋  Hello! I'm the CDA Transit AI.\n\n"
            "I can help you navigate Islamabad's bus routes.\n\n"
            "Try asking:\n"
            "  •  I have to travel from Khanna Pul to NUST — what are my options?\n"
            "  •  Which route goes through Faizabad?\n"
            "  •  What time does the last bus leave from H-9?\n"
            "  •  How long does it take from Khanna Pul to Faizabad?\n"
            "  •  Do any routes connect G-9 Markaz to F-10 Markaz?\n\n"
            "Or click a quick query in the sidebar →"
        )

    # ── Message bubble rendering ───────────────────────────
    def _add_user_message(self, text: str):
        row = tk.Frame(self.chat_inner, bg=CHAT_BG, pady=4)
        row.pack(fill="x", padx=16)

        # Timestamp
        ts = time.strftime("%H:%M")
        info = tk.Label(row, text=f"You  •  {ts}",
                        font=(FONT_FAMILY, 8),
                        bg=CHAT_BG, fg=TEXT_DIM)
        info.pack(anchor="e", pady=(0, 2))

        bubble = tk.Label(row, text=text,
                          font=(FONT_FAMILY, 11),
                          bg=BUBBLE_USR, fg="white",
                          wraplength=520,
                          justify="left",
                          padx=16, pady=10,
                          relief="flat")
        bubble.pack(anchor="e")
        self._scroll_to_bottom()

    def _add_bot_message(self, text: str):
        row = tk.Frame(self.chat_inner, bg=CHAT_BG, pady=4)
        row.pack(fill="x", padx=16)

        # Agent label row
        info_row = tk.Frame(row, bg=CHAT_BG)
        info_row.pack(anchor="w", pady=(0, 2))
        tk.Label(info_row, text="🚍",
                 font=(FONT_FAMILY, 11),
                 bg=CHAT_BG, fg=ACCENT).pack(side="left")
        tk.Label(info_row, text=f"  CDA Agent  •  {time.strftime('%H:%M')}",
                 font=(FONT_FAMILY, 8),
                 bg=CHAT_BG, fg=TEXT_DIM).pack(side="left")

        bubble = tk.Label(row, text=text,
                          font=(FONT_FAMILY, 11),
                          bg=BUBBLE_BOT, fg=TEXT_PRI,
                          wraplength=560,
                          justify="left",
                          padx=16, pady=12,
                          relief="flat",
                          anchor="w")
        bubble.pack(anchor="w", fill="x")
        self._scroll_to_bottom()

    def _add_thinking_indicator(self):
        row = tk.Frame(self.chat_inner, bg=CHAT_BG, pady=4)
        row.pack(fill="x", padx=16)
        row._is_thinking = True

        info_row = tk.Frame(row, bg=CHAT_BG)
        info_row.pack(anchor="w", pady=(0, 2))
        tk.Label(info_row, text="🚍  CDA Agent",
                 font=(FONT_FAMILY, 8),
                 bg=CHAT_BG, fg=TEXT_DIM).pack(side="left")

        self._thinking_lbl = tk.Label(row,
                                       text="●  ●  ●",
                                       font=(FONT_FAMILY, 14),
                                       bg=BUBBLE_BOT, fg=TEXT_DIM,
                                       padx=16, pady=12)
        self._thinking_lbl.pack(anchor="w")
        self._thinking_row = row
        self._animate_thinking()
        self._scroll_to_bottom()

    def _animate_thinking(self, step=0):
        if not self._typing:
            return
        dots = ["●  ○  ○", "●  ●  ○", "●  ●  ●", "○  ●  ●", "○  ○  ●"][step % 5]
        try:
            self._thinking_lbl.config(text=dots)
            self.root.after(350, self._animate_thinking, step + 1)
        except Exception:
            pass

    def _remove_thinking(self):
        try:
            self._thinking_row.destroy()
        except Exception:
            pass

    def _scroll_to_bottom(self):
        self.root.after(50, lambda: self.chat_canvas.yview_moveto(1.0))

    # ── Send / receive ─────────────────────────────────────
    def _on_enter_key(self, event):
        if not event.state & 0x1:   # Shift not held
            self.send_message()
            return "break"

    def send_message(self):
        text = self.chat_entry.get("1.0", "end").strip()
        if not text or self._typing:
            return
        self.chat_entry.delete("1.0", "end")
        self._typing = True
        self.send_btn.config(state="disabled", bg=TEXT_DIM)
        self.typing_label.config(text="Agent is thinking…")
        self._add_user_message(text)
        self._add_thinking_indicator()
        threading.Thread(target=self._run_agent, args=(text,), daemon=True).start()

    def _run_agent(self, query: str):
        response = self.agent.ask(query)
        self.root.after(0, self._on_agent_response, response)

    def _on_agent_response(self, response: str):
        self._typing = False
        self._remove_thinking()
        self._add_bot_message(response)
        self.typing_label.config(text="")
        self.send_btn.config(state="normal", bg=ACCENT)

    def _fill_and_send(self, query: str):
        if self._typing:
            return
        self.chat_entry.delete("1.0", "end")
        self.chat_entry.insert("1.0", query)
        self.send_message()

    # ──────────────────────────────────────────────────────
    # ANALYTICS PANEL
    # ──────────────────────────────────────────────────────
    def _build_analytics_panel(self):
        p = self.analytics_frame
        p.columnconfigure(0, weight=1)
        p.rowconfigure(1, weight=1)

        hdr = tk.Frame(p, bg=CHAT_BG, pady=14, padx=20)
        hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(hdr, text="📊  Process Mining Analytics",
                 font=(FONT_FAMILY, 14, "bold"),
                 bg=CHAT_BG, fg=TEXT_PRI).pack(side="left")
        tk.Frame(p, bg=BORDER, height=1).grid(row=0, column=0, sticky="sew")

        out = scrolledtext.ScrolledText(p,
                                         font=("Consolas", 10),
                                         bg=CHAT_BG, fg=TEXT_PRI,
                                         insertbackground=ACCENT,
                                         selectbackground=ACCENT,
                                         relief="flat", bd=0,
                                         padx=20, pady=16)
        out.grid(row=1, column=0, sticky="nsew")

        try:
            if self.log:
                tt   = compute_throughput_times(self.log)
                trans = compute_transition_times(self.log)
                bns   = detect_bottlenecks(trans, threshold=300)

                report = (
                    "═" * 52 + "\n"
                    "  CDA EVENT LOG — PROCESS MINING REPORT\n"
                    + "═" * 52 + "\n\n"
                    "THROUGHPUT TIMES\n"
                    + "─" * 40 + "\n"
                    f"  Minimum : {tt['min']/60:>8.1f} min\n"
                    f"  Maximum : {tt['max']/60:>8.1f} min\n"
                    f"  Average : {tt['avg']/60:>8.1f} min\n\n"
                    "TOP 10 TRANSITIONS  (avg seconds)\n"
                    + "─" * 40 + "\n"
                )
                for (src, dst), v in sorted(trans.items(), key=lambda x: -x[1])[:10]:
                    report += f"  {src[:22]:<22} → {dst[:22]:<22}  {v:>6.0f}s\n"

                report += "\nBOTTLENECKS  (> 300s avg)\n" + "─" * 40 + "\n"
                if bns:
                    for (src, dst), v in bns.items():
                        report += f"  {src:<22} → {dst:<22}  {v:>6.0f}s\n"
                else:
                    report += "  None detected.\n"
            else:
                report = "No XES log loaded. Run task2_xes_generator.py first."
        except Exception as ex:
            report = f"Analytics error:\n{ex}"

        out.configure(state="normal")
        out.insert("end", report)
        out.configure(state="disabled")

    # ──────────────────────────────────────────────────────
    # ABOUT PANEL
    # ──────────────────────────────────────────────────────
    def _build_about_panel(self):
        p = self.about_frame
        p.columnconfigure(0, weight=1)
        p.rowconfigure(1, weight=1)

        hdr = tk.Frame(p, bg=CHAT_BG, pady=14, padx=20)
        hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(hdr, text="ℹ️   About This System",
                 font=(FONT_FAMILY, 14, "bold"),
                 bg=CHAT_BG, fg=TEXT_PRI).pack(side="left")
        tk.Frame(p, bg=BORDER, height=1).grid(row=0, column=0, sticky="sew")

        body = tk.Frame(p, bg=BG, padx=40, pady=30)
        body.grid(row=1, column=0, sticky="nsew")

        about_text = [
            ("🚍  CDA AI Transport System", 16, "bold", ACCENT),
            ("FAST National University  •  SE4009 Process Mining", 10, "normal", TEXT_SEC),
            ("", 10, "normal", TEXT_PRI),
            ("TASK OVERVIEW", 11, "bold", TEXT_SEC),
            ("Task 1  —  Data Extraction & CSV Generation", 10, "normal", TEXT_PRI),
            ("Task 2  —  XES Event Log Construction", 10, "normal", TEXT_PRI),
            ("Task 3  —  Process Map Discovery (pm4py DFG)", 10, "normal", TEXT_PRI),
            ("Task 4  —  Throughput & Bottleneck Analytics", 10, "normal", TEXT_PRI),
            ("Task 5  —  Agentic AI Trip Planner (this GUI)", 10, "normal", ACCENT),
            ("Task 6  —  Personal Route Visualisation", 10, "normal", TEXT_PRI),
            ("", 10, "normal", TEXT_PRI),
            ("ROUTE COVERAGE", 11, "bold", TEXT_SEC),
            ("19 CDA bus routes  •  106 unique stops", 10, "normal", TEXT_PRI),
            ("8 daily trips per route  •  60-min frequency", 10, "normal", TEXT_PRI),
            ("", 10, "normal", TEXT_PRI),
            ("AI STACK", 11, "bold", TEXT_SEC),
            ("Natural language  →  Claude Sonnet API (intent parsing)", 10, "normal", TEXT_PRI),
            ("Routing  →  NetworkX undirected shortest path", 10, "normal", TEXT_PRI),
            ("Stop resolution  →  Exact / Substring / Token / Fuzzy (difflib)", 10, "normal", TEXT_PRI),
        ]
        for text, size, weight, color in about_text:
            tk.Label(body, text=text,
                     font=(FONT_FAMILY, size, weight),
                     bg=BG, fg=color,
                     anchor="w").pack(anchor="w", pady=1)

    # ──────────────────────────────────────────────────────
    # PANEL SWITCHING
    # ──────────────────────────────────────────────────────
    def _show_chat(self):
        self.chat_frame.tkraise()

    def _show_analytics(self):
        self.analytics_frame.tkraise()

    def _show_about(self):
        self.about_frame.tkraise()


# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.25)
    except Exception:
        pass
    app = App(root)
    root.mainloop()