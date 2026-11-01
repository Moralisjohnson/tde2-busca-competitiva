# TDE2 · Busca Competitiva: Lig 4 (Connect Four)

Equipe: Guilherme Arcanjo de Morais, Lucas da Costa Paula, Renan da Silva Andrade e Renan Americo Herculano.

Agente alfa-beta com profundidade fixa para o Lig 4 6×7, comparado contra um agente aleatório e contra
ele mesmo com profundidade menor. O custo é medido em nós visitados.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `lig4.py` | Formalização: s₀, JOGADOR, AÇÕES, RESULTADO, TESTE-TERMINAL, UTILIDADE (bitboard, tamanho e K genéricos) |
| `busca.py` | Minimax, alfa-beta, AVAL, ordenação centro-primeiro, contador de nós, agentes |
| `verificacao.py` | Alfa-beta == Minimax (instância 4×4 K=3 em profundidade completa + posições aleatórias) e rastreio == busca |
| `experimento.py` | Protocolo experimental completo; gera `resultados.json` (com a sequência de lances de cada partida) e `resultados.md` |
| `verificacao_saida.txt`, `resultados.md`, `resultados.json` | Saídas da última execução |
| `rastreio.py` | Busca instrumentada para o visualizador (árvore, eventos, valor por coluna, cancelamento); idêntica a `busca.py` (Teste 5) |
| `visualizador.py`, `viz/` | Interface interativa em Tkinter (só biblioteca padrão) |
| `exportar_dados.py`, `relatorio/` | Relatório, slides e ficha em LaTeX, com gráficos gerados de `resultados.json` |
| `TDE2_Ficha_de_Projeto6A_preenchida.docx` | Ficha de projeto preenchida (versão Word) |

## Como rodar

Requer Python 3.10+ e nenhuma dependência externa.

```bash
python3 verificacao.py    # ~1,5 min, termina com APROVADO / REPROVADO
python3 experimento.py    # ~3,5 min em 16 núcleos (multiprocessing), 394 partidas
python3 visualizador.py   # interface interativa (Tkinter)
```

## Visualizador

`python3 visualizador.py` abre uma janela com três abas. Usa a mesma busca de `busca.py`: `rastreio.py` só
acrescenta registro, e o Teste 5 de `verificacao.py` confere que valor, jogada e nós são idênticos.

- **Jogar.** Cada lado pode ser Humano, Aleatório ou AlfaBeta-d2/d4/d6/d8, com abertura forçada opcional
  (as 49 do protocolo). As peças caem animadas. O contador de nós visitados sobe ao vivo durante a
  busca (o tempo aparece só como informação). Depois de cada lance, uma faixa sobre o tabuleiro mostra o
  valor de cada coluna para quem jogou, com os limites da poda na raiz tracejados e as vitórias forçadas
  decodificadas ("perde em 2"). Também há o gráfico de nós por lance em escala log, a decomposição da
  AVAL da posição (5·3-abertas + 2·2-abertas + 3·centro) e o mapa de janelas por casa, que justifica o
  peso do centro. O botão *Analisar posição (d8)* mostra a análise sem jogar, e *Desfazer* volta o lance.
- **Reproduzir partida do experimento.** Escolha o adversário e o número da partida. O app monta os
  mesmos jogadores, abertura, lado e semente, joga a partida e confere resultado, peças, sequência de
  colunas e nós de cada lance contra `resultados.json` (✓/✗).
- **Árvore alfa-beta.** Animação passo a passo, com tocar, passo, voltar, "próxima poda" e linha do tempo.
  A árvore Minimax completa aparece em cinza e o alfa-beta acende só os nós que visita. Os nós na pilha
  mostram α e β, e as subárvores podadas aparecem tracejadas com ✂. Os contadores comparam os nós do
  alfa-beta com os do Minimax e terminam com "valor Minimax = valor alfa-beta". As posições prontas
  incluem finais em profundidade completa, o Lig 3 em 3×4 e 4×4, e cortes d = 2 e 3. Também dá para
  enviar a posição atual da aba Jogar. Clicar em um nó mostra o tabuleiro dele.
- **Resultados.** V/E/D com IC 95% de Wilson, box plots de nós por lance (escala log), dispersão
  com × sem ordenação nas 300 posições e duração das partidas. Dá para filtrar por lado.

`python3 visualizador.py --teste` roda um roteiro automático na interface: uma partida d2 × d4, a
reprodução de uma partida do experimento, o cancelamento de uma busca d8, o valor de todas as árvores
prontas e a aba de resultados. `python3 visualizador.py --capturas DIR` gera as capturas usadas no
relatório.

## Relatório, slides e ficha (LaTeX)

