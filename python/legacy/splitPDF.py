import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk
from PyPDF2 import PdfReader, PdfWriter  # <-- PyPDF2 3.x
import fitz  # PyMuPDF


class PDFSplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Splitter")
        self.current_pdf = None
        self.page_images = []
        self.page_vars = []

        # Colori
        self.bg_color = "#3b5798"  # azzurro bottoni/widget
        self.fg_color = "#ffff5f"  # giallo testo

        # Paned
        main_frame = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(main_frame, width=800)
        main_frame.add(left_frame, weight=3)

        right_frame = ttk.Frame(main_frame, width=200)
        main_frame.add(right_frame, weight=1)

        # Seleziona PDF
        self.select_button = tk.Button(
            left_frame, text="Seleziona PDF", command=self.load_pdf,
            relief="raised", bg=self.bg_color, fg=self.fg_color
        )
        self.select_button.pack(pady=5)

        # Zoom
        zoom_frame = ttk.Frame(left_frame)
        zoom_frame.pack(pady=5)

        self.zoom_out_button = tk.Button(
            zoom_frame, text="-", command=self.zoom_out,
            relief="raised", bg=self.bg_color, fg=self.fg_color, width=3
        )
        self.zoom_out_button.pack(side=tk.LEFT, padx=5)

        self.zoom_reset_button = tk.Button(
            zoom_frame, text="Reset Zoom", command=self.zoom_reset,
            relief="raised", bg=self.bg_color, fg=self.fg_color
        )
        self.zoom_reset_button.pack(side=tk.LEFT, padx=5)

        self.zoom_in_button = tk.Button(
            zoom_frame, text="+", command=self.zoom_in,
            relief="raised", bg=self.bg_color, fg=self.fg_color, width=3
        )
        self.zoom_in_button.pack(side=tk.LEFT, padx=5)

        # Anteprima
        self.preview_frame = ttk.Frame(left_frame)
        self.preview_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.preview_frame)
        scrollbar = ttk.Scrollbar(self.preview_frame, orient="vertical", command=self.canvas.yview)
        self.preview_container = ttk.Frame(self.canvas)

        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((0, 0), window=self.preview_container, anchor="nw")

        # Scroll con rotellina
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Selezione pagine
        self.select_all_button = tk.Button(
            right_frame, text="Seleziona Tutte", command=self.select_all_pages,
            relief="raised", bg=self.bg_color, fg=self.fg_color
        )
        self.select_all_button.pack(pady=5)

        self.deselect_all_button = tk.Button(
            right_frame, text="Deseleziona Tutte", command=self.deselect_all_pages,
            relief="raised", bg=self.bg_color, fg=self.fg_color
        )
        self.deselect_all_button.pack(pady=5)

        self.range_label = ttk.Label(right_frame, text="Pagine (es. 1-3; 4; 6-8):")
        self.range_label.pack(pady=5)
        self.range_entry = tk.Entry(right_frame, relief="raised", bg=self.bg_color, fg=self.fg_color, width=30)
        self.range_entry.pack(pady=5)

        self.export_button = tk.Button(
            right_frame, text="Esporta Pagine", command=self.export_pages,
            relief="raised", bg=self.bg_color, fg=self.fg_color
        )
        self.export_button.pack(pady=5)

        self.zoom_factor = 1.0

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def load_pdf(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if file_path:
            self.current_pdf = file_path
            self.load_previews()

    def load_previews(self):
        # pulizia
        for widget in self.preview_container.winfo_children():
            widget.destroy()
        self.page_images.clear()
        self.page_vars.clear()

        doc = fitz.open(self.current_pdf)

        canvas_width = self.canvas.winfo_width()
        if canvas_width < 100:
            canvas_width = 800
        available_width = canvas_width - 100

        max_width = max(page.rect.width for page in doc)
        base_zoom = available_width / max_width

        for page_num in range(len(doc)):
            page = doc[page_num]
            final_zoom = base_zoom * self.zoom_factor
            matrix = fitz.Matrix(final_zoom, final_zoom)

            pix = page.get_pixmap(matrix=matrix)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_tk = ImageTk.PhotoImage(img)
            self.page_images.append(img_tk)

            page_frame = ttk.Frame(self.preview_container)
            page_frame.pack(pady=5)

            var = tk.BooleanVar()
            self.page_vars.append(var)
            cb = ttk.Checkbutton(page_frame, text=f"Pagina {page_num + 1}", variable=var)
            cb.pack(side=tk.LEFT)

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

        selected_pages = [i + 1 for i, var in enumerate(self.page_vars) if var.get()]
        page_ranges = self.range_entry.get().strip()

        if not selected_pages and not page_ranges:
            messagebox.showwarning("Attenzione", "Seleziona delle pagine o inserisci un intervallo")
            return

        # Ramo: selezione via checkbox
        if selected_pages:
            save_option = messagebox.askyesno("Esportazione", "Vuoi esportare tutte le pagine in un unico file?")

            if save_option:  # UNICO FILE
                save_path = filedialog.asksaveasfilename(
                    defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")]
                )
                if save_path:
                    try:
                        with open(self.current_pdf, "rb") as f:
                            reader = PdfReader(f)
                            writer = PdfWriter()
                            for page_num in selected_pages:
                                writer.add_page(reader.pages[page_num - 1])
                        with open(save_path, "wb") as out:
                            writer.write(out)
                        messagebox.showinfo("Successo", f"Pagine esportate in: {save_path}")
                    except Exception as e:
                        messagebox.showerror("Errore", f"Si è verificato un errore durante l'esportazione: {e}")
                return

            else:  # FILE SEPARATI
                try:
                    with open(self.current_pdf, "rb") as f:
                        reader = PdfReader(f)
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
                                with open(save_path, "wb") as out:
                                    writer.write(out)
                    messagebox.showinfo("Successo", "Pagine esportate in file separati")
                except Exception as e:
                    messagebox.showerror("Errore", f"Si è verificato un errore durante l'esportazione: {e}")
                return

        # Ramo: intervalli nella entry
        page_ranges = self.range_entry.get().strip()
        ranges = [r.strip() for r in page_ranges.split(';')]

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

                    # Gestione gruppi separati da ';'
                    groups = []
                    current_group = []
                    for range_str in ranges:
                        range_str = range_str.strip()
                        if range_str.endswith(';'):
                            current_group.append(range_str[:-1])
                            if current_group:
                                groups.append(current_group)
                                current_group = []
                        else:
                            current_group.append(range_str)
                    if current_group:
                        groups.append(current_group)

                    for group in groups:
                        try:
                            for range_str in group:
                                if '-' in range_str:
                                    start, end = map(int, range_str.split('-'))
                                    for page_num in range(start - 1, end):
                                        writer.add_page(reader.pages[page_num])
                                else:
                                    page_num = int(range_str) - 1
                                    writer.add_page(reader.pages[page_num])
                        except ValueError:
                            messagebox.showwarning("Attenzione", f"Numero pagina non valido nel gruppo: {group}")
                            return

                with open(save_path, "wb") as output_file:
                    writer.write(output_file)

                messagebox.showinfo("Successo", f"Pagine esportate in: {save_path}")

            except Exception as e:
                messagebox.showerror("Errore", f"Si è verificato un errore durante l'esportazione: {e}")

    def save_separate_ranges(self, ranges):
        try:
            with open(self.current_pdf, 'rb') as file:
                reader = PdfReader(file)

                for group in ranges:
                    writer = PdfWriter()
                    group_pages = []
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
            messagebox.showerror("Errore", f"Si è verificato un errore durante l'esportazione: {e}")

    def zoom_in(self):
        self.zoom_factor += 0.1
        self.reload_previews()

    def zoom_out(self):
        if self.zoom_factor > 0.2:
            self.zoom_factor -= 0.1
            self.reload_previews()

    def zoom_reset(self):
        self.zoom_factor = 1.0
        self.reload_previews()

    def reload_previews(self):
        if self.current_pdf:
            self.load_previews()

    def _on_window_resize(self, event):
        if event.widget == self.root:
            self.root.after_cancel(getattr(self, '_resize_job', None)) if hasattr(self, '_resize_job') else None
            self._resize_job = self.root.after(100, self.reload_previews)


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1200x800")
    app = PDFSplitterApp(root)
    root.mainloop()
