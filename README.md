# TCDD e-Bilet Bot

TCDD e-bilet sitesini Selenium ile otomatik tarayan, belirttiğiniz güzergah ve saat aralığında **EKONOMİ veya BUSİNESS** vagonunda boş koltuk çıktığında Telegram, e-posta veya WhatsApp ile bildirim gönderen bir Python botudur.

> Tekerlekli sandalye koltuklarını filtreler; sadece standart yolcu koltuklarını raporlar.

---

## Özellikler

- Belirli güzergah, tarih ve saat aralığı için periyodik kontrol
- Sonuç sayfasındaki accordion kartları tek tek açarak vagon tipini doğrular
- EKONOMİ / BUSİNESS dışındaki vagonları (tekerlekli sandalye vb.) filtreler
- Dolu trenler için gereksiz bildirim göndermez (spam koruması)
- Üç bildirim kanalı: **Telegram**, **e-posta (Gmail/SMTP)**, **WhatsApp (Callmebot)**
- Headless veya görünür tarayıcı modu
- Renkli terminal çıktısı (Rich)

---

## Gereksinimler

| Gereksinim | Sürüm |
|---|---|
| Python | 3.10+ |
| Google Chrome | Güncel |
| ChromeDriver | Otomatik indirilir (webdriver-manager) |

---

## Kurulum

### 1. Depoyu klonla

```bash
git clone https://github.com/KULLANICI_ADINIZ/tcdd-ebilet.git
cd tcdd-ebilet
```

### 2. Sanal ortam oluştur ve aktif et

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Bağımlılıkları yükle

```bash
pip install -r requirements.txt
```

### 4. Yapılandırma dosyasını oluştur

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Ardından `.env` dosyasını bir metin editörüyle açıp doldurun (ayrıntılar aşağıda).

---

## Yapılandırma (`.env`)

### Zorunlu alanlar

```env
DEPARTURE_STATION=Söğütlüçeşme   # Kalkış istasyonu adı
ARRIVAL_STATION=Eskişehir         # Varış istasyonu adı
TRAVEL_DATE=13/05/2026            # GG/AA/YYYY formatında
```

İstasyon adını tam yazmak zorunda değilsiniz; site kısmi eşleşmeyi destekler (örn. `Ankara`, `İstanbul`).

### Opsiyonel alanlar

```env
HOUR_START=16          # Bu saatten önce kalkan seferleri atla (boş = 00:00'dan itibaren)
HOUR_END=22            # Bu saatten sonra kalkan seferleri atla (boş = gece yarısına kadar)
CHECK_INTERVAL_MINUTES=5          # Kaç dakikada bir kontrol edilsin? (varsayılan: 5)
HEADLESS=false         # true = arka planda çalış | false = tarayıcı penceresi görünsün
```

---

### Telegram Bildirimi

**Bot oluşturma:**

1. Telegram'da [@BotFather](https://t.me/BotFather)'ı açın.
2. `/newbot` komutunu gönderin, istenen bilgileri girin.
3. Verilen **token**'ı kopyalayın.

**Chat ID bulma:**

