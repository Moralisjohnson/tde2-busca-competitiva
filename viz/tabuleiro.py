"""Aba "Jogar": tabuleiro animado, contador de nós ao vivo, valor de cada coluna, AVAL e reprodução
de partidas do experimento."""
from __future__ import annotations

import json
import math
import os
import threading
import time
import tkinter as tk
from tkinter import ttk

from busca import AgenteAleatorio, Avaliacao, ordem_centro
from lig4 import MAX, Lig4
from rastreio import (Cancelado, ContadorCancelavel, casas_vencedoras, componentes_aval, decidir_detalhado,
                      eh_vitoria, janelas_por_casa)
from viz.comum import (COR, F_GRANDE, F_NEG, F_NORM, F_PEQ, F_TIT, Eixos, cor_jogador, fmt, potencias_10,
                       rotulo_pot10)

JOGADORES = ["Humano", "Aleatório", "AlfaBeta-d2", "AlfaBeta-d4", "AlfaBeta-d6", "AlfaBeta-d8"]
CEL = 72
MARGEM = 20
Y_FAIXA = 8          # faixa de valores por coluna
ALT_FAIXA = 112
Y_PREVIA = Y_FAIXA + ALT_FAIXA + 6
Y_TAB = Y_PREVIA + CEL
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AgenteBusca:
    """Mesmo agente de busca.AgenteAlfaBeta (profundidade fixa, AVAL, centro primeiro), mas usando
    decidir_detalhado para também mostrar o valor de cada coluna."""

    def __init__(self, jogo, prof):
        self.prof, self.aval, self.ordem = prof, Avaliacao(jogo), ordem_centro(jogo)
        self.nome = f"AlfaBeta-d{prof}"


