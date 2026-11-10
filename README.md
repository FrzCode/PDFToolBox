# PDF Suite

Strumenti per gestire i PDF, in due versioni.

## Web app (`public/index.html`)

Funziona nel browser, su PC e su Android, senza server. I file restano sul dispositivo: l'elaborazione avviene nella pagina, con mupdf.js (WASM).

Moduli: Unisci, Riordina, Sostituisci, Dividi, Segnalibri, Annota (evidenziatore e testo), Converti (Markdown e DOCX in HTML o EPUB).

Pubblicazione: Netlify serve la cartella `public/` (vedi `netlify.toml`), senza build.

### Ricostruire `public/index.html`

```
cd web
npm install
node build.mjs node_modules/mupdf/dist node_modules
cp dist/index.html ../public/index.html
```

Sorgenti: `web/app.src.html` (interfaccia), `web/motore.mjs` (logica PDF), `web/toc.mjs` (segnalibri), `web/build.mjs` (build).

## Suite Python (`python/main.py`)

Applicazione desktop con tkinter e ttkbootstrap, basata su PyMuPDF. Da ora serve solo per **Rinomina batch** e per la conversione da e verso `.doc` e DOCX. Le funzioni PDF vivono nella web app.

```
pip install ttkbootstrap pymupdf Pillow
pip install markdown mammoth ebooklib beautifulsoup4 python-docx   # per il modulo Converti
python python/main.py
```

`python/legacy/` contiene la vecchia versione a più file, che usava `pdfarranger.exe`. Si può eliminare: resta nella storia di Git.

## Licenza

mupdf.js e PyMuPDF sono distribuiti con licenza AGPL-3.0. Chi usa la web app può chiedere il sorgente.