1. Az önce oluşturduğunuz bota herhangi bir mesaj gönderin.
2. Tarayıcınızda şu adresi açın (`<TOKEN>` yerine gerçek token'ı yazın):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. Gelen JSON'daki `"id"` değeri sizin Chat ID'nizdir.

```env
TELEGRAM_BOT_TOKEN=123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=987654321
```

---

### E-posta Bildirimi (Gmail)

Gmail normal şifresini SMTP ile kullanmaya izin vermez; **Uygulama Şifresi** gerekir.

**Uygulama Şifresi oluşturma:**

1. [Google Hesabım](https://myaccount.google.com/) → **Güvenlik** sekmesine gidin.
2. **2 Adımlı Doğrulama**'yı etkinleştirin (etkin değilse).
3. Güvenlik sayfasında **Uygulama şifreleri**'ni açın.
4. Uygulama: **Posta**, Cihaz: **Windows Bilgisayarı** seçin → **Oluştur**.
5. Çıkan 16 haneli şifreyi kopyalayın.

```env
EMAIL_SENDER=sizin@gmail.com
EMAIL_PASSWORD=xxxx xxxx xxxx xxxx   # 16 haneli uygulama şifresi (boşluksuz da olur)
EMAIL_RECIPIENT=bildirim@ornek.com
SMTP_HOST=smtp.gmail.com             # Varsayılan, değiştirmenize gerek yok
SMTP_PORT=587                        # Varsayılan, değiştirmenize gerek yok
```

---

### WhatsApp Bildirimi (Callmebot — ücretsiz)

**Aktivasyon:**

1. WhatsApp'tan **+34 644 82 99 38** numarasına şu mesajı gönderin:
   ```
   I allow callmebot to send me messages
   ```
2. Birkaç saniye içinde size bir **API key** gelir.
3. Bu key'i `.env` dosyasına girin.

```env
WHATSAPP_PHONE=+905551234567   # Uluslararası format, başında + olmalı
WHATSAPP_API_KEY=1234567
```

> En az bir bildirim kanalı yapılandırılmışsa bot çalışır. Birden fazlasını aynı anda aktif edebilirsiniz.

---

## Çalıştırma

```bash
python main.py
```

Terminal çıktısı örneği:

```
╭──────────────────────────────────────────╮
│  TCDD e-Bilet Bot  (Selenium)            │
│  Ctrl+C ile durdurabilirsiniz            │
╰──────────────────────────────────────────╯

  Güzergah:  Söğütlüçeşme → Eskişehir
  Tarih:     13/05/2026 (16:00–22:59)
  Kontrol:   Her 5 dakikada bir
  Mod:       Görünür tarayıcı
  Bildirim:  telegram

──────────── Kontrol – 14:32:10 ────────────
  22 sefer kartı bulundu, tek tek açılıyor...
  gidis0: DOLU (başlık), atlanıyor.
  gidis3: Sadece tekerlekli sandalye var.
  ✓ gidis7: 17:25→20:29 | EKONOMİ | 4 koltuk | ₺450,00
```

Boş koltuk bulunduğunda yapılandırdığınız kanallara şu formatta bildirim gider:

```
🚂 TCDD BİLET BULUNDU!
📍 Güzergah: Söğütlüçeşme → Eskişehir
📅 Tarih: 13/05/2026
🎟 Müsait 1 sefer:

• Sefer 154134 | YHT: 81022 İSTANBUL - ANKARA
  ⏰ 17:25 → 20:29
  💺 4 boş koltuk  |  💰 ₺450,00 TL

🔗 https://ebilet.tcddtasimacilik.gov.tr/
```

Botu durdurmak için `Ctrl+C`.

---

## Proje Yapısı

```
tcdd-ebilet/
├── main.py          # Giriş noktası; zamanlama, bildirim akışı, terminal tablosu
├── tcdd_api.py      # Selenium scraper — form doldurma, kart açma, vagon okuma
├── config.py        # .env okuma ve doğrulama
├── notifier.py      # Telegram / e-posta / WhatsApp gönderici
├── requirements.txt # Python bağımlılıkları
├── .env.example     # Yapılandırma şablonu (bu dosyayı .env olarak kopyalayın)
└── .gitignore
```

---

## Sorun Giderme

| Belirti | Çözüm |
|---|---|
| `Sefer kartı bulunamadı` | `HEADLESS=false` yapıp tarayıcıyı izleyin. Proje dizininde oluşan `debug_results.png` dosyasını inceleyin. |
| `Konfigürasyon hatası` | `.env` dosyasının mevcut olduğunu ve zorunlu alanların (`DEPARTURE_STATION`, `ARRIVAL_STATION`, `TRAVEL_DATE`) dolu olduğunu kontrol edin. |
| Telegram bildirimi gelmiyor | Token ve Chat ID'yi `getUpdates` URL'si ile doğrulayın; bota en az bir mesaj göndermiş olmanız gerekir. |
| Gmail kimlik doğrulama hatası | Normal şifre yerine **16 haneli Uygulama Şifresi** kullandığınızdan emin olun. |
| ChromeDriver uyumsuzluğu | `pip install -U webdriver-manager` ile güncelleyin. |
| İstasyon seçilemiyor | İstasyon adını tam veya kısmi olarak farklı şekillerde deneyin (örn. `İstanbul` yerine `Söğütlüçeşme`). |

---

## Lisans

MIT