class AbaJogar(ttk.Frame):
    def __init__(self, mestre, app):
        super().__init__(mestre, padding=8)
        self.app = app
        self.jogo = Lig4()
        self.aval = Avaliacao(self.jogo)
        self.janelas_casa = janelas_por_casa(self.jogo)
        self.s = self.jogo.inicial()
        self.lances: list[dict] = []
        self.agentes = {}
        self.geracao = 0
        self.busca = None          # (geracao, contador, holder, t0, jogador, só_análise)
        self.animando = False
        self.pausado = False
        self.passo = False
        self.analise = None        # (estado, raiz, escolhida, jogador) mostrada na faixa de valores
        self.replay = None
        self.hover = None
        self._dados = None
        self.ao_terminar = []      # callbacks usados pelos testes/capturas

        self._montar()
        self.novo_jogo()

    # ------------------------------------------------------------------ interface
    def _montar(self):
        esq = ttk.Frame(self)
        esq.pack(side="left", fill="y", padx=(0, 10))
        centro = ttk.Frame(self)
        centro.pack(side="left", fill="both")
        dir_ = ttk.Frame(self)
        dir_.pack(side="left", fill="both", expand=True, padx=(10, 0))

        # --- controles
        ttk.Label(esq, text="Partida", font=F_TIT).pack(anchor="w")
        self.var_x = tk.StringVar(value="Humano")
        self.var_o = tk.StringVar(value="AlfaBeta-d8")
        for rot, var, cor in (("X (MAX, começa)", self.var_x, COR["X"]), ("O (MIN)", self.var_o, COR["O"])):
            f = ttk.Frame(esq)
            f.pack(fill="x", pady=2)
            c = tk.Canvas(f, width=16, height=16, highlightthickness=0, bg=COR["fundo"])
            c.create_oval(2, 2, 14, 14, fill=cor, outline="")
            c.pack(side="left")
            ttk.Label(f, text=rot, width=15).pack(side="left", padx=4)
            ttk.Combobox(f, textvariable=var, values=JOGADORES, state="readonly", width=13).pack(side="left")

        f = ttk.Frame(esq)
        f.pack(fill="x", pady=2)
        ttk.Label(f, text="Semente do aleatório").pack(side="left")
        self.var_semente = tk.IntVar(value=0)
        ttk.Spinbox(f, from_=0, to=9999, textvariable=self.var_semente, width=6).pack(side="right")

        f = ttk.Frame(esq)
        f.pack(fill="x", pady=2)
        ttk.Label(f, text="Abertura forçada").pack(side="left")
        self.var_abertura = tk.StringVar(value="nenhuma")
        aberturas = ["nenhuma"] + [f"{a},{b}" for a in range(7) for b in range(7)]
        ttk.Combobox(f, textvariable=self.var_abertura, values=aberturas, state="readonly",
                     width=8).pack(side="right")

        bt = ttk.Frame(esq)
        bt.pack(fill="x", pady=(8, 2))
        ttk.Button(bt, text="Novo jogo", command=self.novo_jogo).pack(side="left", expand=True, fill="x")
        ttk.Button(bt, text="Desfazer", command=self.desfazer).pack(side="left", expand=True, fill="x")
        bt = ttk.Frame(esq)
        bt.pack(fill="x", pady=2)
        self.bt_pausa = ttk.Button(bt, text="Pausar", command=self.alternar_pausa)
        self.bt_pausa.pack(side="left", expand=True, fill="x")
        ttk.Button(bt, text="Passo", command=self.dar_passo).pack(side="left", expand=True, fill="x")
        ttk.Button(esq, text="Analisar posição (d8)", command=self.analisar).pack(fill="x", pady=2)
        ttk.Button(esq, text="Ver árvore desta posição →", command=self._abrir_arvore).pack(fill="x", pady=2)

        ttk.Label(esq, text="Animação").pack(anchor="w", pady=(8, 0))
        self.var_vel = tk.DoubleVar(value=1.0)
        ttk.Scale(esq, from_=0.3, to=4.0, variable=self.var_vel).pack(fill="x")
        ttk.Label(esq, text="Pausa entre lances (ms)").pack(anchor="w")
        self.var_pausa = tk.IntVar(value=350)
        ttk.Scale(esq, from_=0, to=2000, variable=self.var_pausa).pack(fill="x")
        self.var_mapa = tk.BooleanVar(value=False)
        ttk.Checkbutton(esq, text="Mapa: janelas por casa", variable=self.var_mapa,
                        command=self.redesenhar).pack(anchor="w", pady=(6, 0))

        ttk.Separator(esq).pack(fill="x", pady=10)
        ttk.Label(esq, text="Reproduzir partida do experimento", font=F_NEG).pack(anchor="w")
        f = ttk.Frame(esq)
        f.pack(fill="x", pady=2)
        self.var_rep_adv = tk.StringVar(value="AlfaBeta-d2")
        ttk.Combobox(f, textvariable=self.var_rep_adv, state="readonly", width=12,
                     values=["Aleatório", "AlfaBeta-d2", "AlfaBeta-d4", "AlfaBeta-d6"]).pack(side="left")
        ttk.Label(f, text=" nº ").pack(side="left")
        self.var_rep_id = tk.IntVar(value=0)
        ttk.Spinbox(f, from_=0, to=99, textvariable=self.var_rep_id, width=4).pack(side="left")
        ttk.Button(esq, text="Reproduzir (avaliado = d8)", command=self.reproduzir).pack(fill="x", pady=2)
        self.lb_replay = ttk.Label(esq, text="", wraplength=250, font=F_PEQ, justify="left")
        self.lb_replay.pack(anchor="w", fill="x")

        # --- tabuleiro
        w = CEL * self.jogo.colunas + 2 * MARGEM
        h = Y_TAB + CEL * self.jogo.linhas + 34
        self.cv = tk.Canvas(centro, width=w, height=h, bg=COR["fundo"], highlightthickness=0)
        self.cv.pack()
        self.cv.bind("<Motion>", self._mover)
        self.cv.bind("<Leave>", lambda e: self._mover(None))
        self.cv.bind("<Button-1>", self._clicar)
        self.lb_status = ttk.Label(centro, text="", font=F_NEG, anchor="center")
        self.lb_status.pack(fill="x", pady=(4, 0))

        # --- painel de custo
        ttk.Label(dir_, text="Custo: nós visitados", font=F_TIT).pack(anchor="w")
        self.lb_nos = tk.Label(dir_, text="0", font=F_GRANDE, fg=COR["texto"], bg=COR["fundo"], anchor="w")
        self.lb_nos.pack(anchor="w")
        self.lb_nos_info = ttk.Label(dir_, text="neste lance", foreground=COR["suave"])
        self.lb_nos_info.pack(anchor="w")
        self.lb_tempo = ttk.Label(dir_, text="", foreground=COR["muito_suave"], font=F_PEQ)
        self.lb_tempo.pack(anchor="w")
        self.cv_tot = tk.Canvas(dir_, width=420, height=58, bg=COR["fundo"], highlightthickness=0)
        self.cv_tot.pack(anchor="w", pady=(4, 0))
        self.cv_barras = tk.Canvas(dir_, width=420, height=190, bg=COR["painel"], highlightthickness=1,
                                   highlightbackground=COR["borda"])
        self.cv_barras.pack(anchor="w", pady=4)
        ttk.Label(dir_, text="AVAL(s) da posição atual (ponto de vista de X)", font=F_NEG).pack(anchor="w",
                                                                                                pady=(6, 0))
        self.cv_aval = tk.Canvas(dir_, width=420, height=150, bg=COR["painel"], highlightthickness=1,
                                 highlightbackground=COR["borda"])
        self.cv_aval.pack(anchor="w", pady=4)
        ttk.Label(dir_, text="Lances", font=F_NEG).pack(anchor="w")
        self.txt = tk.Text(dir_, width=56, height=7, font=("Courier", 9), relief="flat", bg=COR["painel"])
        self.txt.pack(anchor="w", fill="both", expand=True)

    # ------------------------------------------------------------------ partida
    def _criar_agente(self, spec, semente):
        if spec == "Humano":
            return None
        if spec == "Aleatório":
            return AgenteAleatorio(semente)
        return AgenteBusca(self.jogo, int(spec.split("-d")[1]))

    def _cancelar(self):
        self.geracao += 1
        if self.busca is not None:
            self.busca[1].cancelar = True
        self.busca = None

    def novo_jogo(self, abertura=None, replay=None):
        self._cancelar()
        self.replay = replay
        if replay is None:
            self.lb_replay.config(text="")
        sem = self.var_semente.get()
        self.agentes = {"X": self._criar_agente(self.var_x.get(), sem), "O": self._criar_agente(self.var_o.get(), sem)}
        if abertura is None:
            ab = self.var_abertura.get()
            abertura = [] if ab == "nenhuma" else [int(v) for v in ab.split(",")]
        self.s = self.jogo.inicial()
        self.lances = []
        self.analise = None
        self.animando = False
        for a in abertura:
            self._registrar(a, {"nos": 0, "forcado": True, "nome": "abertura"})
            self.s = self.jogo.resultado(self.s, a)
        self.lb_nos.config(text="0")
        self.lb_nos_info.config(text="neste lance")
        self.lb_tempo.config(text="")
        self.redesenhar()
        self._agendar()

    def _vez(self):
        return "X" if self.s.vez == MAX else "O"

    def _agendar(self, atraso=None):
        if self.animando:
            return
        if self.jogo.terminal(self.s):
            self._fim()
            return
        j = self._vez()
        ag = self.agentes[j]
        if ag is None:
            self._status(f"Vez de {j} (humano): clique em uma coluna", cor_jogador(j))
            return
        if self.pausado and not self.passo:
            self._status(f"Pausado — vez de {j} ({ag.nome})", COR["suave"])
            return
        self.passo = False
        g = self.geracao
        self.after(self.var_pausa.get() if atraso is None else atraso,
                   lambda: g == self.geracao and self._iniciar_busca())

    def _iniciar_busca(self, so_analise=False):
        if self.busca is not None or self.animando or self.jogo.terminal(self.s):
            return
        j = self._vez()
        ag = AgenteBusca(self.jogo, 8) if so_analise else self.agentes[j]
        if isinstance(ag, AgenteAleatorio):
            a, n = ag.jogar(self.jogo, self.s)
            self.lb_nos.config(text="0")
            self.lb_nos_info.config(text=f"lance {len(self.lances) + 1} · Aleatório ({j}) não busca")
            self._registrar(a, {"nos": n, "nome": ag.nome})
            self._animar_queda(a, j)
            return
        cont = ContadorCancelavel()
        holder = {}
        s, jogo = self.s, self.jogo

        def trabalho():
            try:
                holder["res"] = decidir_detalhado(jogo, s, ag.prof, ag.aval, cont, ag.ordem)
            except Cancelado:
                holder["cancelado"] = True

        self.busca = (self.geracao, cont, holder, time.perf_counter(), j, so_analise, ag, s)
        self.analise = ("buscando", s, None, None, j)
        self.redesenhar_faixa()
        acao = "analisando" if so_analise else "pensando"
        self._status(f"{ag.nome} ({j}) {acao}…", cor_jogador(j))
        self.lb_nos_info.config(text=f"lance {len(self.lances) + 1} · {ag.nome} ({j})" +
                                (" · só análise" if so_analise else ""))
        threading.Thread(target=trabalho, daemon=True).start()
        self._monitorar()

    def _monitorar(self):
        if self.busca is None:
            return
        g, cont, holder, t0, j, so_analise, ag, s = self.busca
        if g != self.geracao:
            return
        self.lb_nos.config(text=fmt(cont.nos), fg=cor_jogador(j) if j == "X" else "#b38600")
        self.lb_tempo.config(text=f"tempo de parede {time.perf_counter() - t0:.1f} s (só informativo, não é a unidade de custo)")
        if "res" not in holder:
            self.after(40, self._monitorar)
            return
        self.busca = None
        a, v, raiz = holder["res"]
        self.lb_nos.config(text=fmt(cont.nos), fg=COR["texto"])
        self.analise = ("pronto", s, raiz, a, j)
        if so_analise:
            self.redesenhar_faixa()
            self._status(f"Análise d8: melhor coluna para {j} é {a}", cor_jogador(j))
            return
        self._registrar(a, {"nos": cont.nos, "valor": v, "raiz": raiz, "nome": ag.nome,
                            "seg": time.perf_counter() - t0})
        self._animar_queda(a, j)

    def _registrar(self, a, info):
        info.update({"col": a, "jogador": self._vez(), "pecas": sum(self.s.alturas)})
        self.lances.append(info)

    def _animar_queda(self, a, j):
        """Peça caindo com aceleração constante até a casa livre mais baixa."""
        self.animando = True
        r = self.s.alturas[a]
        x = MARGEM + a * CEL + CEL / 2
        y_fim = Y_TAB + (self.jogo.linhas - 1 - r) * CEL + CEL / 2
        y_ini = Y_PREVIA + CEL / 2
        raio = CEL * 0.4
        item = self.cv.create_oval(x - raio, y_ini - raio, x + raio, y_ini + raio, fill=cor_jogador(j),
                                   outline="", tags="queda")
        g = self.geracao
        dist = y_fim - y_ini
        dur = max(0.08, 0.06 * math.sqrt(dist / CEL) * 2.2 / max(0.05, self.var_vel.get()))
        t0 = time.perf_counter()

        def passo():
            if g != self.geracao:
                return
            t = (time.perf_counter() - t0) / dur
            if t >= 1:
                self.cv.delete("queda")
                self._aplicar(a)
                return
            y = y_ini + dist * t * t
            self.cv.coords(item, x - raio, y - raio, x + raio, y + raio)
            self.after(12, passo)

        passo()

    def _aplicar(self, a):
        self.s = self.jogo.resultado(self.s, a)
        self.animando = False
        self.redesenhar()
        self._agendar()

    def _fim(self):
        u = self.jogo.utilidade(self.s)
        if u > 0:
            self._status(f"X venceu com {sum(self.s.alturas)} peças  (UTILIDADE = {u:+d})", COR["X"])
        elif u < 0:
            self._status(f"O venceu com {sum(self.s.alturas)} peças  (UTILIDADE = {u:+d})", "#b38600")
        else:
            self._status("Empate: tabuleiro cheio (UTILIDADE = 0)", COR["suave"])
        if self.replay is not None:
            self._conferir_replay()
        for f in list(self.ao_terminar):
            f()

    # ------------------------------------------------------------------ ações
    def _clicar(self, ev):
        c = int((ev.x - MARGEM) // CEL)
        if not (0 <= c < self.jogo.colunas) or self.animando or self.busca is not None:
            return
        if self.jogo.terminal(self.s) or self.agentes[self._vez()] is not None:
            return
        if c not in self.jogo.acoes(self.s):
            return
        j = self._vez()
        self._registrar(c, {"nos": 0, "nome": "Humano"})
        self.analise = None
        self._animar_queda(c, j)

    def _mover(self, ev):
        c = None if ev is None else int((ev.x - MARGEM) // CEL)
        if c is not None and not (0 <= c < self.jogo.colunas):
            c = None
        if c != self.hover:
            self.hover = c
            self._desenhar_previa()

    def desfazer(self):
        self._cancelar()
        self.animando = False
        self.cv.delete("queda")
        humanos = [j for j in "XO" if self.agentes[j] is None]
        while self.lances and not self.lances[-1].get("forcado"):
            ultimo = self.lances.pop()
            if not humanos or ultimo["jogador"] in humanos:
                break
        self.s = self.jogo.inicial()
        for l in self.lances:
            self.s = self.jogo.resultado(self.s, l["col"])
        if not humanos:
            self.pausado = True
            self.bt_pausa.config(text="Continuar")
        self.analise = None
        self.redesenhar()
        self._agendar()

    def alternar_pausa(self):
        self.pausado = not self.pausado
        self.bt_pausa.config(text="Continuar" if self.pausado else "Pausar")
        if not self.pausado and self.busca is None:
            self._agendar(0)

    def dar_passo(self):
        if self.busca is None and not self.animando:
            self.passo = True
            self._agendar(0)

    def analisar(self):
        if self.busca is None and not self.animando:
            self._iniciar_busca(so_analise=True)

    def _abrir_arvore(self):
        self.app.abrir_arvore(self.jogo, self.s)

    # ------------------------------------------------------------------ reprodução
    def dados(self):
        if self._dados is None:
            with open(os.path.join(RAIZ, "resultados.json"), encoding="utf-8") as f:
                self._dados = json.load(f)["partidas"]
        return self._dados

    def reproduzir(self, adv=None, id_=None):
        adv = adv or self.var_rep_adv.get()
        id_ = self.var_rep_id.get() if id_ is None else id_
        try:
            ps = self.dados()[adv]
        except (OSError, KeyError) as e:
            self.lb_replay.config(text=f"resultados.json indisponível: {e}")
            return
        id_ = max(0, min(len(ps) - 1, id_))
        p = ps[id_]
        avaliado, outro = ("X", "O") if p["avaliado_comeca"] else ("O", "X")
        (self.var_x if avaliado == "X" else self.var_o).set("AlfaBeta-d8")
        (self.var_o if avaliado == "X" else self.var_x).set(adv)
        self.var_semente.set(p["id"])
        ab = p["abertura"]
        self.var_abertura.set(f"{ab[0]},{ab[1]}" if ab else "nenhuma")
        self.pausado = False
        self.bt_pausa.config(text="Pausar")
        res = {"V": "vitória", "E": "empate", "D": "derrota"}[p["resultado"]]
        self.lb_replay.config(text=f"{adv} nº {p['id']}: d8 joga com {avaliado}, abertura {ab or '—'}. "
                                   f"Registrado: {res} do d8 com {p['jogadas']} peças. Reproduzindo…",
                              foreground=COR["texto"])
        self.novo_jogo(abertura=list(ab), replay=(adv, p, avaliado))

    def _conferir_replay(self):
        adv, p, avaliado = self.replay
        self.replay = None
        u = self.jogo.utilidade(self.s)
        venc = None if u == 0 else ("X" if u > 0 else "O")
        res = "E" if venc is None else ("V" if venc == avaliado else "D")
        nos_av = [l["nos"] for l in self.lances if not l.get("forcado") and l["jogador"] == avaliado]
        nos_ad = [l["nos"] for l in self.lances if not l.get("forcado") and l["jogador"] != avaliado]
        checks = [("resultado", res == p["resultado"]), ("peças", sum(self.s.alturas) == p["jogadas"]),
                  ("nós do d8 em cada lance", nos_av == p["nos"]["avaliado"]),
                  ("nós do adversário", nos_ad == p["nos"]["adversario"])]
        if "lances" in p:
            checks.append(("sequência de colunas", [l["col"] for l in self.lances] == p["lances"]))
        ok = all(c for _, c in checks)
        linhas = [f"{'✓' if c else '✗'} {n}" for n, c in checks]
        self.lb_replay.config(
            text=(f"{adv} nº {p['id']}: " + ("IDÊNTICA ao resultados.json" if ok else "DIFERENTE do resultados.json")
                  + "\n" + "\n".join(linhas) + f"\nnós do d8 na partida: {fmt(sum(nos_av))}"),
            foreground=COR["bom"] if ok else COR["ruim"])
        self.ultimo_replay_ok = ok

    # ------------------------------------------------------------------ desenho
    def _status(self, txt, cor=None):
        self.lb_status.config(text=txt, foreground=cor or COR["texto"])

    def redesenhar(self):
        self._desenhar_tabuleiro()
        self.redesenhar_faixa()
        self._desenhar_previa()
        self._desenhar_totais()
        self._desenhar_barras()
        self._desenhar_aval()
        self._desenhar_log()

    def _xy(self, c, r):
        return MARGEM + c * CEL, Y_TAB + (self.jogo.linhas - 1 - r) * CEL

    def _desenhar_tabuleiro(self):
        cv, jogo, s = self.cv, self.jogo, self.s
        cv.delete("tab")
        x0, y0 = MARGEM, Y_TAB
        cv.create_rectangle(x0 - 6, y0 - 6, x0 + CEL * jogo.colunas + 6, y0 + CEL * jogo.linhas + 6,
                            fill=COR["tabuleiro"], outline=COR["tabuleiro_escuro"], width=2, tags="tab")
        venc = set(casas_vencedoras(jogo, s)) if jogo.vencedor(s) is not None else set()
        ultimo = None
        if self.lances:
            l = self.lances[-1]
            ultimo = (l["col"], s.alturas[l["col"]] - 1)
        mapa = self.var_mapa.get()
        maxj = max(self.janelas_casa.values())
        h = jogo.linhas + 1
        for c in range(jogo.colunas):
            for r in range(jogo.linhas):
                x, y = self._xy(c, r)
                bit = 1 << (c * h + r)
                p = "X" if s.x & bit else "O" if s.o & bit else None
                pad = CEL * 0.1
                fill = COR["furo"] if p is None else cor_jogador(p)
                if p is None and mapa:
                    t = self.janelas_casa[(c, r)] / maxj
                    fill = _mistura("#ffffff", "#2e8b57", t * 0.85)
                cv.create_oval(x + pad, y + pad, x + CEL - pad, y + CEL - pad, fill=fill,
                               outline=COR["tabuleiro_escuro"], width=2, tags="tab")
                if p is None and mapa:
                    cv.create_text(x + CEL / 2, y + CEL / 2, text=str(self.janelas_casa[(c, r)]),
                                   font=F_NEG, fill=COR["texto"], tags="tab")
                if (c, r) in venc:
                    cv.create_oval(x + pad - 3, y + pad - 3, x + CEL - pad + 3, y + CEL - pad + 3,
                                   outline="#ffffff", width=4, tags="tab")
                    cv.create_oval(x + CEL / 2 - 6, y + CEL / 2 - 6, x + CEL / 2 + 6, y + CEL / 2 + 6,
                                   fill="#ffffff", outline="", tags="tab")
                elif (c, r) == ultimo:
                    cv.create_oval(x + CEL / 2 - 5, y + CEL / 2 - 5, x + CEL / 2 + 5, y + CEL / 2 + 5,
                                   fill=COR["texto"], outline="", tags="tab")
        for c in range(jogo.colunas):
            cv.create_text(MARGEM + c * CEL + CEL / 2, y0 + CEL * jogo.linhas + 18, text=str(c),
                           font=F_NEG, fill=COR["suave"], tags="tab")
        if mapa:
            cv.create_text(MARGEM + CEL * jogo.colunas / 2, y0 + CEL * jogo.linhas + 32,
                           text="número de janelas de 4 casas que passam por cada casa vazia",
                           font=F_PEQ, fill=COR["suave"], tags="tab")

    def _desenhar_previa(self):
        cv = self.cv
        cv.delete("previa")
        c = self.hover
        if c is None or self.jogo.terminal(self.s) or self.agentes.get(self._vez()) is not None:
            return
        if self.s.alturas[c] >= self.jogo.linhas or self.animando:
            return
        x = MARGEM + c * CEL + CEL / 2
        y = Y_PREVIA + CEL / 2
        r = CEL * 0.4
        claro = COR["X_claro"] if self._vez() == "X" else COR["O_claro"]
        cv.create_oval(x - r, y - r, x + r, y + r, fill=claro, outline=cor_jogador(self._vez()), width=2,
                       dash=(4, 3), tags="previa")

    def redesenhar_faixa(self):
        """Valor de cada coluna na raiz da última busca, do ponto de vista de quem jogava."""
        cv = self.cv
        cv.delete("faixa")
        x0, x1 = MARGEM, MARGEM + CEL * self.jogo.colunas
        meio = Y_FAIXA + ALT_FAIXA / 2 + 4
        cv.create_rectangle(x0 - 6, Y_FAIXA, x1 + 6, Y_FAIXA + ALT_FAIXA, fill=COR["painel"],
                            outline=COR["borda"], tags="faixa")
        if self.analise is None:
            cv.create_text((x0 + x1) / 2, Y_FAIXA + ALT_FAIXA / 2,
                           text="Valor de cada coluna aparece aqui depois de cada busca",
                           font=F_PEQ, fill=COR["muito_suave"], tags="faixa")
            return
        fase, s, raiz, escolhida, j = self.analise
        if fase == "buscando":
            cv.create_text((x0 + x1) / 2, Y_FAIXA + ALT_FAIXA / 2, text=f"buscando a melhor coluna para {j}…",
                           font=F_NORM, fill=cor_jogador(j), tags="faixa")
            return
        cv.create_text(x0, Y_FAIXA + 9, anchor="w", font=F_PEQ, fill=COR["suave"], tags="faixa",
                       text=f"valor de cada coluna para {j} ({sum(s.alturas)} peças) · tracejado = só limite · "
                            f"▲ escolhida")
        cv.create_line(x0, meio, x1, meio, fill=COR["borda"], tags="faixa")
        meia = ALT_FAIXA / 2 - 24
        pecas = sum(s.alturas)
        for vr in raiz:
            v = vr.valor if j == "X" else -vr.valor
            lim = vr.limite()
            if j == "O" and lim:
                lim = "≥" if lim == "≤" else "≤"
            cx = MARGEM + vr.acao * CEL + CEL / 2
            if eh_vitoria(v):
                n = 1000 - abs(v)
                frac = 1.0
                txt = f"{'vence' if v > 0 else 'perde'} em {n - pecas}"
            else:
                frac = min(1.0, math.log10(1 + abs(v)) / 2.2)
                txt = f"{v:+d}"
            frac = math.copysign(frac, v) if v else 0
            cor = COR["bom"] if v > 0 else COR["ruim"] if v < 0 else COR["neutro"]
            ytop = meio - frac * meia
            cv.create_rectangle(cx - CEL * 0.3, min(meio, ytop), cx + CEL * 0.3, max(meio, ytop) + (2 if not v else 0),
                                fill=cor if not lim else "", outline=cor, width=2,
                                dash=(3, 2) if lim else None, tags="faixa")
            # rótulo do lado oposto ao da barra, para não sair da faixa
            cv.create_text(cx, meio + 4 if v > 0 else meio - 4, text=lim + txt, font=F_PEQ, fill=COR["texto"],
                           tags="faixa", anchor="n" if v > 0 else "s")
            if vr.acao == escolhida:
                cv.create_text(cx, Y_FAIXA + ALT_FAIXA - 1, text="▲", anchor="s", font=F_NEG,
                               fill=COR["destaque"], tags="faixa")
            cv.create_text(cx, Y_FAIXA + ALT_FAIXA + 2, text=f"{fmt(vr.nos)} nós", anchor="n",
                           font=(F_PEQ[0], 7), fill=COR["suave"], tags="faixa")

    def _desenhar_totais(self):
        cv = self.cv_tot
        cv.delete("all")
        for i, j in enumerate("XO"):
            ls = [l for l in self.lances if l["jogador"] == j and not l.get("forcado")]
            tot = sum(l["nos"] for l in ls)
            nome = self.agentes[j].nome if self.agentes.get(j) is not None else "Humano"
            y = 6 + i * 26
            cv.create_oval(4, y + 2, 18, y + 16, fill=cor_jogador(j), outline="")
            cv.create_text(26, y + 9, anchor="w", font=F_NEG, fill=COR["texto"], text=f"{j} · {nome}")
            media = tot / len(ls) if ls else 0
            cv.create_text(410, y + 9, anchor="e", font=F_NORM, fill=COR["texto"],
                           text=f"{len(ls)} lances · total {fmt(tot)} · média {fmt(round(media))}")

    def _desenhar_barras(self):
        cv = self.cv_barras
        cv.delete("all")
        W, H = 420, 190
        ax = Eixos(cv, 48, 26, W - 10, H - 26, (0, self.jogo.linhas * self.jogo.colunas), (1, 3e6), logy=True)
        ax.moldura(titulo=None)
        cv.create_text(8, 6, anchor="nw", text="nós por lance (escala log)", font=F_PEQ, fill=COR["suave"])
        ax.ticks_y(potencias_10(1, 3e6), rotulo=rotulo_pot10)
        ax.ticks_x([0, 10, 20, 30, 42], rotulo=str)
        larg = (ax.x1 - ax.x0) / 42 * 0.8
        for i, l in enumerate(self.lances):
            x = ax.X(i + 0.5)
            if l.get("forcado"):
                cv.create_text(x, ax.y1 - 6, text="·", fill=COR["suave"])
                continue
            n = max(1, l["nos"])
            cor = cor_jogador(l["jogador"])
            cv.create_rectangle(x - larg / 2, ax.Y(n), x + larg / 2, ax.y1, fill=cor, outline="")
        cv.create_text(W - 10, 6, anchor="ne", text="eixo x: nº do lance", font=F_PEQ, fill=COR["suave"])

    def _desenhar_aval(self):
        cv = self.cv_aval
        cv.delete("all")
        W = 420
        s = self.s
        if self.jogo.terminal(s):
            u = self.jogo.utilidade(s)
            cv.create_text(W / 2, 40, text=f"Estado terminal: UTILIDADE(s, MAX) = {u:+d}", font=F_NEG,
                           fill=COR["texto"])
            cv.create_text(W / 2, 66, text="vitória de X: +(1000 − n); de O: −(1000 − n); empate: 0",
                           font=F_PEQ, fill=COR["suave"])
            return
        c = componentes_aval(self.aval, s)
        v = c["total"]
        # barra: centro = 0, tanh comprime
        x0, x1, y = 20, W - 20, 22
        cv.create_rectangle(x0, y - 8, x1, y + 8, fill="#f0eee9", outline=COR["borda"])
        meio = (x0 + x1) / 2
        xv = meio + math.tanh(v / 40) * (x1 - x0) / 2
        cv.create_rectangle(min(meio, xv), y - 8, max(meio, xv), y + 8,
                            fill=COR["X"] if v > 0 else COR["O"] if v < 0 else COR["neutro"], outline="")
        cv.create_line(meio, y - 12, meio, y + 12, fill=COR["texto"])
        cv.create_text(x0, y + 12, anchor="nw", text="← favorece O", font=F_PEQ, fill=COR["suave"])
        cv.create_text(x1, y + 12, anchor="ne", text="favorece X →", font=F_PEQ, fill=COR["suave"])
        cv.create_text(meio, y + 12, anchor="n", text=f"AVAL = {v:+d}", font=F_NEG, fill=COR["texto"])
        linhas = [("3 em linha + 1 vazia", "k1", 5), ("2 em linha + 2 vazias", "k2", 2), ("peças no centro", "centro", 3)]
        yy = 64
        cv.create_text(20, yy, anchor="w", text="característica", font=F_PEQ, fill=COR["suave"])
        cv.create_text(220, yy, anchor="e", text="X", font=F_PEQ, fill=COR["X"])
        cv.create_text(260, yy, anchor="e", text="O", font=F_PEQ, fill="#b38600")
        cv.create_text(400, yy, anchor="e", text="peso × (X − O)", font=F_PEQ, fill=COR["suave"])
        for rot, k, peso in linhas:
            yy += 19
            a, b = c[f"{k}_x"], c[f"{k}_o"]
            cv.create_text(20, yy, anchor="w", text=rot, font=F_NORM, fill=COR["texto"])
            cv.create_text(220, yy, anchor="e", text=str(a), font=F_NORM, fill=COR["texto"])
            cv.create_text(260, yy, anchor="e", text=str(b), font=F_NORM, fill=COR["texto"])
            cv.create_text(400, yy, anchor="e", text=f"{peso} × {a - b:+d} = {peso * (a - b):+d}", font=F_NORM,
                           fill=COR["texto"])
        if c["bruto"] != v:
            cv.create_text(20, yy + 20, anchor="w", text=f"limitada a ±900 (bruto {c['bruto']:+d})", font=F_PEQ,
                           fill=COR["suave"])

    def _desenhar_log(self):
        t = self.txt
        t.config(state="normal")
        t.delete("1.0", "end")
        for i, l in enumerate(self.lances, 1):
            if l.get("forcado"):
                t.insert("end", f"{i:2d}. {l['jogador']} → col {l['col']}   (abertura forçada)\n")
                continue
            val = ""
            if "valor" in l:
                v = l["valor"]
                val = f" · valor {v:+d}" if not eh_vitoria(v) else f" · {'X' if v > 0 else 'O'} vence (peça {1000 - abs(v)})"
            t.insert("end", f"{i:2d}. {l['jogador']} → col {l['col']}   {fmt(l['nos']):>9} nós{val}\n")
        t.see("end")
        t.config(state="disabled")


def _mistura(a, b, t):
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(pa, pb))
