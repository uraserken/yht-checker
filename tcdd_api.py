"""
TCDD e-Bilet Selenium scraper.
HTML analizine dayalı, doğrulanmış seçiciler kullanır.
"""

import time
from typing import Optional
from rich.console import Console

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementNotInteractableException,
)
from webdriver_manager.chrome import ChromeDriverManager

console = Console()

SITE_URL = "https://ebilet.tcddtasimacilik.gov.tr/"


def build_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def _close_modal(driver: webdriver.Chrome):
    """Sayfa açılışında çıkan araç kiralama popup'ını kapatır."""
    try:
        # Modal görünür mü?
        modal = driver.find_element(By.ID, "rentalCarInformation")
        if "show" in modal.get_attribute("class"):
            close_btn = modal.find_element(By.CSS_SELECTOR, "button.close")
            close_btn.click()
            time.sleep(0.8)
            console.print("[dim]  Popup kapatıldı.[/dim]")
    except NoSuchElementException:
        pass
    except Exception as e:
        console.print(f"[dim]  Popup kapatma: {e}[/dim]")


def _fill_station(
    driver: webdriver.Chrome,
    wait: WebDriverWait,
    trigger_id: str,       # fromTrainInput / toTrainInput
    search_aria: str,      # departureInput / arrivalInput
    station_name: str,
) -> bool:
    """
    İstasyon alanını doldurur.

    Akış:
    1. Ana görünen inputa JS click → Bootstrap dropdown açılır
    2. Dropdown içindeki arama kutusuna JS focus + JS value set + input event
    3. .allStations içindeki ilk eşleşen öğeye JS click
    """
    # 1. Dropdown'ı aç
    trigger = wait.until(EC.presence_of_element_located((By.ID, trigger_id)))
    driver.execute_script("arguments[0].click();", trigger)
    time.sleep(1.2)

    # 2. Arama kutusunu JS ile bul ve değer ata (Vue reaktivitesini tetikler)
    search_input = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, f'input[aria-label="{search_aria}"]')
        )
    )
    # Kutuya JS ile focus + value yaz + 'input' event'i tetikle
    driver.execute_script(
        """
        var el = arguments[0];
        var val = arguments[1];
        el.focus();
        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(el, val);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        search_input,
        station_name,
    )
    time.sleep(1.8)  # Vue filtrelesin

    # 3. .allStations içindeki ilk görünür öğeye tıkla
    # Öğeler div, button, span, li olabilir — hepsini dene
    for xpath in [
        f".//div[contains(@class,'allStations')]//button[not(contains(@class,'btnClose'))]",
        f".//div[contains(@class,'allStations')]//*[self::div or self::li or self::span][normalize-space(text())]",
        f".//div[contains(@class,'searchArea')]//*[contains(text(),'{station_name[:4]}')]",
        f".//div[contains(@class,'allStations')]//*",
    ]:
        try:
            items = driver.find_elements(By.XPATH, xpath)
            visible = [i for i in items if i.is_displayed() and i.text.strip()]
            if visible:
                chosen = visible[0]
                console.print(f"[dim]  Seçilen: {chosen.text.strip()[:60]}[/dim]")
                driver.execute_script("arguments[0].click();", chosen)
                time.sleep(0.7)
                return True
        except Exception:
            pass

    # Fallback: liste açıksa ilk eleman ne olursa olsun seç
    try:
        first = driver.find_element(
            By.XPATH,
            ".//div[contains(@class,'allStations')]//*[normalize-space(text())]"
        )
        console.print(f"[dim]  Fallback seçimi: {first.text.strip()[:60]}[/dim]")
        driver.execute_script("arguments[0].click();", first)
        time.sleep(0.7)
        return True
    except NoSuchElementException:
        pass

    console.print(f"[yellow]  Öneri listesi boş kaldı, Enter deneniyor.[/yellow]")
    search_input.send_keys(Keys.RETURN)
    time.sleep(0.5)
    return False


def _set_date(driver: webdriver.Chrome, wait: WebDriverWait, date_str: str):
    """
    Tarih seçer. date_str: 'DD/MM/YYYY'
    Takvim widget'ı kullanır — readonly input'a tıkla, takvimden günü seç.
    """
    # Tarih inputuna tıkla → takvim açılır
    date_input = wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "input.calenderPurpleImg, .departureDate input[readonly]")
        )
    )
    driver.execute_script("arguments[0].click();", date_input)
    time.sleep(1.0)

    # data-date="YYYY-MM-DD" formatına çevir
    parts = date_str.split("/")  # DD/MM/YYYY
    data_date = f"{parts[2]}-{parts[1]}-{parts[0]}"  # YYYY-MM-DD

    # Takvimde bu tarihe ait td'yi bul
    try:
        day_cell = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, f'td[data-date="{data_date}"]')
            )
        )
        driver.execute_script("arguments[0].click();", day_cell)
        console.print(f"[dim]  Tarih seçildi: {date_str}[/dim]")
        time.sleep(0.5)
        return
    except TimeoutException:
        console.print(f"[yellow]  Takvimde {date_str} bulunamadı, ileri/geri geziniliyor...[/yellow]")

    # Takvimde gün görünmüyorsa "sonraki ay" okuna bas ve tekrar dene
    for _ in range(6):  # En fazla 6 ay ileri git
        try:
            next_btn = driver.find_element(
                By.CSS_SELECTOR, ".daterangepicker .next.available"
            )
            next_btn.click()
            time.sleep(0.5)
            day_cell = driver.find_element(
                By.CSS_SELECTOR, f'td[data-date="{data_date}"]'
            )
            if day_cell:
                driver.execute_script("arguments[0].click();", day_cell)
                console.print(f"[dim]  Tarih seçildi: {date_str}[/dim]")
                time.sleep(0.5)
                return
        except NoSuchElementException:
            continue

    console.print(f"[red]  Tarih seçilemedi: {date_str}[/red]")


def _click_search(driver: webdriver.Chrome, wait: WebDriverWait):
    """'Sefer Ara' butonuna basar."""
    btn = wait.until(EC.element_to_be_clickable((By.ID, "searchSeferButton")))
    driver.execute_script("arguments[0].click();", btn)
    console.print("[dim]  Arama başlatıldı.[/dim]")


def _tc(el) -> str:
    """Element'in textContent'ini döndürür — gizli elementlerde .text boş döner, bu çalışır."""
    return (el.get_attribute("textContent") or "").strip()


def _parse_results(
    driver: webdriver.Chrome,
    wait: WebDriverWait,
    hour_start: Optional[int],
    hour_end: Optional[int],
) -> list[dict]:
    """Sonuç sayfasındaki seferleri parse eder, müsait olanları döndürür."""
    available = []
    time.sleep(5)

    try:
        driver.save_screenshot("debug_results.png")
    except Exception:
        pass

    cards = driver.find_elements(By.CSS_SELECTOR, "div.card[id^='gidis']")

    if not cards:
        console.print("[dim]  Sefer kartı bulunamadı.[/dim]")
        try:
            body_text = driver.find_element(By.TAG_NAME, "main").text[:500]
            console.print(f"[dim]  Sayfa içeriği: {body_text}[/dim]")
        except Exception:
            pass
        return available

    console.print(f"[dim]  {len(cards)} sefer kartı bulundu, tek tek açılıyor...[/dim]")

    for card in cards:
        card_id = ""
        try:
            card_id = card.get_attribute("id") or ""

            # ── 1. Kalkış saati (card-header'da, her zaman erişilebilir) ─────────
            dep_time = ""
            try:
                dep_el = card.find_element(By.CSS_SELECTOR, "span.textDepartureArea time")
                dep_time = (dep_el.get_attribute("datetime") or _tc(dep_el))
            except NoSuchElementException:
                pass

            # ── 2. Saat filtresi ─────────────────────────────────────────────────
            if dep_time and (hour_start is not None or hour_end is not None):
                try:
                    h = int(dep_time.split(":")[0])
                    if hour_start is not None and h < hour_start:
                        continue
                    if hour_end is not None and h > hour_end:
                        continue
                except (ValueError, IndexError):
                    pass

            # ── 3. Kart başlığında "Dolu" var mı? (hızlı eleme) ─────────────────
            try:
                header_price_text = _tc(card.find_element(
                    By.CSS_SELECTOR, ".card-header .priceArea .price"
                )).lower()
                if header_price_text == "dolu":
                    console.print(f"[dim]  {card_id}: DOLU (başlık), atlanıyor.[/dim]")
                    continue
            except NoSuchElementException:
                pass

            # ── 4. Kartı aç: card-header içindeki [data-toggle='collapse'] div'e tıkla
            #       (Outer button'a tıklamak Bootstrap'i tetiklemiyor; data-toggle div'i lazım)
            opened = False
            try:
                # Collapse div'in "show" class'ı var mı kontrol et
                toggle_div = card.find_element(
                    By.CSS_SELECTOR, ".card-header [data-toggle='collapse']"
                )
                collapse_target = toggle_div.get_attribute("data-target") or ""
                if collapse_target:
                    collapse_div = driver.find_element(
                        By.CSS_SELECTOR, collapse_target
                    )
                    already_open = "show" in (collapse_div.get_attribute("class") or "")
                else:
                    already_open = False

                if not already_open:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", toggle_div
                    )
                    time.sleep(0.3)
                    toggle_div.click()
                    # Collapse animasyonunun bitmesini bekle
                    try:
                        WebDriverWait(driver, 5).until(
                            lambda d: "show" in (
                                d.find_element(By.CSS_SELECTOR, collapse_target)
                                 .get_attribute("class") or ""
                            )
                        )
                    except Exception:
                        time.sleep(1.2)
                opened = True
            except Exception as e:
                console.print(f"[dim]  {card_id}: Kart açılamadı ({e}), textContent ile okunuyor.[/dim]")

            # ── 5. Vagon tipi butonları — textContent ile oku (açık veya gizli çalışır) ──
            wagon_btns = card.find_elements(
                By.XPATH, ".//button[contains(@id, '-vagonType-')]"
            )

            if not wagon_btns:
                console.print(f"[dim]  {card_id}: Vagon butonu yok, atlanıyor.[/dim]")
                continue

            # Disabled olmayan vagon butonları
            avail_wagons = [
                b for b in wagon_btns
                if "disabled" not in (b.get_attribute("class") or "")
            ]

            if not avail_wagons:
                console.print(f"[dim]  {card_id}: Tüm vagonlar dolu.[/dim]")
                continue

            # ── 6. Tekerlekli sandalye filtresi (textContent ile — gizliyken de çalışır) ──
            real_avail = [
                b for b in avail_wagons
                if "tekerlekli" not in _tc(b).lower()
            ]

            if not real_avail:
                console.print(f"[dim]  {card_id}: Sadece tekerlekli sandalye var.[/dim]")
                continue

            # ── 7. Müsait vagonlardan fiyat, koltuk, tip oku ────────────────────
            price = ""
            seats_display = "?"
            wagon_types = []

            for wagon_btn in real_avail:
                # Vagon tipi adı (span.mb-0 içindeki metin)
                try:
                    wtype = _tc(wagon_btn.find_element(By.CSS_SELECTOR, "span.mb-0"))
                    if wtype:
                        wagon_types.append(wtype)
                except NoSuchElementException:
                    pass

                # Fiyat (ilk müsait vagondan al)
                if not price:
                    try:
                        p = _tc(wagon_btn.find_element(By.CSS_SELECTOR, ".priceArea .price"))
                        if p and p.upper() != "DOLU":
                            price = p
                    except NoSuchElementException:
                        pass

                # Boş koltuk sayısı (varsa)
                if seats_display == "?":
                    try:
                        s = _tc(wagon_btn.find_element(
                            By.CSS_SELECTOR, ".priceArea .emptySeat"
                        )).strip("()")
                        if s:
                            seats_display = s
                    except NoSuchElementException:
                        pass

            wagon_label = ", ".join(wagon_types) if wagon_types else "?"

            # ── 8. Varış saati ───────────────────────────────────────────────────
            arr_time = ""
            try:
                arr_el = card.find_element(By.CSS_SELECTOR, "span.textArrivalArea time")
                arr_time = arr_el.get_attribute("datetime") or _tc(arr_el)
            except NoSuchElementException:
                pass

            # ── 9. Tren adı ve numarası ──────────────────────────────────────────
            train_name = ""
            try:
                train_name = _tc(card.find_element(
                    By.CSS_SELECTOR, ".seferDepartureArea .textDepartureArrival p.col"
                ))
            except NoSuchElementException:
                pass

            train_no = ""
            try:
                hid = card.find_element(
                    By.CSS_SELECTOR, ".card-header"
                ).get_attribute("id") or ""
                train_no = hid.replace("sefer", "").replace("-", "").strip()
            except NoSuchElementException:
                pass

            console.print(
                f"[bold green]  ✓ {card_id}: {dep_time}→{arr_time} | "
                f"{wagon_label} | {seats_display} koltuk | {price}[/bold green]"
            )

            available.append({
                "train_no": train_no or "?",
                "train_name": train_name or "?",
                "departure_time": dep_time or "?",
                "arrival_time": arr_time or "?",
                "available_seats": seats_display,
                "price": price or "?",
            })

        except StaleElementReferenceException:
            continue
        except Exception as e:
            console.print(f"[dim]  Kart hatası ({card_id}): {e}[/dim]")

    return available


def check_availability(
    departure: str,
    arrival: str,
    date: str,
    hour_start: Optional[int] = None,
    hour_end: Optional[int] = None,
    headless: bool = True,
) -> list[dict]:
    """
    Selenium ile TCDD sitesini açar, formu doldurur ve müsait seferleri döndürür.

    Args:
        departure: Kalkış (örn. "Ankara")
        arrival:   Varış  (örn. "İstanbul")
        date:      "DD/MM/YYYY"
        hour_start/hour_end: Opsiyonel saat filtresi
        headless:  True = arka planda çalış

    Returns:
        Müsait sefer listesi
    """
    driver = None
    try:
        console.print("[dim]  Chrome başlatılıyor...[/dim]")
        driver = build_driver(headless=headless)
        wait = WebDriverWait(driver, 25)

        driver.get(SITE_URL)
        time.sleep(2)

        # Açılışta gelen popup'ı kapat
        _close_modal(driver)

        # Kalkış istasyonu
        console.print(f"[dim]  Kalkış: {departure}[/dim]")
        _fill_station(driver, wait, "fromTrainInput", "departureInput", departure)

        # Varış istasyonu (kalkış seçildikten sonra aktif olur)
        time.sleep(0.5)
        console.print(f"[dim]  Varış: {arrival}[/dim]")
        _fill_station(driver, wait, "toTrainInput", "arrivalInput", arrival)

        # Tarih
        time.sleep(0.5)
        console.print(f"[dim]  Tarih: {date}[/dim]")
        _set_date(driver, wait, date)

        # Ara
        time.sleep(0.3)
        _click_search(driver, wait)

        # Sonuçları parse et
        return _parse_results(driver, wait, hour_start, hour_end)

    except Exception as e:
        console.print(f"[red]Hata: {e}[/red]")
        if driver:
            try:
                driver.save_screenshot("debug_screenshot.png")
                console.print("[dim]  debug_screenshot.png kaydedildi.[/dim]")
            except Exception:
                pass
        return []
    finally:
        if driver:
            driver.quit()
