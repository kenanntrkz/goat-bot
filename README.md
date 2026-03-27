```
   ██████╗  ██████╗  █████╗ ████████╗
  ██╔════╝ ██╔═══██╗██╔══██╗╚══██╔══╝
  ██║  ███╗██║   ██║███████║   ██║
  ██║   ██║██║   ██║██╔══██║   ██║
  ╚██████╔╝╚██████╔╝██║  ██║   ██║
   ╚═════╝  ╚═════╝ ╚═╝  ╚═╝   ╚═╝
```

# GOAT — Ajans Komuta Merkezi

> Tek kişilik AI otomasyon ajansını kur, müşteri bul, teklif hazırla, kampanya gönder.
> Hepsi tek bir terminal arayüzünden.

---

## Ne Yapar?

GOAT, solo girişimciler için AI otomasyon ajansı kurma platformu. 6 ajan sırayla çalışarak senin yerine müşteri buluyor, puanlıyor, teklif hazırlıyor ve email kampanyası oluşturuyor.

```
Scout ━━● Filter ━━● Pitch ━━● Outreach
  ↓          ↓         ↓          ↓
lead bul   puanla    teklif    kampanya
```

## Ajanlar

| Ajan | Görev | Araç |
|------|-------|------|
| **GOAT** | Ana orkestratör — tüm pipeline'ı yönetir | — |
| **Scout** | Google Maps'ten müşteri adayı bulur | Apify |
| **Filter** | Leadleri puanlayıp sıcak/ılık/soğuk ayırır | — |
| **Pitch** | Kişiselleştirilmiş teklif ve kapak görseli hazırlar | Claude + fal.ai |
| **Outreach** | 3 aşamalı email kampanyası oluşturur | Instantly.ai |
| **Mentor** | Ajans kurma hakkında her soruyu cevaplar | Claude |

## Hızlı Başlangıç

```bash
# 1. Kur
git clone https://github.com/goatstarter/goat-bot.git
cd goat-bot
pip install -r requirements.txt

# 2. API anahtarlarını ayarla
cp .env.example .env
# .env dosyasını düzenle — en azından APIFY_TOKEN ekle

# 3. Çalıştır
python app.py
# http://localhost:7778 adresini aç
```

## API Anahtarları

| Anahtar | Env Değişkeni | Neden Gerekli | Nereden Alınır |
|---------|---------------|---------------|----------------|
| Apify | `APIFY_TOKEN` | Lead bulmak için (Google Maps) | [console.apify.com](https://console.apify.com) |
| fal.ai | `FAL_KEY` | Teklif kapağı ve reklam görseli | [fal.ai](https://fal.ai) |
| Instantly.ai | `INSTANTLY_API_KEY` | Email kampanyası (opsiyonel) | [instantly.ai](https://app.instantly.ai) |

## Nasıl Çalışır?

1. **Ajansını kur** — İsim, niş ve hedef şehirleri belirle
2. **Scout çalıştır** — Google Maps'ten yüzlerce işletme bul
3. **Filter ile puanla** — Email, yorum, puan bazlı otomatik skorlama
4. **Pitch ile teklif hazırla** — AI destekli kişisel teklif + kapak görseli
5. **Outreach ile ulaş** — 3 adımlı soğuk email kampanyası (taslak)
6. **Mentor'a sor** — Fiyatlama, strateji, müşteri kazanımı hakkında

## Teknoloji

- **Backend:** FastAPI (Python 3.9+)
- **Frontend:** Terminal tarzı tek sayfa dashboard
- **Depolama:** JSON dosyalar (veritabanı yok)
- **AI:** Claude CLI + fal.ai (nano-banana-2)
- **Port:** 7778

## Komutlar

Dashboard'da şunları yazabilirsin:

```
ara / scout       → müşteri adaylarını bul
puanla / filter   → leadleri puanla
teklif / pitch    → müşteriye teklif hazırla
email / ulaş      → email kampanyası oluştur
görsel / reklam   → AI ile reklam görseli oluştur
leadler           → lead tablosu göster
yardım            → komut listesi
```

## Proje Yapısı

```
goat-bot/
├── app.py                    # FastAPI sunucu
├── agents/
│   ├── goat/agent.py         # Ana orkestratör
│   ├── scout/agent.py        # Lead bulucu (Apify)
│   ├── filter/agent.py       # Lead puanlayıcı
│   ├── pitch/agent.py        # Teklif motoru
│   ├── outreach/agent.py     # Kampanya yöneticisi
│   └── mentor/agent.py       # Bilgi bankası
├── services/
│   ├── scraper.py            # Google Maps (Apify)
│   ├── email.py              # Instantly.ai
│   └── image.py              # fal.ai (nano-banana-2)
├── templates/
│   └── dashboard.html        # Terminal arayüz
└── data/
    ├── config/               # Ajans ayarları
    ├── leads/                # Ham ve puanlı leadler
    └── classroom/            # Mentor içerikleri
```

## Tasarım Kararları

- **Veritabanı yok** — her şey JSON dosyalarda
- **Claude CLI opsiyonel** — her LLM çağrısının template fallback'i var
- **Türkçe** — tüm arayüz ve içerik Türkçe
- **Taslak kampanya** — outreach asla otomatik göndermez, kullanıcı Instantly.ai'dan aktif eder
- **Dark terminal teması** — pixel art bot karakteri ile retro komuta merkezi estetiği

---

*GOAT tarafından oluşturuldu*
