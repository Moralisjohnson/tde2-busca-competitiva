"""Verificação de corretude: alfa-beta devolve EXATAMENTE o mesmo valor que Minimax.

1. Instância pequena (Lig 4 em 4x4, K=3), profundidade completa a partir de s0.
2. 200 posições aleatórias da instância 3x4, K=3, profundidade completa.
3. 100 finais aleatórios do Lig 4 6x7 com 8 casas vazias, profundidade completa.
4. 100 posições aleatórias do 6x7 com corte em profundidade 4 e a mesma AVAL:
   mesmo valor e mesma jogada escolhida.

Uso: python3 verificacao.py
"""
import random
import sys
import time

from busca import Avaliacao, Contador, alfabeta, decidir, minimax, ordem_centro
from lig4 import Lig4

falhas = 0


def confere(rotulo, vm, va):
    global falhas
    if vm != va:
        falhas += 1
        print(f"  FALHA {rotulo}: minimax={vm} alfabeta={va}")


def posicao_aleatoria(jogo, n_jogadas, rng):
    """Joga n_jogadas aleatórias a partir de s0; recomeça se a partida acabar antes."""
    while True:
        s = jogo.inicial()
        for _ in range(n_jogadas):
            if jogo.terminal(s):
                break
            s = jogo.resultado(s, rng.choice(jogo.acoes(s)))
        if not jogo.terminal(s):
            return s


# 1 ------------------------------------------------------------------
jogo = Lig4(4, 4, 3)
print("Teste 1: Lig 4 4x4 (K=3), profundidade completa a partir de s0")
t = time.time(); cm = Contador(); vm = minimax(jogo, jogo.inicial(), cont=cm); tm = time.time() - t
t = time.time(); ca = Contador(); va = alfabeta(jogo, jogo.inicial(), cont=ca); ta = time.time() - t
t = time.time(); co = Contador(); vo = alfabeta(jogo, jogo.inicial(), cont=co, ordem=ordem_centro(jogo)); to = time.time() - t
print(f"  Minimax                      valor={vm:5d}  nós={cm.nos:>10,}  ({tm:.1f}s)")
print(f"  Alfa-beta (sem ordenação)    valor={va:5d}  nós={ca.nos:>10,}  ({ta:.2f}s)")
print(f"  Alfa-beta (centro primeiro)  valor={vo:5d}  nós={co.nos:>10,}  ({to:.2f}s)")
confere("4x4 s0 sem ordem", vm, va)
confere("4x4 s0 com ordem", vm, vo)

# 2 ------------------------------------------------------------------
jogo = Lig4(3, 4, 3)
rng = random.Random(1)
print("Teste 2: 200 posições aleatórias do 3x4 (K=3), profundidade completa")
nm = na = 0
for i in range(200):
    s = posicao_aleatoria(jogo, rng.randint(0, 8), rng)
    cm, ca = Contador(), Contador()
    vm = minimax(jogo, s, cont=cm)
    va = alfabeta(jogo, s, cont=ca, ordem=ordem_centro(jogo))
    nm += cm.nos; na += ca.nos
    confere(f"3x4 #{i}", vm, va)
print(f"  nós totais: minimax={nm:,}  alfa-beta={na:,}  ({100 * na / nm:.1f}%)")

# 3 ------------------------------------------------------------------
jogo = Lig4()
rng = random.Random(2)
print("Teste 3: 100 finais aleatórios do 6x7 com 8 casas vazias, profundidade completa")
nm = na = 0
for i in range(100):
    s = posicao_aleatoria(jogo, 34, rng)
    cm, ca = Contador(), Contador()
    vm = minimax(jogo, s, cont=cm)
    va = alfabeta(jogo, s, cont=ca, ordem=ordem_centro(jogo))
    nm += cm.nos; na += ca.nos
    confere(f"6x7 final #{i}", vm, va)
print(f"  nós totais: minimax={nm:,}  alfa-beta={na:,}  ({100 * na / nm:.1f}%)")

# 4 ------------------------------------------------------------------
aval = Avaliacao(jogo)
ordem = ordem_centro(jogo)
rng = random.Random(3)
print("Teste 4: 100 posições aleatórias do 6x7, corte em profundidade 4 com AVAL")
nm = na = 0
for i in range(100):
    s = posicao_aleatoria(jogo, rng.randint(0, 20), rng)
    cm, ca = Contador(), Contador()
    am, vm = decidir(jogo, s, minimax, 4, aval, cm, ordem)
    aa, va = decidir(jogo, s, alfabeta, 4, aval, ca, ordem)
    nm += cm.nos; na += ca.nos
    confere(f"6x7 d4 #{i} valor", vm, va)
    confere(f"6x7 d4 #{i} jogada", am, aa)
print(f"  nós totais: minimax={nm:,}  alfa-beta={na:,}  ({100 * na / nm:.1f}%)")

print()
if falhas:
    print(f"REPROVADO: {falhas} divergência(s) entre Minimax e alfa-beta")
    sys.exit(1)
print("APROVADO: alfa-beta devolveu exatamente o mesmo valor que Minimax em todos os casos")
