# Gera os PDFs do TDE2: relatorio.pdf, slides.pdf e ficha.pdf.
#   make           exporta os dados do experimento e compila os três documentos
#   make capturas  regera as capturas de tela do visualizador (abre uma janela por ~30 s)
#   make clean     remove os arquivos auxiliares do LaTeX (mantém os PDFs)

DOCS    := relatorio.pdf slides.pdf ficha.pdf
FIGS    := figs/jogar.png figs/arvore.png figs/resultados.png
LATEXMK := latexmk -pdf -interaction=nonstopmode -halt-on-error

.PHONY: all dados capturas clean

all: dados $(DOCS)

dados:
	cd .. && python3 exportar_dados.py

$(FIGS):
	cd .. && python3 visualizador.py --capturas relatorio/figs

capturas:
	cd .. && python3 visualizador.py --capturas relatorio/figs

relatorio.pdf: relatorio.tex graficos.tex tabuleiro.sty dados $(FIGS)
	$(LATEXMK) relatorio.tex

slides.pdf: slides.tex graficos.tex tabuleiro.sty dados $(FIGS)
	$(LATEXMK) slides.tex

ficha.pdf: ficha.tex tabuleiro.sty dados
	$(LATEXMK) ficha.tex

clean:
	latexmk -c relatorio.tex slides.tex ficha.tex
	rm -f *.nav *.snm *.vrb
