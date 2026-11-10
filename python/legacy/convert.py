import os
import subprocess
import tempfile
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox

import markdown
import mammoth
from ebooklib import epub
from bs4 import BeautifulSoup
from docx import Document  # python-docx

# fallback COM per .docx import
try:
    import win32com.client
    HAS_COM = True
except ImportError:
    HAS_COM = False


def read_text_file(path):
    """
    Prova a leggere il file path con più encodings:
    utf-8, cp1252, latin-1. Se tutte falliscono, solleva UnicodeDecodeError.
    """
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(
        "read_text_file", b"", 0, 1,
        f"Impossibile decodificare {path} con utf-8, cp1252 o latin-1"
    )


def find_soffice_executable():
    """
    Ritorna il path di soffice (LibreOffice), cercando prima in PATH,
    poi nelle installazioni Windows standard.
    """
    soffice = shutil.which("soffice")
    if soffice:
        return soffice
    for base in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)")):
        if base:
            candidate = os.path.join(base, "LibreOffice", "program", "soffice.exe")
            if os.path.isfile(candidate):
                return candidate
    raise RuntimeError(
        "LibreOffice non trovato in PATH né nelle cartelle standard di Windows.\n"
        "Installa LibreOffice o aggiungi 'soffice' alla variabile PATH."
    )


def html_to_docx(html: str, save_path: str, title: str):
    """
    Converte un frammento HTML in un .docx puro usando python-docx.
    """
    soup = BeautifulSoup(html, "html.parser")
    doc = Document()
    doc.add_heading(title, level=1)

    for elem in soup.find_all(['h1','h2','h3','h4','h5','h6','p','ul','ol']):
        if elem.name == 'p':
            doc.add_paragraph(elem.get_text())
        elif elem.name.startswith('h') and elem.name[1:].isdigit():
            lvl = int(elem.name[1])
            doc.add_heading(elem.get_text(), level=min(lvl, 4))
        elif elem.name in ('ul', 'ol'):
            is_ordered = (elem.name == 'ol')
            for li in elem.find_all('li', recursive=False):
                style = 'List Number' if is_ordered else 'List Bullet'
                para = doc.add_paragraph(style=style)
                para.add_run(li.get_text())
    
    doc.save(save_path)


def save_output(html, save_path, title):
    """
    Salva l'HTML generato come .html, .epub, .docx o .doc a seconda dell'estensione.
    """
    ext = os.path.splitext(save_path)[1].lower()

    if ext == ".html":
        with open(save_path, "w", encoding="utf-8") as out:
            out.write(html)

    elif ext == ".epub":
        # parsing headings e generazione TOC multi-livello
        soup = BeautifulSoup(html, 'html.parser')
        headings = []
        for idx, tag in enumerate(soup.find_all(['h1','h2','h3','h4','h5','h6'])):
            level = int(tag.name[1])
            hid = f'heading_{idx}'
            tag['id'] = hid
            headings.append({'level': level, 'title': tag.get_text(), 'id': hid})

        html_with_ids = str(soup)

        book = epub.EpubBook()
        book.set_identifier("id123456")
        book.set_title(title)
        book.set_language("en")

        chapter = epub.EpubHtml(title=title, file_name='chap.xhtml', content=html_with_ids)
        book.add_item(chapter)

        # costruisci struttura TOC
        toc = []
        stack = [{'level': 0, 'children': toc}]
        for h in headings:
            node = {'level': h['level'],
                    'link': epub.Link('chap.xhtml#'+h['id'], h['title'], h['id']),
                    'children': []}
            while stack and h['level'] <= stack[-1]['level']:
                stack.pop()
            stack[-1]['children'].append(node)
            stack.append(node)

        def build_nav(items):
            nav = []
            for item in items:
                if item['children']:
                    nav.append((item['link'], build_nav(item['children'])))
                else:
                    nav.append(item['link'])
            return nav

        book.toc = build_nav(toc)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ['nav', chapter]
        epub.write_epub(save_path, book, {})

    elif ext == ".docx":
        html_to_docx(html, save_path, title)

    elif ext == ".doc":
        tmpdir = tempfile.mkdtemp()
        try:
            tmp_docx = os.path.join(tmpdir, "temp.docx")
            html_to_docx(html, tmp_docx, title)
            soffice = find_soffice_executable()
            subprocess.run(
                [soffice, "--headless", "--convert-to", "doc", "--outdir", tmpdir, tmp_docx],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            )
            tmp_out = os.path.join(tmpdir, "temp.doc")
            if not os.path.exists(tmp_out):
                raise RuntimeError("Conversione in .doc fallita: output mancante")
            shutil.copy(tmp_out, save_path)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    else:
        raise RuntimeError(f"Formato di output non supportato: {ext}")


