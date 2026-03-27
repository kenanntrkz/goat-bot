"""Pitch — Proposal Generator Agent

Generates service proposals for specific leads.
Uses Claude CLI for text, fal.ai for cover image.
"""

import json
from datetime import datetime
from pathlib import Path

from agents.base import BaseAgent, DATA_DIR
from services.image import generate_proposal_cover


class PitchAgent(BaseAgent):
    agent_id = "pitch"
    name = "Pitch"
    role = "Generates service proposals and pitch decks"
    category = "sales"

    def run(self, lead_index=0) -> dict:
        config = self.load_config()
        leads = self._load_hot_leads()

        if not leads:
            return {
                "status": "error",
                "summary": "Sıcak lead yok. Önce Scout ve Filter çalıştır.",
                "metrics": {},
                "recommendations": ["Önce lead bul ve puanla"],
            }

        # Pick the lead
        if lead_index >= len(leads):
            lead_index = 0
        lead_data = leads[lead_index]
        lead = lead_data.get("lead", {})

        self.log(f"Teklif hazırlanıyor: {lead.get('name', '?')}")

        agency = config.get("agency_name", "goat Agency")
        owner = config.get("owner_name", "")
        niche = config.get("niche", "")

        # Generate proposal text via Claude
        proposal = self._generate_proposal(agency, owner, niche, lead)

        # Generate cover image via fal.ai
        self.log("Kapak görseli oluşturuluyor...")
        cover_path = generate_proposal_cover(agency, lead.get("name", ""), lead.get("category", niche))
        if cover_path:
            self.log(f"Kapak görseli: {cover_path}")

        # Save proposal
        slug = lead.get("name", "lead").lower().replace(" ", "_")[:30]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        proposal_path = DATA_DIR / "proposals" / f"{slug}_{timestamp}.md"
        proposal_path.parent.mkdir(parents=True, exist_ok=True)
        with open(proposal_path, "w", encoding="utf-8") as f:
            f.write(proposal)
        self.log(f"Teklif kaydedildi: {proposal_path}")

        results = {
            "status": "ok",
            "summary": f"Teklif hazır: {lead.get('name', '?')} için {agency} proposal",
            "metrics": {
                "lead_name": lead.get("name", "?"),
                "lead_email": lead.get("email", "—"),
                "lead_category": lead.get("category", "—"),
                "lead_score": lead_data.get("score", 0),
                "proposal_path": str(proposal_path),
                "cover_image": cover_path,
            },
            "proposal": proposal,
            "recommendations": [
                "Teklifi incele ve düzenle",
                f"Email: {lead.get('email', '—')}",
                f"Telefon: {lead.get('phone', '—')}",
                "Teklifi göndermeye hazırsan outreach kullan",
            ],
        }

        self.save_output("pitch_proposal_report.json", results)
        return results

    def _generate_proposal(self, agency, owner, niche, lead):
        """Generate proposal markdown via Claude or template."""
        lead_name = lead.get("name", "İşletme")
        lead_category = lead.get("category", niche)
        lead_rating = lead.get("rating", 0)
        lead_reviews = lead.get("review_count", 0)
        lead_address = lead.get("address", "")

        prompt = f"""Bir otomasyon ajansı için profesyonel iş teklifi yaz. Markdown formatında, Türkçe.

Ajans: {agency}
Kurucu: {owner}
Müşteri: {lead_name}
Sektör: {lead_category}
Adres: {lead_address}
Google Puanı: {lead_rating}/5 ({lead_reviews} yorum)

Teklif şunları içersin:
1. Kapak (ajans adı, müşteri adı, tarih)
2. Yönetici Özeti (1 paragraf — ne sunuyoruz, neden)
3. Mevcut Durum Analizi (müşterinin muhtemel sorunları)
4. Çözüm Önerisi (3 paket halinde)
5. Fiyatlandırma (Başlangıç $300/ay, Pro $500/ay, Kurumsal $1000/ay)
6. Zaman Çizelgesi (4 haftalık)
7. Neden Biz (kısa)
8. Sonraki Adımlar

Profesyonel, samimi, somut ol. Gereksiz şeyler yazma."""

        response = self.call_claude(prompt, timeout=45)
        if response:
            return response

        # Fallback template
        today = datetime.now().strftime("%d.%m.%Y")
        return f"""# İş Teklifi

**{agency}** → **{lead_name}**
Tarih: {today}

---

## Yönetici Özeti

{lead_name} için otomasyon çözümleri sunuyoruz. Google'da {lead_rating}/5 puanınız ve {lead_reviews} yorumunuz var — bu güçlü bir temel. Otomasyonla müşteri deneyiminizi bir üst seviyeye çıkarabiliriz.

---

## Mevcut Durum

- Google yorumlarına yanıt süresi muhtemelen uzun veya hiç yanıt verilmiyor
- Sosyal medya yönetimi manuel ve zaman alıcı
- Müşteri takibi sistematik değil
- Tekrarlayan işler çalışan zamanını yiyor

---

## Çözüm Önerimiz

### Paket 1: Başlangıç — $300/ay
- Google yorum otomatik yanıtlama
- Haftalık performans raporu
- Email destek

### Paket 2: Profesyonel — $500/ay
- Google yorum otomasyonu
- Sosyal medya planlama (haftalık 5 paylaşım)
- Aylık strateji toplantısı
- Öncelikli destek

### Paket 3: Kurumsal — $1,000/ay
- Tüm Pro özellikleri
- WhatsApp müşteri desteği otomasyonu
- Özel dashboard
- CRM entegrasyonu
- 7/24 destek

---

## Zaman Çizelgesi

| Hafta | İş |
|-------|-----|
| 1 | Analiz + kurulum |
| 2 | Otomasyon geliştirme |
| 3 | Test + optimizasyon |
| 4 | Canlıya alma + eğitim |

---

## Neden {agency}?

- {lead_category} sektöründe uzmanlaşmış otomasyon çözümleri
- Kurulum + sürekli bakım tek elde
- Sonuç odaklı: ölçülebilir metriklerle çalışıyoruz

---

## Sonraki Adımlar

1. 15 dakikalık demo görüşmesi
2. İhtiyaç analizi
3. Pilot uygulama (1 otomasyon)
4. Tam geçiş

İletişim: {owner} — {agency}
"""

    def _load_hot_leads(self):
        """Load hot leads from latest qualified file."""
        qual_dir = DATA_DIR / "leads" / "qualified"
        if not qual_dir.exists():
            return []
        files = sorted(qual_dir.glob("*.json"), reverse=True)
        if files:
            with open(files[0]) as f:
                data = json.load(f)
                return [l for l in data.get("leads", []) if l.get("qualification") == "hot"]
        return []
