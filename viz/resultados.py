"""Aba "Resultados": gráficos do experimento lidos de resultados.json (desenhados em tk.Canvas)."""
from __future__ import annotations

import json
import math
import os
import statistics as st
import tkinter as tk
from tkinter import ttk

from viz.comum import (COR, F_NEG, F_NORM, F_PEQ, F_TIT, Eixos, fmt, fmt_pct, potencias_10, rotulo_pot10)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADVERSARIOS = ["Aleatório", "AlfaBeta-d2", "AlfaBeta-d4", "AlfaBeta-d6"]
COR_VED = {"V": "#1a9e5a", "E": "#9aa3ad", "D": "#d7263d"}


def _quantil(xs, q):
    xs = sorted(xs)
    if not xs:
        return 0
    pos = q * (len(xs) - 1)
    i = int(pos)
    f = pos - i
    return xs[i] if i + 1 >= len(xs) else xs[i] * (1 - f) + xs[i + 1] * f


class AbaResultados(ttk.Frame):
    def __init__(self, mestre, app):
        super().__init__(mestre, padding=8)
        self.app = app
        try:
            with open(os.path.join(RAIZ, "resultados.json"), encoding="utf-8") as f:
                self.r = json.load(f)
        except OSError as e:
            ttk.Label(self, text=f"resultados.json não encontrado ({e}). Rode python3 experimento.py.").pack()
            self.r = None
            return
        topo = ttk.Frame(self)
        topo.pack(fill="x")
        ttk.Label(topo, text="AlfaBeta-d8 contra as linhas de base · custo em nós visitados", font=F_TIT).pack(
            side="left")
        self.var_lado = tk.StringVar(value="todos")
        for t in ("todos", "começando (X)", "em segundo (O)"):
            ttk.Radiobutton(topo, text=t, value=t, variable=self.var_lado, command=self.desenhar).pack(side="right")
        ttk.Label(topo, text="partidas:").pack(side="right", padx=4)
        self.cv = tk.Canvas(self, bg=COR["painel"], highlightthickness=1, highlightbackground=COR["borda"])
        self.cv.pack(fill="both", expand=True, pady=(6, 0))
        self.cv.bind("<Configure>", lambda e: self.desenhar())
        self.cv.bind("<Motion>", self._dica)
        self.dicas = []

    # ------------------------------------------------------------------
    def _partidas(self, nome):
        ps = self.r["partidas"][nome]
        lado = self.var_lado.get()
        if lado == "todos":
            return ps
        return [p for p in ps if p["avaliado_comeca"] == (lado == "começando (X)")]

    def desenhar(self):
        if self.r is None:
            return
        cv = self.cv
        cv.delete("all")
        self.dicas = []
        W, H = max(cv.winfo_width(), 900), max(cv.winfo_height(), 600)
        m = 70
        meio_x, meio_y = W / 2, H / 2
        self._ved(m, 50, meio_x - 30, meio_y - 40)
        self._caixas(meio_x + m, 50, W - 30, meio_y - 40)
        self._ordenacao(m, meio_y + 50, meio_x - 30, H - 50)
        self._duracao(meio_x + m, meio_y + 50, W - 30, H - 50)

    def _ved(self, x0, y0, x1, y1):
        cv = self.cv
        ax = Eixos(cv, x0 + 40, y0, x1, y1, (0, 1), (0, len(ADVERSARIOS)))
        cv.create_text(x0 - 30, y0 - 26, anchor="sw", font=F_NEG, fill=COR["texto"],
                       text="Vitória / empate / derrota do d8 (barra preta: IC 95% de Wilson da taxa de vitória)")
        ax.ticks_x([0, 0.25, 0.5, 0.75, 1], rotulo=lambda v: fmt_pct(v, 0), grade=True)
        bh = (y1 - y0) / len(ADVERSARIOS) * 0.6
        for i, nome in enumerate(ADVERSARIOS):
            ps = self._partidas(nome)
            n = len(ps)
            cont = {k: sum(p["resultado"] == k for p in ps) for k in "VED"}
            yc = y0 + (i + 0.5) * (y1 - y0) / len(ADVERSARIOS)
            cv.create_text(x0 + 34, yc, anchor="e", text=nome.replace("AlfaBeta-", "vs "), font=F_NORM,
                           fill=COR["texto"])
            cv.create_text(x0 + 34, yc + 14, anchor="e", text=f"n = {n}", font=F_PEQ, fill=COR["suave"])
            acc = 0
            for k in "VED":
                fr = cont[k] / n if n else 0
                if fr:
                    a, b = ax.X(acc), ax.X(acc + fr)
                    it = cv.create_rectangle(a, yc - bh / 2, b, yc + bh / 2, fill=COR_VED[k], outline="white")
                    if b - a > 26:
                        cv.create_text((a + b) / 2, yc, text=str(cont[k]), fill="white", font=F_NEG)
                    self.dicas.append((it, f"{nome}: {k} = {cont[k]} de {n} ({fmt_pct(fr)})"))
                acc += fr
            lo, hi = _wilson(cont["V"], n)
            cv.create_line(ax.X(lo), yc - bh / 2 - 6, ax.X(hi), yc - bh / 2 - 6, width=2, fill=COR["texto"])
            for v in (lo, hi):
                cv.create_line(ax.X(v), yc - bh / 2 - 10, ax.X(v), yc - bh / 2 - 2, width=2, fill=COR["texto"])
            pts = (cont["V"] + 0.5 * cont["E"]) / n if n else 0
            cv.create_text(x1 + 4, yc, anchor="w", text=f"{pts:.2f}".replace(".", ","), font=F_PEQ, fill=COR["suave"])
        cv.create_text(x1 + 4, y0 - 6, anchor="sw", text="pontos", font=F_PEQ, fill=COR["suave"])
        lx = x0 + 40
        for k, t in (("V", "vitória"), ("E", "empate"), ("D", "derrota")):
            cv.create_rectangle(lx, y1 + 26, lx + 12, y1 + 38, fill=COR_VED[k], outline="")
            cv.create_text(lx + 16, y1 + 32, anchor="w", text=t, font=F_PEQ, fill=COR["texto"])
            lx += 80

    def _caixas(self, x0, y0, x1, y1):
        cv = self.cv
        ax = Eixos(cv, x0, y0, x1, y1, (0, len(ADVERSARIOS)), (10, 3e6), logy=True)
        cv.create_text(x0 - 60, y0 - 26, anchor="sw", font=F_NEG, fill=COR["texto"],
                       text="Nós visitados por lance do d8 (escala log): caixa = quartis, bigodes = mín…p95, ◆ = máx")
        ax.ticks_y(potencias_10(10, 3e6), rotulo=rotulo_pot10)
        ax.moldura()
        w = (x1 - x0) / len(ADVERSARIOS) * 0.36
        for i, nome in enumerate(ADVERSARIOS):
            xs = [n for p in self._partidas(nome) for n in p["nos"]["avaliado"]]
            if not xs:
                continue
            q1, med, q3 = _quantil(xs, .25), _quantil(xs, .5), _quantil(xs, .75)
            p95, mn, mx = _quantil(xs, .95), min(xs), max(xs)
            media = st.mean(xs)
            xc = ax.X(i + 0.5)
            cv.create_line(xc, ax.Y(max(mn, 10)), xc, ax.Y(q1), fill=COR["suave"])
            cv.create_line(xc, ax.Y(q3), xc, ax.Y(p95), fill=COR["suave"])
            for v in (max(mn, 10), p95):
                cv.create_line(xc - w / 3, ax.Y(v), xc + w / 3, ax.Y(v), fill=COR["suave"])
            it = cv.create_rectangle(xc - w, ax.Y(q3), xc + w, ax.Y(q1), fill="#dbe6f6", outline=COR["max"])
            cv.create_line(xc - w, ax.Y(med), xc + w, ax.Y(med), fill=COR["max"], width=3)
            ym = ax.Y(mx)
            cv.create_polygon(xc, ym - 5, xc + 5, ym, xc, ym + 5, xc - 5, ym, fill=COR["ruim"])
            cv.create_text(xc + 8, ym, anchor="w", text=fmt(mx), font=F_PEQ, fill=COR["ruim"])
            cv.create_text(xc + w + 4, ax.Y(med), anchor="w", text=fmt(round(med)), font=F_PEQ, fill=COR["max"])
            y_med = ax.Y(media)
            cv.create_line(xc - w, y_med, xc + w, y_med, fill=COR["destaque"], dash=(3, 2), width=2)
            self.dicas.append((it, f"{nome}: {len(xs)} lances · média {fmt(round(media))} · mediana {fmt(round(med))}"
                                   f" · p95 {fmt(round(p95))} · máx {fmt(mx)}"))
            adv = [n for p in self._partidas(nome) for n in p["nos"]["adversario"]]
            cv.create_text(xc, y1 + 8, anchor="n", text=nome.replace("AlfaBeta-", "vs "), font=F_NORM, fill=COR["texto"])
            cv.create_text(xc, y1 + 24, anchor="n", font=F_PEQ, fill=COR["suave"],
                           text=f"adversário: {fmt(round(st.mean(adv))) if adv else 0} nós/lance")
        cv.create_line(x1 - 150, y0 - 6, x1 - 130, y0 - 6, fill=COR["destaque"], dash=(3, 2), width=2)
        cv.create_text(x1 - 126, y0 - 6, anchor="w", text="média", font=F_PEQ, fill=COR["texto"])
        cv.create_line(x1 - 80, y0 - 6, x1 - 60, y0 - 6, fill=COR["max"], width=3)
        cv.create_text(x1 - 56, y0 - 6, anchor="w", text="mediana", font=F_PEQ, fill=COR["texto"])

    def _ordenacao(self, x0, y0, x1, y1):
        cv = self.cv
        o = self.r["agregado"]["_ordenacao"]
        pares = o.get("por_posicao")
        lado = min(x1 - x0, y1 - y0)
        x1 = x0 + lado
        y1 = y0 + lado
        ax = Eixos(cv, x0, y0, x1, y1, (50, 1e6), (50, 1e6), logx=True, logy=True)
        cv.create_text(x0 - 60, y0 - 26, anchor="sw", font=F_NEG, fill=COR["texto"],
                       text=f"Ordenação centro-primeiro: {o['posicoes']} posições, d8 (cada ponto = 1 posição)")
        ax.ticks_y(potencias_10(100, 1e6), rotulo=rotulo_pot10)
        ax.ticks_x(potencias_10(100, 1e6), rotulo=rotulo_pot10, grade=True)
        ax.moldura(xlabel="nós SEM ordenação", ylabel="nós COM")
        cv.create_line(ax.X(50), ax.Y(50), ax.X(1e6), ax.Y(1e6), fill=COR["suave"], dash=(4, 3))
        cv.create_text(ax.X(3e5), ax.Y(3e5) - 6, text="y = x", anchor="se", font=F_PEQ, fill=COR["suave"])
        if not pares:
            cv.create_text((x0 + x1) / 2, (y0 + y1) / 2, text="rode experimento.py para obter os dados por posição",
                           font=F_PEQ, fill=COR["suave"])
            return
        pior = 0
        for com, sem in pares:
            acima = com > sem
            pior += acima
            cor = COR["ruim"] if acima else COR["max"]
            x, y = ax.X(max(sem, 50)), ax.Y(max(com, 50))
            cv.create_oval(x - 3, y - 3, x + 3, y + 3, fill=cor, outline="", stipple="" if acima else "")
        tx = x1 + 16
        razao = f"{o['razao_com_sem']['mediana']:.2f}".replace(".", ",")
        cv.create_text(tx, y0 + 10, anchor="nw", font=F_NORM, fill=COR["texto"], width=170,
                       text=(f"média com: {fmt(round(o['com']['media']))}\nmédia sem: {fmt(round(o['sem']['media']))}\n\n"
                             f"mediana com: {fmt(round(o['com']['mediana']))}\nmediana sem: {fmt(round(o['sem']['mediana']))}\n\n"
                             f"razão com/sem (mediana): {razao}\n\n"
                             + f"pontos vermelhos (acima da diagonal): {pior} posições em que ordenar custou MAIS\n\n"
                             f"mesmo valor na raiz: {'sim' if o['mesmos_valores'] else 'NÃO'}"))

    def _duracao(self, x0, y0, x1, y1):
        cv = self.cv
        ax = Eixos(cv, x0, y0, x1, y1, (6, 43), (0, 1))
        cv.create_text(x0 - 60, y0 - 26, anchor="sw", font=F_NEG, fill=COR["texto"],
                       text="Duração das partidas: fração acumulada de partidas terminadas até n peças")
        ax.ticks_x([7, 14, 21, 28, 35, 42], rotulo=str, grade=True)
        ax.ticks_y([0, .25, .5, .75, 1], rotulo=lambda v: fmt_pct(v, 0))
        ax.moldura(xlabel="peças no tabuleiro ao fim da partida")
        cores = ["#8a8f98", "#2b6cb0", "#9b2c8f", "#ff7a00"]
        for i, nome in enumerate(ADVERSARIOS):
            js = sorted(p["jogadas"] for p in self._partidas(nome))
            if not js:
                continue
            pts = [(ax.X(7), ax.Y(0))]
            for n in range(7, 43):
                f = sum(j <= n for j in js) / len(js)
                pts += [(ax.X(n), pts[-1][1]), (ax.X(n), ax.Y(f))]
            cv.create_line(*[c for p in pts for c in p], fill=cores[i], width=2)
            cv.create_text(x0 + 70, y0 + (y1 - y0) * 0.32 + i * 16, anchor="w", fill=cores[i], font=F_NEG,
                           text=f"{nome.replace('AlfaBeta-', 'vs ')}: mediana {_quantil(js, .5):.0f}")
        empates = sum(p["jogadas"] == 42 and p["resultado"] == "E" for n in ADVERSARIOS for p in self._partidas(n))
        cv.create_text(x0 + 70, y0 + (y1 - y0) * 0.32 + 4 * 16, anchor="w", font=F_PEQ, fill=COR["suave"],
                       text=f"{empates} partidas terminaram empatadas com 42 peças")

    def _dica(self, ev):
        cv = self.cv
        cv.delete("dica")
        itens = cv.find_overlapping(ev.x, ev.y, ev.x, ev.y)
        for it, txt in self.dicas:
            if it in itens:
                t = cv.create_text(ev.x + 12, ev.y + 12, anchor="nw", text=txt, font=F_PEQ, tags="dica")
                b = cv.bbox(t)
                r = cv.create_rectangle(b[0] - 4, b[1] - 3, b[2] + 4, b[3] + 3, fill="#fffbe6", outline=COR["borda"],
                                        tags="dica")
                cv.tag_raise(t, r)
                return


def _wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - m), min(1.0, c + m))
