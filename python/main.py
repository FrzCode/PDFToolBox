"""
PDF Suite – tutto in un file
Dipendenze: pip install ttkbootstrap pymupdf Pillow
"""

import os
import io
import uuid
import sys
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from PIL import Image, ImageTk
import fitz  # PyMuPDF


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS GLOBALI
# ═══════════════════════════════════════════════════════════════════════════════

def page_to_photo(page, zoom=0.22):
    """Converte una pagina fitz in PhotoImage."""
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    img = Image.open(io.BytesIO(pix.tobytes("ppm")))
    return ImageTk.PhotoImage(img)


def make_scrollable_canvas(parent):
    """Crea canvas + scrollbar verticale. Ritorna (canvas, inner_frame)."""
    frame = ttk.Frame(parent)
    frame.pack(fill=BOTH, expand=True)

    canvas = tk.Canvas(frame, bg="#f8f9fa", highlightthickness=0)
    sb = ttk.Scrollbar(frame, orient=VERTICAL, command=canvas.yview)
    canvas.configure(yscrollcommand=sb.set)
    sb.pack(side=RIGHT, fill=Y)
    canvas.pack(side=LEFT, fill=BOTH, expand=True)

    inner = ttk.Frame(canvas)
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_configure(e):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _on_canvas_resize(e):
        canvas.itemconfig(win_id, width=e.width)

    inner.bind("<Configure>", _on_configure)
    canvas.bind("<Configure>", _on_canvas_resize)
    canvas.bind_all("<MouseWheel>",
                    lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    return canvas, inner


def normalizza_toc(toc):
    """Rende valido un indice per set_toc: il primo livello è 1 e ogni voce
    scende al massimo di un livello rispetto alla precedente."""
    out, prec = [], 0
    for lvl, titolo, pag in toc:
        lvl = max(1, min(lvl, prec + 1))
        out.append([lvl, titolo, pag])
        prec = lvl
    return out


def salva_pdf_doc(doc, path):
    """Salva doc in path, anche se path è il file da cui doc è stato aperto.
    Ritorna (documento, errore). Il documento va riassegnato, perché nel caso
    di salvataggio sullo stesso file viene riaperto dal file appena scritto."""
    nome = doc.name
    stesso = bool(nome) and os.path.exists(nome) and os.path.exists(path) \
        and os.path.samefile(nome, path)
    if not stesso:
        try:
            doc.save(path)
            return doc, None
        except Exception as e:
            return doc, e
    tmp = path + ".tmp_save"
    try:
        with open(tmp, "wb") as f:
            f.write(doc.tobytes())
        doc.close()
        os.replace(tmp, path)
        return fitz.open(path), None
    except Exception as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        if doc.is_closed:
            doc = fitz.open(nome)
        return doc, e


CARATTERI_NON_VALIDI = set('\\/:*?"<>|')


def nome_file_valido(nome):
    """Controlla che un nome di file (con estensione) sia accettato dal filesystem."""
    base = nome[:-4] if nome.lower().endswith(".pdf") else os.path.splitext(nome)[0]
    if not base.strip():
        return False
    if any(c in CARATTERI_NON_VALIDI or ord(c) < 32 for c in nome):
        return False
    return nome == nome.rstrip(" .")


def applica_rinomine(coppie):
    """Rinomina [(da, a), ...] in due fasi, passando da nomi temporanei, così
    scambi e catene di nomi funzionano. Non sovrascrive mai un file esistente.
    In caso di errore ripristina tutto e rilancia l'eccezione."""
    temp_map, terminati = [], set()
    try:
        for da, a in coppie:
            tmp = os.path.join(os.path.dirname(da), f".tmp_{uuid.uuid4().hex}.ren")
            os.rename(da, tmp)
            temp_map.append((tmp, a, da))
        for tmp, a, _ in temp_map:
            if os.path.exists(a):
                raise FileExistsError(f"Esiste già un file chiamato {os.path.basename(a)}")
            os.rename(tmp, a)
            terminati.add(tmp)
    except Exception:
        for tmp, a, _ in temp_map:
            if tmp in terminati:
                os.rename(a, tmp)
        for tmp, _, da in temp_map:
            os.rename(tmp, da)
        raise


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 1 – UNISCI PDF
# ═══════════════════════════════════════════════════════════════════════════════

class TabUnisci(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Unisci PDF", font=("Helvetica", 15, "bold")).pack(pady=(0, 8))

        # Listbox
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=BOTH, expand=True, pady=5)

        self.listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE,
                                  font=("Helvetica", 11), height=14,
                                  bg="#ffffff", relief="flat",
                                  highlightthickness=1, highlightcolor="#dee2e6")
        sb = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        self.listbox.pack(side=LEFT, fill=BOTH, expand=True)

        # Pulsanti
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=X, pady=8)

        ttk.Button(btn_frame, text="➕  Aggiungi PDF",
                   bootstyle=PRIMARY, command=self.add_files).pack(side=LEFT, padx=3)
        ttk.Button(btn_frame, text="🗑  Rimuovi",
                   bootstyle=SECONDARY, command=self.remove_selected).pack(side=LEFT, padx=3)
        ttk.Button(btn_frame, text="⬆  Su",
                   bootstyle=WARNING, command=self.move_up).pack(side=LEFT, padx=3)
        ttk.Button(btn_frame, text="⬇  Giù",
                   bootstyle=WARNING, command=self.move_down).pack(side=LEFT, padx=3)
        ttk.Button(btn_frame, text="✔  Unisci PDF",
                   bootstyle=SUCCESS, command=self.merge_pdfs).pack(side=RIGHT, padx=3)

    def add_files(self):
        files = filedialog.askopenfilenames(
            title="Seleziona i PDF da unire",
            filetypes=[("File PDF", "*.pdf")])
        existing = list(self.listbox.get(0, END))
        for f in files:
            if f not in existing:
                self.listbox.insert(END, f)

    def remove_selected(self):
        sel = self.listbox.curselection()
        for i in reversed(sel):
            self.listbox.delete(i)

    def move_up(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        val = self.listbox.get(i)
        self.listbox.delete(i)
        self.listbox.insert(i - 1, val)
        self.listbox.select_set(i - 1)

    def move_down(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == self.listbox.size() - 1:
            return
        i = sel[0]
        val = self.listbox.get(i)
        self.listbox.delete(i)
        self.listbox.insert(i + 1, val)
        self.listbox.select_set(i + 1)

    def merge_pdfs(self):
        files = list(self.listbox.get(0, END))
        if len(files) < 2:
            messagebox.showwarning("Attenzione", "Aggiungi almeno due PDF.")
            return
        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("File PDF", "*.pdf")],
            title="Salva PDF unito come")
        if not save_path:
            return
        try:
            writer = fitz.open()
            toc_unito, offset = [], 0
            for path in files:
                doc = fitz.open(path)
                for lvl, titolo, pag in doc.get_toc():
                    if pag >= 1:
                        toc_unito.append([lvl, titolo, pag + offset])
                offset += doc.page_count
                writer.insert_pdf(doc)
                doc.close()
            if toc_unito:
                writer.set_toc(normalizza_toc(toc_unito))
            writer.save(save_path)
            writer.close()
            messagebox.showinfo("Successo", f"PDF unito salvato in:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Errore", str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 2 – RIORDINA PAGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TabRiordina(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.pdf_path = None
        self.photos = []      # PhotoImage references
        self.page_order = []  # lista indici pagine nell'ordine corrente
        self.selected = set()
        self.drag_from = None
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Riordina pagine", font=("Helvetica", 15, "bold")).pack(pady=(0, 4))

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=X, pady=5)
        ttk.Button(btn_frame, text="📂  Apri PDF",
                   bootstyle=PRIMARY, command=self.open_pdf).pack(side=LEFT, padx=3)
        ttk.Button(btn_frame, text="⬆  Sposta su",
                   bootstyle=WARNING, command=self.move_up).pack(side=LEFT, padx=3)
        ttk.Button(btn_frame, text="⬇  Sposta giù",
                   bootstyle=WARNING, command=self.move_down).pack(side=LEFT, padx=3)
        ttk.Button(btn_frame, text="🗑  Elimina selezionate",
                   bootstyle=DANGER, command=self.delete_selected).pack(side=LEFT, padx=3)
        ttk.Button(btn_frame, text="💾  Salva PDF",
                   bootstyle=SUCCESS, command=self.save_pdf).pack(side=RIGHT, padx=3)
        ttk.Button(btn_frame, text="📤  Esporta selezione",
                   bootstyle=INFO, command=self.export_selected).pack(side=RIGHT, padx=3)

        self.info_lbl = ttk.Label(self, text="Nessun PDF aperto", foreground="#6c757d")
        self.info_lbl.pack(anchor=W, pady=2)

        self.canvas, self.inner = make_scrollable_canvas(self)

    def open_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        self.pdf_path = path
        self._load_doc()

    def _load_doc(self):
        doc = fitz.open(self.pdf_path)
        self.photos = [page_to_photo(p) for p in doc]
        self.page_order = list(range(len(self.photos)))
        doc.close()
        self.selected.clear()
        self.info_lbl.config(text=f"{os.path.basename(self.pdf_path)}  –  {len(self.page_order)} pagine")
        self._redraw()

    def _redraw(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self.thumb_labels = []
        COLS = 4
        row_frame = None
        for i, pg_idx in enumerate(self.page_order):
            if i % COLS == 0:
                row_frame = ttk.Frame(self.inner)
                row_frame.pack(fill=X, pady=4, padx=8)
            lbl = ttk.Label(row_frame, image=self.photos[pg_idx],
                            text=f"  {pg_idx + 1}  ", compound=TOP,
                            cursor="hand2")
            lbl.pack(side=LEFT, padx=6)
            lbl.bind("<Button-1>", lambda e, idx=i: self._toggle(idx, e))
            lbl.bind("<ButtonPress-3>", lambda e, idx=i: self._drag_start(idx))
            lbl.bind("<ButtonRelease-3>", lambda e, idx=i: self._drag_end(idx))
            self.thumb_labels.append(lbl)
        self._update_colors()

    def _toggle(self, idx, event):
        if event.state & 0x0004:
            self.selected ^= {idx}
        else:
            self.selected = {idx}
        self._update_colors()

    def _update_colors(self):
        for i, lbl in enumerate(self.thumb_labels):
            lbl.configure(background="#0d6efd" if i in self.selected else "")

    def _drag_start(self, idx):
        self.drag_from = idx

    def _drag_end(self, idx):
        if self.drag_from is not None and self.drag_from != idx:
            o = self.page_order
            o[self.drag_from], o[idx] = o[idx], o[self.drag_from]
            self.selected = {idx}
        self.drag_from = None
        self._redraw()

    def move_up(self):
        if not self.selected:
            return
        idx = min(self.selected)
        if idx > 0:
            self.page_order[idx - 1], self.page_order[idx] = \
                self.page_order[idx], self.page_order[idx - 1]
            self.selected = {idx - 1}
            self._redraw()

    def move_down(self):
        if not self.selected:
            return
        idx = max(self.selected)
        if idx < len(self.page_order) - 1:
            self.page_order[idx + 1], self.page_order[idx] = \
                self.page_order[idx], self.page_order[idx + 1]
            self.selected = {idx + 1}
            self._redraw()

    def delete_selected(self):
        if not self.selected:
            return
        if not messagebox.askyesno("Conferma", f"Elimino {len(self.selected)} pagina/e?"):
            return
        for i in sorted(self.selected, reverse=True):
            self.page_order.pop(i)
        self.selected.clear()
        self._redraw()

    def save_pdf(self):
        """Salva tutte le pagine nell'ordine mostrato."""
        self._salva(range(len(self.page_order)))

    def export_selected(self):
        """Salva solo le pagine selezionate, nell'ordine mostrato."""
        if not self.selected:
            messagebox.showwarning("Attenzione", "Seleziona almeno una pagina.")
            return
        self._salva(sorted(self.selected))

    def _salva(self, indices):
        if not self.pdf_path:
            return
        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not save_path:
            return
        try:
            stesso = os.path.exists(save_path) and \
                os.path.samefile(self.pdf_path, save_path)
            original = fitz.open(self.pdf_path)
            new_doc = fitz.open()
            for i in indices:
                pg = self.page_order[i]
                new_doc.insert_pdf(original, from_page=pg, to_page=pg)
            original.close()
            tmp = save_path + ".tmp_save"
            new_doc.save(tmp)
            new_doc.close()
            os.replace(tmp, save_path)
        except Exception as e:
            messagebox.showerror("Errore", str(e))
            return
        messagebox.showinfo("Salvato", f"{len(indices)} pagine salvate in:\n{save_path}")
        if stesso:
            # il file aperto è stato riscritto: ricarica per riallineare le pagine
            self._load_doc()


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 3 – SOSTITUISCI PAGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TabSostituisci(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.doc = None
        self.pdf_path = None
        self.photos = []
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Sostituisci pagine", font=("Helvetica", 15, "bold")).pack(pady=(0, 4))

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=X, pady=5)
        ttk.Button(btn_frame, text="📂  Apri PDF",
                   bootstyle=PRIMARY, command=self.open_pdf).pack(side=LEFT, padx=3)
        ttk.Button(btn_frame, text="💾  Salva come…",
                   bootstyle=SUCCESS, command=self.save_pdf).pack(side=RIGHT, padx=3)

        self.info_lbl = ttk.Label(self,
            text="Apri un PDF, poi clicca su una pagina per sostituirla.",
            foreground="#6c757d")
        self.info_lbl.pack(anchor=W, pady=2)

        self.canvas, self.inner = make_scrollable_canvas(self)

    def open_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        self.pdf_path = path
        if self.doc:
            self.doc.close()
        self.doc = fitz.open(path)
        self._render()

    def _render(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self.photos = [page_to_photo(p) for p in self.doc]
        self.info_lbl.config(
            text=f"{os.path.basename(self.pdf_path)}  –  {len(self.photos)} pagine  |  "
                 "clicca una miniatura per sostituire quella pagina")
        COLS = 4
        row_frame = None
        for i, photo in enumerate(self.photos):
            if i % COLS == 0:
                row_frame = ttk.Frame(self.inner)
                row_frame.pack(fill=X, pady=4, padx=8)
            btn = ttk.Button(row_frame, image=photo, text=f"  {i + 1}  ",
                             compound=TOP, bootstyle="outline-secondary",
                             command=lambda idx=i: self._replace(idx))
            btn.image = photo  # prevent GC
            btn.pack(side=LEFT, padx=6)

    def _replace(self, index):
        if not self.doc:
            return
        path = filedialog.askopenfilename(
            title=f"PDF sostituto per pagina {index + 1}",
            filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        try:
            src = fitz.open(path)
            if src.page_count == 0:
                messagebox.showerror("Errore", "Il PDF sostituto è vuoto.")
                return
            self.doc.delete_page(index)
            self.doc.insert_pdf(src, from_page=0, to_page=0, start_at=index)
            src.close()
            self._render()
            messagebox.showinfo("Fatto", f"Pagina {index + 1} sostituita.")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def save_pdf(self):
        if not self.doc:
            messagebox.showwarning("Attenzione", "Nessun PDF aperto.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        self.doc, err = salva_pdf_doc(self.doc, path)
        if err:
            messagebox.showerror("Errore", str(err))
        else:
            messagebox.showinfo("Salvato", f"PDF salvato in:\n{path}")


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 4 – DIVIDI / ESTRAI PAGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TabDividi(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.pdf_path = None
        self.photos = []
        self.check_vars = []
        self.zoom = 0.22
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Dividi / estrai pagine", font=("Helvetica", 15, "bold")).pack(pady=(0, 4))

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=X, pady=5)
        ttk.Button(btn_frame, text="📂  Apri PDF",
                   bootstyle=PRIMARY, command=self.open_pdf).pack(side=LEFT, padx=3)
        ttk.Button(btn_frame, text="✅  Tutte",
                   bootstyle=SECONDARY, command=self.select_all).pack(side=LEFT, padx=3)
        ttk.Button(btn_frame, text="⬜  Nessuna",
                   bootstyle=SECONDARY, command=self.deselect_all).pack(side=LEFT, padx=3)
        ttk.Button(btn_frame, text="➕  Zoom",
                   bootstyle=LIGHT, command=self.zoom_in).pack(side=LEFT, padx=2)
        ttk.Button(btn_frame, text="➖  Zoom",
                   bootstyle=LIGHT, command=self.zoom_out).pack(side=LEFT, padx=2)

        # Range testuale
        range_frame = ttk.Frame(self)
        range_frame.pack(fill=X, pady=4)
        ttk.Label(range_frame, text="Oppure inserisci intervallo (es. 1-3; 5; 7-9):").pack(side=LEFT, padx=3)
        self.range_entry = ttk.Entry(range_frame, width=30)
        self.range_entry.pack(side=LEFT, padx=5)
        ttk.Button(range_frame, text="📤  Esporta",
                   bootstyle=SUCCESS, command=self.export).pack(side=LEFT, padx=3)

        self.info_lbl = ttk.Label(self, text="Nessun PDF aperto.", foreground="#6c757d")
        self.info_lbl.pack(anchor=W, pady=2)

        self.canvas, self.inner = make_scrollable_canvas(self)

    def open_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        self.pdf_path = path
        self._render()

    def _render(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self.check_vars = []
        doc = fitz.open(self.pdf_path)
        self.photos = [page_to_photo(p, zoom=self.zoom) for p in doc]
        doc.close()
        self.info_lbl.config(
            text=f"{os.path.basename(self.pdf_path)}  –  {len(self.photos)} pagine")
        COLS = 4
        row_frame = None
        for i, photo in enumerate(self.photos):
            if i % COLS == 0:
                row_frame = ttk.Frame(self.inner)
                row_frame.pack(fill=X, pady=4, padx=8)
            cell = ttk.Frame(row_frame)
            cell.pack(side=LEFT, padx=6)
            lbl = ttk.Label(cell, image=photo)
            lbl.pack()
            var = tk.BooleanVar()
            self.check_vars.append(var)
            ttk.Checkbutton(cell, text=f"Pag. {i + 1}", variable=var).pack()

    def select_all(self):
        for v in self.check_vars:
            v.set(True)

    def deselect_all(self):
        for v in self.check_vars:
            v.set(False)

    def zoom_in(self):
        self.zoom = min(self.zoom + 0.06, 0.7)
        if self.pdf_path:
            self._render()

    def zoom_out(self):
        self.zoom = max(self.zoom - 0.06, 0.1)
        if self.pdf_path:
            self._render()

    def _parse_range(self, text, total):
        """Ritorna lista di indici 0-based da stringa tipo '1-3; 5; 7-9'."""
        pages = set()
        for part in text.replace(",", ";").split(";"):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-", 1)
                for n in range(int(a), int(b) + 1):
                    if 1 <= n <= total:
                        pages.add(n - 1)
            else:
                n = int(part)
                if 1 <= n <= total:
                    pages.add(n - 1)
        return sorted(pages)

    def export(self):
        if not self.pdf_path:
            messagebox.showwarning("Attenzione", "Prima apri un PDF.")
            return

        total = len(self.photos)
        # Priorità: checkbox > range testuale
        selected = [i for i, v in enumerate(self.check_vars) if v.get()]
        range_text = self.range_entry.get().strip()
        if not selected and range_text:
            try:
                selected = self._parse_range(range_text, total)
            except ValueError:
                messagebox.showerror("Errore", "Intervallo non valido.")
                return

        if not selected:
            messagebox.showwarning("Attenzione", "Seleziona almeno una pagina.")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not save_path:
            return

        try:
            src = fitz.open(self.pdf_path)
            out = fitz.open()
            for i in selected:
                out.insert_pdf(src, from_page=i, to_page=i)
            out.save(save_path)
            out.close()
            src.close()
            messagebox.showinfo("Esportato",
                                f"{len(selected)} pagine salvate in:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Errore", str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 5 – RINOMINA BATCH
# ═══════════════════════════════════════════════════════════════════════════════

class TabRinomina(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self._init_vars()
        self._build_ui()
        self.undo_stack = []
        self.redo_stack = []

    def _init_vars(self):
        self.cartella_var     = tk.StringVar()
        self.prefisso_var     = tk.StringVar()
        self.basename_var     = tk.StringVar()
        self.suffisso_var     = tk.StringVar()
        self.numerazione_var  = tk.BooleanVar(value=False)
        self.posizione_var    = tk.StringVar(value="dopo_base")
        self.start_var        = tk.IntVar(value=1)
        self.digits_var       = tk.IntVar(value=3)
        self.remove_mode      = tk.StringVar(value="none")
        self.remove_first_n   = tk.IntVar(value=1)
        self.remove_last_n    = tk.IntVar(value=1)
        self.remove_from      = tk.IntVar(value=0)
        self.remove_to        = tk.IntVar(value=0)

    def _build_ui(self):
        ttk.Label(self, text="Rinomina batch PDF", font=("Helvetica", 15, "bold")).pack(pady=(0, 6))

        # ── Cartella ──────────────────────────────────────────────────────────
        cf = ttk.Frame(self)
        cf.pack(fill=X, pady=3)
        ttk.Button(cf, text="📁  Scegli cartella",
                   bootstyle=PRIMARY, command=self.scegli_cartella).pack(side=LEFT, padx=3)
        ttk.Entry(cf, textvariable=self.cartella_var,
                  state="readonly", width=70).pack(side=LEFT, fill=X, expand=True, padx=4)

        # ── Treeview ──────────────────────────────────────────────────────────
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=BOTH, expand=True, pady=5)

        cols = ("File originale", "Nuovo nome")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                  selectmode="extended", height=10)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, anchor=W, width=320)
        sb = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        self.tree.tag_configure("mod", background="#fff8dc")

        # Menu tasto destro
        self.menu_dx = tk.Menu(self, tearoff=0)
        self.menu_dx.add_command(label="Rinomina singolo…", command=self.rename_single)
        self.tree.bind("<Button-3>", lambda e: (
            self.menu_dx.tk_popup(e.x_root, e.y_root)
            if self.tree.identify_row(e.y) else None))
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.aggiorna_preview())

        # ── Parametri ─────────────────────────────────────────────────────────
        fp = ttk.Labelframe(self, text="Parametri di rinomina", padding=8)
        fp.pack(fill=X, pady=5)

        # Riga 0: etichette
        for col, txt in enumerate(["Prefisso", "Base (sovrascrive)", "Suffisso"]):
            ttk.Label(fp, text=txt).grid(row=0, column=col, padx=4, sticky=W)

        self.entry_pref = ttk.Entry(fp, textvariable=self.prefisso_var, width=18)
        self.entry_base = ttk.Entry(fp, textvariable=self.basename_var, width=18)
        self.entry_suff = ttk.Entry(fp, textvariable=self.suffisso_var, width=18)
        self.entry_pref.grid(row=1, column=0, padx=4)
        self.entry_base.grid(row=1, column=1, padx=4)
        self.entry_suff.grid(row=1, column=2, padx=4)

        # Numerazione
        self.chk_num = ttk.Checkbutton(fp, text="Aggiungi numerazione",
                                        variable=self.numerazione_var,
                                        command=self._toggle_num)
        self.chk_num.grid(row=0, column=3, padx=6, sticky=W)
        ttk.Label(fp, text="Start").grid(row=0, column=4, sticky=E)
        self.spin_start = ttk.Spinbox(fp, from_=0, to=9999, width=5,
                                       textvariable=self.start_var)
        self.spin_start.grid(row=1, column=4, padx=2)
        ttk.Label(fp, text="Cifre").grid(row=0, column=5, sticky=E)
        self.spin_digits = ttk.Spinbox(fp, from_=1, to=6, width=3,
                                        textvariable=self.digits_var)
        self.spin_digits.grid(row=1, column=5, padx=2)

        # Posizione numero
        pos_frame = ttk.Frame(fp)
        pos_frame.grid(row=2, column=0, columnspan=6, pady=4, sticky=W)
        for val, lbl in [("inizio","Inizio"), ("dopo_pref","Dopo prefisso"),
                          ("dopo_base","Dopo base"), ("fine","Fine")]:
            rb = ttk.Radiobutton(pos_frame, text=lbl, value=val,
                                  variable=self.posizione_var,
                                  command=self.aggiorna_preview)
            rb.pack(side=LEFT, padx=4)
            self._rb_pos_widgets = getattr(self, "_rb_pos_widgets", [])
            self._rb_pos_widgets.append(rb)

        # Taglia caratteri
        fc = ttk.Labelframe(fp, text="Taglia caratteri dal nome", padding=6)
        fc.grid(row=3, column=0, columnspan=6, pady=4, sticky=W+E)

        self.rb_none = ttk.Radiobutton(fc, text="No taglio", value="none",
                                        variable=self.remove_mode, command=self._toggle_remove)
        self.rb_first = ttk.Radiobutton(fc, text="Primi", value="first",
                                         variable=self.remove_mode, command=self._toggle_remove)
        self.spin_first = ttk.Spinbox(fc, from_=1, to=99, width=4,
                                       textvariable=self.remove_first_n)
        self.rb_last = ttk.Radiobutton(fc, text="Ultimi", value="last",
                                        variable=self.remove_mode, command=self._toggle_remove)
        self.spin_last = ttk.Spinbox(fc, from_=1, to=99, width=4,
                                      textvariable=self.remove_last_n)
        self.rb_range = ttk.Radiobutton(fc, text="Dal car.", value="range",
                                         variable=self.remove_mode, command=self._toggle_remove)
        self.spin_from = ttk.Spinbox(fc, from_=0, to=99, width=4,
                                      textvariable=self.remove_from)
        ttk.Label(fc, text="al").pack(side=LEFT)
        self.spin_to = ttk.Spinbox(fc, from_=0, to=99, width=4,
                                    textvariable=self.remove_to)

        for w in [self.rb_none, self.rb_first, self.spin_first, self.rb_last,
                   self.spin_last, self.rb_range, self.spin_from, self.spin_to]:
            w.pack(side=LEFT, padx=3)

        # ── Pulsanti azione ───────────────────────────────────────────────────
        act_frame = ttk.Frame(self)
        act_frame.pack(fill=X, pady=4)
        self.btn_undo = ttk.Button(act_frame, text="↶ Undo",
                                    bootstyle=SECONDARY, command=self.undo, state=DISABLED)
        self.btn_redo = ttk.Button(act_frame, text="↷ Redo",
                                    bootstyle=SECONDARY, command=self.redo, state=DISABLED)
        self.btn_rinomina = ttk.Button(act_frame, text="✔  Rinomina",
                                        bootstyle=SUCCESS, command=self.rinomina, state=DISABLED)
        self.btn_undo.pack(side=LEFT, padx=3)
        self.btn_redo.pack(side=LEFT, padx=3)
        self.btn_rinomina.pack(side=RIGHT, padx=5)

        self.stato_lbl = ttk.Label(self, text="", foreground="#6c757d")
        self.stato_lbl.pack(anchor=W, padx=4)

        # Live trace
        for v in (self.prefisso_var, self.basename_var, self.suffisso_var,
                   self.start_var, self.digits_var,
                   self.remove_first_n, self.remove_last_n,
                   self.remove_from, self.remove_to):
            v.trace_add("write", lambda *_: self.aggiorna_preview())

    # ── Logica ────────────────────────────────────────────────────────────────

    def scegli_cartella(self):
        path = filedialog.askdirectory(title="Seleziona cartella con PDF")
        if not path:
            return
        self.cartella_var.set(path)
        self.carica_file()

    def carica_file(self):
        self.tree.delete(*self.tree.get_children())
        folder = self.cartella_var.get()
        if not folder:
            return
        for nome in sorted(os.listdir(folder)):
            if nome.lower().endswith(".pdf"):
                iid = os.path.join(folder, nome)
                self.tree.insert("", END, iid=iid, values=(nome, ""))
        n = len(self.tree.get_children())
        self.stato_lbl.config(text=f"Trovati {n} PDF." if n else "Nessun PDF trovato.")

    def _apply_remove(self, base):
        mode = self.remove_mode.get()
        try:
            if mode == "first":
                n = max(0, self.remove_first_n.get())
                return base[n:] or base
            elif mode == "last":
                n = max(0, self.remove_last_n.get())
                return base[:-n] or base
            elif mode == "range":
                a, b = self.remove_from.get(), self.remove_to.get()
                if 0 <= a <= b < len(base):
                    return base[:a] + base[b + 1:]
        except tk.TclError:
            pass
        return base

    def aggiorna_preview(self, *_):
        sel = self.tree.selection()
        if not sel:
            self.btn_rinomina.config(state=DISABLED)
            for iid in self.tree.get_children():
                self.tree.item(iid, tags=())
            return
        sel_ord = sorted(sel, key=lambda r: list(self.tree.get_children()).index(r))
        idx_map = {iid: idx for idx, iid in enumerate(sel_ord, start=self.start_var.get())}
        for iid in sel:
            old = self.tree.set(iid, "#1")
            base, ext = os.path.splitext(old)
            base_cut = self._apply_remove(base)
            new_base = self.basename_var.get() or base_cut
            numero = ""
            if self.numerazione_var.get():
                numero = str(idx_map[iid]).zfill(self.digits_var.get())
            parts = {"pref": self.prefisso_var.get(), "base": new_base,
                     "suff": self.suffisso_var.get(), "num": numero}
            order = {
                "inizio":    ("num", "pref", "base", "suff"),
                "dopo_pref": ("pref", "num", "base", "suff"),
                "dopo_base": ("pref", "base", "num", "suff"),
                "fine":      ("pref", "base", "suff", "num"),
            }[self.posizione_var.get()]
            nuovo = "".join(parts[k] for k in order) + ext
            self.tree.set(iid, "#2", nuovo)
            self.tree.item(iid, tags=("mod",) if nuovo != old else ())
        self.btn_rinomina.config(state=NORMAL)

    def _toggle_num(self):
        self.aggiorna_preview()

    def _toggle_remove(self):
        self.aggiorna_preview()

    def rinomina(self):
        sel = [iid for iid in self.tree.selection()
               if "mod" in self.tree.item(iid, "tags")]
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona almeno un file da rinominare.")
            return
        mapping, nuovi_set = [], set()
        vecchi = {os.path.normcase(iid) for iid in sel}
        for iid in sel:
            new_name = self.tree.set(iid, "#2")
            if not nome_file_valido(new_name):
                messagebox.showerror("Errore", f"Nome non valido: {new_name!r}")
                return
            new_path = os.path.join(self.cartella_var.get(), new_name)
            chiave = os.path.normcase(new_path)
            if chiave in nuovi_set:
                messagebox.showerror("Errore", f"Nome duplicato: {new_name}")
                return
            if os.path.exists(new_path) and chiave not in vecchi:
                messagebox.showerror("Errore",
                                     f"Esiste già un file con questo nome: {new_name}")
                return
            nuovi_set.add(chiave)
            mapping.append((iid, new_path))
        # Conferma
        preview = "\n".join(f"{os.path.basename(o)} → {os.path.basename(n)}"
                             for o, n in mapping[:10])
        extra = f"\n… (+{len(mapping)-10} altri)" if len(mapping) > 10 else ""
        if not messagebox.askyesno("Conferma", f"Rinomino {len(mapping)} file:\n\n{preview}{extra}"):
            return
        try:
            applica_rinomine(mapping)
        except Exception as e:
            messagebox.showerror("Errore", f"{e}\nRollback eseguito.")
            return
        # ogni voce dello stack è (nome attuale, nome precedente)
        self.undo_stack.append([(new, old) for old, new in mapping])
        self.redo_stack.clear()
        self.carica_file()
        self.stato_lbl.config(text=f"{len(mapping)} file rinominati ✓")
        self._update_undo_redo()

    def undo(self):
        if not self.undo_stack:
            return
        batch = self.undo_stack.pop()
        try:
            applica_rinomine([(att, prec) for att, prec in batch
                              if os.path.exists(att)])
        except Exception as e:
            self.undo_stack.append(batch)
            messagebox.showerror("Errore", f"{e}\nRollback eseguito.")
            return
        self.redo_stack.append(batch)
        self.carica_file()
        self.stato_lbl.config(text="Undo eseguito ↶")
        self._update_undo_redo()

    def redo(self):
        if not self.redo_stack:
            return
        batch = self.redo_stack.pop()
        try:
            applica_rinomine([(prec, att) for att, prec in batch
                              if os.path.exists(prec)])
        except Exception as e:
            self.redo_stack.append(batch)
            messagebox.showerror("Errore", f"{e}\nRollback eseguito.")
            return
        self.undo_stack.append(batch)
        self.carica_file()
        self.stato_lbl.config(text="Redo eseguito ↷")
        self._update_undo_redo()

    def _update_undo_redo(self):
        self.btn_undo.config(state=NORMAL if self.undo_stack else DISABLED)
        self.btn_redo.config(state=NORMAL if self.redo_stack else DISABLED)

    def rename_single(self):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        base, _ = os.path.splitext(self.tree.set(iid, "#1"))
        nuovo = simpledialog.askstring("Rinomina singolo",
                                       "Nuovo nome (senza estensione):",
                                       initialvalue=base, parent=self)
        if not nuovo:
            return
        self.basename_var.set(nuovo)
        self.prefisso_var.set("")
        self.suffisso_var.set("")
        self.numerazione_var.set(False)
        self.aggiorna_preview()
        self.rinomina()
        self.basename_var.set("")


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 6 – SEGNALIBRI
# ═══════════════════════════════════════════════════════════════════════════════

class TabSegnalibri(ttk.Frame):
    """
    Visualizzatore PDF a pagina intera con gestione segnalibri.
    Clicca sulla pagina per aggiungere un segnalibro.
    Salva il PDF con i segnalibri incorporati tramite fitz (TOC).
    """
    def __init__(self, master):
        super().__init__(master, padding=6)
        self.pdf_path = None
        self.doc = None
        self.current_page = 0
        self.zoom = 1.0
        self.segnalibri = []   # lista di (titolo, pagina_0based, livello)
        self._img_ref = None
        self._build_ui()

    def _build_ui(self):
        # ── Pannello sinistro: segnalibri ─────────────────────────────────────
        left = ttk.Frame(self, width=280)
        left.pack(side=LEFT, fill=Y, padx=(0, 6))
        left.pack_propagate(False)

        ttk.Label(left, text="📌  Segnalibri",
                  font=("Helvetica", 13, "bold")).pack(anchor=W, pady=(0, 4))

        # Treeview segnalibri
        tf = ttk.Frame(left)
        tf.pack(fill=BOTH, expand=True)
        self.tree = ttk.Treeview(tf, columns=("Pag", "Titolo"),
                                  show="headings", selectmode="browse")
        self.tree.heading("Pag",   text="Pag.")
        self.tree.heading("Titolo",text="Titolo")
        self.tree.column("Pag",    width=45, anchor="center")
        self.tree.column("Titolo", width=210, anchor=W)
        sb = ttk.Scrollbar(tf, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)

        self.tree.bind("<Double-1>",         self._on_tree_double)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Menu tasto destro sull'albero
        self._menu = tk.Menu(self, tearoff=0)
        self._menu.add_command(label="✏️  Modifica titolo", command=self._modifica)
        self._menu.add_command(label="🗑️  Elimina",         command=self._elimina)
        self.tree.bind("<Button-3>", self._popup_menu)

        # Pulsanti sotto il tree
        bf = ttk.Frame(left)
        bf.pack(fill=X, pady=6)
        ttk.Button(bf, text="📂  Apri PDF",  bootstyle=INFO,
                   command=self.apri_pdf).pack(fill=X, pady=2)
        ttk.Button(bf, text="💾  Salva PDF", bootstyle=SUCCESS,
                   command=self.salva_pdf).pack(fill=X, pady=2)
        ttk.Button(bf, text="🗑️  Elimina sel.", bootstyle=DANGER,
                   command=self._elimina).pack(fill=X, pady=2)
        liv_frame = ttk.Frame(bf)
        liv_frame.pack(fill=X, pady=2)
        ttk.Button(liv_frame, text="⇤  Livello su", bootstyle=SECONDARY,
                   command=lambda: self._livello(-1)).pack(side=LEFT, expand=True,
                                                          fill=X, padx=(0, 2))
        ttk.Button(liv_frame, text="Livello giù  ⇥", bootstyle=SECONDARY,
                   command=lambda: self._livello(+1)).pack(side=LEFT, expand=True,
                                                          fill=X, padx=(2, 0))
        ttk.Button(bf, text="📄  Vai a pagina…", bootstyle=SECONDARY,
                   command=self._vai_a_pagina_dialog).pack(fill=X, pady=2)

        self.info_lbl = ttk.Label(left, text="Nessun PDF aperto.",
                                   foreground="#6c757d", wraplength=260)
        self.info_lbl.pack(anchor=W)

        # ── Pannello destro: visualizzatore ───────────────────────────────────
        right = ttk.Frame(self)
        right.pack(side=LEFT, fill=BOTH, expand=True)

        # Canvas + scrollbar
        cv_frame = ttk.Frame(right)
        cv_frame.pack(fill=BOTH, expand=True)

        self.canvas = tk.Canvas(cv_frame, bg="white", cursor="crosshair",
                                highlightthickness=0)
        sb_v = ttk.Scrollbar(cv_frame, orient=VERTICAL,   command=self.canvas.yview)
        sb_h = ttk.Scrollbar(right,    orient=HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=sb_v.set, xscrollcommand=sb_h.set)
        sb_v.pack(side=RIGHT, fill=Y)
        sb_h.pack(side=BOTTOM, fill=X)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)

        # Barra navigazione/zoom
        nav = ttk.Frame(right)
        nav.pack(fill=X, pady=4)
        ttk.Button(nav, text="◀ Prec.",  bootstyle=INFO,
                   command=self._prev).pack(side=LEFT, padx=3)
        ttk.Button(nav, text="Succ. ▶", bootstyle=INFO,
                   command=self._next).pack(side=LEFT, padx=3)
        self.page_lbl = ttk.Label(nav, text="—")
        self.page_lbl.pack(side=LEFT, padx=10)
        ttk.Button(nav, text="➕", bootstyle=SUCCESS,
                   command=self._zoom_in).pack(side=RIGHT, padx=2)
        ttk.Button(nav, text="➖", bootstyle=DANGER,
                   command=self._zoom_out).pack(side=RIGHT, padx=2)
        ttk.Label(nav, text="Clicca sulla pagina per aggiungere un segnalibro",
                  foreground="#6c757d").pack(side=LEFT, padx=20)

        # Binding
        self.canvas.bind("<Button-1>", self._click_aggiungi)
        self.canvas.bind("<MouseWheel>",
                         lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    # ── Caricamento ───────────────────────────────────────────────────────────

    def apri_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        if self.doc:
            self.doc.close()
        self.pdf_path = path
        self.doc = fitz.open(path)
        self.current_page = 0
        self.zoom = 1.0
        # Carica segnalibri esistenti dal TOC
        toc = self.doc.get_toc()  # [[level, title, page], ...]
        self.segnalibri = [(t, p - 1, lvl) for lvl, t, p in toc]
        self._aggiorna_tree()
        self._render()
        self.info_lbl.config(
            text=f"{os.path.basename(path)}\n{len(self.doc)} pagine")

    def _render(self):
        if not self.doc:
            return
        page = self.doc[self.current_page]
        mat = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self._img_ref = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._img_ref)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        n = len(self.doc)
        self.page_lbl.config(text=f"Pag. {self.current_page + 1} / {n}")

    # ── Navigazione ───────────────────────────────────────────────────────────

    def _prev(self):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self._render()

    def _next(self):
        if self.doc and self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self._render()

    def _zoom_in(self):
        self.zoom = min(self.zoom * 1.15, 4.0)
        self._render()

    def _zoom_out(self):
        self.zoom = max(self.zoom / 1.15, 0.3)
        self._render()

    def _vai_a_pagina_dialog(self):
        if not self.doc:
            return
        testo = self._input_dialog(
            f"Vai a pagina (1–{len(self.doc)})", "")
        if testo:
            try:
                n = int(testo) - 1
                if 0 <= n < len(self.doc):
                    self.current_page = n
                    self._render()
            except ValueError:
                pass

    # ── Segnalibri ────────────────────────────────────────────────────────────

    def _click_aggiungi(self, event):
        if not self.doc:
            return
        titolo = self._input_dialog(
            f"Titolo segnalibro per pagina {self.current_page + 1}", "")
        if titolo:
            # inserisce dopo l'ultimo segnalibro di pagina <= corrente,
            # con lo stesso livello di quello che precede
            pos = len(self.segnalibri)
            for k, (_t, p, _l) in enumerate(self.segnalibri):
                if p > self.current_page:
                    pos = k
                    break
            livello = self.segnalibri[pos - 1][2] if pos > 0 else 1
            self.segnalibri.insert(pos, (titolo, self.current_page, livello))
            self._aggiorna_tree()

    def _livello(self, delta):
        """Sposta il segnalibro selezionato di un livello (delta = -1 o +1)."""
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        titolo, pagina, livello = self.segnalibri[idx]
        massimo = self.segnalibri[idx - 1][2] + 1 if idx > 0 else 1
        self.segnalibri[idx] = (titolo, pagina, max(1, min(livello + delta, massimo)))
        self._aggiorna_tree()
        self.tree.selection_set(str(idx))

    def _aggiorna_tree(self):
        self.tree.delete(*self.tree.get_children())
        for i, (titolo, pagina, livello) in enumerate(self.segnalibri):
            self.tree.insert("", END, iid=str(i),
                             values=(pagina + 1, "    " * (livello - 1) + titolo))

    def _on_tree_select(self, event):
        sel = self.tree.selection()
        if sel and self.doc:
            idx = int(sel[0])
            _, pg, _liv = self.segnalibri[idx]
            self.current_page = pg
            self._render()

    def _on_tree_double(self, event):
        self._modifica()

    def _popup_menu(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            self._menu.tk_popup(event.x_root, event.y_root)

    def _modifica(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        titolo_old, pagina, livello = self.segnalibri[idx]
        nuovo = self._input_dialog(
            f"Modifica titolo (pagina {pagina + 1})", titolo_old)
        if nuovo:
            self.segnalibri[idx] = (nuovo, pagina, livello)
            self._aggiorna_tree()

    def _elimina(self):
        sel = self.tree.selection()
        if not sel:
            return
        for iid in sel:
            del self.segnalibri[int(iid)]
        self._aggiorna_tree()

    def salva_pdf(self):
        if not self.doc:
            messagebox.showwarning("Attenzione", "Nessun PDF aperto.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        try:
            # fitz TOC: [[livello, titolo, pagina_1based], ...]
            toc = normalizza_toc([[livello, titolo, pagina + 1]
                                  for titolo, pagina, livello in self.segnalibri])
            self.doc.set_toc(toc)
            self.doc, err = salva_pdf_doc(self.doc, path)
            if err:
                raise err
            messagebox.showinfo("Salvato", f"PDF con segnalibri salvato in:\n{path}")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    # ── Utility ───────────────────────────────────────────────────────────────

    def _input_dialog(self, prompt, valore_iniziale=""):
        win = ttk.Toplevel(self)
        win.title("Testo")
        win.resizable(False, False)
        ttk.Label(win, text=prompt, wraplength=320).pack(padx=15, pady=10)
        entry = ttk.Entry(win, width=40)
        entry.pack(padx=15, pady=5)
        entry.insert(0, valore_iniziale)
        entry.focus()
        valore = {"v": None}

        def ok(e=None):
            valore["v"] = entry.get()
            win.destroy()

        entry.bind("<Return>", ok)
        ttk.Button(win, text="OK", bootstyle=PRIMARY, command=ok).pack(pady=8)
        win.grab_set()
        self.wait_window(win)
        return valore["v"]


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 7 – CONVERTI DOCUMENTI
# ═══════════════════════════════════════════════════════════════════════════════

# Import opzionali: se mancano, il tab mostra un messaggio di installazione
try:
    import markdown as _md
    import mammoth as _mammoth
    from ebooklib import epub as _epub
    from bs4 import BeautifulSoup as _BS
    from docx import Document as _Document
    _CONV_DEPS_OK = True
except ImportError as _e:
    _CONV_DEPS_OK = False
    _CONV_DEPS_ERR = str(_e)

try:
    import win32com.client as _win32
    _HAS_COM = True
except ImportError:
    _HAS_COM = False


class TabConverti(ttk.Frame):
    """
    Converte file Markdown, DOCX, DOC in HTML, EPUB, DOCX, DOC.
    Dipendenze extra: pip install markdown mammoth ebooklib beautifulsoup4 python-docx
    """
    def __init__(self, master):
        super().__init__(master, padding=16)
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Converti documenti",
                  font=("Helvetica", 15, "bold")).pack(pady=(0, 8))

        if not _CONV_DEPS_OK:
            msg = ("Dipendenze mancanti per questo modulo.\n\n"
                   "Installa con:\n"
                   "pip install markdown mammoth ebooklib beautifulsoup4 python-docx\n\n"
                   f"Dettaglio: {_CONV_DEPS_ERR}")
            ttk.Label(self, text=msg, foreground="#dc3545",
                      font=("Helvetica", 11), justify=LEFT).pack(anchor=W)
            return

        ttk.Label(self,
                  text="Converte  Markdown / DOCX / DOC  →  HTML / EPUB / DOCX / DOC",
                  foreground="#6c757d").pack(anchor=W, pady=(0, 20))

        ttk.Button(self, text="📂  Scegli file e converti…",
                   bootstyle=PRIMARY, width=36,
                   command=self._converti).pack(pady=10)

        self.log = tk.Text(self, height=10, state="disabled",
                           font=("Courier", 10), relief="flat",
                           bg="#f8f9fa", wrap="word")
        self.log.pack(fill=X, pady=10)

    def _log(self, msg):
        self.log.config(state="normal")
        self.log.insert(END, msg + "\n")
        self.log.see(END)
        self.log.config(state="disabled")

    def _converti(self):
        if not _CONV_DEPS_OK:
            return
        file_path = filedialog.askopenfilename(
            title="Seleziona file da convertire",
            filetypes=[("Markdown", "*.md"),
                       ("Word DOCX", "*.docx"),
                       ("Word DOC",  "*.doc")])
        if not file_path:
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML",  "*.html"),
                       ("EPUB",  "*.epub"),
                       ("DOCX",  "*.docx"),
                       ("DOC",   "*.doc")],
            title="Salva come…")
        if not save_path:
            return

        ext_in  = os.path.splitext(file_path)[1].lower()
        ext_out = os.path.splitext(save_path)[1].lower()
        title   = os.path.splitext(os.path.basename(file_path))[0]
        self._log(f"Input : {file_path}")
        self._log(f"Output: {save_path}")

        try:
            html = self._to_html(file_path, ext_in)
            self._save_output(html, save_path, ext_out, title)
            self._log("✅  Conversione completata.\n")
            messagebox.showinfo("Fatto", f"File salvato:\n{save_path}")
        except Exception as e:
            self._log(f"❌  Errore: {e}\n")
            messagebox.showerror("Errore", str(e))

    def _to_html(self, path, ext):
        if ext == ".md":
            return _md.markdown(self._read_text(path))
        elif ext == ".docx":
            try:
                with open(path, "rb") as f:
                    return _mammoth.convert_to_html(f).value
            except PermissionError:
                if not _HAS_COM:
                    raise RuntimeError(
                        "File bloccato e pywin32 non disponibile.\n"
                        "Chiudi Word/OneDrive oppure: pip install pywin32")
                return self._docx_via_com(path)
        elif ext == ".doc":
            return self._doc_via_soffice(path)
        else:
            raise RuntimeError(f"Formato di input non supportato: {ext}")

    def _read_text(self, path):
        for enc in ("utf-8", "cp1252", "latin-1"):
            try:
                with open(path, encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        raise UnicodeDecodeError("utf-8", b"", 0, 1, f"Impossibile leggere {path}")

    def _docx_via_com(self, path):
        word = _win32.Dispatch("Word.Application")
        word.Visible = False
        import tempfile
        doc = word.Documents.Open(os.path.abspath(path), ReadOnly=True)
        tmp = os.path.join(tempfile.gettempdir(), "tmp_conv.html")
        doc.SaveAs(tmp, FileFormat=8)
        doc.Close(False); word.Quit()
        html = self._read_text(tmp)
        os.remove(tmp)
        return html

    def _doc_via_soffice(self, path):
        import subprocess, tempfile, shutil
        soffice = shutil.which("soffice")
        if not soffice:
            for base in (os.environ.get("PROGRAMFILES"),
                         os.environ.get("PROGRAMFILES(X86)")):
                if base:
                    c = os.path.join(base, "LibreOffice", "program", "soffice.exe")
                    if os.path.isfile(c):
                        soffice = c; break
        if not soffice:
            raise RuntimeError("LibreOffice non trovato. Installalo o aggiungi soffice al PATH.")
        tmpdir = tempfile.mkdtemp()
        try:
            subprocess.run([soffice, "--headless", "--convert-to", "html",
                            "--outdir", tmpdir, path],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            fname = os.path.splitext(os.path.basename(path))[0] + ".html"
            return self._read_text(os.path.join(tmpdir, fname))
        finally:
            import shutil as _sh; _sh.rmtree(tmpdir, ignore_errors=True)

    def _save_output(self, html, path, ext, title):
        import tempfile, subprocess, shutil
        if ext == ".html":
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)

        elif ext == ".epub":
            soup = _BS(html, "html.parser")
            for idx, tag in enumerate(soup.find_all(
                    ["h1","h2","h3","h4","h5","h6"])):
                tag["id"] = f"h{idx}"
            book = _epub.EpubBook()
            book.set_title(title)
            book.set_language("it")
            ch = _epub.EpubHtml(title=title, file_name="cap.xhtml",
                                 content=str(soup))
            book.add_item(ch)
            book.add_item(_epub.EpubNcx())
            book.add_item(_epub.EpubNav())
            book.spine = ["nav", ch]
            _epub.write_epub(path, book, {})

        elif ext == ".docx":
            self._html_to_docx(html, path, title)

        elif ext == ".doc":
            tmpdir = tempfile.mkdtemp()
            try:
                tmp_docx = os.path.join(tmpdir, "tmp.docx")
                self._html_to_docx(html, tmp_docx, title)
                soffice = shutil.which("soffice") or ""
                subprocess.run([soffice, "--headless", "--convert-to", "doc",
                                "--outdir", tmpdir, tmp_docx],
                               check=True, stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE)
                shutil.copy(os.path.join(tmpdir, "tmp.doc"), path)
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
        else:
            raise RuntimeError(f"Formato di output non supportato: {ext}")

    def _html_to_docx(self, html, path, title):
        soup = _BS(html, "html.parser")
        doc = _Document()
        doc.add_heading(title, level=1)
        for el in soup.find_all(["h1","h2","h3","h4","h5","h6","p","ul","ol"]):
            if el.name == "p":
                doc.add_paragraph(el.get_text())
            elif el.name.startswith("h") and el.name[1:].isdigit():
                doc.add_heading(el.get_text(), level=min(int(el.name[1]), 4))
            elif el.name in ("ul", "ol"):
                for li in el.find_all("li", recursive=False):
                    style = "List Number" if el.name == "ol" else "List Bullet"
                    doc.add_paragraph(li.get_text(), style=style)
        doc.save(path)


# ═══════════════════════════════════════════════════════════════════════════════
#  APP PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    app = ttk.Window(themename="flatly")
    app.title("PDF Suite")
    app.geometry("1100x740")
    app.minsize(860, 580)

    notebook = ttk.Notebook(app, bootstyle="primary")
    notebook.pack(fill=BOTH, expand=True, padx=8, pady=8)

    tabs = [
        ("🔗  Unisci",      TabUnisci),
        ("↕  Riordina",    TabRiordina),
        ("🔄  Sostituisci", TabSostituisci),
        ("✂  Dividi",      TabDividi),
        ("🏷  Rinomina",    TabRinomina),
        ("📌  Segnalibri",  TabSegnalibri),
        ("🔁  Converti",    TabConverti),
    ]

    for label, cls in tabs:
        frame = cls(notebook)
        notebook.add(frame, text=f"  {label}  ")

    app.mainloop()


if __name__ == "__main__":
    main()
