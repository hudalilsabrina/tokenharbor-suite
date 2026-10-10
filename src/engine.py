"""TokenHarbor Engine - Otomasi akun + panen API key + aktivasi free models.

Alur:
  1. Buat inbox tempik (session lock)
  2. Buka https://tokenharbor.ai/login?mode=signup via patchright
  3. Loloskan Turnstile jika ada
  4. Input email + password -> Submit
  5. Tunggu dashboard -> Aktifkan free models consent
  6. Klik tombol verify email
  7. Polling link verifikasi dari inbox tempik
  8. Buka link verifikasi
  9. Panggil POST /api/keys -> dapatkan API key plaintext (thk_live_...)
 10. Uji key via chat completions (mimo-v2.6-flash:free)
 11. Simpan ke accounts.txt
"""

import asyncio
import json
import random
import re
import string
import time
from typing import Dict, Any, Optional, Tuple

import requests
from patchright.async_api import async_playwright

from .config import TIMEOUT
from .tempmail import TempikClient

FREE_MODELS = [
    "mimo-v2.6-flash:free",
    "mimo-v2.5:free",
    "deepseek-v4-flash:free",
    "deepseek-v4.1-flash:free",
    "claude-haiku-5.5:free"
]


def generate_password() -> str:
    core = "".join(random.choices(string.ascii_letters + string.digits, k=11))
    return f"Th!{core}9#"


async def create_account(log_fn=print) -> Optional[Dict[str, Any]]:
    """Daftarkan 1 akun baru TokenHarbor dan panen API key-nya."""
    client = TempikClient()
    email = client.create_inbox()
    password = generate_password()
    log_fn(f"[1/7] Inbox Tempik dibuat: [bold cyan]{email}[/]")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        ctx = await browser.new_context()
        page = await ctx.new_page()

        try:
            log_fn("[2/7] Membuka formulir pendaftaran TokenHarbor...")
            await page.goto("https://tokenharbor.ai/login?mode=signup", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2500)

            # Cek dan tangani Turnstile jika muncul
            is_email_vis = await page.is_visible('input[name="email"]')
            if not is_email_vis:
                log_fn("[*] Menyelesaikan Cloudflare Turnstile...")
                for attempt in range(5):
                    for f in page.frames:
                        if "challenges.cloudflare.com" in f.url:
                            cb = await f.query_selector('input[type="checkbox"], #challenge-stage, .ctp-checkbox-label')
                            if cb:
                                await cb.click()
                                break
                    await page.wait_for_timeout(2000)
                    if await page.is_visible('input[name="email"]'):
                        break

            # Tunggu input email siap
            await page.wait_for_selector('input[name="email"]', state="visible", timeout=15000)

            log_fn("[3/7] Mengisi kredensial & submit...")
            await page.fill('input[name="email"]', email)
            await page.fill('input[name="password"]', password)
            await page.click('button[type="submit"]')

            # Cek respons cepat (rate limit / sukses)
            await page.wait_for_timeout(3000)
            body_text = await page.inner_text('body')
            if "Too many sign-ups from this network" in body_text:
                log_fn("[red]✗ IP Rate Limit: 'Too many sign-ups from this network. Please try again in an hour.'[/]")
                await browser.close()
                return None

            # Tunggu navigasi ke dashboard (client-side router)
            await page.wait_for_function("() => window.location.href.includes('/dashboard')", timeout=20000)
            log_fn("[4/7] Dashboard tercapai! Mengaktifkan consent model gratis...")

            # Enable free models consent
            try:
                btn_free = page.locator('button:has-text("Enable free models")')
                if await btn_free.is_visible(timeout=5000):
                    await btn_free.click()
            except Exception:
                pass

            # Klik tombol verify email
            try:
                btn_verify = page.locator('button:has-text("Verify email")')
                if await btn_verify.is_visible(timeout=5000):
                    await btn_verify.click()
            except Exception:
                pass

            log_fn("[5/7] Menunggu link verifikasi dari inbox Tempik...")
            verify_url = client.wait_for_verification_link(email, timeout=60, interval=4)

            if not verify_url:
                log_fn("[!] Timeout menunggu link verifikasi email.")
                await browser.close()
                return None

            log_fn(f"[6/7] Memverifikasi akun: {verify_url[:45]}...")
            await page.goto(verify_url, wait_until="networkidle", timeout=25000)

            log_fn("[7/7] Memanen API key TokenHarbor...")
            res = await page.evaluate('''async () => {
                const r = await fetch('/api/keys', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                    body: JSON.stringify({ label: 'router-prod' })
                });
                return await r.json();
            }''')

            key = res.get("plaintext")
            if not key:
                log_fn(f"[!] Gagal memanen API key: {res}")
                await browser.close()
                return None

            await browser.close()
            return {
                "email": email,
                "password": password,
                "apikey": key,
                "created_at": time.time()
            }

        except Exception as e:
            log_fn(f"[!] Error saat pendaftaran: {e}")
            await browser.close()
            return None


def test_api_key(api_key: str, model: str = "mimo-v2.6-flash:free") -> Tuple[bool, str]:
    """Uji API key langsung ke TokenHarbor chat completions."""
    url = "https://tokenharbor.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "What is 2+2? Answer only the number."}],
        "max_tokens": 10
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        if r.status_code == 200:
            data = r.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            return True, content
        return False, f"HTTP {r.status_code}: {r.text[:100]}"
    except Exception as e:
        return False, str(e)
