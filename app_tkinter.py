"""
app_tkinter.py — Simulateur M/M/1 avec Abandon
Palette  : Noir · Blanc · Rouge · Jaune · Vert
Menus    : Paramètres · Résultats · Score · Graphiques · Journal
Graphiques : histogrammes annotés + nuages de points lisibles
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading, time
from datetime import datetime

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
try:
    # NavigationToolbar2Tk may be exported from different modules
    from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
except Exception:
    try:
        from matplotlib.backends._backend_tk import NavigationToolbar2Tk
    except Exception:
        NavigationToolbar2Tk = None
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch, Arc, Wedge
import numpy as np

try:
    from scipy import stats as sp_stats
    HAS_SCIPY = True
except ImportError:
    sp_stats = None
    HAS_SCIPY = False

from core.simulation_des import simuler_une_realisation
from core.monte_carlo    import monte_carlo
from analyse.indicateurs import analyser_qualite, calculer_valeurs_theoriques

# ══════════════════════════════════════════════════════════════════════════════
#  PALETTE  —  Noir · Blanc · Rouge · Jaune · Vert
# ══════════════════════════════════════════════════════════════════════════════
C = {
    # Fonds
    "bg"           : "#F5F5F5",   # gris très clair
    "nav_bg"       : "#111111",   # barre latérale noire
    "nav_top"      : "#1A1A1A",   # titre noir
    "card"         : "#FFFFFF",   # blanc
    "card2"        : "#F8F8F8",   # gris quasi-blanc
    "card_hi"      : "#FFF9E6",   # survol nav jaune pâle

    # Accents principaux
    "red"          : "#D32F2F",
    "red_h"        : "#F44336",
    "red_bg"       : "#FFEBEE",   # fond badge rouge
    "yellow"       : "#F9A825",   # jaune doré
    "yellow_h"     : "#FFB300",
    "yellow_bg"    : "#FFFDE7",   # fond badge jaune
    "green"        : "#2E7D32",
    "green_h"      : "#43A047",
    "green_bg"     : "#E8F5E9",   # fond badge vert

    # Textes
    "txt"          : "#111111",   # noir principal
    "txt_nav"      : "#CCCCCC",   # texte nav (sur fond noir)
    "txt_nav_act"  : "#FFFFFF",   # texte nav actif
    "txt2"         : "#555555",
    "txt3"         : "#999999",

    # Bordures
    "border"       : "#E0E0E0",
    "border2"      : "#EEEEEE",
    "sep_nav"      : "#2A2A2A",   # séparateur nav

    # Boutons
    "btn_run"      : "#D32F2F",
    "btn_run_h"    : "#F44336",
    "btn_ok"       : "#2E7D32",
    "btn_ok_h"     : "#43A047",
    "btn_dl"       : "#F9A825",
    "btn_dl_h"     : "#FFB300",
    "btn_neu"      : "#424242",
    "btn_neu_h"    : "#616161",

    # Statuts
    "ok"           : "#2E7D32",
    "warn"         : "#F9A825",
    "crit"         : "#D32F2F",

    # Graphiques
    "plot_bg"      : "#FFFFFF",
    "plot_grid"    : "#EEEEEE",
    "bar_wq"       : "#1565C0",   # bleu — Wq
    "bar_lq"       : "#6A1B9A",   # violet — Lq
    "bar_rho"      : "#2E7D32",   # vert — ρ
    "bar_pa"       : "#D32F2F",   # rouge — Pa
    "bar_w"        : "#E65100",   # orange foncé — W

    # Journal
    "log_bg"       : "#0D0D0D",
}

# Polices
FONT_BRAND = ("Segoe UI", 19, "bold")
FONT_TITLE = ("Segoe UI", 11, "bold")
FONT_HEAD  = ("Segoe UI", 10, "bold")
FONT_BODY  = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_MONO  = ("Consolas", 11, "bold")
FONT_MONOS = ("Consolas", 9)
FONT_NAV   = ("Segoe UI", 10, "bold")
FONT_HUGE  = ("Consolas", 32, "bold")


# ══════════════════════════════════════════════════════════════════════════════
#  BOUTON ARRONDI (Canvas) — stable contre GC
# ══════════════════════════════════════════════════════════════════════════════
class FlatButton(tk.Canvas):
    def __init__(self, parent, text, command, bg, bg_hover,
                 fg="#FFFFFF", font=FONT_HEAD, width=220, height=36,
                 radius=7, **kw):
        try:    pbg = parent["bg"]
        except: pbg = C["bg"]
        super().__init__(parent, width=width, height=height,
                         bg=pbg, highlightthickness=0, cursor="hand2", **kw)
        self._bg=bg; self._bgh=bg_hover; self._fg=fg
        self._font=font; self._txt=text; self._cmd=command
        self._r=radius; self._width=width; self._height=height
        self._enabled=True
        self.after_idle(lambda: self._draw(bg))
        self.bind("<Enter>",    lambda e: self._draw(bg_hover) if self._enabled else None)
        self.bind("<Leave>",    lambda e: self._draw(bg)       if self._enabled else None)
        self.bind("<Button-1>", lambda e: command()            if self._enabled else None)

    def _draw(self, color):
        try:
            if not self.winfo_exists(): return
            self.delete("all")
        except tk.TclError: return
        r, w, h = self._r, self._width, self._height
        fg   = self._fg if self._enabled else "#AAAAAA"
        fill = color    if self._enabled else "#CCCCCC"
        for x0,y0,x1,y1,s in [(0,0,2*r,2*r,90),(w-2*r,0,w,2*r,0),
                                (0,h-2*r,2*r,h,180),(w-2*r,h-2*r,w,h,270)]:
            self.create_arc(x0,y0,x1,y1,start=s,extent=90,fill=fill,outline=fill)
        self.create_rectangle(r,0,w-r,h,fill=fill,outline=fill)
        self.create_rectangle(0,r,w,h-r,fill=fill,outline=fill)
        self.create_text(w//2,h//2,text=self._txt,fill=fg,font=self._font,anchor="center")

    def set_state(self, state):
        """Set widget enabled/disabled state (replacement for configure(state=...))."""
        self._enabled = state != "disabled"
        col = self._bg if self._enabled else "#CCCCCC"
        try:
            self.after_idle(lambda c=col: self._draw(c))
        except Exception:
            pass

    def update_text(self, txt):
        self._txt = txt; self.after_idle(lambda: self._draw(self._bg))


# ══════════════════════════════════════════════════════════════════════════════
#  BOUTON NAVIGATION (barre noire)
# ══════════════════════════════════════════════════════════════════════════════
class NavButton(tk.Frame):
    def __init__(self, parent, icon, label, command, **kw):
        super().__init__(parent, bg=C["nav_bg"], cursor="hand2", **kw)
        self._active=False; self._cmd=command

        self._bar = tk.Frame(self, bg=C["nav_bg"], width=4)
        self._bar.pack(side=tk.LEFT, fill=tk.Y)

        inner = tk.Frame(self, bg=C["nav_bg"])
        inner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8,12), pady=10)

        self._ico = tk.Label(inner, text=icon, font=("Segoe UI",13),
                             bg=C["nav_bg"], fg="#555555")
        self._ico.pack(side=tk.LEFT)
        self._lbl = tk.Label(inner, text=label, font=FONT_NAV,
                             bg=C["nav_bg"], fg=C["txt_nav"])
        self._lbl.pack(side=tk.LEFT, padx=(10,0))

        for w in (self, inner, self._ico, self._lbl):
            w.bind("<Button-1>", lambda e: self._cmd())
            w.bind("<Enter>",    lambda e: self._hover(True))
            w.bind("<Leave>",    lambda e: self._hover(False))

    def _hover(self, on):
        if self._active: return
        bg = "#222222" if on else C["nav_bg"]
        for w in (self, self._ico, self._lbl): w.configure(bg=bg)

    def set_active(self, state):
        self._active = state
        bg   = "#1E1E1E"       if state else C["nav_bg"]
        bbar = C["yellow"]     if state else C["nav_bg"]
        fgi  = C["yellow"]     if state else "#555555"
        fgt  = C["txt_nav_act"] if state else C["txt_nav"]
        self._bar.configure(bg=bbar)
        for w in (self, self._ico, self._lbl): w.configure(bg=bg)
        self._ico.configure(fg=fgi)
        self._lbl.configure(fg=fgt)


# ══════════════════════════════════════════════════════════════════════════════
#  CARTE KPI
# ══════════════════════════════════════════════════════════════════════════════
class CarteKPI(tk.Frame):
    def __init__(self, parent, label, icon="", accent=C["yellow"], **kw):
        super().__init__(parent, bg=C["card"],
                         highlightthickness=1, highlightbackground=C["border"], **kw)
        self._accent = accent
        # Bandeau coloré gauche
        tk.Frame(self, bg=accent, width=5).pack(side=tk.LEFT, fill=tk.Y)

        body = tk.Frame(self, bg=C["card"])
        body.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        hdr = tk.Frame(body, bg=C["card"])
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text=icon,  font=("Segoe UI",14), bg=C["card"], fg=accent).pack(side=tk.LEFT)
        tk.Label(hdr, text=f" {label}", font=FONT_SMALL,
                 bg=C["card"], fg=C["txt2"]).pack(side=tk.LEFT)

        self.var_sim = tk.StringVar(value="—")
        self.var_th  = tk.StringVar(value="—")

        tk.Label(body, textvariable=self.var_sim, font=FONT_MONO,
                 bg=C["card"], fg=C["txt"]).pack(anchor="w", pady=(4,0))

        row = tk.Frame(body, bg=C["card"])
        row.pack(fill=tk.X)
        tk.Label(row, text="Théorique : ", font=FONT_SMALL,
                 bg=C["card"], fg=C["txt3"]).pack(side=tk.LEFT)
        tk.Label(row, textvariable=self.var_th, font=("Segoe UI",9,"bold"),
                 bg=C["card"], fg=C["green"]).pack(side=tk.LEFT)

    def set_sim(self, v): self.var_sim.set(v)
    def set_th(self,  v): self.var_th.set(v)
    def reset(self):      self.var_sim.set("—"); self.var_th.set("—")

    def flash(self, col):
        self.configure(highlightbackground=col)
        self.after(1500, lambda: self.configure(highlightbackground=C["border"]))


# ══════════════════════════════════════════════════════════════════════════════
#  APPLICATION
# ══════════════════════════════════════════════════════════════════════════════
class SimulateurApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Simulateur M/M/1  ·  Monte Carlo + DES")
        self.geometry("1300x820")
        self.minsize(1100, 700)
        self.configure(bg=C["bg"])

        self._res=None; self._analyse=None
        self._th=None;  self._params=None
        self._figs={};  self._raw={}

        self._init_vars()
        self._build()
        self._show_page("params")

    # ─────────────────────────────────────────────────────────────
    def _init_vars(self):
        self.var_lambda = tk.DoubleVar(value=0.8)
        self.var_mu     = tk.DoubleVar(value=1.0)
        self.var_theta  = tk.DoubleVar(value=0.2)
        self.var_K      = tk.IntVar(value=10)
        self.var_nsim   = tk.IntVar(value=1000)
        self.var_tmax   = tk.DoubleVar(value=200.0)
        self.var_score  = tk.StringVar(value="—")
        self.var_statut = tk.StringVar(value="En attente")
        self.var_little = tk.StringVar(value="—")
        self.var_prog   = tk.StringVar(value="")

    # ══════════════════════════════════════════════════════════════
    #  STRUCTURE PRINCIPALE
    # ══════════════════════════════════════════════════════════════
    def _build(self):
        self._build_titlebar()
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill=tk.BOTH, expand=True)
        self._build_nav(body)
        self._content = tk.Frame(body, bg=C["bg"])
        self._content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._pages = {
            "params"    : self._build_page_params(self._content),
            "resultats" : self._build_page_resultats(self._content),
            "score"     : self._build_page_score(self._content),
            "graphiques": self._build_page_graphiques(self._content),
            "journal"   : self._build_page_journal(self._content),
        }

    # ── TITRE ────────────────────────────────────────────────────
    def _build_titlebar(self):
        bar = tk.Frame(self, bg=C["nav_top"], pady=11)
        bar.pack(fill=tk.X)
        left = tk.Frame(bar, bg=C["nav_top"])
        left.pack(side=tk.LEFT, padx=20)
        tk.Label(left, text="M/M/1", font=FONT_BRAND,
                 bg=C["nav_top"], fg="#FFFFFF").pack(side=tk.LEFT)
        tk.Label(left, text="  Simulator", font=("Segoe UI",13),
                 bg=C["nav_top"], fg="#888888").pack(side=tk.LEFT)
        right = tk.Frame(bar, bg=C["nav_top"])
        right.pack(side=tk.RIGHT, padx=20)
        tk.Label(right, text="File d'attente avec impatience  ·  Monte Carlo + DES",
                 font=FONT_SMALL, bg=C["nav_top"], fg="#666666").pack()
        # Bande tricolore rouge/jaune/vert
        stripe = tk.Frame(self, height=4)
        stripe.pack(fill=tk.X)
        for col in (C["red"], C["yellow"], C["green"]):
            tk.Frame(stripe, bg=col, height=4).pack(
                side=tk.LEFT, fill=tk.X, expand=True)

    # ── NAVIGATION NOIRE ─────────────────────────────────────────
    def _build_nav(self, parent):
        nav = tk.Frame(parent, bg=C["nav_bg"], width=215)
        nav.pack(side=tk.LEFT, fill=tk.Y)
        nav.pack_propagate(False)

        tk.Frame(nav, bg=C["sep_nav"], height=1).pack(fill=tk.X, pady=(10,8))

        defs = [
            ("⚙",  "Paramètres",  "params"),
            ("📊", "Résultats",   "resultats"),
            ("🏆", "Score",       "score"),
            ("📈", "Graphiques",  "graphiques"),
            ("📋", "Journal",     "journal"),
        ]
        self._nav_btns = {}
        for icon, label, key in defs:
            btn = NavButton(nav, icon, label,
                            command=lambda k=key: self._show_page(k))
            btn.pack(fill=tk.X, padx=4, pady=1)
            self._nav_btns[key] = btn

        tk.Frame(nav, bg=C["sep_nav"], height=1).pack(fill=tk.X, pady=10)

        # ρ live
        frm = tk.Frame(nav, bg=C["nav_bg"])
        frm.pack(fill=tk.X, padx=14)
        tk.Label(frm, text="Charge théorique", font=FONT_SMALL,
                 bg=C["nav_bg"], fg="#666666").pack(anchor="w")
        self.lbl_rho = tk.Label(frm, text="ρ = 0.800",
                                 font=("Consolas",16,"bold"),
                                 bg=C["nav_bg"], fg=C["yellow"])
        self.lbl_rho.pack(anchor="w", pady=(2,10))
        self.var_lambda.trace_add("write", self._rho_live)
        self.var_mu.trace_add("write",     self._rho_live)

        # Progression simulation
        self.lbl_prog = tk.Label(nav, textvariable=self.var_prog,
                                  font=("Segoe UI",8), bg=C["nav_bg"],
                                  fg="#666666", wraplength=190)
        self.lbl_prog.pack(padx=12, pady=(0,8))

        tk.Frame(nav, bg=C["sep_nav"], height=1).pack(fill=tk.X, pady=(0,10))

        # Boutons d'action
        self.btn_simuler = FlatButton(
            nav, "▶  SIMULER", self._lancer,
            C["btn_run"], C["btn_run_h"], width=183, height=42)
        self.btn_simuler.pack(pady=(0,6))

        self.btn_score_nav = FlatButton(
            nav, "🏆  VOIR LE SCORE",
            lambda: self._show_page("score"),
            C["btn_neu"], C["btn_neu_h"],
            fg="#FFFFFF", width=183, height=36)
        self.btn_score_nav.pack(pady=(0,6))
        self.btn_score_nav.set_state("disabled")

        self.btn_graph_nav = FlatButton(
            nav, "📈  GRAPHIQUES",
            lambda: self._show_page("graphiques"),
            C["btn_ok"], C["btn_ok_h"], width=183, height=36)
        self.btn_graph_nav.pack(pady=(0,6))
        self.btn_graph_nav.set_state("disabled")

        self.btn_reinit = FlatButton(
            nav, "↺  Réinitialiser", self._reinit,
            "#333333", "#444444",
            fg="#CCCCCC", width=183, height=30)
        self.btn_reinit.pack(pady=(0,4))

        tk.Label(nav, text="v4.0", font=("Segoe UI",7),
                 bg=C["nav_bg"], fg="#333333").pack(side=tk.BOTTOM, pady=8)

    def _show_page(self, key):
        for f in self._pages.values(): f.pack_forget()
        self._pages[key].pack(fill=tk.BOTH, expand=True)
        for k, b in self._nav_btns.items(): b.set_active(k == key)

    # ══════════════════════════════════════════════════════════════
    #  HELPERS LAYOUT
    # ══════════════════════════════════════════════════════════════
    def _page_title(self, parent, title, subtitle="", accent=C["red"]):
        bar = tk.Frame(parent, bg=C["card"],
                       highlightthickness=1, highlightbackground=C["border"])
        bar.pack(fill=tk.X)
        tk.Frame(bar, bg=accent, height=3).pack(fill=tk.X)
        inner = tk.Frame(bar, bg=C["card"])
        inner.pack(fill=tk.X, padx=18, pady=10)
        tk.Label(inner, text=title, font=FONT_TITLE,
                 bg=C["card"], fg=C["txt"]).pack(anchor="w")
        if subtitle:
            tk.Label(inner, text=subtitle, font=FONT_SMALL,
                     bg=C["card"], fg=C["txt3"]).pack(anchor="w")

    def _section(self, parent, title, accent=C["red"]):
        frm = tk.Frame(parent, bg=C["card"],
                       highlightthickness=1, highlightbackground=C["border"])
        frm.pack(fill=tk.X, pady=(0,8))
        hdr = tk.Frame(frm, bg=C["card2"])
        hdr.pack(fill=tk.X)
        tk.Frame(hdr, bg=accent, width=4).pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(hdr, text=f"  {title}", font=FONT_TITLE,
                 bg=C["card2"], fg=C["txt"]).pack(side=tk.LEFT, pady=8, padx=4)
        tk.Frame(frm, bg=C["border"], height=1).pack(fill=tk.X)
        return frm

    # ══════════════════════════════════════════════════════════════
    #  PAGE — PARAMÈTRES
    # ══════════════════════════════════════════════════════════════
    def _build_page_params(self, parent):
        page = tk.Frame(parent, bg=C["bg"])
        self._page_title(page, "⚙  Paramètres de Simulation",
                         "Configurez les paramètres du modèle M/M/1 avec impatience client",
                         accent=C["yellow"])
        body = tk.Frame(page, bg=C["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=22, pady=12)

        s1 = self._section(body, "🔧  Paramètres du Modèle", C["yellow"])
        g1 = tk.Frame(s1, bg=C["card"])
        g1.pack(fill=tk.X, padx=14, pady=(6,14))
        mparams = [
            ("λ  —  Taux d'arrivée",  self.var_lambda,0.01,10.0,0.05,
             "Nombre moyen d'arrivées par unité de temps"),
            ("μ  —  Taux de service", self.var_mu,    0.01,10.0,0.05,
             "Nombre moyen de clients servis par unité de temps"),
            ("θ  —  Impatience",      self.var_theta, 0.0, 10.0,0.05,
             "Taux d'abandon (0 = patience infinie)"),
            ("K  —  Capacité file",   self.var_K,     1,   200, 1,
             "Nombre maximum de clients en attente"),
        ]
        for i,(lbl,var,lo,hi,step,tip) in enumerate(mparams):
            self._param_card(g1, lbl, var, lo, hi, step, tip, row=i//2, col=i%2)
        g1.columnconfigure(0, weight=1); g1.columnconfigure(1, weight=1)

        s2 = self._section(body, "🎲  Paramètres Monte Carlo", C["yellow"])
        g2 = tk.Frame(s2, bg=C["card"])
        g2.pack(fill=tk.X, padx=14, pady=(6,14))
        sparams = [
            ("N_sim  —  Réalisations",self.var_nsim,100, 5000,100,
             "Nombre de simulations indépendantes"),
            ("T_max  —  Durée (ut)",  self.var_tmax,10.0,2000,10,
             "Horizon temporel par réalisation"),
        ]
        for i,(lbl,var,lo,hi,step,tip) in enumerate(sparams):
            self._param_card(g2, lbl, var, lo, hi, step, tip, row=0, col=i)
        g2.columnconfigure(0, weight=1); g2.columnconfigure(1, weight=1)

        s3 = self._section(body, "📐  Stabilité du Système", C["green"])
        f3 = tk.Frame(s3, bg=C["card"])
        f3.pack(fill=tk.X, padx=14, pady=(6,14))
        self.lbl_recap_rho = tk.Label(
            f3, text="ρ = λ/μ = 0.800  ·  ✓  Système STABLE",
            font=("Consolas",12,"bold"), bg=C["card"], fg=C["green"])
        self.lbl_recap_rho.pack(anchor="w", padx=14, pady=(10,4))
        tk.Label(f3, text="Si ρ ≥ 1 et θ = 0, le système diverge — "
                           "les formules M/M/1 théoriques ne sont plus valides.",
                 font=FONT_SMALL, bg=C["card"], fg=C["txt2"],
                 wraplength=740).pack(anchor="w", padx=14, pady=(0,10))
        self.var_lambda.trace_add("write", self._update_recap)
        self.var_mu.trace_add("write",     self._update_recap)

        btn_row = tk.Frame(body, bg=C["bg"])
        btn_row.pack(pady=16)
        self.btn_lancer_p = FlatButton(
            btn_row, "▶   LANCER LA SIMULATION", self._lancer,
            C["btn_run"], C["btn_run_h"],
            width=280, height=48, font=("Segoe UI",12,"bold"))
        self.btn_lancer_p.pack(side=tk.LEFT, padx=8)
        self.btn_reinit_p = FlatButton(
            btn_row, "↺  Réinitialiser", self._reinit,
            "#424242", "#616161", fg="#FFFFFF", width=160, height=48)
        self.btn_reinit_p.pack(side=tk.LEFT, padx=8)

        return page

    def _param_card(self, parent, label, var, lo, hi, step, tip, row, col):
        f = tk.Frame(parent, bg=C["card"],
                     highlightthickness=1, highlightbackground=C["border"])
        f.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        tk.Label(f, text=label, font=FONT_HEAD,
                 bg=C["card"], fg=C["txt"]).pack(anchor="w", padx=14, pady=(12,0))
        tk.Label(f, text=tip, font=("Segoe UI",8),
                 bg=C["card"], fg=C["txt3"]).pack(anchor="w", padx=14)
        tk.Spinbox(
            f, textvariable=var, from_=lo, to=hi, increment=step,
            font=("Consolas",14,"bold"), width=12,
            bg=C["card2"], fg=C["txt"],
            insertbackground=C["txt"],
            buttonbackground=C["border"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=C["border"],
            highlightcolor=C["yellow"]
        ).pack(fill=tk.X, padx=14, pady=(6,14))

    # ══════════════════════════════════════════════════════════════
    #  PAGE — RÉSULTATS
    # ══════════════════════════════════════════════════════════════
    def _build_page_resultats(self, parent):
        page = tk.Frame(parent, bg=C["bg"])
        self._page_title(page, "📊  Résultats de Simulation",
                         "Estimateurs Monte Carlo avec intervalles de confiance à 95%",
                         accent=C["green"])
        body = tk.Frame(page, bg=C["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=22, pady=12)

        s1 = self._section(body, "📐  Indicateurs de Performance", C["green"])
        g  = tk.Frame(s1, bg=C["card"])
        g.pack(fill=tk.X, padx=14, pady=(6,14))
        accents = [C["bar_wq"], C["bar_lq"], C["bar_rho"], C["bar_pa"], C["bar_w"]]
        configs = [
            ("Wq — Temps moyen d'attente en file","⏱"),
            ("Lq — Longueur moyenne de la file",  "👥"),
            ("ρ  — Taux d'occupation du serveur", "⚡"),
            ("Pa — Taux d'abandon",               "🚪"),
            ("W  — Temps total dans le système",  "🕐"),
        ]
        self.cartes = []
        for i,(lbl,ico) in enumerate(configs):
            c = CarteKPI(g, lbl, ico, accent=accents[i])
            c.grid(row=i//2, column=i%2, padx=6, pady=6, sticky="nsew")
            self.cartes.append(c)
        g.columnconfigure(0, weight=1); g.columnconfigure(1, weight=1)

        s2 = self._section(body, "🎯  Qualité de Service", C["yellow"])
        bande = tk.Frame(s2, bg=C["card"])
        bande.pack(fill=tk.X, padx=14, pady=(6,14))
        row_qos = tk.Frame(bande, bg=C["card"])
        row_qos.pack(fill=tk.X, padx=8, pady=6)

        def _box(p, label, var, col):
            f = tk.Frame(p, bg=C["card"],
                         highlightthickness=1, highlightbackground=C["border"])
            f.pack(side=tk.LEFT, padx=(0,10), ipadx=10, ipady=4)
            tk.Label(f, text=label, font=FONT_SMALL,
                     bg=C["card"], fg=C["txt3"]).pack(pady=(8,0))
            tk.Label(f, textvariable=var, font=("Consolas",16,"bold"),
                     bg=C["card"], fg=col).pack(pady=(2,8))

        _box(row_qos, "Score QoS", self.var_score, C["yellow"])

        f_st = tk.Frame(row_qos, bg=C["card"],
                        highlightthickness=1, highlightbackground=C["border"])
        f_st.pack(side=tk.LEFT, padx=(0,10), ipadx=10, ipady=4)
        tk.Label(f_st, text="Statut", font=FONT_SMALL,
                 bg=C["card"], fg=C["txt3"]).pack(pady=(8,0))
        self.lbl_statut = tk.Label(f_st, textvariable=self.var_statut,
                                    font=("Segoe UI",12,"bold"),
                                    bg=C["card"], fg=C["txt2"])
        self.lbl_statut.pack(pady=(2,8))

        f_li = tk.Frame(row_qos, bg=C["card"],
                        highlightthickness=1, highlightbackground=C["border"])
        f_li.pack(side=tk.LEFT, ipadx=10, ipady=4)
        tk.Label(f_li, text="Loi de Little", font=FONT_SMALL,
                 bg=C["card"], fg=C["txt3"]).pack(pady=(8,0))
        tk.Label(f_li, textvariable=self.var_little,
                 font=("Consolas",11,"bold"), bg=C["card"],
                 fg=C["txt"]).pack(pady=(2,8))

        s3 = self._section(body, "⚠  Alertes & Recommandations", C["red"])
        self.frm_alertes = tk.Frame(s3, bg=C["card"])
        self.frm_alertes.pack(fill=tk.X, padx=14, pady=(4,14))
        self.lbl_no_alert = tk.Label(
            self.frm_alertes, text="  Aucune simulation lancée.",
            font=FONT_SMALL, bg=C["card"], fg=C["txt3"])
        self.lbl_no_alert.pack(anchor="w", pady=6)

        return page

    # ══════════════════════════════════════════════════════════════
    #  PAGE — SCORE  (nouvelle page dédiée)
    # ══════════════════════════════════════════════════════════════
    def _build_page_score(self, parent):
        page = tk.Frame(parent, bg=C["bg"])
        self._page_title(page, "🏆  Score de Qualité de Service",
                         "Analyse détaillée du score global et des indicateurs par rapport aux seuils",
                         accent=C["yellow"])

        body = tk.Frame(page, bg=C["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=22, pady=12)

        # Placeholder avant simulation
        self._score_ph = tk.Frame(body, bg=C["card"],
                                   highlightthickness=1,
                                   highlightbackground=C["border"])
        self._score_ph.pack(fill=tk.BOTH, expand=True)
        tk.Label(self._score_ph,
                 text="🏆\n\nLancez une simulation pour afficher\nle score de qualité de service.",
                 font=("Segoe UI",14), bg=C["card"], fg=C["txt3"],
                 justify=tk.CENTER).pack(expand=True)

        # Conteneur du score (rempli après simulation)
        self._score_content = tk.Frame(body, bg=C["bg"])
        # Ne pas le pack pour l'instant

        return page

    def _build_score_content(self):
        """Construit la page Score après réception des résultats."""
        # Vérifier que les données existent
        if self._res is None or self._analyse is None or self._params is None:
            self._log("Données manquantes pour afficher le score.", "warn")
            return

        # Détruire l'ancien contenu
        for w in self._score_content.winfo_children():
            w.destroy()
        self._score_ph.pack_forget()
        self._score_content.pack(fill=tk.BOTH, expand=True)

        res = self._res; an = self._analyse; p = self._params

        # ── Ligne du haut : score global + statut ────────────────
        top = tk.Frame(self._score_content, bg=C["bg"])
        top.pack(fill=tk.X, pady=(0,8))

        # Grand score
        score_val = an.score
        col_score = (C["green"] if score_val >= 80
                     else C["yellow"] if score_val >= 50 else C["red"])
        frm_score = tk.Frame(top, bg=C["card"],
                             highlightthickness=2,
                             highlightbackground=col_score)
        frm_score.pack(side=tk.LEFT, padx=(0,10), ipadx=20, ipady=10)
        tk.Label(frm_score, text="SCORE GLOBAL", font=("Segoe UI",9,"bold"),
                 bg=C["card"], fg=C["txt3"]).pack(pady=(12,0))
        tk.Label(frm_score, text=f"{score_val:.0f}",
                 font=("Consolas",52,"bold"),
                 bg=C["card"], fg=col_score).pack()
        tk.Label(frm_score, text="/ 100",
                 font=("Segoe UI",11), bg=C["card"], fg=C["txt3"]).pack()
        emoji = "🟢" if score_val>=80 else "🟡" if score_val>=50 else "🔴"
        statut_txt = an.statut
        tk.Label(frm_score, text=f"{emoji}  {statut_txt}",
                 font=("Segoe UI",12,"bold"),
                 bg=C["card"], fg=col_score).pack(pady=(4,14))

        # ── Jauge matplotlib (barre de progression) ──────────────
        frm_gauge = tk.Frame(top, bg=C["card"],
                             highlightthickness=1,
                             highlightbackground=C["border"])
        frm_gauge.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipadx=10)
        fig_g = Figure(figsize=(5.5, 2.0), facecolor=C["card"])
        ax_g  = fig_g.add_subplot(1,1,1)
        ax_g.set_facecolor(C["card"])
        # Fond gris
        ax_g.barh(["Score QoS"], [100], color="#EEEEEE", height=0.55, zorder=1)
        # Couleur selon zone
        zones = [(0,50,"#FFCDD2"),(50,80,C["yellow_bg"]),(80,100,C["green_bg"])]
        for x0,x1,col_z in zones:
            ax_g.barh(["Score QoS"], [x1-x0], left=x0,
                      color=col_z, height=0.55, zorder=2)
        # Barre de valeur
        ax_g.barh(["Score QoS"], [score_val], color=col_score,
                  height=0.35, zorder=3)
        # Lignes de seuil
        for sv, slabel in [(50,"50"),(80,"80")]:
            ax_g.axvline(sv, color="#AAAAAA", lw=1.2, ls="--", zorder=4)
            ax_g.text(sv, 0.7, slabel, ha="center", va="bottom",
                      color="#888888", fontsize=8)
        ax_g.text(score_val, 0, f"  {score_val:.0f}",
                  va="center", color=col_score,
                  fontsize=14, fontweight="bold")
        ax_g.set_xlim(0, 110)
        ax_g.set_ylim(-0.6, 1.0)
        ax_g.axis("off")
        fig_g.tight_layout(pad=0.3)
        cv_g = FigureCanvasTkAgg(fig_g, frm_gauge)
        cv_g.draw()
        cv_g.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ── Graphique radar / barres des indicateurs vs seuils ───
        fig_r = Figure(figsize=(11, 4.0), facecolor=C["bg"])
        gs    = gridspec.GridSpec(1, 2, figure=fig_r,
                                  wspace=0.32, left=0.06, right=0.97,
                                  top=0.85, bottom=0.18)

        # -- Graphique 1 : Barres comparatives indicateurs vs seuils
        ax_b = fig_r.add_subplot(gs[0])
        ax_b.set_facecolor(C["plot_bg"])

        indicateurs = ["Wq (ut)", "Lq", "ρ", "Pa (%)"]
        valeurs_sim = [
            res.wq_moy,
            res.lq_moy,
            res.rho_moy,
            res.pa_moy * 100,
        ]
        seuils_ref = [3.0, None, 0.85, 10.0]
        couleurs_b = []
        for val, seuil in zip(valeurs_sim, seuils_ref):
            if seuil is None:
                couleurs_b.append(C["bar_lq"])
            elif val > seuil:
                couleurs_b.append(C["red"])
            elif val > seuil * 0.85:
                couleurs_b.append(C["yellow"])
            else:
                couleurs_b.append(C["green"])

        x_pos = np.arange(len(indicateurs))
        bars  = ax_b.bar(x_pos, valeurs_sim, color=couleurs_b,
                          width=0.5, zorder=3, edgecolor="white", linewidth=1.2)

        # Seuils en pointillés rouges
        for i, s in enumerate(seuils_ref):
            if s is not None:
                ax_b.plot([i-0.3, i+0.3], [s, s],
                          color=C["red"], lw=2.2, ls="--", zorder=4)
                ax_b.text(i+0.32, s, f" Seuil\n {s}",
                          va="center", color=C["red"], fontsize=7.5)

        # Valeurs au-dessus des barres
        for bar, val in zip(bars, valeurs_sim):
            ax_b.text(bar.get_x() + bar.get_width()/2,
                      bar.get_height() + max(valeurs_sim)*0.02,
                      f"{val:.3f}", ha="center", va="bottom",
                      fontsize=9, fontweight="bold", color="#222222")

        ax_b.set_xticks(x_pos)
        ax_b.set_xticklabels(indicateurs, fontsize=9)
        ax_b.tick_params(axis="y", labelsize=8.5, colors="#555555")
        ax_b.tick_params(axis="x", colors="#222222")
        ax_b.yaxis.grid(True, color=C["plot_grid"], linestyle="--", alpha=0.8)
        ax_b.set_axisbelow(True)
        for sp in ax_b.spines.values(): sp.set_color("#DDDDDD")
        ax_b.set_title("Indicateurs vs Seuils de qualité",
                        color=C["txt"], fontsize=10, fontweight="bold", pad=10)

        patches_leg = [
            mpatches.Patch(color=C["green"],  label="✓  Dans la norme"),
            mpatches.Patch(color=C["yellow"], label="⚡  Proche du seuil"),
            mpatches.Patch(color=C["red"],    label="✗  Hors norme"),
        ]
        ax_b.legend(handles=patches_leg, fontsize=8,
                    loc="upper right", facecolor="white",
                    edgecolor="#CCCCCC", framealpha=0.9)

        # -- Graphique 2 : Score par dimension (barres horizontales)
        ax_s = fig_r.add_subplot(gs[1])
        ax_s.set_facecolor(C["plot_bg"])

        dims     = ["Occupation (ρ)", "Abandon (Pa)", "Attente (Wq)", "Little"]
        # Calcul partiel des pénalités (inversées → contribution au score)
        pen_rho  = min(30, 30*max(0, res.rho_moy-0.85)/0.15)
        pen_pa   = min(40, 40*max(0, res.pa_moy/0.10-1)) if res.pa_moy>0.10 else 0
        pen_wq   = min(20, 20*max(0,(res.wq_moy-3.0)/3.0)) if res.wq_moy>3.0 else 0
        pen_lit  = min(10, 10*res.erreur_little_pct/5.0) if res.erreur_little_pct>5 else 0
        max_vals = [30, 40, 20, 10]
        scores_d = [max(0, mv - pen)
                    for mv, pen in zip(max_vals, [pen_rho,pen_pa,pen_wq,pen_lit])]
        pcts     = [s/mv*100 for s, mv in zip(scores_d, max_vals)]

        cols_s = [C["green"] if p>=80 else C["yellow"] if p>=50 else C["red"]
                  for p in pcts]
        y_pos  = np.arange(len(dims))

        ax_s.barh(y_pos, [100]*len(dims), color="#F0F0F0", height=0.5, zorder=1)
        ax_s.barh(y_pos, pcts, color=cols_s, height=0.5, zorder=3,
                  edgecolor="white", linewidth=1)

        for yi, (pct, sc, mx) in enumerate(zip(pcts, scores_d, max_vals)):
            ax_s.text(pct + 1.5, yi, f"{sc:.0f}/{mx}",
                      va="center", fontsize=9, fontweight="bold",
                      color=cols_s[yi])

        ax_s.set_yticks(y_pos)
        ax_s.set_yticklabels(dims, fontsize=9)
        ax_s.set_xlim(0, 115)
        ax_s.set_xlabel("Score par dimension (%)", fontsize=9, color="#555555")
        ax_s.tick_params(axis="x", labelsize=8.5, colors="#555555")
        ax_s.tick_params(axis="y", colors="#222222")
        ax_s.xaxis.grid(True, color=C["plot_grid"], linestyle="--", alpha=0.8)
        ax_s.set_axisbelow(True)
        for sp in ax_s.spines.values(): sp.set_color("#DDDDDD")
        ax_s.axvline(80, color=C["green"], lw=1.4, ls=":", alpha=0.7)
        ax_s.axvline(50, color=C["yellow"],lw=1.4, ls=":", alpha=0.7)
        ax_s.set_title("Score par dimension de qualité",
                        color=C["txt"], fontsize=10, fontweight="bold", pad=10)

        fig_r.suptitle(
            f"Analyse QoS — λ={p['lambda_']}  μ={p['mu']}  "
            f"θ={p['theta']}  K={p['K']}  N_sim={p['N_sim']}",
            color=C["txt2"], fontsize=9, y=0.97)

        frm_charts = tk.Frame(self._score_content, bg=C["bg"],
                              highlightthickness=1,
                              highlightbackground=C["border"])
        frm_charts.pack(fill=tk.BOTH, expand=True)
        cv_r = FigureCanvasTkAgg(fig_r, frm_charts)
        cv_r.draw()
        cv_r.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # ── Alertes compactes ────────────────────────────────────
        if an.alertes or an.recommandations:
            frm_al = tk.Frame(self._score_content, bg=C["bg"])
            frm_al.pack(fill=tk.X, pady=(4,0))
            for a in an.alertes:
                tk.Label(frm_al, text=f"  ✗  {a}", font=FONT_SMALL,
                         bg=C["red_bg"], fg=C["red"],
                         anchor="w").pack(fill=tk.X, padx=4, pady=1)
            for r in an.recommandations:
                tk.Label(frm_al, text=f"  →  {r}", font=FONT_SMALL,
                         bg=C["yellow_bg"], fg=C["txt"],
                         anchor="w").pack(fill=tk.X, padx=4, pady=1)

    # ══════════════════════════════════════════════════════════════
    #  PAGE — GRAPHIQUES
    # ══════════════════════════════════════════════════════════════
    def _build_page_graphiques(self, parent):
        page = tk.Frame(parent, bg=C["bg"])
        self._page_title(page, "📈  Visualisation Graphique",
                         "Histogrammes annotés et nuages de points — N réalisations Monte Carlo",
                         accent=C["green"])

        # Barre téléchargement
        dl = tk.Frame(page, bg=C["card"],
                      highlightthickness=1, highlightbackground=C["border"], pady=7)
        dl.pack(fill=tk.X)
        tk.Label(dl, text="  Exporter :", font=FONT_SMALL,
                 bg=C["card"], fg=C["txt2"]).pack(side=tk.LEFT, padx=(14,8))
        self.btn_dl_png = FlatButton(
            dl, "💾  PNG (200 dpi)", self._dl_png,
            C["btn_ok"], C["btn_ok_h"], width=186, height=30)
        self.btn_dl_png.pack(side=tk.LEFT, padx=4)
        self.btn_dl_pdf = FlatButton(
            dl, "📄  PDF vectoriel", self._dl_pdf,
            C["btn_dl"], C["btn_dl_h"],
            fg=C["txt"], width=168, height=30)
        self.btn_dl_pdf.pack(side=tk.LEFT, padx=4)
        self.btn_dl_all = FlatButton(
            dl, "📦  Tous (PNG)", self._dl_all,
            "#424242", "#616161", fg="#FFFFFF", width=148, height=30)
        self.btn_dl_all.pack(side=tk.LEFT, padx=4)

        # Notebook
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("G.TNotebook", background=C["bg"], borderwidth=0)
        style.configure("G.TNotebook.Tab", background=C["border2"],
                        foreground=C["txt2"], font=FONT_BODY, padding=[14,6])
        style.map("G.TNotebook.Tab",
                  background=[("selected", C["nav_bg"])],
                  foreground=[("selected", "#FFFFFF")])
        self.nb = ttk.Notebook(page, style="G.TNotebook")
        self.nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self._graph_ph = tk.Frame(page, bg=C["card"],
                                   highlightthickness=1,
                                   highlightbackground=C["border"])
        self._graph_ph.pack(fill=tk.BOTH, expand=True)
        tk.Label(self._graph_ph,
                 text="📈\n\nLancez une simulation pour afficher\nles histogrammes et nuages de points.",
                 font=("Segoe UI",14), bg=C["card"], fg=C["txt3"],
                 justify=tk.CENTER).pack(expand=True)
        self.nb.pack_forget()

        return page

    def _build_graph_tabs(self):
        for tab in self.nb.tabs(): self.nb.forget(tab)
        self._figs = {}
        self._graph_ph.pack_forget()
        self.nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        tabs = [
            ("📊  4 Distributions",  self._tab_distributions),
            ("⏱   Wq & W",           self._tab_wq_w),
            ("⚡  ρ vs Pa",           self._tab_rho_pa),
            ("🔗  Loi de Little",     self._tab_little),
        ]
        for label, fn in tabs:
            frm = tk.Frame(self.nb, bg=C["bg"])
            self.nb.add(frm, text=f"  {label}  ")
            fn(frm)

    # ══════════════════════════════════════════════════════════════
    #  PAGE — JOURNAL
    # ══════════════════════════════════════════════════════════════
    def _build_page_journal(self, parent):
        page = tk.Frame(parent, bg=C["bg"])
        self._page_title(page, "📋  Journal d'Exécution",
                         "Historique des opérations et messages système",
                         accent=C["red"])
        outer = tk.Frame(page, bg=C["bg"])
        outer.pack(fill=tk.BOTH, expand=True, padx=22, pady=12)
        ctrl = tk.Frame(outer, bg=C["bg"])
        ctrl.pack(fill=tk.X, pady=(0,6))
        tk.Label(ctrl, text="Historique de simulation",
                 font=FONT_HEAD, bg=C["bg"], fg=C["txt"]).pack(side=tk.LEFT)
        self.btn_clear_log = FlatButton(
            ctrl, "🗑  Effacer", self._clear_log,
            "#424242", "#616161", fg="#FFFFFF", width=110, height=30)
        self.btn_clear_log.pack(side=tk.RIGHT)
        lf = tk.Frame(outer, bg=C["log_bg"],
                      highlightthickness=1, highlightbackground=C["border"])
        lf.pack(fill=tk.BOTH, expand=True)
        self.log = scrolledtext.ScrolledText(
            lf, font=("Consolas",10),
            bg=C["log_bg"], fg="#D4D4D4",
            insertbackground="#FFFFFF",
            selectbackground="#333333",
            relief=tk.FLAT, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.log.tag_config("ok",   foreground="#4EC994")
        self.log.tag_config("warn", foreground="#E8C44A")
        self.log.tag_config("err",  foreground="#F47070")
        self.log.tag_config("info", foreground="#9CDCFE")
        self.log.tag_config("rec",  foreground="#DCDCAA")
        self._log("Simulateur prêt. Configurez les paramètres et lancez.", "info")
        return page

    def _clear_log(self): self.log.delete("1.0", tk.END)

    # ══════════════════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════════════════
    def _rho_live(self, *_):
        try:
            rho = self.var_lambda.get() / self.var_mu.get()
            col = (C["red"] if rho>=0.85 else
                   C["yellow"] if rho>=0.7 else C["green"])
            self.lbl_rho.config(text=f"ρ = {rho:.3f}", fg=col)
        except Exception: pass

    def _update_recap(self, *_):
        try:
            rho   = self.var_lambda.get() / self.var_mu.get()
            theta = self.var_theta.get()
            if rho>=1.0 and theta==0.0:
                t=f"ρ = {rho:.3f}  ·  ⚠  INSTABLE (θ=0)"; c=C["red"]
            elif rho>=0.85:
                t=f"ρ = {rho:.3f}  ·  ⚡  Charge ÉLEVÉE"; c=C["yellow"]
            else:
                t=f"ρ = {rho:.3f}  ·  ✓  Système STABLE"; c=C["green"]
            self.lbl_recap_rho.config(text=t, fg=c)
        except Exception: pass

    def _log(self, msg, tag="info"):
        h = datetime.now().strftime("%H:%M:%S")
        self.log.insert(tk.END, f"[{h}]  {msg}\n", tag)
        self.log.see(tk.END)

    # ══════════════════════════════════════════════════════════════
    #  SIMULATION
    # ══════════════════════════════════════════════════════════════
    def _lancer(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        p = dict(
            lambda_=float(self.var_lambda.get()), mu=float(self.var_mu.get()),
            theta=float(self.var_theta.get()),    K=int(self.var_K.get()),
            N_sim=int(self.var_nsim.get()),      T_max=float(self.var_tmax.get()))
        self._log(
            f"Lancement — λ={p['lambda_']}  μ={p['mu']}  θ={p['theta']}  "
            f"K={p['K']}  N_sim={p['N_sim']}  T_max={p['T_max']}", "info")
        t0 = time.time()
        try:
            vecs = {"wq":[], "lq":[], "rho":[], "pa":[], "w":[]}
            N = int(p["N_sim"])
            for i in range(1, N+1):
                r = simuler_une_realisation(
                    lambda_=p["lambda_"], mu=p["mu"],
                    theta=p["theta"],     K=int(p["K"]), T_max=p["T_max"])
                vecs["wq"].append(r.wq); vecs["lq"].append(r.lq)
                vecs["rho"].append(r.rho); vecs["pa"].append(r.pa)
                vecs["w"].append(r.w)
                if i % 200 == 0:
                    self.after(0, lambda i=i:
                               self.var_prog.set(f"Simulation {i}/{N}…"))
            self.after(0, lambda: self.var_prog.set(""))

            res     = monte_carlo(lambda_=p["lambda_"], mu=p["mu"],
                                  theta=p["theta"], K=int(p["K"]),
                                  N_sim=int(p["N_sim"]), T_max=float(p["T_max"]),
                                  verbose=False)
            analyse = analyser_qualite(res)
            th      = calculer_valeurs_theoriques(p["lambda_"], p["mu"])

            self._res=res; self._analyse=analyse
            self._th=th;   self._params=p; self._raw=vecs

            duree = time.time() - t0
            self.after(0, lambda: self._afficher(res, analyse, th, p))
            tag = {"OK":"ok","ATTENTION":"warn","CRITIQUE":"err"
                   }.get(analyse.statut,"info")
            self._log(
                f"Terminé en {duree:.2f}s — Score : {analyse.score}/100  "
                f"[{analyse.statut}]", tag)
            for a in analyse.alertes:
                self._log(f"  ⚠  {a}", "warn")
            for r in analyse.recommandations:
                self._log(f"  →  {r}", "rec")
        except ValueError as e:
            self._log(f"[ERREUR paramètre] {e}", "err")
        except Exception  as e:
            self._log(f"[ERREUR] {e}", "err")

    def _afficher(self, res, analyse, th, p):
        stb  = th.get("stable", False)
        data = [
            (f"{res.wq_moy:.4f}   IC [{res.wq_ic[0]:.3f} — {res.wq_ic[1]:.3f}]",
             f"{th['Wq_th']:.4f}" if stb else "instable"),
            (f"{res.lq_moy:.4f}   IC [{res.lq_ic[0]:.3f} — {res.lq_ic[1]:.3f}]",
             f"{th['Lq_th']:.4f}" if stb else "instable"),
            (f"{res.rho_moy:.4f}   IC [{res.rho_ic[0]:.3f} — {res.rho_ic[1]:.3f}]",
             f"{th['rho']:.4f}" if stb else f"{p['lambda_']/p['mu']:.3f}"),
            (f"{res.pa_moy:.4f}   ({res.pa_moy*100:.1f}%)", "n/a"),
            (f"{res.w_moy:.4f}   IC [{res.w_ic[0]:.3f} — {res.w_ic[1]:.3f}]",
             f"{th['W_th']:.4f}" if stb else "instable"),
        ]
        flash = {"OK":C["green"],"ATTENTION":C["yellow"],"CRITIQUE":C["red"]
                 }.get(analyse.statut, C["yellow"])
        for carte,(sim,the) in zip(self.cartes, data):
            carte.set_sim(sim); carte.set_th(the); carte.flash(flash)

        self.var_score.set(f"{analyse.score:.0f} / 100")
        self.var_statut.set(f"● {analyse.statut}")
        self.var_little.set(f"écart = {res.erreur_little_pct:.2f}%")
        col_stat = {"OK":C["green"],"ATTENTION":C["yellow"],"CRITIQUE":C["red"]
                    }.get(analyse.statut, C["txt2"])
        self.lbl_statut.configure(fg=col_stat)

        # Alertes page résultats
        for w in self.frm_alertes.winfo_children(): w.destroy()
        if not analyse.alertes and not analyse.recommandations:
            tk.Label(self.frm_alertes,
                     text="  ✓  Qualité de service nominale — aucune alerte.",
                     font=FONT_SMALL, bg=C["card"], fg=C["green"]).pack(anchor="w", pady=6)
        for a in analyse.alertes:
            tk.Label(self.frm_alertes, text=f"  ✗  {a}",
                     font=FONT_SMALL, bg=C["red_bg"], fg=C["red"],
                     wraplength=720, anchor="w").pack(fill=tk.X, pady=1, padx=2)
        for r in analyse.recommandations:
            tk.Label(self.frm_alertes, text=f"  →  {r}",
                     font=FONT_SMALL, bg=C["yellow_bg"], fg=C["txt"],
                     wraplength=720, anchor="w").pack(fill=tk.X, pady=1, padx=2)

        # Construire score + graphiques
        self._build_score_content()
        self._build_graph_tabs()
        self.btn_graph_nav.set_state("normal")
        self.btn_score_nav.set_state("normal")

    # ══════════════════════════════════════════════════════════════
    #  UTILITAIRES MATPLOTLIB
    # ══════════════════════════════════════════════════════════════
    def _embed(self, fig, parent, key):
        self._figs[key] = fig
        cv = FigureCanvasTkAgg(fig, master=parent)
        cv.draw()
        cv.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        tbf = tk.Frame(parent, bg=C["border2"])
        tbf.pack(fill=tk.X)
        if NavigationToolbar2Tk is not None:
            try:
                tb = NavigationToolbar2Tk(cv, tbf)
                try: tb.config(background=C["border2"])
                except Exception: pass
                for ch in tb.winfo_children():
                    try: ch.configure(background=C["border2"])
                    except Exception: pass
                try: tb.update()
                except Exception: pass
            except Exception:
                # Toolbar creation failed; ignore and continue
                pass

    def _ax_style(self, ax, xlabel="", ylabel="", title=""):
        ax.set_facecolor(C["plot_bg"])
        for sp in ax.spines.values(): sp.set_color("#DDDDDD")
        ax.tick_params(colors="#444444", labelsize=9)
        ax.xaxis.grid(True, color=C["plot_grid"], linestyle="--", alpha=0.9, zorder=0)
        ax.yaxis.grid(True, color=C["plot_grid"], linestyle="--", alpha=0.9, zorder=0)
        ax.set_axisbelow(True)
        if xlabel: ax.set_xlabel(xlabel, color="#555555", fontsize=9.5)
        if ylabel: ax.set_ylabel(ylabel, color="#555555", fontsize=9.5)
        if title:  ax.set_title(title, color="#111111",
                                fontsize=10.5, fontweight="bold", pad=9)

    def _histo(self, ax, data, color, bins=30,
               xlabel="", ylabel="Nombre de réalisations", title="",
               th_val=None, th_label="", seuil=None, seuil_label="",
               note=""):
        """
        Histogramme soigné :
        - barres semi-transparentes + contour blanc
        - courbe KDE (si scipy)
        - ligne moyenne noire épaisse avec valeur
        - ligne théorique verte pointillée
        - ligne de seuil rouge pointillée
        - zone colorée IC 95%
        - note explicative en bas
        """
        arr  = np.array(data, dtype=float)
        moy  = arr.mean()
        p025 = np.percentile(arr, 2.5)
        p975 = np.percentile(arr, 97.5)

        # ── Histogramme ──────────────────────────────────────────
        counts, edges, _ = ax.hist(
            arr, bins=bins, color=color, alpha=0.45,
            edgecolor="white", linewidth=0.8, zorder=3,
            label="Réalisations")

        # ── KDE ──────────────────────────────────────────────────
        if HAS_SCIPY and sp_stats is not None and len(np.unique(arr)) > 5:
            try:
                kde   = sp_stats.gaussian_kde(arr)
                kx    = np.linspace(arr.min(), arr.max(), 300)
                ky    = kde(kx) * len(arr) * (edges[1]-edges[0])
                ax.plot(kx, ky, color=color, lw=2.5, zorder=5, label="Densité (KDE)")
            except Exception:
                pass

        # ── Zone IC 95% ──────────────────────────────────────────
        ax.axvspan(p025, p975, color=color, alpha=0.07, zorder=2,
                   label=f"IC 95% [{p025:.3f} — {p975:.3f}]")
        ax.axvline(p025, color=color, lw=0.9, ls="--", alpha=0.5, zorder=4)
        ax.axvline(p975, color=color, lw=0.9, ls="--", alpha=0.5, zorder=4)

        # ── Ligne moyenne ────────────────────────────────────────
        ymax = ax.get_ylim()[1] if ax.get_ylim()[1] > 0 else 1
        ax.axvline(moy, color="#111111", lw=2.2, zorder=6,
                   label=f"Moyenne = {moy:.4f}")
        ax.text(moy, ymax*0.88,
                f" {moy:.4f}", color="#111111",
                fontsize=9, fontweight="bold", va="top")

        # ── Valeur théorique ─────────────────────────────────────
        if th_val is not None:
            ax.axvline(th_val, color=C["green"], lw=2.0, ls="--",
                       zorder=6, label=f"{th_label} = {th_val:.4f}")

        # ── Seuil critique ───────────────────────────────────────
        if seuil is not None:
            ax.axvline(seuil, color=C["red"], lw=2.0, ls=":",
                       zorder=6, label=seuil_label)
            # Zone dépassement
            if moy > seuil:
                xr = ax.get_xlim()[1]
                ax.axvspan(seuil, min(xr, arr.max()*1.1),
                           color=C["red"], alpha=0.06, zorder=1)

        # ── Style ────────────────────────────────────────────────
        self._ax_style(ax, xlabel=xlabel, ylabel=ylabel, title=title)
        ax.legend(fontsize=8, facecolor="white", edgecolor="#DDDDDD",
                  labelcolor="#333333", framealpha=0.95,
                  loc="upper right")

        if note:
            ax.text(0.02, 0.02, note, transform=ax.transAxes,
                    fontsize=7.5, color="#888888", va="bottom")

    # ══════════════════════════════════════════════════════════════
    #  ONGLET 1 — 4 Histogrammes
    # ══════════════════════════════════════════════════════════════
    def _tab_distributions(self, parent):
        key = "distributions"
        raw = self._raw; th = self._th
        if not raw or th is None:
            tk.Label(parent, text="Aucune donnée — lancez une simulation.",
                     font=("Segoe UI",12), bg=C["card"], fg=C["txt3"]).pack(expand=True)
            return
        stb = th.get("stable", False)
        fig = Figure(figsize=(10.8, 5.8), facecolor=C["bg"])
        fig.subplots_adjust(hspace=0.50, wspace=0.28,
                            left=0.07, right=0.97, top=0.91, bottom=0.10)

        specs = [
            (1, raw["wq"],  C["bar_wq"], "Wq (unités de temps)",
             "Wq — Temps d'attente en file",
             th.get("Wq_th") if stb else None, "Wq_th",
             3.0, "Seuil Wq = 3 ut",
             "Plus Wq est faible, plus les clients attendent peu"),
            (2, raw["lq"],  C["bar_lq"], "Lq (nombre de clients)",
             "Lq — Longueur de la file",
             th.get("Lq_th") if stb else None, "Lq_th",
             None, "", "Longueur moyenne de la file d'attente"),
            (3, raw["rho"], C["bar_rho"], "ρ — Taux d'occupation",
             "ρ — Occupation du serveur",
             th.get("rho") if stb else None, "ρ_th",
             0.85, "Seuil ρ = 0.85",
             "Au-dessus de 0.85 : risque de congestion"),
            (4, [v*100 for v in raw["pa"]], C["bar_pa"], "Pa (%)",
             "Pa — Taux d'abandon (%)",
             None, "", 10.0, "Seuil Pa = 10%",
             "Proportion de clients ayant quitté la file"),
        ]
        for pos, data, col, xlabel, title, tv, tl, s, sl, note in specs:
            ax = fig.add_subplot(2, 2, pos)
            self._histo(ax, data, col, xlabel=xlabel, title=title,
                        th_val=tv, th_label=tl,
                        seuil=s, seuil_label=sl, note=note)

        fig.suptitle(
            f"Distributions Monte Carlo  —  N = {len(raw['wq'])} réalisations  "
            f"·  IC 95% en zone ombrée  ·  Ligne noire = moyenne simulée",
            color=C["txt"], fontsize=10, fontweight="bold")
        self._embed(fig, parent, key)

    # ══════════════════════════════════════════════════════════════
    #  ONGLET 2 — Histogrammes Wq & W
    # ══════════════════════════════════════════════════════════════
    def _tab_wq_w(self, parent):
        key = "wq_w"
        raw=self._raw; res=self._res; th=self._th
        if not raw or th is None:
            tk.Label(parent, text="Aucune donnée — lancez une simulation.",
                     font=("Segoe UI",12), bg=C["card"], fg=C["txt3"]).pack(expand=True)
            return
        stb=th.get("stable",False)
        if res is None:
            tk.Label(parent, text="Aucune donnée — lancez une simulation.",
                     font=("Segoe UI",12), bg=C["card"], fg=C["txt3"]).pack(expand=True)
            return
        assert res is not None
        fig = Figure(figsize=(10.8, 5.5), facecolor=C["bg"])
        fig.subplots_adjust(wspace=0.28, left=0.07, right=0.97,
                            top=0.88, bottom=0.12)

        ax1 = fig.add_subplot(1, 2, 1)
        self._histo(ax1, raw["wq"], C["bar_wq"],
                    xlabel="Wq (unités de temps)",
                    ylabel="Nombre de réalisations",
                    title="Wq — Temps d'attente en file",
                    th_val=th.get("Wq_th") if stb else None,
                    th_label="Wq_th (M/M/1)",
                    seuil=3.0, seuil_label="Seuil qualité = 3 ut",
                    note="Un Wq élevé → clients mécontents")

        ax2 = fig.add_subplot(1, 2, 2)
        self._histo(ax2, raw["w"], C["bar_w"],
                    xlabel="W (unités de temps)",
                    ylabel="Nombre de réalisations",
                    title="W — Temps total dans le système",
                    th_val=th.get("W_th") if stb else None,
                    th_label="W_th (M/M/1)",
                    note="W = Wq + temps de service (1/μ)")

        fig.suptitle(
            "Histogrammes Wq & W  ·  Ligne noire = moyenne  "
            "·  Zone ombrée = IC 95%  ·  Pointillé vert = théorique M/M/1",
            color=C["txt"], fontsize=10, fontweight="bold")
        self._embed(fig, parent, key)

    # ══════════════════════════════════════════════════════════════
    #  ONGLET 3 — ρ histogramme + nuage ρ vs Pa
    # ══════════════════════════════════════════════════════════════
    def _tab_rho_pa(self, parent):
        key = "rho_pa"
        raw=self._raw; res=self._res; th=self._th
        if not raw or th is None:
            tk.Label(parent, text="Aucune donnée — lancez une simulation.",
                     font=("Segoe UI",12), bg=C["card"], fg=C["txt3"]).pack(expand=True)
            return
        stb=th.get("stable",False)
        fig = Figure(figsize=(10.8, 5.5), facecolor=C["bg"])
        fig.subplots_adjust(wspace=0.30, left=0.07, right=0.97,
                            top=0.88, bottom=0.12)

        # Histogramme ρ
        ax1 = fig.add_subplot(1, 2, 1)
        self._histo(ax1, raw["rho"], C["bar_rho"],
                    xlabel="ρ",
                    ylabel="Nombre de réalisations",
                    title="Distribution de ρ  (taux d'occupation)",
                    th_val=th.get("rho") if stb else None,
                    th_label="ρ théorique λ/μ",
                    seuil=0.85, seuil_label="Seuil critique ρ = 0.85",
                    note="ρ > 0.85 : risque de saturation")

        # Nuage de points ρ vs Pa
        ax2 = fig.add_subplot(1, 2, 2)
        rho_arr = np.array(raw["rho"])
        pa_arr  = np.array(raw["pa"]) * 100

        # Couleur des points selon criticité
        cols_pts = np.where(pa_arr > 10, C["red"],
                   np.where(pa_arr > 5,  C["yellow"], C["green"]))

        ax2.scatter(rho_arr, pa_arr, c=cols_pts, s=20, alpha=0.40,
                    edgecolors="none", zorder=3)

        # Lignes moyennes annotées
        ax2.axvline(res.rho_moy, color="#333333", lw=1.8, ls="--", zorder=5)
        ax2.text(res.rho_moy, ax2.get_ylim()[1] if ax2.get_ylim()[1]>0 else pa_arr.max()*1.1,
                 f"ρ̄={res.rho_moy:.3f}", ha="left", va="top",
                 color="#333333", fontsize=8.5, fontweight="bold")

        ax2.axhline(res.pa_moy*100, color="#333333", lw=1.8, ls="-.", zorder=5)
        ax2.text(ax2.get_xlim()[1] if ax2.get_xlim()[1]>0 else rho_arr.max()*1.05,
                 res.pa_moy*100,
                 f" P̄a={res.pa_moy*100:.1f}%",
                 va="bottom", color="#333333", fontsize=8.5, fontweight="bold")

        # Lignes de seuil
        ax2.axvline(0.85, color=C["red"], lw=1.6, ls=":", zorder=4)
        ax2.axhline(10.0, color=C["red"], lw=1.6, ls=":", zorder=4)

        # Annotations des zones
        ylim_top = max(pa_arr.max()*1.15, 12)
        ax2.text(0.86, ylim_top*0.95,
                 "Zone\ncritique", color=C["red"],
                 fontsize=8, ha="left", va="top", style="italic")

        patches = [
            mpatches.Patch(color=C["green"],  label="Pa < 5%  ✓  Ok"),
            mpatches.Patch(color=C["yellow"], label="Pa 5–10%  ⚡  Attention"),
            mpatches.Patch(color=C["red"],    label="Pa > 10%  ✗  Critique"),
        ]
        ax2.legend(handles=patches, fontsize=8.5,
                   facecolor="white", edgecolor="#DDDDDD", framealpha=0.95)
        self._ax_style(ax2,
                       xlabel="ρ — Taux d'occupation du serveur",
                       ylabel="Pa (%) — Taux d'abandon",
                       title="Nuage de points : ρ vs Pa")

        fig.suptitle(
            "Occupation & Abandon  ·  Chaque point = 1 réalisation  "
            "·  Couleur = zone de criticité  ·  Lignes = moyennes simulées",
            color=C["txt"], fontsize=10, fontweight="bold")
        self._embed(fig, parent, key)

    # ══════════════════════════════════════════════════════════════
    #  ONGLET 4 — Loi de Little : nuage + histogramme écarts
    # ══════════════════════════════════════════════════════════════
    def _tab_little(self, parent):
        key = "little"
        raw=self._raw; res=self._res; p=self._params
        if not raw or res is None or p is None:
            tk.Label(parent, text="Aucune donnée — lancez une simulation.",
                     font=("Segoe UI",12), bg=C["card"], fg=C["txt3"]).pack(expand=True)
            return
        fig = Figure(figsize=(10.8, 5.5), facecolor=C["bg"])
        fig.subplots_adjust(wspace=0.30, left=0.07, right=0.97,
                            top=0.88, bottom=0.12)

        lq_arr  = np.array(raw["lq"])
        wq_arr  = np.array(raw["wq"])
        pa_arr  = np.array(raw["pa"])
        lam_eff = p["lambda_"] * (1.0 - pa_arr)
        lq_lit  = lam_eff * wq_arr
        ecarts  = np.abs(lq_arr - lq_lit) / np.maximum(lq_arr, 1e-9) * 100

        cols_pts = np.where(ecarts > 10, C["red"],
                   np.where(ecarts > 5,  C["yellow"], C["green"]))

        # Nuage Lq_sim vs Lq_Little
        ax1 = fig.add_subplot(1, 2, 1)
        ax1.scatter(lq_lit, lq_arr, c=cols_pts, s=20,
                    alpha=0.40, edgecolors="none", zorder=3)

        vmax = max(float(lq_arr.max()), float(lq_lit.max())) * 1.22 + 0.05
        xs   = np.linspace(0, vmax, 200)
        # Zone ±5%
        ax1.fill_between(xs, xs*0.95, xs*1.05,
                         color=C["green"], alpha=0.10,
                         label="Zone ±5%  (tolérance)")
        # Diagonale idéale
        ax1.plot(xs, xs, color=C["green"], ls="--", lw=2.2,
                 label="Idéal : Lq_sim = Lq_Little", zorder=4)
        # Point moyen
        lq_lit_moy = p["lambda_"] * (1-res.pa_moy) * res.wq_moy
        ax1.scatter([lq_lit_moy], [res.lq_moy],
                    s=160, color=C["yellow"],
                    edgecolors="#333333", linewidths=2.5, zorder=6,
                    label=f"Moy. simulée  (écart {res.erreur_little_pct:.2f}%)")

        # Annotation de l'écart
        ax1.annotate(
            f"Écart = {res.erreur_little_pct:.2f}%",
            xy=(lq_lit_moy, res.lq_moy),
            xytext=(lq_lit_moy + vmax*0.12, res.lq_moy + vmax*0.10),
            fontsize=9, color="#333333",
            arrowprops=dict(arrowstyle="->", color="#333333", lw=1.5),
            bbox=dict(boxstyle="round,pad=0.3", fc="white",
                      ec="#CCCCCC", alpha=0.9))

        ax1.set_xlim(0, vmax); ax1.set_ylim(0, vmax)
        self._ax_style(ax1,
                       xlabel="Lq prédit par Little  =  λ_eff × Wq",
                       ylabel="Lq simulé  (Monte Carlo)",
                       title="Loi de Little : Lq simulé vs Lq prédit")
        ax1.legend(fontsize=8.5, facecolor="white",
                   edgecolor="#DDDDDD", framealpha=0.95)
        ax1.text(0.02, 0.02,
                 "Si le point moyen est proche de la diagonale → loi de Little vérifiée",
                 transform=ax1.transAxes, fontsize=7.5, color="#888888", va="bottom")

        # Histogramme des écarts relatifs
        ax2 = fig.add_subplot(1, 2, 2)
        self._histo(ax2, ecarts, "#7B1FA2", bins=28,
                    xlabel="Écart relatif |Lq_sim – Lq_Little| / Lq_sim  (%)",
                    ylabel="Nombre de réalisations",
                    title="Distribution des écarts à Little",
                    seuil=5.0, seuil_label="Seuil acceptable = 5%",
                    note="Majorité sous 5% → convergence correcte")

        fig.suptitle(
            "Validation — Loi de Little  ·  Lq = λ_eff × Wq  "
            "·  Point jaune = moyenne  ·  Vert = zone ±5%",
            color=C["txt"], fontsize=10, fontweight="bold")
        self._embed(fig, parent, key)

    # ══════════════════════════════════════════════════════════════
    #  TÉLÉCHARGEMENT
    # ══════════════════════════════════════════════════════════════
    def _fig_active(self):
        try:
            idx  = self.nb.index(self.nb.select())
            keys = ["distributions","wq_w","rho_pa","little"]
            return self._figs.get(keys[idx])
        except Exception: return None

    def _dl_png(self):
        fig = self._fig_active()
        if not fig:
            messagebox.showwarning("Aucun graphique","Lancez d'abord une simulation."); return
        path = filedialog.asksaveasfilename(
            defaultextension=".png", title="Enregistrer en PNG",
            filetypes=[("PNG image","*.png"),("Tous","*.*")],
            initialfile=f"mm1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        if path:
            fig.savefig(path, dpi=200, bbox_inches="tight",
                        facecolor=fig.get_facecolor())
            messagebox.showinfo("✓ Enregistré", f"PNG sauvegardé :\n{path}")
            self._log(f"PNG : {path}", "ok")

    def _dl_pdf(self):
        fig = self._fig_active()
        if not fig:
            messagebox.showwarning("Aucun graphique","Lancez d'abord une simulation."); return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", title="Enregistrer en PDF",
            filetypes=[("PDF vectoriel","*.pdf"),("Tous","*.*")],
            initialfile=f"mm1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        if path:
            fig.savefig(path, bbox_inches="tight",
                        facecolor=fig.get_facecolor())
            messagebox.showinfo("✓ Enregistré", f"PDF sauvegardé :\n{path}")
            self._log(f"PDF : {path}", "ok")

    def _dl_all(self):
        if not self._figs:
            messagebox.showwarning("Aucun graphique","Lancez d'abord une simulation."); return
        folder = filedialog.askdirectory(title="Dossier de destination")
        if not folder: return
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        noms = {"distributions":"distributions","wq_w":"wq_w",
                "rho_pa":"rho_pa","little":"little"}
        saved = []
        for key, fig in self._figs.items():
            path = os.path.join(folder, f"mm1_{noms.get(key,key)}_{ts}.png")
            fig.savefig(path, dpi=200, bbox_inches="tight",
                        facecolor=fig.get_facecolor())
            saved.append(path)
        messagebox.showinfo("✓ Exporté",
                            f"{len(saved)} graphique(s) dans :\n{folder}")
        self._log(f"{len(saved)} graphiques exportés → {folder}", "ok")

    # ══════════════════════════════════════════════════════════════
    #  RESET
    # ══════════════════════════════════════════════════════════════
    def _reinit(self):
        self.var_lambda.set(0.8); self.var_mu.set(1.0)
        self.var_theta.set(0.2);  self.var_K.set(10)
        self.var_nsim.set(1000);  self.var_tmax.set(200.0)
        for c in self.cartes: c.reset()
        self.var_score.set("—"); self.var_statut.set("En attente")
        self.var_little.set("—")
        self.lbl_statut.configure(fg=C["txt2"])
        self.btn_graph_nav.set_state("disabled")
        self.btn_score_nav.set_state("disabled")
        self._res=None; self._figs={}; self._raw={}
        self.nb.pack_forget()
        self._graph_ph.pack(fill=tk.BOTH, expand=True)
        # Reset score
        self._score_content.pack_forget()
        self._score_ph.pack(fill=tk.BOTH, expand=True)
        for w in self.frm_alertes.winfo_children(): w.destroy()
        tk.Label(self.frm_alertes, text="  Aucune simulation lancée.",
                 font=FONT_SMALL, bg=C["card"],
                 fg=C["txt3"]).pack(anchor="w", pady=6)
        self._log("Interface réinitialisée.", "info")


# ── Point d'entrée ───────────────────────────────────────────────
if __name__ == "__main__":
    app = SimulateurApp()
    app.mainloop()
