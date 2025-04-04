import fitz
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk
import os
import io
import time
import json
import shutil

class SplashScreen:
    def __init__(self, root, logo_path, duration=3000):
        self.root = root
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        try:
            logo_img = Image.open(logo_path)
            logo_img = logo_img.resize((400, 300), Image.Resampling.LANCZOS)
            self.logo = ImageTk.PhotoImage(logo_img)
        except Exception as e:
            print(f"Error al cargar el logo: {e}")
            self.logo = None
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 300) // 2
        self.root.geometry(f"400x300+{x}+{y}")
        
        self.canvas = tk.Canvas(self.root, width=400, height=300, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        if self.logo:
            self.canvas.create_image(200, 150, image=self.logo)
        
        self.root.after(duration, self.close_splash)
    
    def close_splash(self):
        self.root.destroy()

class PDFEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("ADOBO PEDF")
        self.root.geometry("1200x800")
        
        try:
            logo_icon = Image.open(r"C:/Users/jnoh/Downloads/pdf felipe/pdf-felipe/logo/logo_adobo.png")
            logo_icon = logo_icon.resize((32, 32), Image.Resampling.LANCZOS)
            self.icon = ImageTk.PhotoImage(logo_icon)
            self.root.iconphoto(True, self.icon)
        except Exception as e:
            print(f"Error al cargar el ícono: {e}")
        
        # Directorio para almacenar firmas
        self.signatures_dir = "signatures"
        if not os.path.exists(self.signatures_dir):
            os.makedirs(self.signatures_dir)
        
        self.signatures_json = "signatures.json"
        self.pdf_path = None
        self.pdf_document = None
        self.current_page = 0
        self.total_pages = 0
        self.page_image = None
        self.tk_image = None
        self.zoom_level = 1.0
        
        self.signatures = {}
        self.available_signatures = []
        self.selected_signature = None
        self.selected_available_signature = None
        self.drag_data = {"x": 0, "y": 0, "item": None, "dragging": False}
        self.resize_data = {"active": False, "corner": None, "start_x": 0, "start_y": 0}
        self.stored_signature = None
        
        # Estilo
        self.style = ttk.Style()
        self.style.configure('TButton', padding=5, font=('Arial', 10))
        self.style.configure('TLabel', font=('Arial', 10))
        
        # Barra superior con todos los botones
        self.top_bar = ttk.Frame(self.root, relief=tk.RAISED, borderwidth=1)
        self.top_bar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Botones de herramientas
        self.load_button = ttk.Button(self.top_bar, text="Cargar PDF", command=self.load_pdf)
        self.load_button.pack(side=tk.LEFT, padx=5)
        
        self.upload_button = ttk.Button(self.top_bar, text="Subir Firma", command=self.upload_signature)
        self.upload_button.pack(side=tk.LEFT, padx=5)
        
        self.signature_select_combobox = ttk.Combobox(self.top_bar, state="readonly", width=15)
        self.signature_select_combobox.pack(side=tk.LEFT, padx=5)
        self.signature_select_combobox.bind("<<ComboboxSelected>>", self.on_signature_select_to_add)
        
        self.delete_button = ttk.Button(self.top_bar, text="Eliminar Firma Disponible", command=self.delete_available_signature)
        self.delete_button.pack(side=tk.LEFT, padx=5)
        
        self.save_button = ttk.Button(self.top_bar, text="Guardar PDF", command=self.save_pdf)
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        # Botones de navegación
        self.prev_button = ttk.Button(self.top_bar, text="◄", command=self.prev_page, width=3)
        self.prev_button.pack(side=tk.LEFT, padx=5)
        
        self.page_label = ttk.Label(self.top_bar, text="Página: 0/0")
        self.page_label.pack(side=tk.LEFT, padx=5)
        
        self.next_button = ttk.Button(self.top_bar, text="►", command=self.next_page, width=3)
        self.next_button.pack(side=tk.LEFT, padx=5)
        
        # Botones de zoom
        self.zoom_in_button = ttk.Button(self.top_bar, text="+", command=lambda: self.adjust_zoom(1.2), width=3)
        self.zoom_in_button.pack(side=tk.LEFT, padx=5)
        
        self.zoom_out_button = ttk.Button(self.top_bar, text="-", command=lambda: self.adjust_zoom(0.8), width=3)
        self.zoom_out_button.pack(side=tk.LEFT, padx=5)
        
        self.zoom_reset_button = ttk.Button(self.top_bar, text="100%", command=self.reset_zoom, width=5)
        self.zoom_reset_button.pack(side=tk.LEFT, padx=5)
        
        # Llamar a load_available_signatures después de crear el Combobox
        self.load_available_signatures()
        
        # Área de visualización del PDF (ocupa todo el espacio)
        self.viewer_frame = ttk.Frame(self.root)
        self.viewer_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.canvas = tk.Canvas(self.viewer_frame, bg="gray")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.v_scroll = ttk.Scrollbar(self.viewer_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scroll = ttk.Scrollbar(self.viewer_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        
        # Vincular eventos
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        
        # Vincular el evento de cierre
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def on_closing(self):
        if not self.pdf_document:
            self.root.destroy()
            return

        response = messagebox.askyesnocancel(
            "Guardar cambios",
            "¿Deseas guardar los cambios antes de cerrar?",
            icon="question"
        )

        if response is True:  # Sí
            self.save_pdf()
            if self.pdf_document:
                self.root.destroy()
        elif response is False:  # No
            self.root.destroy()
        # Si response es None, significa que se seleccionó "Cancelar", así que no hacemos nada
    
    def load_available_signatures(self):
        if not os.path.exists(self.signatures_json):
            return
        try:
            with open(self.signatures_json, "r") as f:
                signatures_data = json.load(f)
            for sig_data in signatures_data:
                image_path = sig_data["image_path"]
                if os.path.exists(image_path):
                    signature_img = Image.open(image_path)
                    if signature_img.mode != 'RGBA':
                        signature_img = signature_img.convert('RGBA')
                    self.available_signatures.append({
                        "name": sig_data["name"],
                        "image": signature_img
                    })
            self.update_signature_select_combobox()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar las firmas:\n{str(e)}")
    
    def load_pdf(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not file_path:
            messagebox.showwarning("Advertencia", "No se seleccionó ningún archivo PDF.")
            return
        try:
            self.pdf_path = file_path
            self.pdf_document = fitz.open(self.pdf_path)
            self.total_pages = len(self.pdf_document)
            self.current_page = 0
            self.signatures = {i: [] for i in range(self.total_pages)}
            self.update_page_label()
            self.root.after(100, self.display_page)
            messagebox.showinfo("Éxito", f"PDF cargado correctamente: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el PDF:\n{str(e)}")
    
    def display_page(self):
        if not self.pdf_document:
            return
        self.canvas.delete("all")
        try:
            page = self.pdf_document[self.current_page]
            zoom_matrix = fitz.Matrix(self.zoom_level, self.zoom_level)
            pix = page.get_pixmap(matrix=zoom_matrix)
            self.page_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            self.tk_image = ImageTk.PhotoImage(self.page_image)
            
            img_width = pix.width
            img_height = pix.height
            canvas_width = self.canvas.winfo_width() or 700
            canvas_height = self.canvas.winfo_height() or 800
            x_offset = (canvas_width - img_width) / 2 if canvas_width > img_width else 0
            y_offset = (canvas_height - img_height) / 2 if canvas_height > img_height else 0
            self.canvas.config(scrollregion=(0, 0, img_width, img_height))
            self.canvas.create_image(x_offset, y_offset, anchor=tk.NW, image=self.tk_image)
            self.restore_signatures()
        except Exception as e:
            messagebox.showerror("Error", f"Error al mostrar la página:\n{str(e)}")
    
    def upload_signature(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")])
        if not file_path:
            messagebox.showwarning("Advertencia", "No se seleccionó ninguna imagen de firma.")
            return
        try:
            signature_img = Image.open(file_path)
            if signature_img.mode != 'RGBA':
                signature_img = signature_img.convert('RGBA')
            
            datas = signature_img.getdata()
            new_data = []
            for item in datas:
                if item[0] > 200 and item[1] > 200 and item[2] > 200:
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append(item)
            signature_img.putdata(new_data)
            
            signature_name = os.path.basename(file_path)
            signature_path = os.path.join(self.signatures_dir, signature_name)
            signature_img.save(signature_path, format="PNG")
            
            new_signature = {
                "name": signature_name,
                "image": signature_img
            }
            self.available_signatures.append(new_signature)
            
            signatures_data = [
                {"name": sig["name"], "image_path": os.path.join(self.signatures_dir, sig["name"])}
                for sig in self.available_signatures
            ]
            with open(self.signatures_json, "w") as f:
                json.dump(signatures_data, f, indent=4)
            
            self.update_signature_select_combobox()
            messagebox.showinfo("Éxito", f"Firma '{signature_name}' añadida correctamente.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo subir la firma:\n{str(e)}")
    
    def delete_available_signature(self):
        selected_index = self.signature_select_combobox.current()
        if selected_index < 0:
            messagebox.showwarning("Advertencia", "No hay firma seleccionada para eliminar.")
            return
        try:
            signature_name = self.available_signatures[selected_index]["name"]
            signature_path = os.path.join(self.signatures_dir, signature_name)
            if os.path.exists(signature_path):
                os.remove(signature_path)
            
            del self.available_signatures[selected_index]
            
            signatures_data = [
                {"name": sig["name"], "image_path": os.path.join(self.signatures_dir, sig["name"])}
                for sig in self.available_signatures
            ]
            with open(self.signatures_json, "w") as f:
                json.dump(signatures_data, f, indent=4)
            
            self.update_signature_select_combobox()
            messagebox.showinfo("Éxito", "Firma eliminada de las disponibles correctamente.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar la firma:\n{str(e)}")
    
    def draw_signature(self, signature_data):
        if not signature_data or not self.page_image:
            return
        
        scaled_width = int(signature_data["original_width"] * self.zoom_level)
        scaled_height = int(signature_data["original_height"] * self.zoom_level)
        scaled_image = signature_data["original_image"].resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
        tk_signature = ImageTk.PhotoImage(scaled_image)
        
        canvas_width = self.canvas.winfo_width() or 700
        canvas_height = self.canvas.winfo_height() or 800
        img_width = self.page_image.width
        img_height = self.page_image.height
        x_offset = (canvas_width - img_width) / 2 if canvas_width > img_width else 0
        y_offset = (canvas_height - img_height) / 2 if canvas_height > img_height else 0
        
        x = signature_data["original_x"] * self.zoom_level + x_offset
        y = signature_data["original_y"] * self.zoom_level + y_offset
        
        signature_data["tk_image"] = tk_signature
        signature_id = self.canvas.create_image(x, y, anchor=tk.NW, image=tk_signature, tags="signature")
        box_id = self.canvas.create_rectangle(
            x, y, x + scaled_width, y + scaled_height,
            outline="red", dash=(5, 2), width=2, tags="signature_box"
        )
        dot_id = self.canvas.create_oval(
            x - 5, y + scaled_height - 5, x + 5, y + scaled_height + 5,
            fill="blue", tags="signature_dot"
        )
        signature_data["canvas_items"] = {"signature": signature_id, "box": box_id, "dot": dot_id}
    
    def restore_signatures(self):
        for signature in self.signatures.get(self.current_page, []):
            self.draw_signature(signature)
    
    def update_signature_select_combobox(self):
        self.signature_select_combobox["values"] = [sig["name"] for sig in self.available_signatures]
        if self.available_signatures:
            self.signature_select_combobox.current(0)
    
    def on_signature_select_to_add(self, event):
        selected_index = self.signature_select_combobox.current()
        if selected_index >= 0:
            self.selected_available_signature = self.available_signatures[selected_index]
            messagebox.showinfo("Instrucción", "Haz clic en el lienzo para insertar la firma.")
    
    def select_signature(self, signature_index):
        for sig in self.signatures.get(self.current_page, []):
            if "box" in sig.get("canvas_items", {}):
                self.canvas.itemconfig(sig["canvas_items"]["box"], outline="red")
        
        if signature_index is not None and 0 <= signature_index < len(self.signatures.get(self.current_page, [])):
            self.selected_signature = signature_index
            if "box" in self.signatures[self.current_page][signature_index].get("canvas_items", {}):
                self.canvas.itemconfig(self.signatures[self.current_page][signature_index]["canvas_items"]["box"], outline="blue")
        else:
            self.selected_signature = None
    
    def insert_signature_at(self, x, y):
        if self.selected_available_signature:
            try:
                signature_img = self.selected_available_signature["image"]
                base_width = 150
                w_percent = (base_width / float(signature_img.size[0]))
                h_size = int((float(signature_img.size[1]) * float(w_percent)))
                
                signature_data = {
                    "original_image": signature_img,
                    "original_x": x,
                    "original_y": y,
                    "original_width": base_width,
                    "original_height": h_size,
                    "canvas_items": {}
                }
                if self.current_page not in self.signatures:
                    self.signatures[self.current_page] = []
                self.signatures[self.current_page].append(signature_data)
                self.draw_signature(signature_data)
                self.selected_available_signature = None
                messagebox.showinfo("Éxito", "Firma insertada correctamente.")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo insertar la firma:\n{str(e)}")
    
    def on_mouse_move(self, event):
        if not self.signatures.get(self.current_page):
            self.canvas.config(cursor="arrow")
            return
        
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        for i, signature in enumerate(self.signatures.get(self.current_page, [])):
            sig_x = signature["original_x"] * self.zoom_level + (self.canvas.winfo_width() - self.page_image.width) / 2
            sig_y = signature["original_y"] * self.zoom_level + (self.canvas.winfo_height() - self.page_image.height) / 2
            sig_width = signature["original_width"] * self.zoom_level
            sig_height = signature["original_height"] * self.zoom_level
            
            corners = {
                "nw": (sig_x, sig_y, sig_x + 10, sig_y + 10),
                "ne": (sig_x + sig_width - 10, sig_y, sig_x + sig_width, sig_y + 10),
                "sw": (sig_x, sig_y + sig_height - 10, sig_x + 10, sig_y + sig_height),
                "se": (sig_x + sig_width - 10, sig_y + sig_height - 10, sig_x + sig_width, sig_y + sig_height),
                "dot": (sig_x - 5, sig_y + sig_height - 5, sig_x + 5, sig_y + sig_height + 5)
            }
            
            for corner, (x1, y1, x2, y2) in corners.items():
                if x1 <= x <= x2 and y1 <= y <= y2:
                    if corner == "dot":
                        self.canvas.config(cursor="size_nw_se")
                    else:
                        self.canvas.config(cursor="size_" + corner)
                    return
            
            if sig_x <= x <= sig_x + sig_width and sig_y <= y <= sig_y + sig_height:
                self.canvas.config(cursor="fleur")
                return
        
        self.canvas.config(cursor="arrow")
    
    def on_canvas_click(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        canvas_width = self.canvas.winfo_width() or 700
        canvas_height = self.canvas.winfo_height() or 800
        img_width = self.page_image.width if self.page_image else 0
        img_height = self.page_image.height if self.page_image else 0
        x_offset = (canvas_width - img_width) / 2 if canvas_width > img_width else 0
        y_offset = (canvas_height - img_height) / 2 if canvas_height > img_height else 0
        
        if self.selected_available_signature and self.page_image:
            canvas_x = (x - x_offset) / self.zoom_level
            canvas_y = (y - y_offset) / self.zoom_level
            self.insert_signature_at(canvas_x, canvas_y)
            return
        
        clicked_items = self.canvas.find_overlapping(x-5, y-5, x+5, y+5)
        if not clicked_items:
            self.select_signature(None)
            return
        
        for i, signature in enumerate(self.signatures.get(self.current_page, [])):
            sig_x = signature["original_x"] * self.zoom_level + x_offset
            sig_y = signature["original_y"] * self.zoom_level + y_offset
            sig_width = signature["original_width"] * self.zoom_level
            sig_height = signature["original_height"] * self.zoom_level
            
            corners = {
                "nw": (sig_x, sig_y, sig_x + 10, sig_y + 10),
                "ne": (sig_x + sig_width - 10, sig_y, sig_x + sig_width, sig_y + 10),
                "sw": (sig_x, sig_y + sig_height - 10, sig_x + 10, sig_y + sig_height),
                "se": (sig_x + sig_width - 10, sig_y + sig_height - 10, sig_x + sig_width, sig_y + sig_height),
                "dot": (sig_x - 5, sig_y + sig_height - 5, sig_x + 5, sig_y + sig_height + 5)
            }
            
            for corner, (x1, y1, x2, y2) in corners.items():
                if x1 <= x <= x2 and y1 <= y <= y2:
                    self.select_signature(i)
                    self.resize_data = {
                        "active": True,
                        "corner": "sw" if corner == "dot" else corner,
                        "start_x": (x - x_offset) / self.zoom_level,
                        "start_y": (y - y_offset) / self.zoom_level,
                        "start_width": signature["original_width"],
                        "start_height": signature["original_height"]
                    }
                    return
            
            if (signature.get("canvas_items", {}).get("signature") in clicked_items or 
                signature.get("canvas_items", {}).get("box") in clicked_items):
                self.select_signature(i)
                self.drag_data = {
                    "x": (x - x_offset) / self.zoom_level,
                    "y": (y - y_offset) / self.zoom_level,
                    "item": i,
                    "start_x": signature["original_x"],
                    "start_y": signature["original_y"],
                    "dragging": False
                }
                return
    
    def on_canvas_drag(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        canvas_width = self.canvas.winfo_width() or 700
        canvas_height = self.canvas.winfo_height() or 800
        img_width = self.page_image.width if self.page_image else 0
        img_height = self.page_image.height if self.page_image else 0
        x_offset = (canvas_width - img_width) / 2 if canvas_width > img_width else 0
        y_offset = (canvas_height - img_height) / 2 if canvas_height > img_height else 0
        canvas_x = (x - x_offset) / self.zoom_level
        canvas_y = (y - y_offset) / self.zoom_level
        
        if self.resize_data["active"] and self.selected_signature is not None:
            signature = self.signatures[self.current_page][self.selected_signature]
            dx = canvas_x - self.resize_data["start_x"]
            dy = canvas_y - self.resize_data["start_y"]
            
            if self.resize_data["corner"] == "nw":
                new_width = self.resize_data["start_width"] - dx
                new_height = self.resize_data["start_height"] - dy
                new_x = self.resize_data["start_x"] + dx
                new_y = self.resize_data["start_y"] + dy
            elif self.resize_data["corner"] == "ne":
                new_width = self.resize_data["start_width"] + dx
                new_height = self.resize_data["start_height"] - dy
                new_x = signature["original_x"]
                new_y = self.resize_data["start_y"] + dy
            elif self.resize_data["corner"] == "sw":
                new_width = self.resize_data["start_width"] - dx
                new_height = self.resize_data["start_height"] + dy
                new_x = self.resize_data["start_x"] + dx
                new_y = signature["original_y"]
            elif self.resize_data["corner"] == "se":
                new_width = self.resize_data["start_width"] + dx
                new_height = self.resize_data["start_height"] + dy
                new_x = signature["original_x"]
                new_y = signature["original_y"]
            
            new_width = max(30, new_width)
            new_height = max(30, new_height)
            
            if event.state & 0x1:  # Shift key pressed
                aspect = signature["original_width"] / signature["original_height"]
                new_height = new_width / aspect
            
            signature["original_width"] = new_width
            signature["original_height"] = new_height
            if self.resize_data["corner"] in ["nw", "sw"]:
                signature["original_x"] = new_x
            if self.resize_data["corner"] in ["nw", "ne"]:
                signature["original_y"] = new_y
            
            self.redraw_signature(self.selected_signature)
        
        elif self.drag_data.get("item") is not None:
            signature = self.signatures[self.current_page][self.drag_data["item"]]
            dx = canvas_x - self.drag_data["x"]
            dy = canvas_y - self.drag_data["y"]
            
            if abs(dx) > 5 or abs(dy) > 5:
                self.drag_data["dragging"] = True
            
            if self.drag_data["dragging"]:
                signature["original_x"] = self.drag_data["start_x"] + dx
                signature["original_y"] = self.drag_data["start_y"] + dy
                self.redraw_signature(self.drag_data["item"])
    
    def on_canvas_release(self, event):
        self.resize_data["active"] = False
        self.drag_data["item"] = None
        self.drag_data["dragging"] = False
    
    def redraw_signature(self, signature_index):
        if not (0 <= signature_index < len(self.signatures.get(self.current_page, []))):
            return
        signature = self.signatures[self.current_page][signature_index]
        for item in signature.get("canvas_items", {}).values():
            self.canvas.delete(item)
        self.draw_signature(signature)
    
    def on_canvas_right_click(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        clicked_items = self.canvas.find_overlapping(x-5, y-5, x+5, y+5)
        if not clicked_items:
            return
        for i, signature in enumerate(self.signatures.get(self.current_page, [])):
            if (signature.get("canvas_items", {}).get("signature") in clicked_items or 
                signature.get("canvas_items", {}).get("box") in clicked_items):
                self.selected_signature = i
                self.delete_signature()
                return
    
    def delete_signature(self):
        if self.selected_signature is None:
            messagebox.showwarning("Advertencia", "No hay firma seleccionada para eliminar.")
            return
        try:
            for item in self.signatures[self.current_page][self.selected_signature]["canvas_items"].values():
                self.canvas.delete(item)
            del self.signatures[self.current_page][self.selected_signature]
            self.selected_signature = None
            self.display_page()
            messagebox.showinfo("Éxito", "Firma eliminada correctamente.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar la firma:\n{str(e)}")
    
    def save_pdf(self):
        if not self.pdf_document:
            messagebox.showwarning("Advertencia", "No hay documento PDF cargado.")
            return

        original_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            initialfile=f"{original_name}_firma.pdf"
        )
        if not save_path:
            return

        try:
            doc = fitz.open(self.pdf_path)
            new_doc = fitz.open()

            # Si no hay firmas, simplemente copiamos las páginas originales al nuevo documento
            if not any(self.signatures.values()):
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
                    img_buffer = io.BytesIO()
                    img.save(img_buffer, format="PNG")
                    img_bytes = img_buffer.getvalue()
                    new_page.insert_image(new_page.rect, stream=img_bytes)
            else:
                # Si hay firmas, las insertamos y aplanamos las páginas
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    if page_num in self.signatures:
                        for signature in self.signatures[page_num]:
                            x1 = signature["original_x"]
                            y1 = signature["original_y"]
                            x2 = x1 + signature["original_width"]
                            y2 = y1 + signature["original_height"]
                            rect = fitz.Rect(x1, y1, x2, y2)
                            img_buffer = io.BytesIO()
                            signature["original_image"].save(img_buffer, format="PNG")
                            img_bytes = img_buffer.getvalue()
                            page.insert_image(rect, stream=img_bytes, keep_proportion=True)

                    pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
                    img_buffer = io.BytesIO()
                    img.save(img_buffer, format="PNG")
                    img_bytes = img_buffer.getvalue()
                    new_page.insert_image(new_page.rect, stream=img_bytes)

            new_doc.save(save_path)
            new_doc.close()
            doc.close()
            messagebox.showinfo("Éxito", f"PDF guardado correctamente en:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el PDF:\n{str(e)}")
    
    def prev_page(self):
        if self.pdf_document and self.current_page > 0:
            self.current_page -= 1
            self.canvas.yview_moveto(0)
            self.display_page()
            self.update_page_label()
    
    def next_page(self):
        if self.pdf_document and self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.canvas.yview_moveto(0)
            self.display_page()
            self.update_page_label()
    
    def update_page_label(self):
        self.page_label.config(text=f"Página: {self.current_page + 1}/{self.total_pages}")
    
    def adjust_zoom(self, factor):
        self.zoom_level *= factor
        self.zoom_level = max(0.5, min(3.0, self.zoom_level))
        self.display_page()
    
    def reset_zoom(self):
        self.zoom_level = 1.0
        self.display_page()
    
    def on_canvas_resize(self, event):
        if self.page_image:
            self.display_page()
    
    def on_mouse_wheel(self, event):
        if event.state & 0x4:  # Control key pressed
            factor = 1.1 if event.delta > 0 else 0.9
            self.adjust_zoom(factor)
            return "break"
        else:
            if self.page_image:
                canvas_height = self.canvas.winfo_height()
                page_height = self.page_image.height
                if page_height <= canvas_height:
                    if event.delta < 0 and self.current_page < self.total_pages - 1:
                        self.next_page()
                    elif event.delta > 0 and self.current_page > 0:
                        self.prev_page()
                else:
                    self.canvas.yview_scroll(-1 * (event.delta // 120), "units")
                    yview = self.canvas.yview()
                    if yview[1] == 1.0 and event.delta < 0 and self.current_page < self.total_pages - 1:
                        self.next_page()
                    elif yview[0] == 0.0 and event.delta > 0 and self.current_page > 0:
                        self.prev_page()
            return "break"

if __name__ == "__main__":
    splash_root = tk.Tk()
    logo_path = r"C:/Users/jnoh/Downloads/pdf felipe/pdf-felipe/logo/logo_adobo.png"
    splash = SplashScreen(splash_root, logo_path, duration=3000)
    splash_root.mainloop()
    
    root = tk.Tk()
    app = PDFEditor(root)
    root.mainloop()

    