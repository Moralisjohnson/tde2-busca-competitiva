# TDE2 — Busca Competitiva: Lig 4 (Connect Four)

Equipe: Guilherme Arcanjo de Morais, Lucas da Costa Paula, Renan da Silva Andrade e Renan Americo Herculano.

Agente alfa-beta com profundidade fixa para o Lig 4 6×7, comparado contra um agente aleatório e contra
ele mesmo com profundidade menor. O custo é medido em **nós visitados**.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `lig4.py` | Formalização: s₀, JOGADOR, AÇÕES, RESULTADO, TESTE-TERMINAL, UTILIDADE (bitboard, tamanho e K genéricos) |
| `busca.py` | Minimax, alfa-beta, AVAL, ordenação centro-primeiro, contador de nós, agentes |
| `verificacao.py` | Alfa-beta == Minimax (instância 4×4 K=3 em profundidade completa + posições aleatórias) |
| `experimento.py` | Protocolo experimental completo; gera `resultados.json` e `resultados.md` |
| `verificacao_saida.txt`, `resultados.md`, `resultados.json` | Saídas da última execução |
| `TDE2_Ficha_de_Projeto6A_preenchida.docx` | Ficha de projeto preenchida |

## Como rodar

Requer Python 3.10+ e nenhuma dependência externa.

```bash
python3 verificacao.py    # ~1,5 min, termina com APROVADO / REPROVADO
python3 experimento.py    # ~3,5 min em 16 núcleos (multiprocessing), 394 partidas
```

## Verificação de corretude

| Caso | Minimax | Alfa-beta |
|---|---|---|
| 4×4 K=3, profundidade completa a partir de s₀ | valor 991, 6.761.217 nós | valor 991, 11.985 nós (33.810 sem ordenação) |
| 200 posições 3×4 K=3, profundidade completa | 7.627.105 nós | 114.733 nós, 0 divergências |
| 100 finais 6×7 (8 casas vazias), profundidade completa | 61.291 nós | 7.614 nós, 0 divergências |
| 100 posições 6×7, d=4 com AVAL (valor **e** jogada) | 238.275 nós | 26.355 nós, 0 divergências |

O valor 991 = 1000 − 9 significa que, no 4×4 com K=3, X vence com jogo perfeito e a vitória sai na 9ª peça.

## Resultados (AlfaBeta-d8)

| Adversário | Partidas | V / E / D | Taxa de vitória (IC 95% Wilson) | Pontos | Nós/lance: média · mediana · p95 · máx |
|---|---|---|---|---|---|
| Aleatório | 100 | 100 / 0 / 0 | 100% (96,3–100%) | 1,000 | 19.727 · 13.149 · 53.476 · 414.620 |
| AlfaBeta-d2 | 98 | 77 / 5 / 16 | 78,6% (69,5–85,5%) | 0,811 | 17.980 · 8.296 · 68.122 · 1.942.939 |
| AlfaBeta-d4 | 98 | 61 / 14 / 23 | 62,2% (52,4–71,2%) | 0,694 | 18.132 · 6.296 · 60.550 · 1.554.522 |
| AlfaBeta-d6 | 98 | 38 / 26 / 34 | 38,8% (29,7–48,7%) | 0,520 | 15.332 · 4.732 · 51.179 · 1.170.289 |

O custo médio por lance dos adversários foi de 20 nós (d2), 196 (d4) e 1.643 (d6). As tabelas completas,
com o resultado por lado e a duração das partidas, estão em `resultados.md`.

**Ordenação de jogadas** (mesmas 300 posições, d=8): média de 15.031 nós com ordenação e 71.884 sem,
medianas de 6.754 e 13.623, e o mesmo valor na raiz nas duas variantes.

## O que não funcionou e as garantias que o sistema não tem

- **Os retornos da profundidade caem rápido.** Contra o d6, o d8 fez 0,520 ponto por partida, e o IC 95% da
  taxa de vitória (29,7–48,7%) fica abaixo de 50%. Não dá para afirmar que d8 > d6 com 98 partidas.
  A partir daí o gargalo é a AVAL, não a profundidade.
- **A AVAL ignora a paridade das ameaças (zugzwang).** O d8 perdeu 16 partidas até para o d2, 14 delas jogando
  em segundo, todas terminadas com 35 a 40 peças. Na partida reproduzida, a AVAL favorecia O até a 25ª peça;
  na 27ª a busca já viu a derrota forçada (+965), tarde demais para evitar. Ameaças em linha ímpar ou par
  decidem o fim do Lig 4, e a AVAL não as distingue.
- **O custo por lance tem cauda pesada.** A mediana fica entre 5 e 13 mil nós, mas o máximo chega a 1,9 milhão.
  A profundidade fixa não limita o pior caso, e por isso reportamos p95 e máximo, não só a média.
- **A ordenação nem sempre ajuda.** Em 41 das 300 posições, examinar o centro primeiro custou mais nós.
- **Garantias ausentes:**
  - O agente não é ótimo: no 6×7 a busca não chega aos terminais, e o valor de corte é uma estimativa.
  - Não há busca de quiescência, então o efeito horizonte é possível.
  - Os pesos (5, 2, 3) foram escolhidos à mão e não foram ajustados.
  - Contra os adversários alfa-beta os resultados valem para as 49 aberturas de 2 jogadas, não para qualquer partida.
  - O agente é determinístico: o mesmo estado sempre produz a mesma jogada, o que um adversário pode explorar.
- **Calibração simétrica.** Todos os agentes de busca usam o mesmo código, a mesma AVAL, os mesmos pesos e a
  mesma ordenação; só a profundidade muda. Nenhum dos lados foi ajustado.
