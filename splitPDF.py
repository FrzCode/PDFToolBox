import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk
from PyPDF2 import PdfFileReader, PdfFileWriter
import fitz  # PyMuPDF

class PDFSplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Splitter")
        self.current_pdf = None
        self.page_images = []
        self.page_vars = []

        # Colore azzurro simile a Facebook
        self.bg_color = "#3b5798" # colore azzurro dei bottoni e widget
        self.fg_color = "#ffff5f" # colore giallo del testo

        # Frame principale diviso in due parti
        main_frame = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Frame sinistro per l'anteprima
        left_frame = ttk.Frame(main_frame, width=800)
        main_frame.add(left_frame, weight=3)

        # Frame destro per la selezione delle pagine
        right_frame = ttk.Frame(main_frame, width=200)
        main_frame.add(right_frame, weight=1)

        # Pulsante per selezionare il PDF
        self.select_button = tk.Button(left_frame, text="Seleziona PDF", command=self.load_pdf, 
                                     relief="raised", bg=self.bg_color, fg=self.fg_color)
        self.select_button.pack(pady=5)

        # Frame per i controlli zoom
        zoom_frame = ttk.Frame(left_frame)
        zoom_frame.pack(pady=5)
        
        # Pulsanti zoom
        self.zoom_out_button = tk.Button(zoom_frame, text="-", command=self.zoom_out, 
                                       relief="raised", bg=self.bg_color, fg=self.fg_color,
                                       width=3)
        self.zoom_out_button.pack(side=tk.LEFT, padx=5)
        
        self.zoom_reset_button = tk.Button(zoom_frame, text="Reset Zoom", command=self.zoom_reset, 
                                         relief="raised", bg=self.bg_color, fg=self.fg_color)
        self.zoom_reset_button.pack(side=tk.LEFT, padx=5)
        
        self.zoom_in_button = tk.Button(zoom_frame, text="+", command=self.zoom_in, 
                                      relief="raised", bg=self.bg_color, fg=self.fg_color,
                                      width=3)
        self.zoom_in_button.pack(side=tk.LEFT, padx=5)

        # Frame per l'anteprima
        self.preview_frame = ttk.Frame(left_frame)
        self.preview_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas per le anteprime
        self.canvas = tk.Canvas(self.preview_frame)
        scrollbar = ttk.Scrollbar(self.preview_frame, orient="vertical", command=self.canvas.yview)
        self.preview_container = ttk.Frame(self.canvas)

        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((0, 0), window=self.preview_container, anchor="nw")

        # Binding per la rotellina del mouse
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Pulsante per selezionare tutte le pagine
        self.select_all_button = tk.Button(right_frame, text="Seleziona Tutte", command=self.select_all_pages, relief="raised", bg=self.bg_color, fg=self.fg_color)
        self.select_all_button.pack(pady=5)

        # Pulsante per deselezionare tutte le pagine
        self.deselect_all_button = tk.Button(right_frame, text="Deseleziona Tutte", command=self.deselect_all_pages, relief="raised", bg=self.bg_color, fg=self.fg_color)
        self.deselect_all_button.pack(pady=5)

        # Entry per l'intervallo di pagine
        self.range_label = ttk.Label(right_frame, text="Pagine (es. 1-3; 4; 6-8):")
        self.range_label.pack(pady=5)
        self.range_entry = tk.Entry(right_frame, relief="raised", bg=self.bg_color, fg=self.fg_color, width=30)
        self.range_entry.pack(pady=5)

        # Pulsante per esportare le pagine selezionate
        self.export_button = tk.Button(right_frame, text="Esporta Pagine", command=self.export_pages, relief="raised", bg=self.bg_color, fg=self.fg_color)
        self.export_button.pack(pady=5)

        # Aggiungi zoom factor
        self.zoom_factor = 1.0  # Fattore di zoom predefinito

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def load_pdf(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if file_path:
            self.current_pdf = file_path
            self.load_previews()

    def load_previews(self):
        # Pulisce le anteprime precedenti
        for widget in self.preview_container.winfo_children():
            widget.destroy()

        self.page_images = []
        self.page_vars = []

        doc = fitz.open(self.current_pdf)
        
        # Calcola la larghezza disponibile del canvas
        canvas_width = self.canvas.winfo_width()
        if canvas_width < 100:  # Se il canvas non è ancora stato renderizzato
            canvas_width = 800  # Larghezza predefinita
        
        # Sottrai un po' di spazio per i margini e la scrollbar
        available_width = canvas_width - 100  # Aumentato il margine per maggiore spazio
        
        # Trova la pagina più larga per calcolare il fattore di zoom base
        max_width = max(page.rect.width for page in doc)
        base_zoom = available_width / max_width
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Applica sia il base_zoom che lo zoom_factor dell'utente
            final_zoom = base_zoom * self.zoom_factor
            matrix = fitz.Matrix(final_zoom, final_zoom)
            
            pix = page.get_pixmap(matrix=matrix)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_tk = ImageTk.PhotoImage(img)
            self.page_images.append(img_tk)

            # Frame per ogni pagina
            page_frame = ttk.Frame(self.preview_container)
            page_frame.pack(pady=5)

            # Checkbox per la selezione
            var = tk.BooleanVar()
            self.page_vars.append(var)
            cb = ttk.Checkbutton(page_frame, text=f"Pagina {page_num + 1}", variable=var)
            cb.pack(side=tk.LEFT)

            # Anteprima
            label = tk.Label(page_frame, image=img_tk)
            label.pack(side=tk.LEFT)

        self.preview_container.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def select_all_pages(self):
        for var in self.page_vars:
            var.set(True)

    def deselect_all_pages(self):
        for var in self.page_vars:
            var.set(False)

    def export_pages(self):
        if not self.current_pdf:
            messagebox.showwarning("Attenzione", "Seleziona prima un PDF")
            return

        # Controlla se ci sono pagine selezionate tramite checkbox
        selected_pages = [i + 1 for i, var in enumerate(self.page_vars) if var.get()]
        
        # Controlla se c'è un intervallo specificato
        page_ranges = self.range_entry.get().strip()
        
        # Se non c'è né selezione né intervallo, mostra un errore
        if not selected_pages and not page_ranges:
            messagebox.showwarning("Attenzione", "Seleziona delle pagine o inserisci un intervallo")
            return

        # Se ci sono pagine selezionate tramite checkbox
        if selected_pages:
            # Chiedi all'utente se vuole salvare in un unico file o file separati
            save_option = messagebox.askyesno("Esportazione", "Vuoi esportare tutte le pagine in un unico file?")
            
            if save_option:  # Unico file
                save_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
                if save_path:
                    try:
                        with open(self.current_pdf, 'rb') as file:
                            reader = PdfFileReader(open(self.current_pdf, 'rb'))
                            writer = PdfFileWriter()
                            
                            for page_num in selected_pages:
                                writer.add_page(reader.pages[page_num - 1])

                        with open(save_path, "wb") as output_file:
                            writer.write(output_file)
                            
                        messagebox.showinfo("Successo", f"Pagine esportate in: {save_path}")
                    except Exception as e:
                        messagebox.showerror("Errore", f"Si è verificato un errore durante l'esportazione: {str(e)}")
                else:  # File separati
                    try:
                        with open(self.current_pdf, 'rb') as file:
                            reader = PdfReader(file)
                            
                            for page_num in selected_pages:
                                writer = PdfWriter()
                                writer.add_page(reader.pages[page_num - 1])
                                
                                filename = f"page_{page_num}.pdf"
                                save_path = filedialog.asksaveasfilename(
                                    defaultextension=".pdf", 
                                    filetypes=[("PDF files", "*.pdf")],
                                    initialfile=filename
                                )
                                
                                if save_path:
                                    with open(save_path, "wb") as output_file:
                                        writer.write(output_file)
                
                        messagebox.showinfo("Successo", "Pagine esportate in file separati")
                    except Exception as e:
                        messagebox.showerror("Errore", f"Si è verificato un errore durante l'esportazione: {str(e)}")
                return

        # Se arriviamo qui, usiamo l'intervallo specificato
        page_ranges = self.range_entry.get().strip()  # Prendiamo la stringa originale
        ranges = [r.strip() for r in page_ranges.split(';')]  # Dividiamo per punto e virgola
        
        if len(ranges) > 1:
            save_option = messagebox.askyesno("Esportazione", "Vuoi esportare tutti i range in un unico file?")
        else:
            save_option = True

        if save_option:
            self.save_combined_ranges(ranges)
        else:
            self.save_separate_ranges(ranges)

    def save_combined_ranges(self, ranges):
        save_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if save_path:
            try:
                with open(self.current_pdf, 'rb') as file:
                    reader = PdfReader(file)
                    writer = PdfWriter()

                    # Separa i gruppi (usando sia ; che ,)
                    groups = []
                    current_group = []
                    
                    for range_str in ranges:
                        range_str = range_str.strip()
                        if range_str.endswith(';'):  # Fine del gruppo
                            current_group.append(range_str[:-1])  # Rimuovi il ;
                            if current_group:
                                groups.append(current_group)
                                current_group = []
                        else:
                            current_group.append(range_str)
                    
                    if current_group:  # Aggiungi l'ultimo gruppo
                        groups.append(current_group)

                    # Processa ogni gruppo separatamente
                    for group in groups:
                        try:
                            for range_str in group:
                                if '-' in range_str:
                                    # Gestisce intervalli (es. 1-3)
                                    start, end = map(int, range_str.split('-'))
                                    for page_num in range(start - 1, end):
                                        writer.add_page(reader.pages[page_num])
                                else:
                                    # Gestisce singole pagine (es. 4)
                                    page_num = int(range_str) - 1
                                    writer.add_page(reader.pages[page_num])
                        except ValueError:
                            messagebox.showwarning("Attenzione", f"Numero pagina non valido nel gruppo: {group}")
                            return

                    with open(save_path, "wb") as output_file:
                        writer.write(output_file)
                        
                    messagebox.showinfo("Successo", f"Pagine esportate in: {save_path}")

            except Exception as e:
                messagebox.showerror("Errore", f"Si è verificato un errore durante l'esportazione: {str(e)}")

    def save_separate_ranges(self, ranges):
        try:
            with open(self.current_pdf, 'rb') as file:
                reader = PdfReader(file)
                
                # Processa ogni gruppo (diviso da punto e virgola)
                for group in ranges:
                    writer = PdfWriter()
                    group_pages = []
                    
                    # Dividi il gruppo per virgole
                    ranges_in_group = [r.strip() for r in group.split(',')]
                    
                    try:
                        for range_str in ranges_in_group:
                            if '-' in range_str:
                                start, end = map(int, range_str.split('-'))
                                for page_num in range(start - 1, end):
                                    writer.add_page(reader.pages[page_num])
                                group_pages.append(f"{start}-{end}")
                            else:
                                page_num = int(range_str)
                                writer.add_page(reader.pages[page_num - 1])
                                group_pages.append(str(page_num))
                        
                        filename = f"pages_{'_'.join(group_pages)}.pdf"
                        save_path = filedialog.asksaveasfilename(
                            defaultextension=".pdf", 
                            filetypes=[("PDF files", "*.pdf")], 
                            initialfile=filename
                        )
                        
                        if save_path:
                            with open(save_path, "wb") as output_file:
                                writer.write(output_file)

                    except ValueError:
                        messagebox.showwarning("Attenzione", f"Numero pagina non valido nel gruppo: {group}")
                        continue

                messagebox.showinfo("Successo", "Pagine esportate in file separati")

        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore durante l'esportazione: {str(e)}")

    def zoom_in(self):
        self.zoom_factor += 0.1
        self.reload_previews()

    def zoom_out(self):
        if self.zoom_factor > 0.2:  # Impedisce zoom troppo piccolo
            self.zoom_factor -= 0.1
            self.reload_previews()

    def zoom_reset(self):
        self.zoom_factor = 1.0  # Cambiato a 1.0 per dimensione naturale
        self.reload_previews()

    def reload_previews(self):
        if self.current_pdf:
            self.load_previews()

    def _on_window_resize(self, event):
        # Controlla se la finestra è stata effettivamente ridimensionata
        if event.widget == self.root:
            # Aggiungi un piccolo ritardo per evitare troppi aggiornamenti
            self.root.after_cancel(self._resize_job) if hasattr(self, '_resize_job') else None
            self._resize_job = self.root.after(100, self.reload_previews)

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1200x800")  # Imposta dimensioni iniziali della finestra
    app = PDFSplitterApp(root)
    root.mainloop()
