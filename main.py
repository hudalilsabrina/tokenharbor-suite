#!/usr/bin/env python3
"""TokenHarbor Suite - CLI: factory akun + panen API key + 9router sync.

Command:
  harvest [n]   Buat n akun (default 1) + panen API key
  test          Uji semua API key ke model free
  sync          Sinkronkan semua API key ke 9router
  report        Ringkasan jumlah dan status akun
  probe         Cek apakah endpoint TokenHarbor aktif
"""
import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rich.console import Console
from rich.table import Table
from rich import box

from src import engine, router9

C = Console()
ROOT = Path(__file__).resolve().parent
ACCOUNTS_FILE = ROOT / "accounts.txt"


def _load_accounts():
    if not ACCOUNTS_FILE.exists():
        return []
    out = []
    for line in ACCOUNTS_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(":")
        if len(parts) >= 3:
            out.append({
                "email": parts[0],
                "password": parts[1],
                "apikey": parts[2]
            })
    return out


def _append_account(email, pwd, apikey):
    with open(ACCOUNTS_FILE, "a") as f:
        f.write(f"{email}:{pwd}:{apikey}\n")


def cmd_harvest(n: int = 1):
    C.print(f"[bold cyan]=== Memulai Harvesting {n} Akun TokenHarbor ===[/]\n")
    success = 0
    for i in range(1, n + 1):
        C.print(f"[yellow]── Akun {i}/{n} ──[/]")
        try:
            acc = asyncio.run(engine.create_account(log_fn=C.print))
            if acc:
                _append_account(acc["email"], acc["password"], acc["apikey"])
                C.print(f"[green]✓ Akun berhasil dibuat:[/] {acc['email']}")
                C.print(f"[green]✓ API Key:[/] {acc['apikey'][:25]}... (panjang {len(acc['apikey'])})")

                # Uji key
                ok, msg = engine.test_api_key(acc["apikey"])
                if ok:
                    C.print(f"[green]✓ Uji Inferensi (mimo-v2.6-flash:free): Berhasil! Jawaban:[/] {msg}")
                else:
                    C.print(f"[yellow]! Uji Inferensi:[/] {msg}")

                # Auto sync ke 9router
                synced = router9.sync_connection(acc["apikey"], acc["email"])
                if synced:
                    C.print("[green]✓ Tersinkronisasi ke 9router (node: tokenharbor)[/]\n")
                else:
                    C.print("[yellow]! Gagal sinkron ke 9router[/]\n")

                success += 1
            else:
                C.print("[red]✗ Gagal membuat akun ini.[/]\n")
        except Exception as e:
            C.print(f"[red]✗ Error:[/] {e}\n")

    C.print(f"[bold green]Harvest selesai:[/] {success}/{n} berhasil.")


def cmd_test():
    accs = _load_accounts()
    if not accs:
        C.print("[yellow]Belum ada akun di accounts.txt.[/]")
        return

    C.print(f"[bold cyan]Menguji {len(accs)} API Key ke TokenHarbor...[/]\n")
    table = Table(box=box.ROUNDED)
    table.add_column("No", style="dim")
    table.add_column("Email", style="cyan")
    table.add_column("API Key Masked", style="dim")
    table.add_column("Model Free", style="blue")
    table.add_column("Status", style="bold")

    for i, a in enumerate(accs, 1):
        key = a["apikey"]
        ok, res = engine.test_api_key(key, "mimo-v2.6-flash:free")
        status_str = f"[green]VALID ({res})[/]" if ok else f"[red]FAIL ({res[:20]})[/]"
        masked = f"{key[:12]}...{key[-6:]}"
        table.add_row(str(i), a["email"], masked, "mimo-v2.6-flash", status_str)

    C.print(table)


def cmd_sync():
    accs = _load_accounts()
    if not accs:
        C.print("[yellow]Belum ada akun di accounts.txt.[/]")
        return

    C.print(f"[bold cyan]Menyinkronkan {len(accs)} Akun ke 9router...[/]")
    success = 0
    for a in accs:
        if router9.sync_connection(a["apikey"], a["email"]):
            success += 1
    C.print(f"[green]Selesai! {success}/{len(accs)} akun aktif di 9router (provider: tokenharbor).[/]")


def cmd_report():
    accs = _load_accounts()
    C.print("\n[bold cyan]=== Laporan TokenHarbor Suite ===[/]")
    C.print(f"Total akun tersimpan : [bold green]{len(accs)}[/]")
    C.print(f"Model gratis bawaan  : [cyan]{', '.join(engine.FREE_MODELS)}[/]")
    C.print(f"File penyimpanan     : [dim]{ACCOUNTS_FILE}[/]\n")


def cmd_probe():
    import requests
    C.print("[bold cyan]Memeriksa status endpoint TokenHarbor...[/]")
    try:
        r = requests.get("https://tokenharbor.ai/v1/models", timeout=10)
        C.print(f"GET /v1/models: [green]{r.status_code}[/] (Server Online)")
    except Exception as e:
        C.print(f"[red]Error:[/] {e}")


def main():
    p = argparse.ArgumentParser(description="TokenHarbor Suite CLI")
    sub = p.add_subparsers(dest="cmd")

    h = sub.add_parser("harvest", help="Buat akun baru & panen API key")
    h.add_argument("count", type=int, nargs="?", default=1, help="Jumlah akun")

    sub.add_parser("test", help="Uji semua API key")
    sub.add_parser("sync", help="Sinkronkan akun ke 9router")
    sub.add_parser("report", help="Ringkasan akun")
    sub.add_parser("probe", help="Cek status endpoint")

    args = p.parse_args()

    if args.cmd == "harvest":
        cmd_harvest(args.count)
    elif args.cmd == "test":
        cmd_test()
    elif args.cmd == "sync":
        cmd_sync()
    elif args.cmd == "report":
        cmd_report()
    elif args.cmd == "probe":
        cmd_probe()
    else:
        p.print_help()


if __name__ == "__main__":
    main()
