import tkinter as tk
from tkinter import ttk, messagebox
import os
import subprocess
import tkinter.scrolledtext as st

# Import dei tool esistenti
from convert import convert_file

# Import PDFMerger
try:
    from MergePDF import PDFMergerApp
    PDF_MERGER_AVAILABLE = True
except ImportError:
    PDF_MERGER_AVAILABLE = False

# Import PDFSplitter
try:
    from splitPDF import PDFSplitterApp
    PDF_SPLITTER_AVAILABLE = True
except ImportError:
    PDF_SPLITTER_AVAILABLE = False


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Suite PDF ToolBox")
        self.geometry("620x550")
        self.configure(bg="#f0f0f0")
        self.resizable(False, False)

        style = ttk.Style(self)
        style.theme_use('clam')
        bg = "#f0f0f0"
        style.configure('TNotebook', background=bg, borderwidth=0)
        style.configure('TNotebook.Tab', padding=(12, 8), font=('Arial', 11, 'bold'))
        style.configure('TFrame', background=bg)
        style.configure('TLabel', background=bg, font=('Arial', 10))
        style.configure('TButton', font=('Arial', 10, 'bold'), padding=6)
        style.map('TButton', background=[('active', '#d0d0d0')])

        self._create_widgets()

    def _create_widgets(self):
        notebook = ttk.Notebook(self)
        notebook.pack(expand=True, fill='both', padx=15, pady=15)

        # Convertitore
        tab_convert = ttk.Frame(notebook)
        notebook.add(tab_convert, text="Converti file")
        btn_convert = ttk.Button(tab_convert, text="Converti file", command=self._launch_convert)
        btn_convert.pack(pady=50)

        # Unisci PDF
        tab_merge = ttk.Frame(notebook)
        notebook.add(tab_merge, text="Unisci PDF")
        btn_merge = ttk.Button(
            tab_merge,
            text="Apri PDF Merger",
            state=('normal' if PDF_MERGER_AVAILABLE else 'disabled'),
            command=self._launch_merge
        )
        btn_merge.pack(pady=50)

        # Dividi PDF
        tab_split = ttk.Frame(notebook)
        notebook.add(tab_split, text="Dividi PDF")
        btn_split = ttk.Button(
            tab_split,
            text="Apri PDF Splitter",
            state=('normal' if PDF_SPLITTER_AVAILABLE else 'disabled'),
            command=self._launch_split
        )
        btn_split.pack(pady=50)

        # Arrange PDF
        tab_arrange = ttk.Frame(notebook)
        notebook.add(tab_arrange, text="Arrange PDF")
        btn_arrange = ttk.Button(
            tab_arrange,
            text="Apri pdfarranger",
            command=self._launch_arranger
        )
        btn_arrange.pack(pady=50)

        # Help con ScrolledText
        tab_help = ttk.Frame(notebook)
        notebook.add(tab_help, text="Help")
        help_box = st.ScrolledText(tab_help, wrap=tk.WORD, state='disabled',
                                   width=70, height=20, font=('Arial', 10))
        help_box.pack(expand=True, fill='both', padx=10, pady=10)

        help_content = (
            "Benvenuto nella Suite PDF ToolBox!\n\n"
            "Questa applicazione ti permette di:\n"
            "📄 Convertire file in vari formati\n"
            "📚 Unire più file PDF\n"
            "✂️ Dividere un PDF in pagine o intervalli\n"
            "🔄 Riordinare/ruotare/suddividere PDF con pdfarranger\n\n"
            "---\n\n"
            "📌 1) Converti File:\n"
            "- Vai su 'Converti file', clicca e seleziona .md/.docx\n"
            "- Puoi generare HTML, EPUB, DOCX, MP3 ecc.\n"
            "🔧 Dipendenze: markdown, mammoth, pyttsx3, ebooklib, bs4, python-docx\n\n"
            "📌 2) Unisci PDF:\n"
            "- Vai su 'Unisci PDF', clicca e utilizza l’interfaccia di merging\n"
            "🔧 Richiede MergePDF.py funzionante\n\n"
            "📌 3) Dividi PDF:\n"
            "- Vai su 'Dividi PDF', clicca e seleziona pagine o intervalli\n"
            "🔧 Richiede PyPDF2>=3.0, PyMuPDF, Pillow\n\n"
            "📌 4) Arrange PDF:\n"
            "- Clicca su 'Apri pdfarranger' per lanciare PDF Arranger\n"
            "⚙️ PDF Arranger è un'app open source (GPL‑3.0) per riordinare/ruotare/croppare PDF :contentReference[oaicite:1]{index=1}\n\n"
            "---\n\n"
            "📋 Crediti:\n"
            "- pdfarranger.exe è sviluppato dal team pdfarranger (GPL‑3.0) :contentReference[oaicite:2]{index=2}\n"
            "- Questa Suite è realizzata da FRANCESCO LIPARI\n\n"
            "🔧 Assicurati che pdfarranger.exe sia nella stessa cartella di main.py\n"
            "Buon lavoro! 👍"
        )

        help_box.configure(state='normal')
        help_box.insert(tk.END, help_content)
        help_box.configure(state='disabled')

    def _launch_convert(self):
        try:
            convert_file()
        except Exception as e:
            messagebox.showerror("Errore Convertitore", str(e))

    def _launch_merge(self):
        if not PDF_MERGER_AVAILABLE:
            messagebox.showwarning("N/D", "Modulo MergePDF non trovato")
            return
        try:
            win = tk.Toplevel(self)
            win.title("PDF Merger")
            win.geometry("800x600")
            PDFMergerApp(win)
        except Exception as e:
            messagebox.showerror("Errore Merger", str(e))

    def _launch_split(self):
        if not PDF_SPLITTER_AVAILABLE:
            messagebox.showwarning("N/D", "Modulo splitPDF non trovato")
            return
        try:
            win = tk.Toplevel(self)
            win.title("PDF Splitter")
            win.geometry("1200x800")
            PDFSplitterApp(win)
        except Exception as e:
            messagebox.showerror("Errore Splitter", str(e))

    def _launch_arranger(self):
        exe_path = os.path.join(os.path.dirname(__file__), "pdfarranger.exe")
        if not os.path.exists(exe_path):
            messagebox.showerror("Errore", "Il file 'pdfarranger.exe' non è stato trovato.")
            return
        try:
            subprocess.Popen([exe_path], shell=True)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile avviare pdfarranger.exe:\n{e}")


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
