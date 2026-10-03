.PHONY: all pdf check clean

all: check

pdf:
	cd s3 && latexmk -r latexmkrc main.tex
	cp s3/.build/notes-colored.pdf s3/notes-colored.pdf

check: pdf
	python3 scripts/check_pdf.py

clean:
	cd s3 && latexmk -r latexmkrc -C main.tex
