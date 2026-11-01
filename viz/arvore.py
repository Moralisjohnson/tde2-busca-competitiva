"""Aba "Árvore alfa-beta": animação passo a passo da busca, com janelas α/β, podas e a comparação
com a árvore completa do Minimax."""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk

from busca import Avaliacao, Contador, alfabeta, minimax, ordem_centro
from lig4 import MAX, Lig4
from rastreio import Rastro, alfabeta_rastreado, contar_minimax, estado_de_lances, minimax_rastreado
from viz.comum import COR, F_NEG, F_NORM, F_PEQ, F_TIT, fmt, mini_tabuleiro

LIMITE_NOS = 2500

# nome -> (linhas, colunas, k, lances desde s0, profundidade (None = completa))
PRESETS = {
    "Meio de jogo 6×7, corte em d = 3 (AVAL)": (6, 7, 4, "33244", 3),
    "Meio de jogo 6×7, corte em d = 2 (AVAL)": (6, 7, 4, "3324", 2),
    "Final 6×7, 6 casas vazias, profundidade completa": (6, 7, 4, "154123621122324613621446660035540005", None),
    "Final 6×7, 8 casas vazias, profundidade completa": (6, 7, 4, "4321422020015004526036426411146663", None),
    "Lig 3 em 3×4 (K = 3), profundidade completa": (3, 4, 3, "1123", None),
    "Lig 3 em 4×4 (K = 3), profundidade completa": (4, 4, 3, "01332320", None),
    "Posição atual da aba Jogar": None,
}
PROFS = ["completa", "1", "2", "3", "4", "5", "6"]


def _txt(v):
    if v is None:
        return ""
    if v == math.inf:
        return "+∞"
    if v == -math.inf:
        return "−∞"
    return f"{v:+d}" if v else "0"


def _caminho(c):
    return "raiz" if not c else "→".join(map(str, c))


