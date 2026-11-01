"""Paleta, fontes e utilitários de desenho compartilhados pelas abas do visualizador."""
from __future__ import annotations

import math
import os
import subprocess
import tkinter as tk

from lig4 import Estado, Lig4

COR = {
    "fundo": "#f6f4ef",
    "painel": "#ffffff",
    "borda": "#d9d5cc",
    "texto": "#1f2328",
    "suave": "#6b7078",
    "muito_suave": "#a9adb3",
    "tabuleiro": "#1f4e9c",
    "tabuleiro_escuro": "#163a75",
    "furo": "#f6f4ef",
    "X": "#d7263d",
    "X_claro": "#f4a3ad",
    "O": "#f2b705",
    "O_claro": "#fbe08a",
    "destaque": "#ff7a00",
    "bom": "#1a9e5a",
    "ruim": "#d7263d",
    "neutro": "#8a8f98",
    "poda": "#b8b8b8",
    "max": "#2b6cb0",
    "min": "#9b2c8f",
    "empate": "#9aa3ad",
}

FONTE = "Helvetica"
F_PEQ = (FONTE, 9)
F_NORM = (FONTE, 11)
F_NEG = (FONTE, 11, "bold")
F_TIT = (FONTE, 13, "bold")
F_GRANDE = (FONTE, 30, "bold")


def fmt(n) -> str:
    """Número inteiro com separador de milhar brasileiro: 1.234.567."""
    if n is None:
        return "—"
    if isinstance(n, float) and not n.is_integer():
        return f"{n:,.1f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{int(n):,}".replace(",", ".")


def fmt_pct(x, casas=1) -> str:
    return f"{100 * x:.{casas}f}%".replace(".", ",")


def cor_jogador(j: str) -> str:
    return COR["X"] if j == "X" else COR["O"]


def mini_tabuleiro(cv: tk.Canvas, x0, y0, cel, jogo: Lig4, s: Estado, tag="mini", destaque=None):
    """Desenha um tabuleiro pequeno com canto superior esquerdo em (x0, y0)."""
    h = jogo.linhas + 1
    w, ht = cel * jogo.colunas, cel * jogo.linhas
    cv.create_rectangle(x0, y0, x0 + w, y0 + ht, fill=COR["tabuleiro"], outline=COR["tabuleiro_escuro"], tags=tag)
    pad = max(1, cel * 0.1)
    for c in range(jogo.colunas):
        for r in range(jogo.linhas):
            bit = 1 << (c * h + r)
            cor = COR["X"] if s.x & bit else COR["O"] if s.o & bit else COR["furo"]
            yy = y0 + (jogo.linhas - 1 - r) * cel
            xx = x0 + c * cel
            larg = 2 if destaque == (c, r) else 0
            cv.create_oval(xx + pad, yy + pad, xx + cel - pad, yy + cel - pad, fill=cor,
                           outline=COR["destaque"] if larg else "", width=larg, tags=tag)


def exportar_eps(cv: tk.Canvas, caminho: str):
    """Exporta o conteúdo do canvas para EPS (e PDF via epstopdf, se existir)."""
    cv.update_idletasks()
    w, h = cv.winfo_width(), cv.winfo_height()
    cv.postscript(file=caminho, colormode="color", width=w, height=h, x=0, y=0)
    try:
        subprocess.run(["epstopdf", caminho], check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        pass


def capturar_janela(raiz: tk.Tk, caminho_png: str) -> bool:
    """Captura a janela inteira como PNG (ImageMagick `import`, depois Pillow). Devolve True se deu certo."""
    raiz.update()
    try:
        wid = raiz.wm_frame()
        wid = int(wid, 16) if isinstance(wid, str) else raiz.winfo_id()
    except (tk.TclError, ValueError):
        wid = raiz.winfo_id()
    try:
        subprocess.run(["import", "-window", str(wid), caminho_png], check=True, capture_output=True, timeout=20)
        return os.path.exists(caminho_png)
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        from PIL import ImageGrab
        x, y = raiz.winfo_rootx(), raiz.winfo_rooty()
        img = ImageGrab.grab(bbox=(x, y, x + raiz.winfo_width(), y + raiz.winfo_height()))
        img.save(caminho_png)
        return True
    except Exception:
        return False


class Eixos:
    """Mapeamento de coordenadas de dados para um retângulo do canvas, com eixo log opcional."""

    def __init__(self, cv: tk.Canvas, x0, y0, x1, y1, xlim, ylim, logx=False, logy=False):
        self.cv, self.x0, self.y0, self.x1, self.y1 = cv, x0, y0, x1, y1
        self.xlim, self.ylim, self.logx, self.logy = xlim, ylim, logx, logy

    def _t(self, v, lim, log):
        a, b = lim
        if log:
            v, a, b = math.log10(max(v, 1e-9)), math.log10(a), math.log10(b)
        return (v - a) / (b - a) if b != a else 0.5

    def X(self, v):
        return self.x0 + self._t(v, self.xlim, self.logx) * (self.x1 - self.x0)

    def Y(self, v):
        return self.y1 - self._t(v, self.ylim, self.logy) * (self.y1 - self.y0)

    def moldura(self, titulo=None, xlabel=None, ylabel=None, tag="graf"):
        cv = self.cv
        cv.create_line(self.x0, self.y1, self.x1, self.y1, fill=COR["suave"], tags=tag)
        cv.create_line(self.x0, self.y0, self.x0, self.y1, fill=COR["suave"], tags=tag)
        if titulo:
            cv.create_text(self.x0, self.y0 - 22, text=titulo, anchor="sw", font=F_NEG, fill=COR["texto"], tags=tag)
        if xlabel:
            cv.create_text((self.x0 + self.x1) / 2, self.y1 + 30, text=xlabel, font=F_PEQ, fill=COR["suave"], tags=tag)
        if ylabel:
            cv.create_text(self.x0 - 8, self.y0 - 6, text=ylabel, anchor="se", font=F_PEQ, fill=COR["suave"], tags=tag)

    def ticks_y(self, valores, rotulo=fmt, grade=True, tag="graf"):
        for v in valores:
            y = self.Y(v)
            if grade:
                self.cv.create_line(self.x0, y, self.x1, y, fill="#ece9e2", tags=tag)
            self.cv.create_text(self.x0 - 5, y, text=rotulo(v), anchor="e", font=F_PEQ, fill=COR["suave"], tags=tag)

    def ticks_x(self, valores, rotulo=fmt, grade=False, tag="graf"):
        for v in valores:
            x = self.X(v)
            if grade:
                self.cv.create_line(x, self.y0, x, self.y1, fill="#ece9e2", tags=tag)
            self.cv.create_line(x, self.y1, x, self.y1 + 4, fill=COR["suave"], tags=tag)
            self.cv.create_text(x, self.y1 + 6, text=rotulo(v), anchor="n", font=F_PEQ, fill=COR["suave"], tags=tag)


def potencias_10(a, b):
    k = math.floor(math.log10(max(a, 1)))
    res = []
    while 10 ** k <= b:
        if 10 ** k >= a:
            res.append(10 ** k)
        k += 1
    return res


def rotulo_pot10(v) -> str:
    e = round(math.log10(v))
    return {0: "1", 1: "10", 2: "100", 3: "1 mil", 4: "10 mil", 5: "100 mil", 6: "1 mi", 7: "10 mi"}.get(e, f"1e{e}")
