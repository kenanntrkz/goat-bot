"""Outreach — Email Campaign Agent

Creates cold email campaigns via Turkoz Outreach (outreach.kenanturkoz.cloud).
Reads qualified leads, generates email sequences, imports to outreach system.
"""

import json
from datetime import datetime
from pathlib import Path

from agents.base import BaseAgent, DATA_DIR
from services.outreach import (
    get_api_key, test_connection, create_campaign,
    import_leads, list_campaigns,
)


class OutreachAgent(BaseAgent):
    agent_id = "outreach"
    name = "Outreach"
    role = "Cold email campaigns via Turkoz Outreach"
    category = "sales"

    def run(self, auto_activate=False) -> dict:
        config = self.load_config()
        api_key = config.get("outreach_api_key") or get_api_key()

        # Check API key
        if not api_key:
            return {
                "status": "needs_key",
                "summary": "Outreach API anahtarı gerekli. Henüz ayarlanmamış.",
                "metrics": {},
                "recommendations": [
                    "outreach.kenanturkoz.cloud sistemini aç",
                    "OUTREACH_API_KEY'i .env dosyasına ekle",
                    "goat dashboard'undan API anahtarını ayarla",
                ],
            }

        # Test connection
        self.log("Outreach sistemi test ediliyor...")
        if not test_connection(api_key):
            return {
                "status": "error",
                "summary": "Outreach sistemine bağlanılamadı. API anahtarını kontrol et.",
                "metrics": {},
                "recommendations": ["OUTREACH_API_KEY ve OUTREACH_URL değerlerini kontrol et"],
            }
        self.log("Bağlantı başarılı.")

        # Load qualified leads
        leads = self._load_hot_leads()
        if not leads:
            return {
                "status": "error",
                "summary": "Sıcak lead yok. Önce Scout ve Filter çalıştır.",
                "metrics": {},
                "recommendations": ["Önce 'müşteri adaylarını ara' ve 'leadleri puanla' komutlarını çalıştır"],
            }

        # Filter to only leads with email
        email_leads = [l for l in leads if l.get("lead", {}).get("email")]
        if not email_leads:
            return {
                "status": "error",
                "summary": "Email adresi olan sıcak lead yok.",
                "metrics": {"total_hot": len(leads), "with_email": 0},
                "recommendations": ["Daha fazla lead bulmak için Scout'u tekrar çalıştır"],
            }

        self.log(f"{len(email_leads)} email'li sıcak lead bulundu.")

        # Generate email sequence
        agency_name = config.get("agency_name", "goat Agency")
        owner_name = config.get("owner_name", "")
        niche = config.get("niche", "işletme")
        sequence = self._generate_sequence(agency_name, owner_name, niche)

        # Use first email as campaign template
        first_email = sequence[0] if sequence else {
            "subject": f"{niche} için otomasyon önerisi",
            "body": f"Merhaba,\n\n{agency_name} olarak sizinle iletişime geçmek istedim.\n\nSaygılarımla,\n{owner_name}",
        }

        # Create campaign in outreach system
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        campaign_name = f"goat_{niche}_{timestamp}"
        self.log(f"Kampanya oluşturuluyor: {campaign_name}")

        campaign_id = create_campaign(
            name=campaign_name,
            subject_template=first_email.get("subject", ""),
            body_template=first_email.get("body", ""),
        )
        if not campaign_id:
            return {
                "status": "error",
                "summary": "Kampanya oluşturulamadı. Outreach sistemini kontrol et.",
                "metrics": {},
                "recommendations": ["outreach.kenanturkoz.cloud adresine gidip durumu kontrol et"],
            }

        self.log(f"Kampanya oluşturuldu: {campaign_id}")

        # Convert and import leads
        outreach_leads = []
        for l in email_leads:
            lead = l.get("lead", {})
            name_parts = (lead.get("name", "") or "").split(maxsplit=1)
            outreach_leads.append({
                "email": lead["email"],
                "first_name": name_parts[0] if name_parts else "",
                "last_name": name_parts[1] if len(name_parts) > 1 else "",
                "company": lead.get("name", ""),
                "sector": lead.get("category", niche),
                "phone": lead.get("phone", ""),
                "website": lead.get("website", ""),
                "country": "TR",
                "source": "goat-scout",
                "notes": f"Rating: {lead.get('rating', '')} | City: {lead.get('location', '')}",
            })

        imported = import_leads(outreach_leads)
        if imported is None:
            self.log("Lead'ler eklenemedi.")
            imported = 0
        else:
            self.log(f"{imported} lead sisteme eklendi.")

        # Save campaign data locally
        campaign_data = {
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "created_at": datetime.now().isoformat(),
            "status": "draft",
            "leads_count": len(outreach_leads),
            "sequence": sequence,
            "leads": outreach_leads,
            "outreach_url": f"https://outreach.kenanturkoz.cloud",
        }
        self.save_data(f"campaigns/{campaign_id}.json", campaign_data)

        results = {
            "status": "ok",
            "summary": f"Kampanya hazır: {imported} lead eklendi. outreach.kenanturkoz.cloud'dan yönet.",
            "metrics": {
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "leads_imported": imported,
                "total_hot": len(leads),
                "with_email": len(email_leads),
                "sequence_steps": len(sequence),
                "status": "draft",
            },
            "sequence": sequence,
            "recommendations": [
                "outreach.kenanturkoz.cloud adresinden kampanyayı görüntüle",
                f"Kampanya adı: {campaign_name}",
                "Email sequence 3 adımlı — lokal dosyada kayıtlı",
                "n8n workflow'dan kampanyayı aktifleştir",
            ],
        }

        self.save_output("outreach_campaign_report.json", results)
        self.log("Kampanya raporu kaydedildi.")
        return results

    def _load_hot_leads(self) -> list:
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

    def _generate_sequence(self, agency_name, owner_name, niche):
        """Generate a 3-step email sequence. Uses Claude if available, otherwise templates."""
        prompt = f"""Bir otomasyon ajansı için 3 adımlı soğuk email dizisi yaz.

Ajans: {agency_name}
Kurucu: {owner_name}
Hedef sektör: {niche}

Her email için subject ve body yaz. Türkçe olsun. Kısa, samimi, değer odaklı.
Email 1: Tanışma + fark ettiğin bir sorun
Email 2: 3 gün sonra, somut değer önerisi
Email 3: 7 gün sonra, son hatırlatma

JSON formatında dön:
[{{"step":1,"delay_days":0,"subject":"...","body":"..."}}, ...]"""

        response = self.call_claude(prompt, timeout=30)
        if response:
            try:
                import re
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except (json.JSONDecodeError, AttributeError):
                pass

        # Fallback: template-based sequence
        sender = owner_name or "Ben"
        return [
            {
                "step": 1,
                "delay_days": 0,
                "subject": f"{niche} işletmeniz için otomasyon önerisi",
                "body": f"Merhaba {{{{first_name}}}},\n\n"
                        f"{{{{company}}}} işletmenizi inceledim. Google yorumlarınıza henüz otomatik yanıt verilmediğini fark ettim.\n\n"
                        f"Biz {agency_name} olarak {niche} işletmeleri için otomasyon çözümleri kuruyoruz. "
                        f"Müşterilerinize 5 dakika içinde profesyonel yanıt göndermek ister misiniz?\n\n"
                        f"15 dakikalık bir demo için müsait misiniz?\n\n"
                        f"Saygılarımla,\n{sender}",
            },
            {
                "step": 2,
                "delay_days": 3,
                "subject": "Re: Otomasyon ile ayda 20+ saat kazanın",
                "body": f"Merhaba {{{{first_name}}}},\n\n"
                        f"Geçen hafta yazdığım mesajı gördünüz mü?\n\n"
                        f"Sizin sektörünüzdeki bir işletme için kurduğumuz sistemle:\n"
                        f"- Google yorum yanıt süresi: 2 gün → 5 dakika\n"
                        f"- Ayda 20+ saat tasarruf\n"
                        f"- Müşteri memnuniyetinde %30 artış\n\n"
                        f"Size de benzer sonuçlar sağlayabilirim. Bu hafta 15 dakikanız var mı?\n\n"
                        f"{sender}",
            },
            {
                "step": 3,
                "delay_days": 7,
                "subject": "Re: Son sorum",
                "body": f"Merhaba {{{{first_name}}}},\n\n"
                        f"Son kez yazıyorum. Eğer otomasyon şu an önceliğiniz değilse tamamen anlıyorum.\n\n"
                        f"Ama ileride düşünürseniz, buradan bana ulaşabilirsiniz.\n\n"
                        f"Başarılar,\n{sender}",
            },
        ]