def convert_file():
    file_path = filedialog.askopenfilename(
        title="Seleziona file da convertire",
        filetypes=[
            ("Markdown", "*.md"),
            ("Word (.docx)", "*.docx"),
            ("Word (.doc)", "*.doc")
        ]
    )
    if not file_path:
        return

    save_path = filedialog.asksaveasfilename(
        defaultextension=".html",
        filetypes=[
            ("HTML", "*.html"),
            ("EPUB", "*.epub"),
            ("Word (.docx)", "*.docx"),
            ("Word (.doc)", "*.doc")
        ],
        title="Salva come…"
    )
    if not save_path:
        return

    ext_in = os.path.splitext(file_path)[1].lower()

    try:
        if ext_in == ".md":
            text = read_text_file(file_path)
            html = markdown.markdown(text)

        elif ext_in == ".docx":
            try:
                with open(file_path, "rb") as docx_file:
                    res = mammoth.convert_to_html(docx_file)
                html = res.value
            except PermissionError:
                if not HAS_COM:
                    raise RuntimeError(
                        "PermissionError .docx e pywin32 non installato.\n"
                        "Chiudi Word/OneDrive o pip install pywin32."
                    )
                word = win32com.client.Dispatch('Word.Application')
                word.Visible = False
                doc = word.Documents.Open(os.path.abspath(file_path), ReadOnly=True)
                tmp = os.path.join(tempfile.gettempdir(), "temp_convert.html")
                doc.SaveAs(tmp, FileFormat=8)
                doc.Close(False); word.Quit()
                html = read_text_file(tmp); os.remove(tmp)

        elif ext_in == ".doc":
            soffice = find_soffice_executable()
            tmpdir = tempfile.mkdtemp()
            try:
                subprocess.run(
                    [soffice, "--headless", "--convert-to", "html", "--outdir", tmpdir, file_path],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
                )
                fname = os.path.splitext(os.path.basename(file_path))[0] + ".html"
                html = read_text_file(os.path.join(tmpdir, fname))
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)

        else:
            messagebox.showerror("Formato non supportato", f"Estensione {ext_in} non gestita.")
            return

        title = os.path.splitext(os.path.basename(file_path))[0]
        save_output(html, save_path, title)
        messagebox.showinfo("Fatto", f"Esportazione riuscita:\n{save_path}")

    except Exception as e:
        messagebox.showerror("Errore", str(e))


def main():
    root = tk.Tk()
    root.title("Convertitore Markdown/DOC → HTML/EPUB/DOCX/DOC")
    root.geometry("560x200")
    root.resizable(False, False)

    lbl = tk.Label(
        root,
        text="Seleziona un file Markdown o Word e convertilo in HTML, EPUB, DOCX o DOC",
        wraplength=540
    )
    lbl.pack(pady=15)

    btn = tk.Button(
        root,
        text="Scegli e Converti",
        command=convert_file,
        width=28, height=2
    )
    btn.pack()

    root.mainloop()

if __name__ == "__main__":
    main()
