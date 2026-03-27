"""Pitch — Proposal Generator Agent

Generates service proposals for specific leads.
Uses Claude CLI for text, fal.ai for cover image.
"""

import json
from datetime import datetime
from pathlib import Path

from agents.base import BaseAgent, DATA_DIR
from services.image import generate_proposal_cover
from services.website_analyzer import analyze_website


class PitchAgent(BaseAgent):
    agent_id = "pitch"
    name = "Pitch"
    role = "Generates service proposals and pitch decks"
    category = "sales"

    def run(self, lead_index: int = -1) -> dict:
        """
        Run pitch for all hot leads (default) or a specific one (lead_index >= 0).
        Returns a summary with all generated proposals.
        """
        config = self.load_config()
        all_leads = self._load_hot_leads()

        if not all_leads:
            return {
                "status": "error",
                "summary": "Sıcak lead yok. Önce Scout ve Filter çalıştır.",
                "metrics": {},
                "recommendations": ["Önce lead bul ve puanla"],
            }

        # Single lead mode (legacy / explicit index)
        if lead_index >= 0:
            leads_to_process = [all_leads[min(lead_index, len(all_leads) - 1)]]
        else:
            leads_to_process = all_leads

        agency = config.get("agency_name", "goat Agency")
        owner = config.get("owner_name", "")
        niche = config.get("niche", "")

        proposals_generated = []

        for lead_data in leads_to_process:
            lead = lead_data.get("lead", {})
            self.log(f"Teklif hazırlanıyor: {lead.get('name', '?')}")

            # Website audit — prefer Scout's cached result
            web_audit = lead.get("website_audit")
            if not web_audit and lead.get("website"):
                self.log(f"Site analizi yapılıyor: {lead['website']}")
                web_audit = analyze_website(lead["website"])
            elif not web_audit:
                web_audit = {"exists": False, "issues": [], "strengths": [],
                             "summary": "Web sitesi yok."}

            proposal = self._generate_proposal(agency, owner, niche, lead, web_audit)

            # Save proposal file
            slug = lead.get("name", "lead").lower().replace(" ", "_")[:30]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            proposal_path = DATA_DIR / "proposals" / f"{slug}_{timestamp}.md"
            proposal_path.parent.mkdir(parents=True, exist_ok=True)
            with open(proposal_path, "w", encoding="utf-8") as f:
                f.write(proposal)

            proposals_generated.append({
                "lead_name": lead.get("name", "?"),
                "lead_email": lead.get("email", "—"),
                "lead_category": lead.get("category", "—"),
                "lead_score": lead_data.get("score", 0),
                "website_audit": web_audit.get("summary", ""),
                "proposal_path": str(proposal_path),
                # Full proposal only in single-lead mode to keep response size sane
                "proposal": proposal if lead_index >= 0 or len(leads_to_process) == 1 else None,
            })

        # First proposal as preview
        preview = ""
        if proposals_generated:
            first_path = proposals_generated[0]["proposal_path"]
            try:
                with open(first_path, encoding="utf-8") as f:
                    preview = f.read()
            except Exception:
                pass

        results = {
            "status": "ok",
            "summary": f"{len(proposals_generated)} teklif hazırlandı ({agency})",
            "metrics": {
                "total_pitched": len(proposals_generated),
                "total_hot": len(all_leads),
                "agency": agency,
            },
            "proposals": proposals_generated,
            # Dashboard preview: first proposal
            "proposal": preview,
            "lead": proposals_generated[0] if proposals_generated else {},
            "recommendations": [
                f"{len(proposals_generated)} teklif data/proposals/ klasörüne kaydedildi",
                "Outreach agent ile email gönderimine geç",
                "Teklifleri tarayıcıda görmek için goat.kenanturkoz.cloud/api/leads/qualified",
            ],
        }

        self.save_output("pitch_proposal_report.json", results)
        return results

    def _generate_proposal(self, agency, owner, niche, lead, web_audit=None):
        """Generate proposal markdown via Claude or template."""
        lead_name = lead.get("name", "İşletme")
        lead_category = lead.get("category", niche)
        lead_rating = lead.get("rating", 0)
        lead_reviews = lead.get("review_count", 0)
        lead_address = lead.get("address", "")
        lead_website = lead.get("website", "")

        # Build website context block for the prompt
        if not lead_website:
            web_context = "Web Sitesi: YOK — tekliffe web sitesi tasarım ve kurulum hizmeti mutlaka öner."
        elif not web_audit or not web_audit.get("exists"):
            web_context = f"Web Sitesi: {lead_website} (ulaşılamadı veya analiz edilemedi)"
        else:
            issues = web_audit.get("issues", [])
            strengths = web_audit.get("strengths", [])
            issues_text = "\n".join(f"  - {i}" for i in issues) if issues else "  (tespit edilmedi)"
            strengths_text = "\n".join(f"  + {s}" for s in strengths) if strengths else "  (tespit edilmedi)"
            web_context = f"""Web Sitesi: {lead_website}
Eksiklikler (bunları tekliffe somut çözüm olarak yansıt):
{issues_text}
Güçlü Noktalar:
{strengths_text}"""

        prompt = f"""Bir otomasyon ajansı için profesyonel iş teklifi yaz. Markdown formatında, Türkçe.

Ajans: {agency}
Kurucu: {owner}
Müşteri: {lead_name}
Sektör: {lead_category}
Adres: {lead_address}
Google Puanı: {lead_rating}/5 ({lead_reviews} yorum)
{web_context}

Teklif şunları içersin:
1. Kapak (ajans adı, müşteri adı, tarih)
2. Yönetici Özeti (1 paragraf — ne sunuyoruz, neden)
3. Mevcut Durum Analizi — web sitesi eksikliklerini somut verilerle göster, site yoksa bunu özellikle vurgula
4. Çözüm Önerisi (3 paket — Temel/Profesyonel/Kurumsal, ₺ fiyatlar kullan)
5. Zaman Çizelgesi (4 haftalık)
6. Neden Biz (kısa)
7. Sonraki Adımlar

Önemli: Web sitesi bulgularını "Mevcut Durum" bölümüne mutlaka yansıt. Site yoksa web sitesi kurulumunu en yüksek öncelikli çözüm olarak sun.
Profesyonel, samimi, somut ol."""

        response = self.call_claude(prompt, timeout=60)
        if response:
            return response

        # Smart fallback template — category-aware + website audit
        return self._build_template(agency, owner, lead_name, lead_category,
                                    lead_rating, lead_reviews, lead_address, web_audit)

    def _build_template(self, agency, owner, lead_name, category, rating, reviews, address, web_audit=None):
        """Category-aware proposal template."""
        today = datetime.now().strftime("%d.%m.%Y")
        cat = (category or "").lower()

        # --- Category-specific content ---
        if any(k in cat for k in ["restoran", "cafe", "bistro", "restaurant", "food", "yemek", "pizza", "burger"]):
            pain_points = [
                f"Google'da {reviews} yorumunuz var — büyük çoğunluğuna yanıt verilmemiş olabilir",
                "Rezervasyon ve sipariş süreçleri muhtemelen telefon/WhatsApp ile yürütülüyor",
                "Sosyal medya için düzenli içerik üretmek zaman alıyor",
                "Müşteri geri bildirimlerini takip etmek için sistematik bir yapı yok",
            ]
            packages = [
                ("Temel", "8.500 ₺/ay", [
                    "Google yorum otomatik yanıtlama (24 saat içinde)",
                    "Haftalık sosyal medya takvimi (3 paylaşım)",
                    "Aylık performans raporu",
                ]),
                ("Profesyonel", "16.000 ₺/ay", [
                    "Tüm Temel paket özellikleri",
                    "WhatsApp otomatik rezervasyon hatırlatıcı",
                    "Günlük sosyal medya yönetimi (7 paylaşım)",
                    "Google ve Şikayetvar anlık izleme",
                    "Aylık strateji toplantısı",
                ]),
                ("Tam Dijital", "28.000 ₺/ay", [
                    "Tüm Profesyonel özellikler",
                    "Menü QR sistemi + dijital sipariş",
                    "Müşteri sadakat programı otomasyonu",
                    "Özel dashboard + haftalık analiz",
                    "CRM entegrasyonu",
                ]),
            ]
            why = f"Restoran ve cafe sektöründe {reviews}+ yorumu olan işletmelerin dijital dönüşümünde uzmanız."
            quick_win = "İlk 30 günde: tüm yanıtsız yorumlarınıza profesyonel yanıt + sosyal medya düzeni"

        elif any(k in cat for k in ["klinik", "doktor", "sağlık", "diş", "hastane", "clinic", "health", "derm", "estetik"]):
            pain_points = [
                "Randevu hatırlatmaları manuel gönderiliyor, no-show oranı yüksek",
                "Hasta kayıtları ve takibi zaman alıcı",
                f"Google'da {reviews} yorum var — potansiyel hastalar burada karar veriyor",
                "Yeni hasta kazanımı için dijital kanallar yeterince kullanılmıyor",
            ]
            packages = [
                ("Temel", "9.500 ₺/ay", [
                    "Otomatik randevu hatırlatma (SMS/WhatsApp)",
                    "Google yorum yönetimi",
                    "Aylık performans raporu",
                ]),
                ("Profesyonel", "18.000 ₺/ay", [
                    "Tüm Temel paket özellikleri",
                    "Online randevu formu entegrasyonu",
                    "Hasta geri bildirim sistemi",
                    "Sosyal medya yönetimi (5 paylaşım/hafta)",
                    "No-show azaltma kampanyası",
                ]),
                ("Klinik Pro", "32.000 ₺/ay", [
                    "Tüm Profesyonel özellikler",
                    "Hasta CRM sistemi",
                    "Tedavi sonrası otomatik takip",
                    "Google Ads yönetimi",
                    "7/24 teknik destek",
                ]),
            ]
            why = "Sağlık sektörü dijital otomasyonunda gizlilik ve profesyonellik en önceliğimiz."
            quick_win = "İlk 30 günde: randevu no-show oranını %40'a kadar düşürme garantisi"

        elif any(k in cat for k in ["otel", "hotel", "pansiyon", "konaklama", "resort", "hostel"]):
            pain_points = [
                "Booking.com, Airbnb gibi platformlardaki yorumlara yanıt vermek zaman alıyor",
                f"{reviews} Google yorumunuzun yönetimi sistematik değil",
                "Misafir iletişimi check-in/out sürecinde yoğun",
                "Tekrar eden sorular için otomatik yanıt sistemi yok",
            ]
            packages = [
                ("Temel", "11.000 ₺/ay", [
                    "Google + Booking yorum otomasyonu",
                    "Misafir karşılama mesajı şablonları",
                    "Aylık itibar raporu",
                ]),
                ("Profesyonel", "20.000 ₺/ay", [
                    "Tüm Temel paket özellikleri",
                    "WhatsApp check-in/check-out otomasyonu",
                    "Sosyal medya yönetimi",
                    "Sezon bazlı kampanya yönetimi",
                    "Aylık strateji toplantısı",
                ]),
                ("Premium", "35.000 ₺/ay", [
                    "Tüm Profesyonel özellikler",
                    "Çoklu platform entegrasyonu (Booking, Airbnb, Expedia)",
                    "Müşteri sadakat sistemi",
                    "Dinamik fiyat takibi + öneri",
                    "7/24 destek",
                ]),
            ]
            why = "Konaklama sektöründe misafir deneyimi otomasyonu özel uzmanlık alanımız."
            quick_win = "İlk 30 günde: tüm platformlardaki yanıtsız yorumlar yanıtlanır"

        elif any(k in cat for k in ["güzellik", "kuaför", "berber", "tırnak", "nail", "beauty", "salon", "spa", "masaj"]):
            pain_points = [
                "Randevu yönetimi telefon/WhatsApp üzerinden yapılıyor",
                "Müşteri hatırlatmaları manuel, zaman alıcı",
                "Sosyal medya için düzenli içerik üretmek zor",
                f"Google'da {reviews} yorum var ama tam kullanılmıyor",
            ]
            packages = [
                ("Temel", "7.500 ₺/ay", [
                    "Online randevu sistemi",
                    "Otomatik randevu hatırlatma (WhatsApp)",
                    "Google yorum yönetimi",
                ]),
                ("Profesyonel", "14.000 ₺/ay", [
                    "Tüm Temel paket özellikleri",
                    "Müşteri doğum günü kampanyaları",
                    "Sosyal medya yönetimi (5 paylaşım/hafta)",
                    "Sadakat programı otomasyonu",
                ]),
                ("Tam Paket", "24.000 ₺/ay", [
                    "Tüm Profesyonel özellikler",
                    "Hizmet öncesi/sonrası fotoğraf sistemi",
                    "Google Ads yönetimi",
                    "Müşteri geri bildirim sistemi",
                    "7/24 teknik destek",
                ]),
            ]
            why = "Güzellik ve bakım sektöründe müşteri sadakati otomasyonunda uzmanız."
            quick_win = "İlk 30 günde: randevu no-show oranında %50 azalma"

        else:
            # Generic business
            pain_points = [
                f"Google'da {reviews} yorumunuz var — sistematik yönetim ile güçlü bir itibar oluşturulabilir",
                "Tekrarlayan müşteri iletişimleri çalışan zamanının büyük bölümünü alıyor",
                "Sosyal medya yönetimi düzensiz veya zaman yetersizliği nedeniyle aksıyor",
                "Yeni müşteri kazanımı için dijital kanallar yeterince optimize edilmemiş",
            ]
            packages = [
                ("Temel", "9.000 ₺/ay", [
                    "Google yorum otomatik yanıtlama",
                    "Sosyal medya yönetimi (haftalık 3 paylaşım)",
                    "Aylık performans raporu",
                ]),
                ("Profesyonel", "17.000 ₺/ay", [
                    "Tüm Temel paket özellikleri",
                    "WhatsApp otomatik müşteri iletişimi",
                    "Email kampanya yönetimi",
                    "Rakip takip + itibar izleme",
                    "Aylık strateji toplantısı",
                ]),
                ("Kurumsal", "30.000 ₺/ay", [
                    "Tüm Profesyonel özellikler",
                    "CRM entegrasyonu",
                    "Özel otomasyon geliştirme",
                    "Google/Meta Ads yönetimi",
                    "7/24 teknik destek",
                ]),
            ]
            why = f"{lead_name} büyüklüğündeki işletmeler için özelleştirilmiş otomasyon çözümleri sunuyoruz."
            quick_win = "İlk 30 günde: en az 1 tam otomasyon canlıya alınır, sonuçlar ölçülür"

        # Inject website audit findings
        web_section = ""
        if web_audit and web_audit.get("url"):
            # Website exists — show issues
            issues = web_audit.get("issues", [])
            if issues:
                pain_points.insert(0, f"Web sitesinde {len(issues)} kritik eksiklik var ({web_audit['url']})")
                web_section = (
                    "\n### Web Sitesi Denetimi\n"
                    + "".join(f"- {i}\n" for i in issues[:6])
                    + "\n> Web sitesi sorunları doğrudan müşteri kaybına yol açıyor.\n"
                )
        else:
            # No website at all
            pain_points.insert(0, "Web sitesi yok — rakipler Google aramasında sizi geride bırakıyor")
            web_section = (
                "\n### Web Sitesi Yok\n"
                "- Potansiyel müşterilerin %70+ sizi Google'da arayıp bulamıyor\n"
                "- Profesyonel bir web sitesi güven oluşturmanın 1. adımı\n"
                "- **Çözüm:** Sektörünüze özel, mobil uyumlu, SEO optimizasyonlu site kuruyoruz\n"
            )

        # Rating-based summary
        if rating >= 4.5:
            rep_comment = f"Google'da **{rating}/5** puanınız ve {reviews} yorumunuzla sektörün üst çeyreğindesiniz. Bu itibarı büyütmek ve korumak için sistem kuruyoruz."
        elif rating >= 4.0:
            rep_comment = f"**{rating}/5** puanınız sağlam bir başlangıç. Doğru otomasyon ile 4.8+ seviyesine çıkmak mümkün."
        else:
            rep_comment = f"**{rating}/5** puanınızı iyileştirmek için sistematik yorum yönetimi kritik öneme sahip."

        # Build packages section
        pkg_md = ""
        for pname, price, features in packages:
            pkg_md += f"\n### {pname} — {price}\n"
            for f in features:
                pkg_md += f"- {f}\n"

        return f"""# İş Teklifi

**{agency}** → **{lead_name}**
Tarih: {today} | Hazırlayan: {owner}

---

## Yönetici Özeti

{rep_comment}

{agency} olarak {lead_name}'e özel otomasyon çözümleri sunuyoruz. Hedefimiz: sizi rekabette öne çıkarmak, tekrarlayan işlerden kurtarmak ve müşteri deneyiminizi sistematik hale getirmek.

---

## Mevcut Durum Analizi

{"".join(f"→ {p}" + chr(10) for p in pain_points)}{web_section}
---

## Çözüm Paketlerimiz
{pkg_md}
---

## Neden {agency}?

{why}

- Kurulum sonrası 3 ay ücretsiz optimizasyon desteği
- Her otomasyon için ölçülebilir hedef ve raporlama
- **Pilot teklif:** İlk ay %50 indirimli başlayın, sonuçları görün

**{quick_win}**

---

## Zaman Çizelgesi

| Hafta | Çalışma |
|-------|---------|
| 1 | Mevcut durum analizi + sistem kurulumu |
| 2 | Otomasyonlar devreye alınıyor |
| 3 | Test, optimizasyon, ince ayar |
| 4 | Canlıya geçiş + ekip eğitimi |

---

## Sonraki Adım

**15 dakikalık ücretsiz demo görüşmesi** için bugün iletişime geçin.

📧 {owner} | {agency}
"""

    def run_batch(self) -> list:
        """
        Generate proposals for ALL hot leads.
        Returns list of {lead_data, lead, proposal, web_audit} dicts.
        Used by GoatAgent for the full automated pipeline.
        """
        config = self.load_config()
        hot_leads = self._load_hot_leads()
        agency = config.get("agency_name", "goat Agency")
        owner = config.get("owner_name", "")
        niche = config.get("niche", "")

        pitched = []
        for lead_data in hot_leads:
            lead = lead_data.get("lead", {})
            if not lead.get("email"):
                continue  # skip — can't email without address

            web_audit = lead.get("website_audit")
            if web_audit is None and lead.get("website"):
                from services.website_analyzer import analyze_website
                web_audit = analyze_website(lead["website"])
            elif web_audit is None:
                web_audit = {"exists": False, "issues": [], "strengths": [], "summary": "Web sitesi yok."}

            self.log(f"Teklif: {lead.get('name', '?')}")
            proposal = self._generate_proposal(agency, owner, niche, lead, web_audit)

            # Save proposal file
            slug = lead.get("name", "lead").lower().replace(" ", "_")[:30]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            proposal_path = DATA_DIR / "proposals" / f"{slug}_{timestamp}.md"
            proposal_path.parent.mkdir(parents=True, exist_ok=True)
            with open(proposal_path, "w", encoding="utf-8") as f:
                f.write(proposal)

            pitched.append({
                "lead_data": lead_data,
                "lead": lead,
                "proposal": proposal,
                "web_audit": web_audit,
                "proposal_path": str(proposal_path),
            })

        self.log(f"Toplu teklif tamamlandı: {len(pitched)} lead")
        return pitched

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
