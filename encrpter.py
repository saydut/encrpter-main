import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import requests
import tempfile
import subprocess
import sys
import threading
import zipfile
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# --- GÖRÜNÜM AYARLARI ---
ctk.set_appearance_mode("Dark")  # Mod: "System" (standart), "Dark", "Light"
ctk.set_default_color_theme("dark-blue")  # Tema: "blue" (standart), "green", "dark-blue"

class ModernApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Pencere Ayarları
        self.title("Saydut Kripto | Pro")
        self.geometry("500x580")
        self.resizable(False, False)
        
        # İkon (Varsa .ico dosyası eklenebilir, yoksa varsayılan kalır)
        # self.iconbitmap('icon.ico')

        self.create_ui()
        
    def create_ui(self):
        # --- BAŞLIK ALANI ---
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.header_frame.pack(pady=(20, 10), padx=20, fill="x")

        self.title_label = ctk.CTkLabel(self.header_frame, text="SAYDUT KRİPTO", font=ctk.CTkFont(family="Inter", size=24, weight="bold"))
        self.title_label.pack()

        self.subtitle_label = ctk.CTkLabel(self.header_frame, text="AES-256 Askeri Standart Şifreleme", font=ctk.CTkFont(family="Inter", size=12), text_color="gray")
        self.subtitle_label.pack()

        # --- PAROLA GİRİŞ ALANI (Global) ---
        self.pass_frame = ctk.CTkFrame(self, corner_radius=15)
        self.pass_frame.pack(pady=10, padx=20, fill="x")

        self.pass_label = ctk.CTkLabel(self.pass_frame, text="Güvenlik Anahtarı (Parola)", font=ctk.CTkFont(size=12, weight="bold"))
        self.pass_label.pack(pady=(10, 5), padx=10, anchor="w")

        self.password_entry = ctk.CTkEntry(self.pass_frame, placeholder_text="Parolanızı buraya girin...", show="*", height=40)
        self.password_entry.pack(pady=(0, 15), padx=15, fill="x")

        # --- SEKMELİ YAPI (Tabs) ---
        self.tabview = ctk.CTkTabview(self, width=460, height=250)
        self.tabview.pack(pady=10, padx=20)

        self.tabview.add("Dosya İşlemleri")
        self.tabview.add("Klasör İşlemleri")
        
        self.setup_file_tab()
        self.setup_folder_tab()

        # --- DURUM VE GÜNCELLEME ---
        self.status_label = ctk.CTkLabel(self, text="Sistem Hazır", text_color="gray", font=ctk.CTkFont(size=11))
        self.status_label.pack(pady=(5, 0))

        self.update_btn = ctk.CTkButton(self, text="Güncellemeleri Kontrol Et", command=self.prog_ver_check, 
                                        fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE"))
        self.update_btn.pack(side="bottom", pady=20)

    def setup_file_tab(self):
        tab = self.tabview.tab("Dosya İşlemleri")
        
        info_label = ctk.CTkLabel(tab, text="Tek bir dosyayı şifrelemek veya çözmek için\naşağıdaki butonları kullanın.", text_color="gray")
        info_label.pack(pady=15)

        # Butonlar Yan Yana
        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10)

        self.encrypt_file_btn = ctk.CTkButton(btn_frame, text="🔒 Dosya Şifrele", command=self.encrypt, height=45, fg_color="#ef4444", hover_color="#b91c1c")
        self.encrypt_file_btn.pack(side="left", expand=True, padx=5, fill="x")

        self.decrypt_file_btn = ctk.CTkButton(btn_frame, text="🔓 Dosya Çöz", command=self.decrypt, height=45, fg_color="#22c55e", hover_color="#15803d")
        self.decrypt_file_btn.pack(side="right", expand=True, padx=5, fill="x")

    def setup_folder_tab(self):
        tab = self.tabview.tab("Klasör İşlemleri")
        
        info_label = ctk.CTkLabel(tab, text="Bir klasör içindeki TÜM dosyaları işler.\nDikkatli kullanın!", text_color="gray")
        info_label.pack(pady=15)

        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10)

        self.encrypt_folder_btn = ctk.CTkButton(btn_frame, text="🔒 Klasör Şifrele", command=self.encrypt_folder, height=45, fg_color="#ef4444", hover_color="#b91c1c")
        self.encrypt_folder_btn.pack(side="left", expand=True, padx=5, fill="x")

        self.decrypt_folder_btn = ctk.CTkButton(btn_frame, text="🔓 Klasör Çöz", command=self.decrypt_folder, height=45, fg_color="#22c55e", hover_color="#15803d")
        self.decrypt_folder_btn.pack(side="right", expand=True, padx=5, fill="x")

    # --- KRİPTOGRAFİ MANTIKLARI (Değişmedi) ---

    def log(self, message, is_error=False):
        self.status_label.configure(text=message, text_color="#ef4444" if is_error else "gray")
        self.update_idletasks()

    def key_derivation(self, password, salt):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(), iterations=100000,
            salt=salt, length=32, backend=default_backend()
        )
        return kdf.derive(password.encode())

    def encrypt_file(self, file_path, password):
        try:
            salt = os.urandom(16)
            key = self.key_derivation(password, salt)
            with open(file_path, 'rb') as f: plaintext = f.read()
            
            cipher = Cipher(algorithms.AES(key), modes.GCM(salt), backend=default_backend())
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(plaintext) + encryptor.finalize()

            with open(file_path + '.enc', 'wb') as f: f.write(encryptor.tag + salt + ciphertext)
            os.remove(file_path)
            return True
        except Exception as e:
            print(e)
            return False

    def decrypt_file(self, encrypted_file_path, password):
        try:
            with open(encrypted_file_path, 'rb') as f: data = f.read()
            tag, salt, ciphertext = data[:16], data[16:32], data[32:]
            
            key = self.key_derivation(password, salt)
            cipher = Cipher(algorithms.AES(key), modes.GCM(salt, tag), backend=default_backend())
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()

            with open(encrypted_file_path[:-4], 'wb') as f: f.write(plaintext)
            os.remove(encrypted_file_path)
            return True
        except Exception:
            return False

    def get_password(self):
        pwd = self.password_entry.get()
        if not pwd:
            messagebox.showwarning("Uyarı", "Lütfen bir parola girin.")
            return None
        return pwd

    # --- BUTON AKSİYONLARI ---

    def encrypt(self):
        pwd = self.get_password()
        if not pwd: return
        
        file_path = filedialog.askopenfilename()
        if file_path:
            self.log("Şifreleniyor...")
            if self.encrypt_file(file_path, pwd):
                self.log("İşlem Başarılı: Dosya şifrelendi.")
                messagebox.showinfo("Başarılı", "Dosya güvenli bir şekilde şifrelendi.")
            else:
                self.log("Hata oluştu!", True)

    def decrypt(self):
        pwd = self.get_password()
        if not pwd: return
        
        file_path = filedialog.askopenfilename(filetypes=[("Encrypted Files", "*.enc")])
        if file_path:
            self.log("Şifre Çözülüyor...")
            if self.decrypt_file(file_path, pwd):
                self.log("İşlem Başarılı: Dosya çözüldü.")
                messagebox.showinfo("Başarılı", "Dosya orijinal haline döndü.")
            else:
                self.log("Hata: Yanlış parola!", True)
                messagebox.showerror("Hata", "Şifre çözülemedi. Parolayı kontrol edin.")

    def encrypt_folder(self):
        pwd = self.get_password()
        if not pwd: return
        
        folder = filedialog.askdirectory()
        if folder:
            self.log("Klasör taranıyor...")
            count = 0
            for root, _, files in os.walk(folder):
                for file in files:
                    if not file.endswith('.enc'):
                        if self.encrypt_file(os.path.join(root, file), pwd):
                            count += 1
            self.log(f"Tamamlandı: {count} dosya şifrelendi.")
            messagebox.showinfo("Toplu İşlem", f"{count} dosya şifrelendi.")

    def decrypt_folder(self):
        pwd = self.get_password()
        if not pwd: return
        
        folder = filedialog.askdirectory()
        if folder:
            self.log("Klasör taranıyor...")
            count = 0
            fail = 0
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.endswith('.enc'):
                        if self.decrypt_file(os.path.join(root, file), pwd):
                            count += 1
                        else:
                            fail += 1
            self.log(f"Bitti: {count} çözüldü, {fail} hata.")
            messagebox.showinfo("Rapor", f"{count} dosya başarıyla çözüldü.\n{fail} dosya çözülemedi (yanlış şifre olabilir).")

    # --- GÜNCELLEME SİSTEMİ (Orijinal Koddan) ---
    def prog_ver_check(self):
        self.log("Sunucu kontrol ediliyor...")
        # Demo amaçlı basit kontrol, orijinal mantığını buraya yapıştırabilirsin.
        # GUI donmaması için bunu thread içinde çalıştırmak en iyisidir.
        threading.Thread(target=self._check_update_thread, daemon=True).start()

    def _check_update_thread(self):
        try:
            # Buraya requests kodlarını koy
            # Örnek:
            # response = requests.get("gitlab_url...")
            # ...
            # GUI'yi güncellemek için:
            # self.after(0, lambda: messagebox.showinfo("Bilgi", "Sistem Güncel"))
            self.log("Sistem Güncel")
        except Exception:
            self.log("Sunucuya ulaşılamadı", True)

if __name__ == "__main__":
    app = ModernApp()
    app.mainloop()