"""goat — Master Orchestrator Agent

Full automated pipeline: Scout → Filter → Pitch → Outreach.
"""

from datetime import datetime

from agents.base import BaseAgent


class GoatAgent(BaseAgent):
    agent_id = "goat"
    name = "goat"
    role = "Master orchestrator — tam pipeline (Scout → Filter → Pitch → Outreach)"
    category = "master"

    def run(self) -> dict:
        """Run the full pipeline: Scout → Filter → Pitch (batch) → Outreach (auto-send)."""
        self.log("goat pipeline başlıyor...")
        config = self.load_config()
        agency = config.get("agency_name", "goat Agency")
        owner = config.get("owner_name", "")
        results = {"agents": {}, "pipeline_status": "running"}

        # ── Step 1: Scout ──────────────────────────────────────────────
        self.log("Adım 1: Scout çalışıyor...")
        try:
            from agents.scout.agent import ScoutAgent
            scout_result = ScoutAgent().run()
            results["agents"]["scout"] = {
                "status": scout_result.get("status"),
                "summary": scout_result.get("summary"),
                "metrics": scout_result.get("metrics", {}),
            }
            self.log(f"Scout: {scout_result.get('summary', 'done')}")
        except Exception as e:
            results["agents"]["scout"] = {"status": "error", "error": str(e)}
            self.log(f"Scout hata: {e}")

        # ── Step 2: Filter ─────────────────────────────────────────────
        self.log("Adım 2: Filter çalışıyor...")
        try:
            from agents.filter.agent import FilterAgent
            filter_result = FilterAgent().run()
            results["agents"]["filter"] = {
                "status": filter_result.get("status"),
                "summary": filter_result.get("summary"),
                "metrics": filter_result.get("metrics", {}),
            }
            self.log(f"Filter: {filter_result.get('summary', 'done')}")
        except Exception as e:
            results["agents"]["filter"] = {"status": "error", "error": str(e)}
            self.log(f"Filter hata: {e}")

        # ── Step 3: Pitch (batch — all hot leads) ──────────────────────
        self.log("Adım 3: Pitch (toplu teklif) çalışıyor...")
        pitched_leads = []
        try:
            from agents.pitch.agent import PitchAgent
            pitched_leads = PitchAgent().run_batch()
            results["agents"]["pitch"] = {
                "status": "ok",
                "summary": f"{len(pitched_leads)} hot lead için teklif oluşturuldu",
                "pitched": len(pitched_leads),
            }
            self.log(f"Pitch: {len(pitched_leads)} teklif hazırlandı")
        except Exception as e:
            results["agents"]["pitch"] = {"status": "error", "error": str(e)}
            self.log(f"Pitch hata: {e}")

        # ── Step 4: Outreach (pause all → send personalized emails) ────
        self.log("Adım 4: Outreach — kampanyalar durduruluyor, emailler gönderiliyor...")
        outreach_metrics = {"paused_campaigns": 0, "sent": 0, "failed": 0}
        if pitched_leads:
            try:
                from agents.outreach.agent import OutreachAgent
                outreach_metrics = OutreachAgent().send_personalized_all(
                    pitched_leads, agency, owner
                )
                results["agents"]["outreach"] = {
                    "status": "ok",
                    "summary": f"{outreach_metrics['sent']} email gönderildi, {outreach_metrics['paused_campaigns']} kampanya durduruldu",
                    "metrics": outreach_metrics,
                }
                self.log(f"Outreach: {outreach_metrics['sent']} email gönderildi")
            except Exception as e:
                results["agents"]["outreach"] = {"status": "error", "error": str(e)}
                self.log(f"Outreach hata: {e}")
        else:
            results["agents"]["outreach"] = {"status": "skipped", "summary": "Email için hot lead yok"}
            self.log("Outreach atlandı — email'li hot lead bulunamadı")

        # ── Summary ────────────────────────────────────────────────────
        steps_ok = sum(1 for a in results["agents"].values() if a.get("status") == "ok")
        results.update({
            "status": "ok",
            "summary": (
                f"Pipeline tamamlandı — "
                f"{results['agents'].get('scout', {}).get('metrics', {}).get('total_found', 0)} lead bulundu, "
                f"{len(pitched_leads)} teklif, "
                f"{outreach_metrics['sent']} email gönderildi"
            ),
            "metrics": {
                "pipeline_ran_at": datetime.now().isoformat(),
                "steps_completed": steps_ok,
                "steps_total": 4,
                "leads_found": results["agents"].get("scout", {}).get("metrics", {}).get("total_found", 0),
                "hot_leads": len(pitched_leads),
                "emails_sent": outreach_metrics["sent"],
                "campaigns_paused": outreach_metrics["paused_campaigns"],
            },
            "pipeline_status": "complete",
            "recommendations": [
                f"{outreach_metrics['sent']} email gönderildi — yanıtları takip et",
                "outreach.kenanturkoz.cloud üzerinden yanıtları gör",
                "Yarın pipeline otomatik tekrar çalışacak",
            ],
        })

        self.save_output("goat_pipeline_report.json", results)
        self.log("Pipeline tamamlandı.")
        return results
