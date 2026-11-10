# PDF Suite

Strumenti per gestire i PDF, in due versioni.

## Web app (`docs/index.html`)

Funziona nel browser, su PC e su Android, senza server. I file restano sul dispositivo: l'elaborazione avviene nella pagina, con mupdf.js (WASM).

Moduli: Unisci, Riordina, Sostituisci, Dividi, Segnalibri, Annota (evidenziatore e testo), Converti (Markdown e DOCX in HTML o EPUB).

Pubblicazione: GitHub Pages serve la cartella `docs/` del ramo `main`, senza build. La cartella contiene anche `manifest.webmanifest`, `sw.js` e le icone della PWA: per forzare l'aggiornamento della cache dopo una modifica incrementa `VERSIONE` in `sw.js`.

### Ricostruire `docs/index.html`

```
cd web
npm install
node build.mjs node_modules/mupdf/dist node_modules
cp dist/index.html ../docs/index.html
```

Sorgenti: `web/app.src.html` (interfaccia), `web/motore.mjs` (logica PDF), `web/toc.mjs` (segnalibri), `web/build.mjs` (build).

## Suite Python (`python/main.py`)

Applicazione desktop con tkinter e ttkbootstrap, basata su PyMuPDF. Da ora serve solo per **Rinomina batch** e per la conversione da e verso `.doc` e DOCX. Le funzioni PDF vivono nella web app.

```
pip install ttkbootstrap pymupdf Pillow
pip install markdown mammoth ebooklib beautifulsoup4 python-docx   # per il modulo Converti
python python/main.py
```


## Licenza

mupdf.js e PyMuPDF sono distribuiti con licenza AGPL-3.0. Chi usa la web app può chiedere il sorgente.
