#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TCDD e-Bilet Bot (Selenium tabanlı)
Belirtilen güzergah ve tarih için periyodik bilet kontrolü yapar.
Boş bilet bulunduğunda Telegram, e-posta veya WhatsApp ile bildirim gönderir.
"""

import time
import signal
import sys
import io
from datetime import datetime

# Windows konsolunda UTF-8 (₺ gibi karakterler için)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import schedule
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from config import load_config
from tcdd_api import check_availability
from notifier import notify_all

console = Console()
_running = True


def signal_handler(sig, frame):
    global _running
    console.print("\n[yellow]Durduruluyor...[/yellow]")
    _running = False
    sys.exit(0)


def build_notification_message(
    departure: str,
    arrival: str,
    date: str,
    trains: list[dict],
) -> str:
    lines = [
        "🚂 TCDD BİLET BULUNDU!",
        f"📍 Güzergah: {departure} → {arrival}",
        f"📅 Tarih: {date}",
        f"🎟 Müsait {len(trains)} sefer:",
        "",
    ]
    for t in trains:
        lines.append(f"• Sefer {t['train_no']} | {t['train_name']}")
        lines.append(f"  ⏰ {t['departure_time']} → {t['arrival_time']}")
        seats = t['available_seats']
        price = t['price']
        line = f"  💺 {seats} boş koltuk"
        if price and price != "?":
            line += f"  |  💰 {price} TL"
        lines.append(line)
        lines.append("")
    lines.append("🔗 https://ebilet.tcddtasimacilik.gov.tr/")
    return "\n".join(lines)


def print_status_table(trains: list[dict], departure: str, arrival: str, date: str):
    table = Table(
        title=f"{departure} → {arrival}  |  {date}",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("Sefer No", style="cyan", justify="center")
    table.add_column("Tren Adı", style="white")
    table.add_column("Kalkış", style="green", justify="center")
    table.add_column("Varış", style="green", justify="center")
    table.add_column("Boş Koltuk", style="bold yellow", justify="center")
    table.add_column("Fiyat", style="magenta", justify="center")

    for t in trains:
        table.add_row(
            str(t["train_no"]),
            str(t["train_name"]),
            str(t["departure_time"]),
            str(t["arrival_time"]),
            str(t["available_seats"]),
            str(t["price"]),
        )
    console.print(table)


def run_check(cfg: dict, notified_set: set):
    """Tek bir kontrol döngüsü: tarayıcıyı açar, sonuçları alır, kapatır."""
    now = datetime.now().strftime("%H:%M:%S")
    console.rule(f"[dim]Kontrol – {now}[/dim]")

    trains = check_availability(
        departure=cfg["departure"],
        arrival=cfg["arrival"],
        date=cfg["travel_date"],
        hour_start=cfg["hour_start"],
        hour_end=cfg["hour_end"],
        headless=cfg.get("headless", True),
    )

    if not trains:
        console.print("[red]Müsait bilet bulunamadı.[/red]")
        return

    console.print(f"[bold green]{len(trains)} müsait sefer bulundu![/bold green]")
    print_status_table(trains, cfg["departure"], cfg["arrival"], cfg["travel_date"])

    # Yeni bulunan seferleri filtrele (spam önleme)
    new_trains = [t for t in trains if t["train_no"] not in notified_set]

    if new_trains:
        msg = build_notification_message(
            cfg["departure"],
            cfg["arrival"],
            cfg["travel_date"],
            new_trains,
        )
        notify_all(msg, cfg["notify"])
        for t in new_trains:
            notified_set.add(t["train_no"])
    else:
        console.print("[dim]Bu seferler için daha önce bildirim gönderilmişti.[/dim]")


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    console.print(
        Panel.fit(
            "[bold cyan]TCDD e-Bilet Bot[/bold cyan]  [dim](Selenium)[/dim]\n"
            "[dim]Ctrl+C ile durdurabilirsiniz[/dim]",
            border_style="cyan",
        )
    )

    try:
        cfg = load_config()
    except ValueError as e:
        console.print(f"[bold red]Konfigürasyon hatası:[/bold red] {e}")
        console.print("[yellow]Lütfen .env dosyasını .env.example'dan oluşturun ve doldurun.[/yellow]")
        sys.exit(1)

    # Özet paneli
    hour_range = ""
    if cfg["hour_start"] is not None or cfg["hour_end"] is not None:
        s = f"{cfg['hour_start']:02d}:00" if cfg["hour_start"] is not None else "00:00"
        e = f"{cfg['hour_end']:02d}:59" if cfg["hour_end"] is not None else "23:59"
        hour_range = f" ({s}–{e})"

    active_channels = [k for k, v in cfg["notify"].items() if v]

    console.print(
        Panel(
            f"[bold]Güzergah:[/bold] {cfg['departure']} → {cfg['arrival']}\n"
            f"[bold]Tarih:[/bold]    {cfg['travel_date']}{hour_range}\n"
            f"[bold]Kontrol:[/bold]  Her {cfg['interval_minutes']} dakikada bir\n"
            f"[bold]Mod:[/bold]      {'Headless (arka plan)' if cfg.get('headless', True) else 'Görünür tarayıcı'}\n"
            f"[bold]Bildirim:[/bold] {', '.join(active_channels) if active_channels else '[red]YOK – .env dosyasını kontrol edin![/red]'}",
            title="Ayarlar",
            border_style="blue",
        )
    )

    if not active_channels:
        console.print(
            "[bold yellow]Uyarı: Hiçbir bildirim kanalı yapılandırılmamış![/bold yellow]"
        )

    notified_set: set = set()

    # İlk kontrol hemen başlasın
    run_check(cfg, notified_set)

    # Sonraki kontroller periyodik
    schedule.every(cfg["interval_minutes"]).minutes.do(
        run_check, cfg=cfg, notified_set=notified_set
    )

    while _running:
        schedule.run_pending()
        time.sleep(10)


if __name__ == "__main__":
    main()
