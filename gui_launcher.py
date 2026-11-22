"""Otomatik Sınav Asistanı - Masaüstü Başlatıcı (GUI Launcher)
Sıfır konsol penceresiyle Flask sunucusunu arka planda ayağa kaldırır ve tarayıcıyı açar.
60-30-10 Zıt Renk Standardı:
- %60 Açık Zemin: #f8fafc
- %30 Yapısal Renk: #0f172a
- %10 Vurgu/Aksan: #ea580c (Canlı Kehribar/Turuncu)
"""

import os
import sys
import time
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox
from werkzeug.serving import make_server

# Dizin ayarı
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

from server import app
from hermes_sentinel import Sentinel

PORT = 5000
HOST = "127.0.0.1"


class AppLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Otomatik Sınav Asistanı v2.0")
        self.root.geometry("460x320")
        self.root.resizable(False, False)
        self.root.configure(bg="#f8fafc")

        self.server = None
        self.server_thread = None
        self.is_running = False

        self._build_ui()
        self.start_server()

    def _build_ui(self):
        # Üst Başlık Kartı (%30 Yapısal Lacivert)
        header_frame = tk.Frame(self.root, bg="#0f172a", height=80)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)

        title_lbl = tk.Label(
            header_frame,
            text="🎓 Otomatik Sınav Asistanı",
            font=("Segoe UI", 16, "bold"),
            fg="#ffffff",
            bg="#0f172a"
        )
        title_lbl.pack(pady=(16, 2))

        sub_lbl = tk.Label(
            header_frame,
            text="MEB Müfredatı Destekli Yapay Zeka Soru Üretim Portalı",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0f172a"
        )
        sub_lbl.pack()

        # Gövde Kartı (%60 Açık Zemin)
        body = tk.Frame(self.root, bg="#f8fafc", padx=25, pady=20)
        body.pack(fill="both", expand=True)

        self.status_lbl = tk.Label(
            body,
            text="⏳ Sunucu başlatılıyor...",
            font=("Segoe UI", 11, "bold"),
            fg="#ea580c",
            bg="#f8fafc"
        )
        self.status_lbl.pack(pady=(5, 12))

        info_lbl = tk.Label(
            body,
            text=f"Yerel Web Arayüzü: http://{HOST}:{PORT}\nMEB 5. Sınıf Sosyal Bilgiler Üniteleri Aktif",
            font=("Segoe UI", 9),
            fg="#64748b",
            bg="#f8fafc",
            justify="center"
        )
        info_lbl.pack(pady=(0, 20))

        # Eylem Butonları Barı (%10 Vurgu Kehribar/Turuncu)
        btn_bar = tk.Frame(body, bg="#f8fafc")
        btn_bar.pack(fill="x")

        self.browser_btn = tk.Button(
            btn_bar,
            text="🌐 Tarayıcıda Aç",
            font=("Segoe UI", 10, "bold"),
            bg="#ea580c",
            fg="#ffffff",
            activebackground="#c2410c",
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
            command=self.open_browser
        )
        self.browser_btn.pack(side="left", expand=True, padx=4)

        self.stop_btn = tk.Button(
            btn_bar,
            text="⏹️ Durdur",
            font=("Segoe UI", 10),
            bg="#e2e8f0",
            fg="#0f172a",
            activebackground="#cbd5e1",
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
            command=self.stop_server
        )
        self.stop_btn.pack(side="left", expand=True, padx=4)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def start_server(self):
        if self.is_running:
            return

        def _run():
            try:
                self.server = make_server(HOST, PORT, app, threaded=True)
                self.is_running = True
                self.root.after(0, self._on_server_started)
                self.server.serve_forever()
            except Exception as e:
                self.root.after(0, lambda: self._on_server_error(str(e)))

        self.server_thread = threading.Thread(target=_run, daemon=True)
        self.server_thread.start()

    def _on_server_started(self):
        self.status_lbl.configure(text="✓ Sistem Hazır ve Çalışıyor!", fg="#16a34a")
        self.open_browser()

    def _on_server_error(self, err):
        self.status_lbl.configure(text=f"Hata: {err}", fg="#dc2626")
        messagebox.showerror("Sunucu Hatası", f"Sunucu başlatılamadı:\n{err}")

    def open_browser(self):
        webbrowser.open(f"http://{HOST}:{PORT}")

    def stop_server(self):
        if self.server and self.is_running:
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            self.is_running = False
            self.status_lbl.configure(text="Sunucu Durduruldu.", fg="#64748b")
            self.browser_btn.configure(state="disabled")
            self.stop_btn.configure(text="▶️ Yeniden Başlat", command=self.restart_server)

    def restart_server(self):
        self.status_lbl.configure(text="⏳ Yeniden başlatılıyor...", fg="#ea580c")
        self.stop_btn.configure(text="⏹️ Durdur", command=self.stop_server)
        self.browser_btn.configure(state="normal")
        self.start_server()

    def on_close(self):
        try:
            if self.server and self.is_running:
                threading.Thread(target=self.server.shutdown, daemon=True).start()
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app_launcher = AppLauncher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