class AbaArvore(ttk.Frame):
    def __init__(self, mestre, app):
        super().__init__(mestre, padding=8)
        self.app = app
        self.posicao_externa = None   # (jogo, estado) vindo da aba Jogar
        self.tocando = False
        self.i = 0                    # número de eventos já aplicados
        self.dados = None
        self.selecionado = None
        self._montar()
        self.construir()

    # ------------------------------------------------------------------ interface
    def _montar(self):
        topo = ttk.Frame(self)
        topo.pack(fill="x")
        ttk.Label(topo, text="Posição").pack(side="left")
        self.var_preset = tk.StringVar(value=next(iter(PRESETS)))
        cb = ttk.Combobox(topo, textvariable=self.var_preset, values=list(PRESETS), state="readonly", width=46)
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self._preset_mudou())
        ttk.Label(topo, text="Profundidade").pack(side="left", padx=(10, 0))
        self.var_prof = tk.StringVar(value="3")
        ttk.Combobox(topo, textvariable=self.var_prof, values=PROFS, state="readonly", width=8).pack(side="left", padx=4)
        self.var_ordem = tk.BooleanVar(value=True)
        ttk.Checkbutton(topo, text="ordenação centro-primeiro", variable=self.var_ordem).pack(side="left", padx=8)
        ttk.Button(topo, text="Construir árvore", command=self.construir).pack(side="left", padx=4)

        ctl = ttk.Frame(self)
        ctl.pack(fill="x", pady=6)
        for txt, cmd in (("⏮", self.inicio), ("◀ passo", self.voltar), ("▶ tocar", self.tocar),
                         ("passo ▶", self.avancar), ("próxima poda ✂", self.ate_poda), ("⏭", self.fim)):
            b = ttk.Button(ctl, text=txt, command=cmd, width=len(txt) + 2)
            b.pack(side="left", padx=1)
            if txt.startswith("▶"):
                self.bt_tocar = b
        ttk.Label(ctl, text="  velocidade").pack(side="left")
        self.var_vel = tk.DoubleVar(value=8)
        ttk.Scale(ctl, from_=1, to=60, variable=self.var_vel, length=140).pack(side="left", padx=4)
        self.var_linha = tk.DoubleVar(value=0)
        self.escala = ttk.Scale(ctl, from_=0, to=1, variable=self.var_linha, command=self._arrastar)
        self.escala.pack(side="left", fill="x", expand=True, padx=8)
        self.lb_pos = ttk.Label(ctl, text="", width=16)
        self.lb_pos.pack(side="left")

        corpo = ttk.Frame(self)
        corpo.pack(fill="both", expand=True)
        lado = ttk.Frame(corpo, width=330)
        lado.pack(side="right", fill="y", padx=(8, 0))
        lado.pack_propagate(False)

        quadro = ttk.Frame(corpo)
        quadro.pack(side="left", fill="both", expand=True)
        self.cv = tk.Canvas(quadro, bg=COR["painel"], highlightthickness=1, highlightbackground=COR["borda"])
        sx = ttk.Scrollbar(quadro, orient="horizontal", command=self.cv.xview)
        sy = ttk.Scrollbar(quadro, orient="vertical", command=self.cv.yview)
        self.cv.configure(xscrollcommand=sx.set, yscrollcommand=sy.set)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        self.cv.pack(side="left", fill="both", expand=True)
        self.cv.bind("<Configure>", lambda e: self._relayout_se_preciso())
        self.cv.bind("<Shift-MouseWheel>", lambda e: self.cv.xview_scroll(-1 * (e.delta // 120 or 1), "units"))
        self.cv.bind("<Shift-Button-4>", lambda e: self.cv.xview_scroll(-3, "units"))
        self.cv.bind("<Shift-Button-5>", lambda e: self.cv.xview_scroll(3, "units"))

        ttk.Label(lado, text="Custo (nós visitados)", font=F_TIT).pack(anchor="w")
        self.cv_cont = tk.Canvas(lado, width=320, height=150, bg=COR["fundo"], highlightthickness=0)
        self.cv_cont.pack(anchor="w")
        ttk.Label(lado, text="Evento atual", font=F_NEG).pack(anchor="w", pady=(6, 0))
        self.lb_evento = tk.Message(lado, text="", width=315, font=F_NORM, bg=COR["fundo"], fg=COR["texto"],
                                    anchor="nw", justify="left")
        self.lb_evento.pack(anchor="w", fill="x")
        self.lb_banner = tk.Message(lado, text="", width=315, font=F_NEG, bg=COR["fundo"], anchor="nw")
        self.lb_banner.pack(anchor="w", fill="x", pady=(6, 0))
        ttk.Label(lado, text="Nó selecionado (clique na árvore)", font=F_NEG).pack(anchor="w", pady=(8, 0))
        self.cv_mini = tk.Canvas(lado, width=320, height=210, bg=COR["fundo"], highlightthickness=0)
        self.cv_mini.pack(anchor="w")
        leg = tk.Canvas(lado, width=320, height=92, bg=COR["fundo"], highlightthickness=0)
        leg.pack(anchor="w", side="bottom")
        self._legenda(leg)

    def _legenda(self, cv):
        itens = [("max", "MAX (X joga)"), ("min", "MIN (O joga)"), ("folha", "folha (terminal ou AVAL)"),
                 ("ativo", "na pilha (mostra α, β)"), ("poda", "podado: alfa-beta não visita")]
        for i, (k, t) in enumerate(itens):
            x, y = 8 + (i % 2) * 160, 10 + (i // 2) * 26
            if k == "max":
                cv.create_polygon(x, y + 12, x + 7, y, x + 14, y + 12, fill=COR["max"], outline="")
            elif k == "min":
                cv.create_polygon(x, y, x + 7, y + 12, x + 14, y, fill=COR["min"], outline="")
            elif k == "folha":
                cv.create_rectangle(x + 1, y + 1, x + 13, y + 13, fill="#555", outline="")
            elif k == "ativo":
                cv.create_oval(x - 1, y - 1, x + 15, y + 15, outline=COR["destaque"], width=3)
            else:
                cv.create_rectangle(x + 1, y + 1, x + 13, y + 13, fill="", outline=COR["poda"], dash=(2, 2))
            cv.create_text(x + 20, y + 7, text=t, anchor="w", font=F_PEQ, fill=COR["texto"])

    # ------------------------------------------------------------------ construção
    def usar_posicao(self, jogo, s):
        self.posicao_externa = (jogo, s)
        self.var_preset.set("Posição atual da aba Jogar")
        if self.var_prof.get() == "completa" and sum(s.alturas) < jogo.linhas * jogo.colunas - 9:
            self.var_prof.set("3")
        self.construir()

    def _preset_mudou(self):
        p = PRESETS[self.var_preset.get()]
        if p is not None:
            self.var_prof.set("completa" if p[4] is None else str(p[4]))
        else:
            self.var_prof.set("3")
        self.construir()

    def _posicao(self):
        p = PRESETS[self.var_preset.get()]
        if p is None:
            if self.posicao_externa is None:
                aba = self.app.aba_jogar
                return aba.jogo, aba.s
            return self.posicao_externa
        jogo = Lig4(p[0], p[1], p[2])
        return jogo, estado_de_lances(jogo, [int(c) for c in p[3]])

    def construir(self):
        self.parar()
        jogo, s = self._posicao()
        prof = None if self.var_prof.get() == "completa" else int(self.var_prof.get())
        ordem = ordem_centro(jogo) if self.var_ordem.get() else None
        aval = Avaliacao(jogo)
        n = contar_minimax(jogo, s, prof, limite=LIMITE_NOS)
        if n > LIMITE_NOS:
            self.dados = None
            self.cv.delete("all")
            self.cv.create_text(20, 20, anchor="nw", font=F_NEG, fill=COR["ruim"],
                                text=f"A árvore Minimax desta posição tem mais de {fmt(LIMITE_NOS)} nós: grande demais "
                                     "para desenhar. Diminua a profundidade.")
            return
        cheia, ab = Rastro(), Rastro()
        cm, ca = Contador(), Contador()
        vm = minimax_rastreado(jogo, s, prof, aval, cm, ordem, rastro=cheia)
        va = alfabeta_rastreado(jogo, s, prof, aval, ca, ordem, rastro=ab)
        # mesmos valores com as funções de busca.py (as que o experimento usa)
        cm2, ca2 = Contador(), Contador()
        vm2 = minimax(jogo, s, prof, aval, cm2, ordem)
        va2 = alfabeta(jogo, s, prof, aval, ca2, ordem)
        self.dados = dict(jogo=jogo, s=s, prof=prof, cheia=cheia, ab=ab, vm=vm, va=va, nm=cm.nos, na=ca.nos,
                          vm2=vm2, va2=va2, nm2=cm2.nos, na2=ca2.nos)
        self.selecionado = ()
        self.i = 0
        self._reiniciar_estado()
        self._layout()
        self.escala.configure(to=max(1, len(ab.eventos)))
        self.ir_para(0)

    def _layout(self):
        d = self.dados
        cheia = d["cheia"]
        folhas = [c for c, n in cheia.nos.items() if not n.filhos]
        # ordem de visita da árvore completa = ordem dos eventos 'entra'
        ordem_dfs = [e[1] for e in cheia.eventos if e[0] == "entra"]
        prof_max = max(n.prof for n in cheia.nos.values())
        larg = max(self.cv.winfo_width(), 600) - 40
        self.dx = max(15, larg / max(1, len(folhas)))
        self.dy = max(56, min(170, (max(self.cv.winfo_height(), 400) - 100) / max(1, prof_max)))
        self.r = 8 if self.dx >= 22 else 6
        pos = {}
        k = 0
        n_folhas = len(folhas)
        x_ini = 20 + max(0, (larg - self.dx * n_folhas) / 2)
        for c in ordem_dfs:
            if not cheia.nos[c].filhos:
                pos[c] = x_ini + self.dx * (k + 0.5)
                k += 1
        for c in sorted(cheia.nos, key=len, reverse=True):
            n = cheia.nos[c]
            if n.filhos:
                pos[c] = (pos[n.filhos[0]] + pos[n.filhos[-1]]) / 2
        self.pos = {c: (x, 40 + cheia.nos[c].prof * self.dy) for c, x in pos.items()}
        self._larg_layout = larg
        self._desenhar_estatico()

    def _relayout_se_preciso(self):
        if self.dados is not None and abs(max(self.cv.winfo_width(), 600) - 40 - getattr(self, "_larg_layout", 0)) > 40:
            i = self.i
            self._layout()
            self.ir_para(i)

    def _desenhar_estatico(self):
        cv, d = self.cv, self.dados
        cv.delete("all")
        cheia = d["cheia"]
        self.itens = {}
        r = self.r
        for c, n in cheia.nos.items():
            if c:
                x0, y0 = self.pos[c[:-1]]
                x1, y1 = self.pos[c]
                e = cv.create_line(x0, y0 + r, x1, y1 - r, fill=COR["borda"])
                rot = cv.create_text((x0 + x1) / 2 - 4, (y0 + y1) / 2 - 2, text=str(c[-1]), font=(F_PEQ[0], 7),
                                     fill=COR["muito_suave"], anchor="e") if self.dx >= 18 or len(c) == 1 else None
            else:
                e = rot = None
            x, y = self.pos[c]
            if not n.filhos:
                f = cv.create_rectangle(x - r + 1, y - r + 1, x + r - 1, y + r - 1, fill="", outline=COR["borda"])
            elif n.jogador == MAX:
                f = cv.create_polygon(x - r, y + r * 0.8, x, y - r, x + r, y + r * 0.8, fill="", outline=COR["borda"])
            else:
                f = cv.create_polygon(x - r, y - r * 0.8, x, y + r, x + r, y - r * 0.8, fill="", outline=COR["borda"])
            t = cv.create_text(x, y + r + 2, text="", anchor="n", font=(F_PEQ[0], 7 if self.dx < 30 else 8),
                               fill=COR["texto"])
            ab = cv.create_text(x + r + 2, y - r - 1, text="", anchor="sw", font=(F_PEQ[0], 7), fill=COR["destaque"])
            for it in (f, t):
                cv.tag_bind(it, "<Button-1>", lambda ev, c=c: self.selecionar(c))
            self.itens[c] = (f, t, e, ab, rot)
        self.anel = cv.create_oval(0, 0, 0, 0, outline=COR["destaque"], width=3, state="hidden")
        self.sel = cv.create_rectangle(0, 0, 0, 0, outline=COR["texto"], dash=(2, 2), state="hidden")
        prof_max = max(n.prof for n in cheia.nos.values())
        for p in range(prof_max + 1):
            y = 40 + p * self.dy
            quem = None
            exemplo = next((n for n in cheia.nos.values() if n.prof == p and n.filhos), None)
            if exemplo is not None:
                quem = "MAX" if exemplo.jogador == MAX else "MIN"
            cv.create_text(4, y - 14, anchor="w", text=f"nível {p}" + (f" · {quem}" if quem else ""),
                           font=(F_PEQ[0], 7), fill=COR["muito_suave"])
        w = 40 + self.dx * len([1 for n in cheia.nos.values() if not n.filhos])
        cv.configure(scrollregion=(0, 0, max(w, 600), 60 + prof_max * self.dy + 40))

    # ------------------------------------------------------------------ estado da animação
    def _reiniciar_estado(self):
        cheia = self.dados["cheia"]
        self.status = {c: "oculto" for c in cheia.nos}
        self.valor = {}
        self.janela = {}
        self.pilha = []
        self.visitados = 0
        self.podados = 0

    def _subarvore(self, c):
        cheia = self.dados["cheia"]
        res, pilha = [], [c]
        while pilha:
            x = pilha.pop()
            if x in cheia.nos:
                res.append(x)
                pilha.extend(cheia.nos[x].filhos)
        return res

    def _aplicar(self, ev):
        tipo, c = ev[0], ev[1]
        if tipo == "entra":
            self.status[c] = "ativo"
            self.janela[c] = (ev[2], ev[3])
            self.pilha.append(c)
            self.visitados += 1
        elif tipo == "folha":
            self.valor[c] = ev[2]
            self.status[c] = "feito"
            self.pilha.pop()
        elif tipo == "atualiza":
            self.valor[c] = ev[2]
            self.janela[c] = (ev[3], ev[4])
        elif tipo == "poda":
            for a in ev[3]:
                for x in self._subarvore(c + (a,)):
                    self.status[x] = "podado"
                    self.podados += 1
        elif tipo == "sai":
            self.valor[c] = ev[2]
            self.status[c] = "feito"
            self.pilha.pop()

    def ir_para(self, i):
        if self.dados is None:
            return
        evs = self.dados["ab"].eventos
        i = max(0, min(len(evs), int(i)))
        if i < self.i or not hasattr(self, "status"):
            self._reiniciar_estado()
            for ev in evs[:i]:
                self._aplicar(ev)
        else:
            for ev in evs[self.i:i]:
                self._aplicar(ev)
        self.i = i
        self._redesenhar()

    def _redesenhar(self):
        cv, d = self.cv, self.dados
        cheia = d["cheia"]
        ativos = set(self.pilha)
        for c, (f, t, e, ab, rot) in self.itens.items():
            st = self.status[c]
            n = cheia.nos[c]
            cor = COR["max"] if n.jogador == MAX and n.filhos else COR["min"] if n.filhos else "#555555"
            if n.filhos == [] and n.tipo == "terminal":
                cor = COR["X"] if n.valor > 0 else COR["O"] if n.valor < 0 else COR["empate"]
            if st == "oculto":
                cv.itemconfigure(f, fill="", outline=COR["borda"], dash=(), width=1)
                cv.itemconfigure(t, text="")
                if e:
                    cv.itemconfigure(e, fill=COR["borda"], width=1, dash=())
            elif st == "podado":
                cv.itemconfigure(f, fill="", outline=COR["poda"], dash=(2, 2), width=1)
                cv.itemconfigure(t, text="")
                if e:
                    cv.itemconfigure(e, fill=COR["poda"], width=1, dash=(2, 3))
            else:
                cv.itemconfigure(f, fill=cor, outline=cor, dash=(), width=1)
                v = self.valor.get(c)
                cv.itemconfigure(t, text=_txt(v) if v is not None else "",
                                 fill=COR["texto"] if st == "feito" else COR["destaque"])
                if e:
                    cv.itemconfigure(e, fill=COR["destaque"] if c in ativos else COR["texto"],
                                     width=3 if c in ativos else 1.5, dash=())
            if c in ativos and n.filhos:
                a, b = self.janela.get(c, (-math.inf, math.inf))
                cv.itemconfigure(ab, text=f"α={_txt(a)} β={_txt(b)}")
            else:
                cv.itemconfigure(ab, text="")
        # tesouras nas arestas podadas
        cv.delete("tesoura")
        for c, st in self.status.items():
            if st == "podado" and c[:-1] in self.status and self.status[c[:-1]] != "podado":
                x0, y0 = self.pos[c[:-1]]
                x1, y1 = self.pos[c]
                cv.create_text((x0 * 0.4 + x1 * 0.6), (y0 * 0.4 + y1 * 0.6), text="✂", fill=COR["ruim"],
                               font=(F_PEQ[0], 10, "bold"), tags="tesoura")
        if self.pilha:
            x, y = self.pos[self.pilha[-1]]
            if self.tocando or self.i <= 1:
                self._mostrar(x)
            R = self.r + 5
            cv.coords(self.anel, x - R, y - R, x + R, y + R)
            cv.itemconfigure(self.anel, state="normal")
            cv.tag_raise(self.anel)
        else:
            cv.itemconfigure(self.anel, state="hidden")
        self._contadores()
        self._texto_evento()
        self.var_linha.set(self.i)
        self.lb_pos.config(text=f"evento {self.i}/{len(d['ab'].eventos)}")
        if self.selecionado is not None:
            self.selecionar(self.selecionado, rolar=False)

    def _mostrar(self, x):
        """Rola a árvore na horizontal para manter o nó ativo visível."""
        reg = self.cv.cget("scrollregion").split()
        if not reg:
            return
        total = float(reg[2])
        vis = self.cv.winfo_width()
        a, b = self.cv.xview()
        if not (a * total + 40 <= x <= b * total - 40):
            self.cv.xview_moveto(max(0.0, (x - vis / 2) / total))

    def _contadores(self):
        cv, d = self.cv_cont, self.dados
        cv.delete("all")
        nm, na = d["nm"], d["na"]
        W = 310
        linhas = [("Alfa-beta (até agora)", self.visitados, COR["destaque"]),
                  ("Alfa-beta (total)", na, COR["texto"]),
                  ("Minimax (árvore completa)", nm, COR["max"]),
                  ("Podados até agora", self.podados, COR["poda"])]
        for k, (rot, v, cor) in enumerate(linhas):
            y = 8 + k * 30
            cv.create_text(4, y, anchor="nw", text=rot, font=F_PEQ, fill=COR["suave"])
            cv.create_text(W, y, anchor="ne", text=fmt(v), font=F_NEG, fill=COR["texto"])
            frac = v / nm if nm else 0
            cv.create_rectangle(4, y + 16, 4 + (W - 4) * frac, y + 24, fill=cor, outline="")
            cv.create_rectangle(4, y + 16, W, y + 24, outline=COR["borda"])
        cv.create_text(4, 128, anchor="nw", font=F_PEQ, fill=COR["texto"],
                       text=f"alfa-beta visita {fmt(na)} de {fmt(nm)} nós ({100 * na / nm:.1f}%)".replace(".", ",", 1)
                       if nm else "")

    def _texto_evento(self):
        d = self.dados
        evs = d["ab"].eventos
        cheia = d["cheia"]
        if self.i == 0:
            txt = ("Início. Pressione ▶ ou 'passo ▶'. A árvore cinza é a que o Minimax visitaria; "
                   "o alfa-beta acende só os nós que visita.")
        else:
            ev = evs[self.i - 1]
            tipo, c = ev[0], ev[1]
            quem = "MAX" if cheia.nos[c].jogador == MAX else "MIN"
            if tipo == "entra":
                txt = f"Entra em {_caminho(c)} ({quem}) com janela α = {_txt(ev[2])}, β = {_txt(ev[3])}."
            elif tipo == "folha":
                f = "UTILIDADE (terminal)" if ev[3] == "terminal" else "AVAL (corte de profundidade)"
                txt = f"Folha {_caminho(c)}: {f} = {_txt(ev[2])}."
            elif tipo == "atualiza":
                if quem == "MAX":
                    txt = f"{_caminho(c)} (MAX): v = {_txt(ev[2])}; α passa a {_txt(ev[3])} (β = {_txt(ev[4])})."
                else:
                    txt = f"{_caminho(c)} (MIN): v = {_txt(ev[2])}; β passa a {_txt(ev[4])} (α = {_txt(ev[3])})."
            elif tipo == "poda":
                n = sum(len(self._subarvore(c + (a,))) for a in ev[3])
                a, b = self.janela.get(c, (None, None))
                cond = f"v = {_txt(ev[2])} ≥ β = {_txt(b)}" if quem == "MAX" else f"v = {_txt(ev[2])} ≤ α = {_txt(a)}"
                txt = (f"✂ PODA em {_caminho(c)} ({quem}): {cond}. Colunas {', '.join(map(str, ev[3]))} não são "
                       f"examinadas: {fmt(n)} nós da árvore Minimax evitados.")
            else:
                txt = f"{_caminho(c)} ({quem}) devolve {_txt(ev[2])}."
        self.lb_evento.config(text=txt)
        if self.i >= len(evs):
            ok = d["vm"] == d["va"] == d["vm2"] == d["va2"]
            self.lb_banner.config(
                text=(f"Valor Minimax = {_txt(d['vm'])}   Valor alfa-beta = {_txt(d['va'])}   {'✓ iguais' if ok else '✗ DIFERENTES'}\n"
                      f"(conferido também com busca.py: {fmt(d['nm2'])} e {fmt(d['na2'])} nós)"),
                fg=COR["bom"] if ok else COR["ruim"])
        else:
            self.lb_banner.config(text="")

    def selecionar(self, c, rolar=True):
        if self.dados is None or c not in self.dados["cheia"].nos:
            return
        self.selecionado = c
        if rolar:
            self._mostrar(self.pos[c][0])
        d = self.dados
        n = d["cheia"].nos[c]
        x, y = self.pos[c]
        R = self.r + 3
        self.cv.coords(self.sel, x - R, y - R, x + R, y + R)
        self.cv.itemconfigure(self.sel, state="normal")
        cv = self.cv_mini
        cv.delete("all")
        jogo = d["jogo"]
        cel = min(36, 300 // jogo.colunas, 160 // jogo.linhas)
        ult = None
        if c:
            col = c[-1]
            ult = (col, n.estado.alturas[col] - 1)
        mini_tabuleiro(cv, 4, 4, cel, jogo, n.estado, destaque=ult)
        st = self.status.get(c, "oculto")
        estado_txt = {"oculto": "ainda não visitado", "podado": "podado (alfa-beta não visita)",
                      "ativo": "na pilha da busca", "feito": "visitado"}[st]
        quem = "MAX (X joga)" if n.jogador == MAX else "MIN (O joga)"
        if not n.filhos:
            quem = "folha " + ("terminal" if n.tipo == "terminal" else "AVAL")
        y0 = 8 + cel * jogo.linhas
        cv.create_text(4, y0, anchor="nw", font=F_PEQ, fill=COR["texto"],
                       text=f"caminho: {_caminho(c)}\n{quem} · {estado_txt}\n"
                            f"valor alfa-beta: {_txt(self.valor.get(c)) if st != 'oculto' else '—'}   "
                            f"valor minimax: {_txt(n.valor)}")


    # ------------------------------------------------------------------ controles
    def inicio(self):
        self.parar()
        self.ir_para(0)

    def fim(self):
        self.parar()
        if self.dados:
            self.ir_para(len(self.dados["ab"].eventos))

    def avancar(self):
        self.parar()
        self.ir_para(self.i + 1)

    def voltar(self):
        self.parar()
        self.ir_para(self.i - 1)

    def ate_poda(self):
        self.parar()
        if not self.dados:
            return
        evs = self.dados["ab"].eventos
        j = self.i
        while j < len(evs) and evs[j][0] != "poda":
            j += 1
        self.ir_para(j + 1)

    def _arrastar(self, v):
        if self.dados and int(float(v)) != self.i:
            self.ir_para(int(float(v)))

    def tocar(self):
        if self.tocando:
            self.parar()
            return
        if self.dados and self.i >= len(self.dados["ab"].eventos):
            self.ir_para(0)
        self.tocando = True
        self.bt_tocar.config(text="⏸ pausar")
        self._tique()

    def parar(self):
        self.tocando = False
        if hasattr(self, "bt_tocar"):
            self.bt_tocar.config(text="▶ tocar")

    def _tique(self):
        if not self.tocando or not self.dados:
            return
        if self.i >= len(self.dados["ab"].eventos):
            self.parar()
            return
        self.ir_para(self.i + 1)
        self.after(int(1000 / self.var_vel.get()), self._tique)
