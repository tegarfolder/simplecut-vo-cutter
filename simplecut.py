import customtkinter as ctk
from tkinter import messagebox, scrolledtext
from tkinterdnd2 import DND_FILES, TkinterDnD
import whisper
from pydub import AudioSegment
import os
import re
import threading
import sys
import shutil
import subprocess
import webbrowser
from tkinter import messagebox
from audacity_pipe import import_audio_and_label, AudacityPipeError


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class ConsoleRedirect:
    def __init__(self, widget):
        self.widget = widget

    def write(self, message):
        if message.strip():
            self.widget.after(0, lambda: self._append(message))

    def _append(self, message):
        self.widget.configure(state="normal")
        self.widget.insert("end", message)
        self.widget.see("end")
        self.widget.configure(state="disabled")

    def flush(self):
        pass

class App(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.audio_path = None
        self.label_path = None

        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        TkinterDnD._require(self)

        self.title("Budak Audacity")
        self.geometry("1000x750")
        ctk.set_appearance_mode("dark")

        self.file_path = ""
        self.current_result = None
        self.console_visible = False
        self.editor_status = None
        self.show_advanced = ctk.BooleanVar(value=False)

        # --- MAIN LAYOUT CONTAINER ---
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True)

        # PANEL KIRI (Kontrol Utama)
        self.left_panel = ctk.CTkFrame(self.main_container, width=450)
        self.left_panel.pack(side="left", fill="both", padx=10, pady=10)
        self.left_panel.pack_propagate(False) # Kunci lebar agar tidak berubah

        # PANEL KANAN (Transcript Editor - Awalnya Tersembunyi)
        self.right_panel = ctk.CTkFrame(self.main_container)
        #self.right_panel.pack(side="right", fill="both", expand=True, padx=10, pady=10) 
        # Pack dilakukan nanti saat AI selesai

        self.label_before = ctk.CTkLabel(self.main_container, text="Transcript will be displayed here\n^_~", font=("consolas", 14, "italic"), text_color="#5a5a5a")
        self.label_before.pack(expand=True,pady=15)

        # --- UI ELEMENTS ---
        self.label_title = ctk.CTkLabel(self.left_panel, text="Budak Audacity", font=("consolas", 18, "bold"))
        self.label_title.pack(pady=15)

        # --- ROW: OPTIONS (MODEL & FORMAT) ---
        # Container frame agar kedua menu sejajar horizontal
        self.options_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.options_frame.pack(pady=(0, 10))

        # === KOLOM KIRI: AI Model ===
        self.model_subframe = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        self.model_subframe.pack(side="left", padx=10)

        self.label_model = ctk.CTkLabel(self.model_subframe, text="AI Model Size:", font=("Arial", 12))
        self.label_model.pack(pady=(0, 2))
        
        self.model_var = ctk.StringVar(value="base")
        self.model_menu = ctk.CTkOptionMenu(self.model_subframe, 
                                            values=["tiny", "base", "small", "medium"],
                                            variable=self.model_var,
                                            width=140, # Lebar sedikit lebih besar untuk nama model
                                            fg_color="#34495e",
                                            button_color="#2c3e50")
        self.model_menu.pack()

        # === KOLOM KANAN: Export Format ===
        self.format_subframe = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        self.format_subframe.pack(side="left", padx=10)

        self.label_format = ctk.CTkLabel(self.format_subframe, text="Export Format:", font=("Arial", 12))
        self.label_format.pack(pady=(0, 2))
        
        self.format_var = ctk.StringVar(value="wav")
        self.format_menu = ctk.CTkOptionMenu(self.format_subframe, 
                                            values=["mp3", "wav"],
                                            variable=self.format_var,
                                            width=100, # Lebar lebih kecil cukup untuk mp3/wav
                                            fg_color="#34495e",
                                            button_color="#2c3e50")
        self.format_menu.pack()

        # --- SETTINGS FRAME (PADDING) ---
        self.settings_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.settings_frame.pack(pady=5)

        # Start Padding
        self.lbl_start_pad = ctk.CTkLabel(self.settings_frame, text="Start Padding (ms):", font=("Arial", 11))
        self.lbl_start_pad.grid(row=0, column=0, padx=5)
        self.entry_start_pad = ctk.CTkEntry(self.settings_frame, width=60)
        self.entry_start_pad.insert(0, "80") # Default: Mundur 50ms (agar awal tidak terpotong)
        self.entry_start_pad.grid(row=0, column=1, padx=5)

        # End Padding
        self.lbl_end_pad = ctk.CTkLabel(self.settings_frame, text="End Padding (ms):", font=("Arial", 11))
        self.lbl_end_pad.grid(row=0, column=2, padx=5)
        self.entry_end_pad = ctk.CTkEntry(self.settings_frame, width=60)
        self.entry_end_pad.insert(0, "-80") # Default: Potong 50ms lebih cepat (agar kata selanjutnya tidak bocor)
        self.entry_end_pad.grid(row=0, column=3, padx=5)
        
        self.lbl_hint = ctk.CTkLabel(self.left_panel, text="(^_____^)", font=("Arial", 10), text_color="gray")
        self.lbl_hint.pack(pady=(0, 10))

        # --- DRAG & DROP ---
        self.drop_frame = ctk.CTkFrame(self.left_panel, width=500, height=120, border_width=2, border_color="gray")
        self.drop_frame.pack(pady=10, padx=20)
        self.drop_frame.pack_propagate(False)

        self.label_drop = ctk.CTkLabel(self.drop_frame, text="Drag & Drop .MP3 / .WAV here", font=("Arial", 14))
        self.label_drop.place(relx=0.5, rely=0.5, anchor="center")

        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind('<<Drop>>', self.handle_drop)

        self.label_status = ctk.CTkLabel(self.left_panel, text="Status: Waiting file...", text_color="gray")
        self.label_status.pack(pady=5)

        # Tombol Aksi
        # === Row: Create Label + Import Audacity ===
        self.label_row = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.label_row.pack(pady=8, fill="x", padx=100)
        self.btn_label = ctk.CTkButton(
            self.label_row,
            text="Create Audacity® Label",
            command=lambda: self.start_process("label"),
            state="disabled", fg_color="#414141"
        )
        self.btn_label.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_import_audacity = ctk.CTkButton(
            self.label_row,
            text="→ Audacity",
            width=100,
            command=self.on_import_to_audacity,
            font=("Arial", 12,),
            state="disabled", fg_color="#414141"
        )
        self.btn_import_audacity.pack(side="right")

        self.btn_transcript = ctk.CTkButton(
            self.left_panel, text="Cut from Transcript",
            command=lambda: self.start_process("transcript"),
            state="disabled", fg_color="#414141"
            )
        self.btn_transcript.pack(pady=8, fill="x", padx=100)

        self.btn_direct_cut = ctk.CTkButton(
            self.left_panel, text="AI Direct Cut",
            command=lambda: self.start_process("cut"),
            state="disabled", fg_color="#414141"
            )
        # self.btn_direct_cut.pack(pady=8, fill="x", padx=100)

        self.progress = ctk.CTkProgressBar(self.left_panel, width=200)
        self.progress.pack(pady=15)
        self.progress.set(0)

        # --- CONSOLE TOGGLE BUTTON ---
        self.btn_toggle_console = ctk.CTkButton(
            self.left_panel,
            text="Show Console",
            command=self.toggle_console,
            fg_color="transparent",
            text_color="#8ab4f8",
            font=("Arial", 11, "underline"),
            height=22,
            corner_radius=0,
            cursor="hand2"
        )
        self.btn_toggle_console.pack(pady=(5, 0))

        self.console_frame = ctk.CTkFrame(self.left_panel)

        self.console_label = ctk.CTkLabel(
            self.console_frame,
            text="Console Log",
            font=("Arial", 11, "bold")
        )
        self.console_label.pack(anchor="w", padx=5)

        self.console = scrolledtext.ScrolledText(
            self.console_frame,
            height=8,
            font=("Consolas", 10),
            bg="#111111",
            fg="#3eac3e",
            insertbackground="white"
        )
        self.console.pack(fill="both", expand=True)
        self.console.configure(state="disabled")

        sys.stdout = ConsoleRedirect(self.console)
        sys.stderr = ConsoleRedirect(self.console)


        # --- FOOTER ---
        self.footer_container = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.footer_container.pack(side="bottom", fill="x", padx=15, pady=10)

        # self.label_credit = ctk.CTkLabel(self.footer_container, text="ZeusDev™ 2025", font=("Arial", 10), text_color="#A1A1A1")
        # self.label_credit.pack(side="left")

        self.label_credit = ctk.CTkLabel(
            self.footer_container, 
            text="ZeusDev™ 2025", 
            font=("Arial", 10,), # Tambah garis bawah agar jelas bisa diklik
            text_color="#A1A1A1",
            cursor="hand2"                  # Kursor berubah jadi tangan
        )
        self.label_credit.pack(side="left")
        
        # Memberikan fungsi klik pada Label
        self.label_credit.bind("<Button-1>", lambda e: webbrowser.open("https://zeusanim.notion.site/SimpleCut-Manual-2d1b85d5ae5a80ca8e96d0003f071394?source=copy_link"))

        # Advanced Toggle (Bottom Right)
        self.switch_advanced = ctk.CTkSwitch(self.footer_container, text="ADV", 
                                             variable=self.show_advanced, 
                                             command=self.toggle_advanced_cut,
                                             font=("Arial", 8, "bold"),
                                             width=50, height=18, switch_width=30, switch_height=16)
        self.switch_advanced.pack(side="right", padx=(5, 0))

        self.ffmpeg_status = ctk.CTkLabel(self.footer_container, text="", font=("Arial", 10))
        self.ffmpeg_status.pack(side="right")
        
        self.btn_install_ffmpeg = ctk.CTkButton(self.footer_container, text="Install FFmpeg", width=80, height=20, font=("Arial", 10), command=self.install_ffmpeg_winget, fg_color="#e67e22")

        self.check_ffmpeg()

    def on_import_to_audacity(self):
            # UBAH DISINI: Gunakan self.file_path, bukan self.audio_path
            if not self.file_path: 
                messagebox.showerror("Error", "No audio file selected")
                return

            try:
                # UBAH DISINI: Kirim self.file_path ke fungsi pipe
                import_audio_and_label(self.file_path)
                
                # Opsional: Gunakan print atau self.console karena self.log mungkin tidak didefinisikan
                print("Audio imported. Pilih manual label nya (.txt) di Audacity ygy.") 
                
            except AudacityPipeError as e:
                # UBAH DISINI: self.show_error sepertinya tidak ada di class App, ganti ke messagebox
                messagebox.showerror("Audacity Error", str(e))

    def check_ffmpeg(self):
        if shutil.which("ffmpeg"):
            self.ffmpeg_status.configure(text="FFmpeg: Installed", text_color="#59864e")
            self.ffmpeg_installed = True
            self.btn_install_ffmpeg.pack_forget()
        else:
            self.ffmpeg_status.configure(text="FFmpeg: Not installed!", text_color="#e04c4c")
            self.ffmpeg_installed = False
            self.btn_install_ffmpeg.pack(side="right", padx=5)

    def handle_drop(self, event):
        path = event.data.strip('{}').strip('"') 
        if path.lower().endswith(('.mp3', '.wav', '.m4a', '.flac')):
            self.file_path = path
            self.label_drop.configure(text=f"Selected:\n{os.path.basename(path)}", text_color="#3abf93")
            if self.ffmpeg_installed: self.btn_direct_cut.configure(state="normal", fg_color="#2980b9")
            self.btn_label.configure(state="normal", fg_color="#2980b9")
            self.btn_transcript.configure(state="normal", fg_color="#2980b9")
            self.label_status.configure(text="Status: Ready", text_color="white")
        else:
            messagebox.showerror("Error", "Format not supported bolo!")

    def start_process(self, mode):
        self.btn_direct_cut.configure(state="disabled")
        self.btn_label.configure(state="disabled")
        self.btn_transcript.configure(state="disabled")
        # self.btn_import_audacity.configure(state="disabled")
        threading.Thread(target=self.run_ai, args=(mode,), daemon=True).start()

    def run_ai(self, mode):
        try:
            pilihan = self.model_var.get()
            self.label_status.configure(text=f"Status: AI Processing ({pilihan})...", text_color="yellow")
            self.progress.set(0.2)
            print("Loading Whisper model...")
            self.progress.set(0.4)
            model_path = resource_path(f"models/{pilihan}.pt")
            model = whisper.load_model(model_path)
            print("Model loaded")
            self.progress.set(0.6)
            print("Transcribing audio...")
            self.progress.set(0.8)
            result = model.transcribe(self.file_path, verbose=False)
            print("Transcription done")
            self.current_result = result
            
            file_name = os.path.basename(self.file_path).rsplit(".", 1)[0]
            dir_path = os.path.dirname(self.file_path)

            if mode == "cut":
                self.process_direct_cut(result, file_name, dir_path)
                messagebox.showinfo("Done", "Auto cut is done bolo!")
            elif mode == "label":
                self.process_label(result, file_name, dir_path)
                messagebox.showinfo("Done", "Audacity's label Created!")
            elif mode == "transcript":
                self.show_transcript_editor(result)

            self.label_status.configure(text="Status: Done!", text_color="green")
        except Exception as e:
            messagebox.showerror("Error", f"There is an error lur: {str(e)}")
        finally:
            self.btn_direct_cut.configure(state="normal")
            self.btn_label.configure(state="normal")
            self.btn_transcript.configure(state="normal")
            self.btn_import_audacity.configure(state="normal", fg_color="#39a182")
            self.progress.set(0)

    def show_transcript_editor(self, result):
        for widget in self.right_panel.winfo_children():
                    widget.destroy()

        # Tampilkan panel kanan
        self.label_before.pack_forget()
        self.right_panel.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        lbl_title = ctk.CTkLabel(self.right_panel, text="Manual Split Editor", font=("Arial", 16, "bold"))
        lbl_title.pack(pady=10)

        # Frame tombol di bawah
        btn_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        btn_frame.pack(side="bottom", pady=20)

        # self.editor_status = ctk.CTkLabel(self.right_panel, text="Ready to process", text_color="gray", font=("Arial", 10))
        # self.editor_status.pack()

        # Penjelasan singkat untuk user
        lbl_info = ctk.CTkLabel(self.right_panel, text="Use ( / ) between the sentences you want to cut ygy.", font=("Arial", 11,))
        lbl_info.pack(pady=(10, 0))

        txt_area = scrolledtext.ScrolledText(
            self.right_panel, 
            wrap='word', 
            font=("Arial", 12), 
            spacing3=10,
            bg="#ffffff",
            fg="black",
            insertbackground="blue",
            height=15,
        )
        # fill='both' dan expand=True akan membagi ruang dengan widget lain
        txt_area.pack(expand=True, fill='both', padx=10, pady=(0, 5))

        # Konfigurasi tag untuk warna merah
        txt_area.tag_configure("highlight_slash", foreground="red", font=("Arial", 12, "bold"))

        # # --- LOGIKA PEMISAHAN BARIS YANG LEBIH CERDAS ---
        # raw_text = result["text"].strip()

        # # Penjelasan Regex:
        # # (?<!\b[A-Z]) -> Jangan potong jika sebelumnya adalah satu huruf besar (inisial)
        # # (?<![A-Z][a-z]\.) -> Jangan potong jika sebelumnya adalah singkatan umum (misal: Mr. Dr.)
        # # ([.!?])\s+ -> Potong pada . ! ? yang diikuti spasi
        # formatted_text = re.sub(r'(?<!\b[A-Z])(?<![A-Z][a-z]\.)([.!?])\s+', r'\1\n', raw_text)

        # txt_area.insert('insert', formatted_text)

        txt_area.insert('insert', result["text"].strip())

        # Fungsi untuk mewarnai "/" secara otomatis saat diketik
        def highlight_slashes(event=None):
            # Hapus tag lama agar tidak tumpang tindih
            txt_area.tag_remove("highlight_slash", "1.0", "end")
            
            start = "1.0"
            while True:
                start = txt_area.search("/", start, stopindex="end")
                if not start:
                    break
                end = f"{start}+1c"
                txt_area.tag_add("highlight_slash", start, end)
                start = end

        # Jalankan pewarnaan pertama kali
        highlight_slashes()

        # Bind setiap kali ada tombol dilepas (KeyRelease) untuk update warna real-time
        txt_area.bind("<KeyRelease>", highlight_slashes)

        def limit_input(event):
            allowed = ["slash", "BackSpace", "Delete", "Left", "Right", "Up", "Down", "space"]
            if event.keysym not in allowed:
                return "break"
        txt_area.bind("<Key>", limit_input)

        # Tombol Apply (Potong Audio)
        btn_apply = ctk.CTkButton(btn_frame, text="CUT AUDIO", fg_color="#315c79", 
                                   command=lambda: self.manual_split_logic(txt_area.get("1.0", "end-1c"), None))
        btn_apply.pack(side="left", padx=5)

        # Tombol Baru: Create Label (Berdasarkan "/" )
        btn_make_label = ctk.CTkButton(btn_frame, text="CREATE LABEL", fg_color="#377ec0", 
                                        command=lambda: self.manual_label_logic(txt_area.get("1.0", "end-1c"), None))
        btn_make_label.pack(side="left", padx=5)

    def manual_split_logic(self, edited_text, window):
        # window.destroy()
        threading.Thread(target=self.process_manual_split, args=(edited_text,), daemon=True).start()

    def manual_label_logic(self, edited_text, window):
        # window.destroy()
        threading.Thread(target=self.process_manual_label, args=(edited_text,), daemon=True).start()

    # --- LOGIKA CORE DENGAN PADDING CUSTOM ---

    def process_manual_split(self, edited_text):
        try:
            # Ambil format dari UI (mp3 atau wav)
            out_fmt = self.format_var.get()

            pad_start = int(self.entry_start_pad.get())
            pad_end = int(self.entry_end_pad.get())

            self.label_status.configure(text="Status: Cutting Manual...", text_color="cyan")
            self.progress.set(0.5)
            
            parts = edited_text.split("/")
            audio = AudioSegment.from_file(self.file_path)
            file_name = os.path.basename(self.file_path).rsplit(".", 1)[0]
            output_folder = os.path.join(os.path.dirname(self.file_path), f"(manualCut)_{file_name}")
            
            if not os.path.exists(output_folder): os.makedirs(output_folder)

            segments = self.current_result["segments"]
            current_start_ms = 0
            
            for i, part in enumerate(parts):
                clean_part = part.strip().replace(" ", "").lower()
                if not clean_part: continue
                
                accumulated = ""
                found_end_ms = len(audio)

                for seg in segments:
                    seg_text = seg["text"].strip().replace(" ", "").lower()
                    accumulated += seg_text
                    if clean_part in accumulated:
                        found_end_ms = seg["end"] * 1000
                        break

                safe_start = max(0, current_start_ms - pad_start)
                safe_end = found_end_ms + pad_end
                if safe_end <= safe_start: safe_end = safe_start + 500 

                chunk = audio[safe_start:safe_end]
                chunk = chunk.fade_out(10)
                
                # UBAH DISINI: Gunakan variabel out_fmt untuk ekstensi dan format
                chunk.export(os.path.join(output_folder, f"part_{i+1}.{out_fmt}"), format=out_fmt)
                
                current_start_ms = found_end_ms

            self.progress.set(1)
            messagebox.showinfo("Success", f"File saved in: (manualCut)_{file_name}")
            self.label_status.configure(text="Status: Done", text_color="green")
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    def process_label(self, result, name, folder):
        try:
            pad_start = int(self.entry_start_pad.get()) / 1000.0 # Convert ke detik
            pad_end = int(self.entry_end_pad.get()) / 1000.0   # Convert ke detik

            label_path = os.path.join(folder, f"{name}.txt")
            with open(label_path, "w", encoding="utf-8") as f:
                start_time_ori, nomor = 0.0, 1
                for seg in result["segments"]:
                    end_time_ori = seg["end"]
                    
                    if re.search(r'[.?!]$', seg["text"].strip()):
                        # Hitung dengan padding
                        final_start = max(0.0, start_time_ori - pad_start)
                        final_end = end_time_ori + pad_end
                        
                        f.write(f"{final_start:.6f}\t{final_end:.6f}\t{nomor}\n")
                        
                        start_time_ori, nomor = end_time_ori, nomor + 1
        except Exception as e:
            messagebox.showerror("Error", f"Label Error: {e}")

    def process_manual_label(self, edited_text):
        try:
            # Ambil nilai padding
            pad_start = int(self.entry_start_pad.get()) / 1000.0
            pad_end = int(self.entry_end_pad.get()) / 1000.0

            self.label_status.configure(text="Status: Generating Manual Label...", text_color="cyan")
            
            parts = edited_text.split("/")
            file_name = os.path.basename(self.file_path).rsplit(".", 1)[0]
            label_path = os.path.join(os.path.dirname(self.file_path), f"{file_name}_manual.txt")
            
            segments = self.current_result["segments"]
            current_start_time = 0.0
            
            with open(label_path, "w", encoding="utf-8") as f:
                for i, part in enumerate(parts):
                    clean_part = part.strip().replace(" ", "").lower()
                    if not clean_part: continue
                    
                    accumulated = ""
                    found_end_time = segments[-1]["end"] # Default ke akhir audio

                    for seg in segments:
                        seg_text = seg["text"].strip().replace(" ", "").lower()
                        accumulated += seg_text
                        if clean_part in accumulated:
                            found_end_time = seg["end"]
                            break

                    # Terapkan padding
                    final_start = max(0.0, current_start_time - pad_start)
                    final_end = found_end_time + pad_end
                    
                    # Tulis ke format label Audacity: Start[tab]End[tab]Label
                    f.write(f"{final_start:.6f}\t{final_end:.6f}\t{i+1}\n")
                    
                    # Update start untuk label berikutnya
                    current_start_time = found_end_time

            self.label_status.configure(text="Status: Label Created", text_color="green")
            messagebox.showinfo("Success", f"Manual label created:\n{os.path.basename(label_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Manual Label Error: {e}")

    def process_direct_cut(self, result, name, folder):
        try:
            # Ambil format dari UI
            out_fmt = self.format_var.get()
            
            pad_start = int(self.entry_start_pad.get())
            pad_end = int(self.entry_end_pad.get())

            output_folder = os.path.join(folder, f"(cuts)_{name}")
            if not os.path.exists(output_folder): os.makedirs(output_folder)
            audio = AudioSegment.from_file(self.file_path)
            
            start_time_ori, nomor = 0, 1
            for seg in result["segments"]:
                end_time_ori = seg["end"] * 1000
                
                if re.search(r'[.?!]$', seg["text"].strip()):
                    safe_start = max(0, start_time_ori - pad_start)
                    safe_end = end_time_ori + pad_end
                    
                    chunk = audio[safe_start:safe_end]
                    chunk = chunk.fade_out(10)
                    
                    # UBAH DISINI: Export sesuai format yang dipilih
                    chunk.export(os.path.join(output_folder, f"{nomor}.{out_fmt}"), format=out_fmt)
                    
                    start_time_ori, nomor = end_time_ori, nomor + 1
        except Exception as e:
            messagebox.showerror("Error", f"Cut Error: {e}")
    
    def toggle_advanced_cut(self):
        if self.show_advanced.get():
            # Show AI Direct Cut
            self.btn_direct_cut.pack(pady=8, fill="x", padx=100, before=self.progress)
        else:
            self.btn_direct_cut.pack_forget()

    def toggle_console(self):
        if self.console_visible:
            self.console_frame.pack_forget()
            self.btn_toggle_console.configure(text="Show Console Log")
            self.console_visible = False
        else:
            self.console_frame.pack(fill="both", expand=False, padx=15, pady=(5, 10))
            self.btn_toggle_console.configure(text="Hide Console Log")
            self.console_visible = True


    def install_ffmpeg_winget(self):
        subprocess.run("winget install ffmpeg --accept-source-agreements --accept-package-agreements", shell=True)
        self.check_ffmpeg()

if __name__ == "__main__":
    app = App()
    app.mainloop()