# TokenHarbor Suite

Automated TokenHarbor account factory, free models activator, and 9router synchronization suite.

## Features
- **Pendaftaran Otomatis:** Membuka akun TokenHarbor baru dengan alur stealth patchright.
- **Integrasi Temp-Mail:** Menggunakan client temp-mail berbasis [Tempik](https://github.com/hirotomasato/tempik).
- **Aktivasi Model Gratis:** Mengaktifkan consent free tier untuk model:
  - `mimo-v2.6-flash:free`
  - `mimo-v2.5:free`
  - `deepseek-v4-flash:free`
  - `deepseek-v4.1-flash:free`
  - `claude-haiku-5.5:free`
- **Pemanenan API Key:** Membuat personal access token (`thk_live_...`).
- **Injeksi 9router:** Sinkronisasi langsung ke node bawaan `tokenharbor` pada 9router.

## Keamanan dan batasan
- Konfigurasikan deployment Tempik milik Anda lewat `TEMPIK_BASE`; endpoint internal tidak disertakan.
- Gunakan `NINEROUTER_URL` dan `NINEROUTER_PASS` untuk konfigurasi gateway tanpa commit kredensial.
- `accounts.txt` menyimpan kredensial plaintext: batasi izin ke `600`, jangan commit atau bagikan.
- Daftar model dan keberhasilan signup bergantung pada layanan; CAPTCHA dan rate limit dapat memblokir pendaftaran. Hormati ketentuan layanan dan batas kuota.
- Engine saat ini membuka browser headed; perlu desktop atau Xvfb. Opsi headless di config belum digunakan oleh engine.
- Modul `mailtm` tersedia sebagai client terpisah, belum menjadi provider email engine.

## Atribusi
Modul disposable email menggunakan client yang diadopsi dari repositori open-source:
**https://github.com/hirotomasato/tempik**

## Persyaratan
- Python 3.10+
- Linux x86_64

## Instalasi
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
patchright install chromium
cp config.example.toml config.toml
```

## Penggunaan
```bash
./run.sh harvest 1    # Buat 1 akun & panen API key
./run.sh harvest 5    # Buat 5 akun
./run.sh test         # Uji semua API key
./run.sh sync         # Sinkronkan ke 9router
./run.sh report       # Tampilkan statistik akun
./run.sh probe        # Cek status endpoint TokenHarbor
```
