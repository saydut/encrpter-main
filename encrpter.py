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
import webbrowser
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# Uygulama bilgisi ve güncelleme kaynağı
APP_VERSION = "2.0"
PROGRAMS_URL = "https://www.saydut.com/static/programs.json"
PROGRAM_ID = "saydut-kripto"


def _semver_tuple(v: str) -> tuple[int, int, int]:
    v = (v or "").strip()
    if v.startswith("v"):
        v = v[1:]
    parts = v.split(".")
    out = []
    for i in range(3):
        try:
            out.append(int(parts[i]))
        except Exception:
            out.append(0)
    return tuple(out)  # type: ignore


def _http_get_json(url: str, timeout: int = 15) -> dict:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()

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

        self.create_ui()
        self.is_busy = False
        self._update_prompted = False
        self.after(1500, self.check_launcher_update_background)

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

        self.encrypt_file_btn = ctk.CTkButton(btn_frame, text="Dosya Şifrele", command=self.encrypt, height=45, fg_color="#ef4444", hover_color="#b91c1c")
        self.encrypt_file_btn.pack(side="left", expand=True, padx=5, fill="x")

        self.decrypt_file_btn = ctk.CTkButton(btn_frame, text="Dosya Çöz", command=self.decrypt, height=45, fg_color="#22c55e", hover_color="#15803d")
        self.decrypt_file_btn.pack(side="right", expand=True, padx=5, fill="x")

    def setup_folder_tab(self):
        tab = self.tabview.tab("Klasör İşlemleri")
        
        info_label = ctk.CTkLabel(tab, text="Bir klasör içindeki TÜM dosyaları işler.\nDikkatli kullanın!", text_color="gray")
        info_label.pack(pady=15)

        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10)

        self.encrypt_folder_btn = ctk.CTkButton(btn_frame, text="Klasör Şifrele", command=self.encrypt_folder, height=45, fg_color="#ef4444", hover_color="#b91c1c")
        self.encrypt_folder_btn.pack(side="left", expand=True, padx=5, fill="x")

        self.decrypt_folder_btn = ctk.CTkButton(btn_frame, text="Klasör Çöz", command=self.decrypt_folder, height=45, fg_color="#22c55e", hover_color="#15803d")
        self.decrypt_folder_btn.pack(side="right", expand=True, padx=5, fill="x")

    # --- KRİPTOGRAFİ MANTIKLARI (Değişmedi) ---

    def log(self, message, is_error=False):
        self.status_label.configure(text=message, text_color="#ef4444" if is_error else "gray")
        self.update_idletasks()

    def show_update_prompt(self, latest_version: str) -> None:
        if self._update_prompted:
            return
        self._update_prompted = True
        top = ctk.CTkToplevel(self)
        top.title("Güncelleme mevcut")
        top.geometry("520x240")
        top.resizable(False, False)
        top.grab_set()
        ctk.CTkLabel(top, text="Güncelleme mevcut", font=("Roboto Medium", 18)).pack(pady=(18, 10))
        ctk.CTkLabel(
            top,
            text=f"Mevcut sürüm: {APP_VERSION}\nYeni sürüm: {latest_version}",
            font=("Roboto", 13),
        ).pack(pady=(0, 16))
        row = ctk.CTkFrame(top, fg_color="transparent")
        row.pack(pady=(4, 12))
        ctk.CTkButton(row, text="Launcher aç", width=140, command=lambda: (top.destroy(), self.prog_ver_check())).pack(side="left", padx=8)
        ctk.CTkButton(row, text="Sonra", width=120, command=top.destroy).pack(side="left", padx=8)

    def check_launcher_update_background(self) -> None:
        def worker():
            try:
                payload = _http_get_json(PROGRAMS_URL)
                latest = None
                for item in payload.get("programs", []):
                    if item.get("id") == PROGRAM_ID:
                        latest = item.get("version", "")
                        break
                if latest and _semver_tuple(latest) > _semver_tuple(APP_VERSION):
                    self.after(0, lambda: self.show_update_prompt(latest))
            except Exception:
                return

        threading.Thread(target=worker, daemon=True).start()

    def key_derivation(self, password, salt):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(), iterations=100000,
            salt=salt, length=32, backend=default_backend()
        )
        return kdf.derive(password.encode())

    def encrypt_file(self, file_path, password):
        try:
            salt = os.urandom(16)
            nonce = os.urandom(12)
            key = self.key_derivation(password, salt)
            with open(file_path, 'rb') as f: plaintext = f.read()
            
            cipher = Cipher(algorithms.AES(key), modes.GCM(nonce), backend=default_backend())
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(plaintext) + encryptor.finalize()

            with open(file_path + '.enc', 'wb') as f: f.write(encryptor.tag + nonce + salt + ciphertext)
            os.remove(file_path)
            return True
        except Exception as e:
            print(e)
            return False

    def decrypt_file(self, encrypted_file_path, password):
        try:
            with open(encrypted_file_path, 'rb') as f: data = f.read()
            tag, nonce, salt, ciphertext = data[:16], data[16:28], data[28:44], data[44:]
            
            key = self.key_derivation(password, salt)
            cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag), backend=default_backend())
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

    def set_busy(self, busy: bool):
        self.is_busy = busy
        state = "disabled" if busy else "normal"
        for btn in (
            self.encrypt_file_btn,
            self.decrypt_file_btn,
            self.encrypt_folder_btn,
            self.decrypt_folder_btn,
            self.update_btn,
        ):
            btn.configure(state=state)

    def run_task(self, task, on_done):
        if self.is_busy:
            return
        self.set_busy(True)

        def worker():
            try:
                result = task()
                self.after(0, lambda: self._task_done(on_done, result))
            except Exception as exc:
                self.after(0, lambda: self._task_failed(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _task_done(self, on_done, result):
        self.set_busy(False)
        on_done(result)

    def _task_failed(self, message):
        self.set_busy(False)
        self.log("Hata oluştu!", True)
        messagebox.showerror("Hata", message)

    def encrypt(self):
        pwd = self.get_password()
        if not pwd:
            return

        file_path = filedialog.askopenfilename()
        if file_path:
            self.log("İşlem başlıyor...")

            def task():
                return self.encrypt_file(file_path, pwd)

            def done(success):
                if success:
                    self.log("İşlem başarılı: Dosya şifrelendi.")
                    messagebox.showinfo("Başarılı", "Dosya güvenli bir şekilde şifrelendi.")
                else:
                    self.log("Hata oluştu!", True)
                    messagebox.showerror("Hata", "İşlem başarısız.")

            self.run_task(task, done)

    def decrypt(self):
        pwd = self.get_password()
        if not pwd:
            return

        file_path = filedialog.askopenfilename(filetypes=[("Encrypted Files", "*.enc")])
        if file_path:
            self.log("İşlem başlıyor...")

            def task():
                return self.decrypt_file(file_path, pwd)

            def done(success):
                if success:
                    self.log("İşlem başarılı: Dosya çözüldü.")
                    messagebox.showinfo("Başarılı", "Dosya orijinal haline döndü.")
                else:
                    self.log("Hata: Yanlış parola!", True)
                    messagebox.showerror("Hata", "Şifre çözülmedi. Parolayı kontrol edin.")

            self.run_task(task, done)

    def encrypt_folder(self):
        pwd = self.get_password()
        if not pwd:
            return

        folder = filedialog.askdirectory()
        if folder:
            self.log("İşlem başlıyor...")

            def task():
                count = 0
                for root, _, files in os.walk(folder):
                    for file in files:
                        if not file.endswith(".enc"):
                            if self.encrypt_file(os.path.join(root, file), pwd):
                                count += 1
                return count

            def done(count):
                self.log(f"Tamamlandı: {count} dosya şifrelendi.")
                messagebox.showinfo("Toplu İşlem", f"{count} dosya şifrelendi.")

            self.run_task(task, done)

    def decrypt_folder(self):
        pwd = self.get_password()
        if not pwd:
            return

        folder = filedialog.askdirectory()
        if folder:
            self.log("İşlem başlıyor...")

            def task():
                count = 0
                fail = 0
                for root, _, files in os.walk(folder):
                    for file in files:
                        if file.endswith(".enc"):
                            if self.decrypt_file(os.path.join(root, file), pwd):
                                count += 1
                            else:
                                fail += 1
                return count, fail

            def done(result):
                count, fail = result
                self.log(f"Bitti: {count} çözüldü, {fail} hata.")
                messagebox.showinfo("Rapor", f"{count} dosya başarıyla çözüldü.\n{fail} dosya çözülemedi.")

            self.run_task(task, done)

    def prog_ver_check(self):
        launcher_hint_path = r"C:\Saydut\launcher_path.txt"
        launcher_candidates = [
            r"C:\Saydut\SaydutLauncher\SaydutLauncher.exe",
            r"C:\Saydut\Saydut Launcher\SaydutLauncher.exe",
            r"C:\Saydut\SaydutLauncher\Saydut Launcher.exe",
        ]

        launcher_path = None
        if os.path.exists(launcher_hint_path):
            try:
                with open(launcher_hint_path, "r", encoding="utf-8") as handle:
                    candidate = handle.read().strip()
                if candidate and os.path.exists(candidate):
                    launcher_path = candidate
            except OSError:
                launcher_path = None

        if not launcher_path:
            launcher_path = next((p for p in launcher_candidates if os.path.exists(p)), None)

        if launcher_path:
            self.log("Güncelleme için Saydut Launcher açılıyor...")
            try:
                if launcher_path.lower().endswith(".py"):
                    subprocess.Popen([sys.executable, launcher_path])
                else:
                    subprocess.Popen([launcher_path])
            except Exception as exc:
                self.log("Launcher açılamadı.", True)
                messagebox.showerror("Hata", f"Launcher açılamadı:\n{exc}")
            return

        self.log("Launcher bulunamadı.", True)
        messagebox.showinfo(
            "Launcher Gerekli",
            "Güncelleme için Saydut Launcher gerekli.\nİndirip kurduktan sonra tekrar deneyin.",
        )
        webbrowser.open("https://www.saydut.com")

if __name__ == "__main__":
    app = ModernApp()
    app.mainloop()



