doc:
	rm doc.zip || echo No zip file to remove
	rst2html.py doc.rst > index.html
	zip doc.zip *.html