```bash
cd relatorio && make      # exporta dados de resultados.json e compila relatorio.pdf, slides.pdf e ficha.pdf
```

Os números citados no texto vêm de `relatorio/dados/numeros.tex`, que `exportar_dados.py` gera a partir de
`resultados.json` e `verificacao_saida.txt`.

## Verificação de corretude

| Caso | Minimax | Alfa-beta |
|---|---|---|
| 4×4 K=3, profundidade completa a partir de s₀ | valor 991, 6.761.217 nós | valor 991, 11.985 nós (33.810 sem ordenação) |
| 200 posições 3×4 K=3, profundidade completa | 7.627.105 nós | 114.733 nós, 0 divergências |
| 100 finais 6×7 (8 casas vazias), profundidade completa | 61.291 nós | 7.614 nós, 0 divergências |
| 100 posições 6×7, d=4 com AVAL (valor *e* jogada) | 238.275 nós | 26.355 nós, 0 divergências |
| `rastreio.py` (visualizador) contra `busca.py` | não se aplica | 240 comparações de valor, jogada e nós, 0 divergências |

O valor 991 = 1000 − 9 significa que, no 4×4 com K=3, X vence com jogo perfeito e a vitória sai na 9ª peça.

## Resultados (AlfaBeta-d8)

| Adversário | Partidas | V / E / D | Taxa de vitória (IC 95% Wilson) | Pontos | Nós/lance: média · mediana · p95 · máx |
|---|---|---|---|---|---|
| Aleatório | 100 | 100 / 0 / 0 | 100% (96,3 a 100%) | 1,000 | 19.727 · 13.149 · 53.476 · 414.620 |
| AlfaBeta-d2 | 98 | 77 / 5 / 16 | 78,6% (69,5 a 85,5%) | 0,811 | 17.980 · 8.296 · 68.122 · 1.942.939 |
| AlfaBeta-d4 | 98 | 61 / 14 / 23 | 62,2% (52,4 a 71,2%) | 0,694 | 18.132 · 6.296 · 60.550 · 1.554.522 |
| AlfaBeta-d6 | 98 | 38 / 26 / 34 | 38,8% (29,7 a 48,7%) | 0,520 | 15.332 · 4.732 · 51.179 · 1.170.289 |

O custo médio por lance dos adversários foi de 20 nós (d2), 196 (d4) e 1.643 (d6). As tabelas completas,
com o resultado por lado e a duração das partidas, estão em `resultados.md`.

Na ordenação de jogadas (mesmas 300 posições, d=8), a média foi de 15.031 nós com ordenação e 71.884 sem, as
medianas foram 6.754 e 13.623, e o valor na raiz foi o mesmo nas duas variantes.

## O que não funcionou e as garantias que o sistema não tem

- **Os retornos da profundidade caem rápido.** Contra o d6, o d8 fez 0,520 ponto por partida, e o IC 95% da
  taxa de vitória (29,7 a 48,7%) fica abaixo de 50%. Não dá para afirmar que d8 > d6 com 98 partidas.
  Nossa hipótese é que, a partir daí, a AVAL limita mais que a profundidade.
- **A AVAL ignora a paridade das ameaças (zugzwang).** O d8 perdeu 16 partidas até para o d2, 14 delas jogando
  em segundo. As 16 terminaram com 35 a 40 peças. Na partida reproduzida, a AVAL favorecia O até a 25ª peça;
  na 27ª a busca já viu a derrota forçada (+965), tarde demais para evitar. Ameaças em linha ímpar ou par
  decidem o fim do Lig 4, e a AVAL não as distingue.
- **O custo por lance tem cauda pesada.** A mediana fica entre 5 e 13 mil nós, mas o máximo chega a 1,9 milhão.
  A profundidade fixa não limita o pior caso, por isso reportamos também p95 e máximo.
- **A ordenação nem sempre ajuda.** Em 41 das 300 posições, examinar o centro primeiro custou mais nós.
- **Garantias ausentes:**
  - O agente não é ótimo: no 6×7 a busca não chega aos terminais, e o valor de corte é uma estimativa.
  - Não há busca de quiescência, então o efeito horizonte é possível.
  - Os pesos (5, 2, 3) foram escolhidos à mão e não foram ajustados.
  - Contra os adversários alfa-beta os resultados valem para as 49 aberturas de 2 jogadas, não para qualquer partida.
  - O agente é determinístico: o mesmo estado sempre produz a mesma jogada, o que um adversário pode explorar.
- **Calibração simétrica.** Todos os agentes de busca usam o mesmo código, a mesma AVAL, os mesmos pesos e a
  mesma ordenação; só a profundidade muda. Nenhum dos lados foi ajustado.
