"""Visualizador interativo do agente alfa-beta para o Lig 4 (TDE2).

Abas:
  Jogar              tabuleiro animado; humano, aleatório ou AlfaBeta-dN em cada lado; contador de nós ao
                     vivo; valor de cada coluna na raiz; decomposição da AVAL; reprodução de qualquer
                     partida do experimento, conferida contra resultados.json.
  Árvore alfa-beta   animação passo a passo da busca: janelas α/β, podas e nós visitados contra Minimax.
  Resultados         gráficos do experimento (resultados.json).

Uso:
  python3 visualizador.py                 abre a interface
  python3 visualizador.py --teste         roteiro automático de verificação da interface
  python3 visualizador.py --capturas DIR  gera DIR/jogar.png, DIR/arvore.png e DIR/resultados.png

Só usa a biblioteca padrão (tkinter). A busca é a mesma de busca.py (ver rastreio.py e o Teste 5 de
verificacao.py).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from viz.arvore import PRESETS, AbaArvore  # noqa: E402
from viz.comum import COR, F_NORM, capturar_janela  # noqa: E402
from viz.resultados import AbaResultados  # noqa: E402
from viz.tabuleiro import AbaJogar  # noqa: E402


class App:
    def __init__(self, raiz: tk.Tk):
        self.raiz = raiz
        raiz.title("Lig 4 · alfa-beta (TDE2 Busca Competitiva)")
        sw, sh = raiz.winfo_screenwidth(), raiz.winfo_screenheight()
        raiz.geometry(f"{min(1480, sw - 40)}x{min(930, sh - 60)}+10+10")
        raiz.configure(bg=COR["fundo"])
        estilo = ttk.Style(raiz)
        if "clam" in estilo.theme_names():
            estilo.theme_use("clam")
        estilo.configure(".", background=COR["fundo"], foreground=COR["texto"], font=F_NORM)
        estilo.configure("TNotebook.Tab", padding=(14, 6))
        estilo.configure("TButton", padding=(6, 3))
        self.abas = ttk.Notebook(raiz)
        self.abas.pack(fill="both", expand=True)
        self.aba_jogar = AbaJogar(self.abas, self)
        self.aba_arvore = AbaArvore(self.abas, self)
        self.aba_result = AbaResultados(self.abas, self)
        self.abas.add(self.aba_jogar, text="Jogar")
        self.abas.add(self.aba_arvore, text="Árvore alfa-beta")
        self.abas.add(self.aba_result, text="Resultados")

    def abrir_arvore(self, jogo, s):
        self.abas.select(self.aba_arvore)
        self.raiz.update_idletasks()
        self.aba_arvore.usar_posicao(jogo, s)


# ---------------------------------------------------------------------- roteiros automáticos

class Roteiro:
    """Executa passos em sequência sem bloquear o laço do Tk: cada passo devolve True quando terminou."""

    def __init__(self, raiz, passos, ao_fim):
        self.raiz, self.passos, self.ao_fim = raiz, list(passos), ao_fim
        self.t0 = time.time()
        self.raiz.after(300, self._rodar)

    def _rodar(self):
        if not self.passos:
            self.ao_fim()
            return
        nome, f = self.passos[0]
        try:
            pronto = f()
        except Exception as e:  # noqa: BLE001
            print(f"  ERRO em '{nome}': {e!r}")
            pronto = True
            Roteiro.falhas += 1
        if pronto:
            self.passos.pop(0)
        self.raiz.after(50, self._rodar)

    falhas = 0


def _esperar_partida(aba):
    return aba.jogo.terminal(aba.s) and not aba.animando and aba.busca is None


def roteiro_teste(app: App):
    j, a = app.aba_jogar, app.aba_arvore
    estado = {}

    def checar(cond, msg):
        print(("  ok    " if cond else "  FALHA ") + msg)
        if not cond:
            Roteiro.falhas += 1

    def p1():
        j.var_x.set("AlfaBeta-d2")
        j.var_o.set("AlfaBeta-d4")
        j.var_abertura.set("nenhuma")
        j.var_vel.set(4.0)
        j.var_pausa.set(0)
        j.pausado = False
        j.novo_jogo()
        return True

    def p2():
        if not _esperar_partida(j):
            return False
        n = sum(j.s.alturas)
        checar(j.jogo.terminal(j.s) and len(j.lances) == n, f"d2 x d4 jogou até o fim ({n} peças)")
        return True

    def p3():
        # partida do experimento com menos nós do d8, para o teste ser rápido
        ps = j.dados()["AlfaBeta-d2"]
        p = min(ps, key=lambda p: sum(p["nos"]["avaliado"]))
        estado["rep"] = p["id"]
        j.reproduzir("AlfaBeta-d2", p["id"])
        return True

    def p4():
        if not _esperar_partida(j):
            return False
        checar(getattr(j, "ultimo_replay_ok", False),
               f"reprodução de AlfaBeta-d2 nº {estado['rep']} idêntica ao resultados.json")
        return True

    def p5():
        j.var_x.set("Humano")
        j.var_o.set("Humano")
        j.novo_jogo()
        j.analisar()
        estado["t"] = time.time()
        return True

    def p6():
        if time.time() - estado["t"] < 0.05:
            return False
        cont = j.busca[1] if j.busca else None
        estado["holder"] = j.busca[2] if j.busca else {}
        j.novo_jogo()  # cancela
        estado["cont"] = cont
        estado["t"] = time.time()
        return True

    def p7():
        if time.time() - estado["t"] < 0.5:
            return False
        c = estado["cont"]
        checar(c is not None and estado["holder"].get("cancelado") and j.busca is None,
               "busca d8 cancelada no meio "
               f"({c.nos if c else 0} nós) e a interface voltou ao estado inicial")
        return True

    def p8():
        for nome in PRESETS:
            if PRESETS[nome] is None:
                continue
            a.var_preset.set(nome)
            a._preset_mudou()
            a.fim()
            d = a.dados
            checar(d is not None and d["vm"] == d["va"] == d["vm2"] == d["va2"] and d["na"] == d["na2"]
                   and d["nm"] == d["nm2"],
                   f"árvore '{nome}': minimax {d['vm']} = alfa-beta {d['va']} ({d['na']}/{d['nm']} nós)")
            a.ir_para(0)
            a.ate_poda()
        return True

    def p9():
        app.abas.select(app.aba_result)
        app.aba_result.desenhar()
        checar(len(app.aba_result.dicas) > 0, "aba de resultados desenhada")
        return True

    passos = [("d2xd4", p1), ("fim", p2), ("replay", p3), ("replay fim", p4), ("análise", p5),
              ("cancelar", p6), ("cancelado", p7), ("árvores", p8), ("resultados", p9)]

    def fim():
        print("APROVADO" if Roteiro.falhas == 0 else f"REPROVADO: {Roteiro.falhas} falha(s)")
        app.raiz.destroy()

    print("Teste da interface")
    Roteiro(app.raiz, passos, fim)


def roteiro_capturas(app: App, pasta: str):
    os.makedirs(pasta, exist_ok=True)
    j, a = app.aba_jogar, app.aba_arvore

    def c1():
        j.var_x.set("AlfaBeta-d8")
        j.var_o.set("AlfaBeta-d4")
        j.var_abertura.set("3,3")
        j.var_vel.set(4.0)
        j.var_pausa.set(0)
        j.pausado = False
        j.novo_jogo()
        return True

    def c2():
        if len(j.lances) >= 17 and not j.pausado:
            j.alternar_pausa()
        return j.pausado and not j.animando and j.busca is None and len(j.lances) >= 17

    def c3():
        j.analisar()   # mostra a faixa de valores da posição atual (d8, vez de O)
        return True

    def c4():
        if j.busca is not None:
            return False
        app.raiz.update()
        ok = capturar_janela(app.raiz, os.path.join(pasta, "jogar.png"))
        print(("  " if ok else "  FALHOU ") + os.path.join(pasta, "jogar.png"))
        return True

    def c5():
        app.abas.select(a)
        app.raiz.update()
        a.var_preset.set("Meio de jogo 6×7, corte em d = 2 (AVAL)")
        a._preset_mudou()
        evs = a.dados["ab"].eventos
        alvo = int(len(evs) * 0.55)
        while alvo < len(evs) and evs[alvo - 1][0] != "poda":
            alvo += 1
        a.ir_para(alvo)
        if a.pilha:
            a.selecionar(a.pilha[-1])
        return True

    def c6():
        app.raiz.update()
        ok = capturar_janela(app.raiz, os.path.join(pasta, "arvore.png"))
        print(("  " if ok else "  FALHOU ") + os.path.join(pasta, "arvore.png"))
        app.abas.select(app.aba_result)
        return True

    def c7():
        app.raiz.update()
        app.aba_result.desenhar()
        app.raiz.update()
        ok = capturar_janela(app.raiz, os.path.join(pasta, "resultados.png"))
        print(("  " if ok else "  FALHOU ") + os.path.join(pasta, "resultados.png"))
        return True

    Roteiro(app.raiz, [("jogo", c1), ("pausa", c2), ("análise", c3), ("cap1", c4), ("árvore", c5),
                       ("cap2", c6), ("cap3", c7)], app.raiz.destroy)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--teste", action="store_true", help="roteiro automático de verificação da interface")
    ap.add_argument("--capturas", metavar="DIR", help="gera capturas de tela das três abas em DIR")
    args = ap.parse_args()
    raiz = tk.Tk()
    app = App(raiz)
    if args.teste:
        roteiro_teste(app)
    elif args.capturas:
        roteiro_capturas(app, args.capturas)
    raiz.mainloop()
    if args.teste and Roteiro.falhas:
        sys.exit(1)


if __name__ == "__main__":
    main()
