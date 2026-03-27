# Otomasyon Araçları Rehberi

## Temel Araçlar

### n8n (Birincil Otomasyon Platformu)
- **Ne yapar**: Farklı uygulamaları birbirine bağlar, iş akışlarını otomatikleştirir
- **Neden**: Açık kaynak, self-hosted seçeneği, sınırsız akış
- **Fiyat**: Ücretsiz (self-hosted) veya $20/ay (cloud)
- **Öğren**: n8n.io/courses

### Make.com (Alternatif)
- **Ne yapar**: Görsel otomasyon oluşturma platformu
- **Neden**: Daha kolay öğrenme eğrisi, güzel arayüz
- **Fiyat**: Ücretsiz başlangıç, $9/ay'dan başlıyor
- **Öğren**: make.com/en/academy

### Claude (AI Asistan)
- **Ne yapar**: İçerik üretimi, analiz, kod yazma, müşteri iletişimi
- **Neden**: En güçlü AI asistan, Türkçe desteği mükemmel
- **Fiyat**: Ücretsiz (sınırlı) veya $20/ay Pro
- **İpucu**: Claude Code ile otomasyon scriptleri yaz

## Müşteri Yönetimi

### Notion
- CRM olarak kullan (müşteri veritabanı)
- Proje takibi
- Dokümantasyon
- Ücretsiz başlangıç

### Google Sheets
- Basit CRM için yeterli
- n8n ile entegre et
- Müşteri listesi + takip

## Ödeme ve Faturalama

### Stripe
- Uluslararası ödemeler
- Otomatik faturalama
- Abonelik yönetimi

### iyzico
- Türkiye'deki müşteriler için
- Türk Lirası desteği

## Sık Kurulan Otomasyonlar

1. **Google Yorum Yanıtlama**: Google Business → n8n → Claude → Google (otomatik yanıt)
2. **Sosyal Medya Planlama**: İçerik takvimi → n8n → Instagram/Facebook/LinkedIn
3. **Lead Takibi**: Form dolduruldu → CRM'e ekle → Email gönder → Takip hatırlat
4. **Müşteri Desteği**: WhatsApp/Email → Claude ile yanıtla → Karmaşık olanları yönlendir
5. **Randevu Hatırlatma**: Takvim → SMS/WhatsApp hatırlatma → Onay al
