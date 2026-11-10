import ttkbootstrap as ttk
import tkinter as tk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
from pdfrw import PdfReader, PdfWriter

class PDFMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Merger con pdfrw")
        self.root.geometry("700x500")
        self.root.resizable(False, False)

        #---- STILE ----
        style = ttk.Style("morph")  # Puoi provare anche 'flatly', 'superhero', 'darkly', ecc.
        
        #---- FRAME CONTENITORE LISTBOX ----
        listbox_frame = ttk.Frame(root, padding=10)
        listbox_frame.pack(pady=20)
        
        #---- LISTBOX ----
        self.listbox = tk.Listbox(
            master=root,
            width=100,
            height=12,
            selectmode=tk.SINGLE
        )
        self.listbox.pack(
            pady=20,
            padx=20
        )

        #---- FRAME BOTTONI ----
        btn_frame = ttk.Frame(root)
        btn_frame.pack(pady=10)

        #-- Bottoni operativi
        ttk.Button(
            master=btn_frame,
            text="Aggiungi PDF",
            command=self.add_files,
            bootstyle=PRIMARY
        ).grid(row=0, column=0, padx=5)

        ttk.Button(
            master=btn_frame,
            text="Rimuovi selezionato",
            command=self.remove_selected,
            bootstyle=SECONDARY
        ).grid(row=0, column=1, padx=5)

        ttk.Button(
            master=btn_frame,
            text="Sposta su",
            command=self.move_up,
            bootstyle=WARNING
        ).grid(row=0, column=2, padx=5)

        ttk.Button(
            master=btn_frame,
            text="Sposta giù",
            command=self.move_down,
            bootstyle=WARNING
        ).grid(row=0, column=3, padx=5)

        #-- Bottone finale unione
        ttk.Button(
            master=root,
            text="Unisci PDF",
            command=self.merge_pdfs,
            bootstyle=SUCCESS,
            width=20
        ).pack(
            pady=25
        )

    #---- FUNZIONI ----

    def add_files(self):
        files = filedialog.askopenfilenames(
            title="Seleziona i file PDF da unire",
            filetypes=[("File PDF", "*.pdf")]
        )
        for f in files:
            if f not in self.listbox.get(0, ttk.END):
                self.listbox.insert(ttk.END, f)

    def remove_selected(self):
        selected = self.listbox.curselection()
        for index in reversed(selected):
            self.listbox.delete(index)

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
        files = self.listbox.get(0, ttk.END)
        if len(files) < 2:
            messagebox.showwarning("Attenzione", "Seleziona almeno due PDF da unire.")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("File PDF", "*.pdf")],
            title="Salva PDF unito come"
        )
        if not save_path:
            return

        try:
            writer = PdfWriter()
            for pdf_path in files:
                reader = PdfReader(pdf_path)
                writer.addpages(reader.pages)
            writer.write(save_path)
            messagebox.showinfo("Successo", f"PDF unito salvato in:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore:\n{e}")

#---- AVVIO INTERFACCIA ----

if __name__ == "__main__":
    app = ttk.Window(themename="cosmo")  # Puoi cambiare tema: 'darkly', 'flatly', 'superhero', 'morph', ecc.
    PDFMergerApp(app)
    app.mainloop()
