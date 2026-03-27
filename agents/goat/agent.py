"""goat — Master Orchestrator Agent

Runs the full pipeline: Scout → Filter.
Routes chat messages to the right agent.
"""

from datetime import datetime

from agents.base import BaseAgent


class GoatAgent(BaseAgent):
    agent_id = "goat"
    name = "goat"
    role = "Master orchestrator — runs the full pipeline"
    category = "master"

    def run(self) -> dict:
        """Run the full acquisition pipeline: Scout → Filter."""
        self.log("Starting goat pipeline...")
        results = {"agents": {}, "pipeline_status": "running"}

        # Step 1: Scout
        self.log("Step 1: Running Scout...")
        try:
            from agents.scout.agent import ScoutAgent
            scout = ScoutAgent()
            scout_result = scout.run()
            results["agents"]["scout"] = {
                "status": scout_result.get("status"),
                "summary": scout_result.get("summary"),
            }
            self.log(f"Scout: {scout_result.get('summary', 'done')}")
        except Exception as e:
            results["agents"]["scout"] = {"status": "error", "error": str(e)}
            self.log(f"Scout failed: {e}")

        # Step 2: Filter
        self.log("Step 2: Running Filter...")
        try:
            from agents.filter.agent import FilterAgent
            filt = FilterAgent()
            filter_result = filt.run()
            results["agents"]["filter"] = {
                "status": filter_result.get("status"),
                "summary": filter_result.get("summary"),
            }
            self.log(f"Filter: {filter_result.get('summary', 'done')}")
        except Exception as e:
            results["agents"]["filter"] = {"status": "error", "error": str(e)}
            self.log(f"Filter failed: {e}")

        # Build summary
        scout_summary = results["agents"].get("scout", {}).get("summary", "not run")
        filter_summary = results["agents"].get("filter", {}).get("summary", "not run")

        results.update({
            "status": "ok",
            "summary": f"Pipeline complete — Scout: {scout_summary} | Filter: {filter_summary}",
            "metrics": {
                "pipeline_ran_at": datetime.now().isoformat(),
                "steps_completed": sum(1 for a in results["agents"].values() if a.get("status") == "ok"),
                "steps_total": 2,
            },
            "pipeline_status": "complete",
            "recommendations": [
                "Puanlanan leadleri incele",
                "Sıcak leadlere ulaşmaya başla",
                "Mentora sor: 'Soğuk email nasıl yazılır?'",
            ],
        })

        self.save_output("goat_pipeline_report.json", results)
        self.log("Pipeline complete")
        return results
