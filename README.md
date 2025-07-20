# PDFToolBox

Una GUI in Python che integra strumenti per **convertire**, **unire**, **dividere** e **riordinare** file PDF (usando `pdfarranger.exe`).

## 🗂️ Contenuto della cartella

```
/
├── main.py                # Launcher con interfaccia TTK Bootstrap
├── convert.py             # Tool di conversione file (md/docx → html/pdf/epub/mp3)
├── MergePDF.py            # Interfaccia per unire PDF
├── splitPDF.py            # Interfaccia per dividere PDF
├── pdfarranger.exe        # Strumento esterno (GPL‑3.0) per riordinare/ruotare/croppare PDF
└── \[altri file e dipendenze]
```

---

## 🧠 Cosa fa  
- **Converti file**: trasformazione da markdown o Word in HTML, EPUB, DOCX, MP3.  
- **Unisci PDF**: interfaccia intuitiva per combinare file PDF.  
- **Dividi PDF**: selezioni pagine o intervalli e le esporti.  
- **Arrange PDF**: avvia `pdfarranger.exe`, app GUI GPL‑3.0 per merge/split, ruota, crop e riordino pagine :contentReference[oaicite:1]{index=1}.

---

## ⚙️ Installazione

1. **Requisiti generali**:
   ```bash
   pip install ttkbootstrap pillow pymupdf PyPDF2>=3.0 markdown mammoth pyttsx3 ebooklib bs4 python-docx
```

2. Metti `pdfarranger.exe` nella stessa cartella di `main.py`.
3. Avvia con:

   ``bash
   python main.py
   ```

---

## ▶️ Uso

1. Seleziona la scheda desiderata: **Converti file**, **Unisci PDF**, **Dividi PDF** o **Arrange PDF**.
2. Usa i pulsanti per aprire gli strumenti e operare sui PDF o sui file di testo.

---

## 🛡️ Licenze & crediti

* ✅ `pdfarranger.exe` è distribuito sotto **GPL‑3.0** e sviluppato dal team pdfarranger ([GitHub][1]).
* 📑 `Suite PDF ToolBox` (questo progetto) è realizzata da **Francesco Lipari** (puoi sostituire con il tuo nome).

---

## 📌 Note importanti

* Se manca `MergePDF.py` o `splitPDF.py`, i rispettivi bottoni saranno disabilitati.
* `pdfarranger.exe` viene avviato in un processo separato, senza bloccare l’interfaccia.
* Funziona su Windows; su Linux puoi compilare `pdfarranger` da sorgente.

---

## 🧩 Strumenti esterni

* [PDF Arranger su GitHub (GPL‑3.0)](https://github.com/pdfarranger/pdfarranger) ([GitHub][1]): tool GTK per merge, split, rotazione, crop e riordino documenti PDF.
* [GPL‑3.0 license info](https://www.gnu.org/licenses/gpl-3.0.html) ([GitHub][1])

---

## 🤝 Contribuzioni e supporto

Aggiunte benvenute: bug fix, miglioramenti all’interfaccia o integrazioni con altri tool.
Per suggerimenti o problemi: apri un issue o contatta via email.

---

### Versione attuale

**v1.0** – prima pubblicazione con tutte le funzionalità integrate.

---

**Buon lavoro!**
*Francesco Lipari*

[1]: https://github.com/pdfarranger/pdfarranger?utm_source=chatgpt.com "GitHub - pdfarranger/pdfarranger"
