"""goat — Agency-in-a-Box Command Center"""

import importlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from agents import AGENTS, CATEGORIES

app = FastAPI(title="goat — Agency-in-a-Box")
BASE_DIR = Path(__file__).parent
scheduler = BackgroundScheduler(timezone="Europe/Istanbul")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

AGENT_MODULES = {
    "goat": "agents.goat.agent:GoatAgent",
    "scout": "agents.scout.agent:ScoutAgent",
    "filter": "agents.filter.agent:FilterAgent",
    "outreach": "agents.outreach.agent:OutreachAgent",
    "pitch": "agents.pitch.agent:PitchAgent",
    "mentor": "agents.mentor.agent:MentorAgent",
}

AGENT_RESULTS = {}


# ── Scheduler ─────────────────────────────────────────────────────────────────

def _run_auto_pipeline():
    """Background job: full goat pipeline."""
    try:
        agent = get_agent_instance("goat")
        result = agent.run()
        AGENT_RESULTS["goat"] = {
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "status": "auto",
        }
    except Exception as e:
        AGENT_RESULTS["goat"] = {
            "result": {"error": str(e)},
            "timestamp": datetime.now().isoformat(),
            "status": "error",
        }


def _setup_scheduler():
    """Read config and (re)schedule daily pipeline job."""
    cfg = load_config()
    scheduler.remove_all_jobs()
    if not cfg.get("auto_run_enabled"):
        return
    time_str = cfg.get("auto_run_time", "09:00")
    try:
        hour, minute = time_str.split(":")
        scheduler.add_job(
            _run_auto_pipeline,
            CronTrigger(hour=int(hour), minute=int(minute)),
            id="daily_pipeline",
            replace_existing=True,
        )
    except Exception:
        pass


@app.on_event("startup")
async def startup_event():
    scheduler.start()
    _setup_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown(wait=False)


# ── Scheduler status endpoint ──────────────────────────────────────────────────

@app.get("/api/scheduler/status")
async def scheduler_status():
    cfg = load_config()
    job = scheduler.get_job("daily_pipeline")
    return JSONResponse({
        "enabled": cfg.get("auto_run_enabled", False),
        "time": cfg.get("auto_run_time", "09:00"),
        "next_run": str(job.next_run_time) if job else None,
    })


def get_agent_instance(agent_id: str):
    module_path, class_name = AGENT_MODULES[agent_id].rsplit(":", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)()


def load_config():
    path = BASE_DIR / "data" / "config" / "user_profile.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def load_pipeline_stats():
    """Load stats from latest reports for the dashboard."""
    stats = {"leads_found": 0, "leads_qualified": 0, "hot": 0, "warm": 0, "cold": 0}
    reports_dir = BASE_DIR / "outputs" / "reports"

    scout_report = reports_dir / "scout_leads_report.json"
    if scout_report.exists():
        with open(scout_report) as f:
            data = json.load(f)
            stats["leads_found"] = data.get("metrics", {}).get("total_found", 0)

    filter_report = reports_dir / "filter_qualified_report.json"
    if filter_report.exists():
        with open(filter_report) as f:
            data = json.load(f)
            m = data.get("metrics", {})
            stats["leads_qualified"] = m.get("total_scored", 0)
            stats["hot"] = m.get("hot", 0)
            stats["warm"] = m.get("warm", 0)
            stats["cold"] = m.get("cold", 0)

    return stats


# --- Dashboard ---

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    config = load_config()
    stats = load_pipeline_stats()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "agents": AGENTS,
        "categories": CATEGORIES,
        "config": config,
        "stats": stats,
        "results": AGENT_RESULTS,
    })


# --- Agent Execution ---

@app.post("/api/agent/{agent_id}/run")
async def run_agent(agent_id: str, request: Request):
    if agent_id not in AGENT_MODULES:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    # Parse optional body params for Scout
    params = {}
    try:
        body = await request.json()
        params = body if isinstance(body, dict) else {}
    except Exception:
        pass

    # Inject config API keys into env for agents
    cfg = load_config()
    if cfg.get("instantly_api_key"):
        os.environ["INSTANTLY_API_KEY"] = cfg["instantly_api_key"]
    if cfg.get("apify_token"):
        os.environ["APIFY_TOKEN"] = cfg["apify_token"]
    if cfg.get("fal_key"):
        os.environ["FAL_KEY"] = cfg["fal_key"]

    try:
        agent = get_agent_instance(agent_id)
        if agent_id == "scout" and params:
            result = agent.run(
                query=params.get("query", ""),
                location=params.get("location", ""),
                limit=params.get("limit", 50),
            )
        else:
            result = agent.run()

        AGENT_RESULTS[agent_id] = {
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "status": "success",
        }
        return JSONResponse({"status": "ok", "agent": agent_id, "result": result})
    except Exception as e:
        AGENT_RESULTS[agent_id] = {
            "result": {"error": str(e)},
            "timestamp": datetime.now().isoformat(),
            "status": "error",
        }
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)


@app.post("/api/agents/run-pipeline")
async def run_pipeline():
    """Run the full pipeline: Scout → Filter → Pitch → Outreach."""
    agent = get_agent_instance("goat")
    result = agent.run()
    AGENT_RESULTS["goat"] = {
        "result": result,
        "timestamp": datetime.now().isoformat(),
        "status": "success",
    }
    return JSONResponse({"status": "ok", "result": result})


@app.post("/api/auto-run")
async def trigger_auto_run():
    """Manually trigger the full automated pipeline (same as scheduled job)."""
    import threading
    t = threading.Thread(target=_run_auto_pipeline, daemon=True)
    t.start()
    return JSONResponse({"status": "started", "message": "Pipeline arka planda çalışıyor"})


@app.get("/api/agent/{agent_id}/result")
async def get_agent_result(agent_id: str):
    if agent_id in AGENT_RESULTS:
        return JSONResponse(AGENT_RESULTS[agent_id])
    return JSONResponse({"status": "not_run"})


# --- Leads ---

@app.get("/api/leads")
async def get_leads():
    """Get all raw leads from latest scrape."""
    raw_dir = BASE_DIR / "data" / "leads" / "raw"
    if not raw_dir.exists():
        return JSONResponse([])
    files = sorted(raw_dir.glob("*.json"), reverse=True)
    if files:
        with open(files[0]) as f:
            data = json.load(f)
            return JSONResponse(data.get("leads", []))
    return JSONResponse([])


@app.get("/api/leads/qualified")
async def get_qualified_leads():
    """Get latest qualified/scored leads."""
    qual_dir = BASE_DIR / "data" / "leads" / "qualified"
    if not qual_dir.exists():
        return JSONResponse([])
    files = sorted(qual_dir.glob("*.json"), reverse=True)
    if files:
        with open(files[0]) as f:
            data = json.load(f)
            return JSONResponse(data.get("leads", []))
    return JSONResponse([])


# --- Chat ---

@app.post("/api/chat")
async def chat_with_agent(request: Request):
    """Chat with an agent. Mentor uses Claude CLI, others use context-based responses."""
    body = await request.json()
    message = body.get("message", "")
    agent_id = body.get("agent_id", "mentor")
    agent_info = AGENTS.get(agent_id, {})

    # Mentor has its own answer method
    if agent_id == "mentor":
        try:
            agent = get_agent_instance("mentor")
            response = agent.answer(message)
            return JSONResponse({"response": response, "agent": agent_id})
        except Exception as e:
            return JSONResponse({"response": f"Mentor error: {e}", "agent": agent_id})

    # For other agents, try Claude CLI with context
    agent_data = ""
    if agent_id in AGENT_RESULTS:
        r = AGENT_RESULTS[agent_id]["result"]
        agent_data = f"\nLatest data: {r.get('summary', '')}\nMetrics: {json.dumps(r.get('metrics', {}), default=str)}"

    config = load_config()
    agency_info = ""
    if config:
        agency_info = f"\nUser's agency: {config.get('agency_name', '')} | Niche: {config.get('niche', '')} | Location: {', '.join(config.get('target_cities', []))}"

    # goat orchestrator gets context about all agents
    goat_extra = ""
    if agent_id == "goat":
        agent_list = "\n".join([f"- {k}: {v['name']} ({v['role']})" for k, v in AGENTS.items()])
        available_results = "\n".join([f"- {k}: {v['result'].get('summary', 'done')}" for k, v in list(AGENT_RESULTS.items())[:10]])
        goat_extra = f"\n\nYou are the master orchestrator. Agents:\n{agent_list}\n\nResults:\n{available_results or 'No agents run yet.'}"

    prompt = f"""You are {agent_info.get('name', agent_id)}, an AI agent for goat (agency-in-a-box platform).
Your role: {agent_info.get('role', '')}
{agency_info}{goat_extra}{agent_data}

Be concise, actionable, specific. Answer in the same language as the user's message.

User: {message}"""

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "text"],
            capture_output=True, text=True, timeout=120,
            cwd=str(BASE_DIR),
        )
        response = result.stdout.strip() if result.stdout else f"[{agent_info.get('name', agent_id)}] Run the agent first to populate data."
        return JSONResponse({"response": response, "agent": agent_id})
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # No Claude CLI — return contextual fallback
        if agent_id in AGENT_RESULTS:
            r = AGENT_RESULTS[agent_id]["result"]
            return JSONResponse({
                "response": f"**{agent_info.get('name', agent_id)}** — {r.get('summary', 'Ready.')}\n\n"
                            + "\n".join(f"- {rec}" for rec in r.get("recommendations", [])),
                "agent": agent_id,
            })
        return JSONResponse({
            "response": f"**{agent_info.get('name', agent_id)}** ready. Hit RUN first to generate data.",
            "agent": agent_id,
        })


# --- Config ---

@app.get("/api/config")
async def get_config():
    return JSONResponse(load_config())


@app.post("/api/config")
async def save_config(request: Request):
    body = await request.json()
    config_dir = BASE_DIR / "data" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "user_profile.json"
    with open(config_path, "w") as f:
        json.dump(body, f, indent=2, ensure_ascii=False)
    _setup_scheduler()  # apply new auto_run_time / auto_run_enabled immediately
    return JSONResponse({"status": "saved"})


@app.post("/api/creative")
async def generate_creative(request: Request):
    """Generate an ad creative or social media image via fal.ai."""
    body = await request.json()
    business_type = body.get("business_type", "business")
    creative_type = body.get("type", "ad")

    # Inject fal key
    cfg = load_config()
    if cfg.get("fal_key"):
        os.environ["FAL_KEY"] = cfg["fal_key"]

    from services.image import generate_ad_creative, generate_social_example

    if creative_type == "social":
        path = generate_social_example(business_type)
    else:
        path = generate_ad_creative(business_type, business_type, "otomasyon")

    if path:
        return JSONResponse({"status": "ok", "path": path})
    return JSONResponse({"status": "error", "path": None})


@app.post("/api/reset")
async def reset_all():
    """Reset everything — delete config, leads, reports, campaigns."""
    import shutil
    global AGENT_RESULTS
    AGENT_RESULTS = {}

    # Delete data files
    for sub in ["config", "leads/raw", "leads/qualified", "campaigns", "proposals"]:
        p = BASE_DIR / "data" / sub
        if p.exists():
            shutil.rmtree(p)
            p.mkdir(parents=True, exist_ok=True)

    # Delete reports
    reports = BASE_DIR / "outputs" / "reports"
    if reports.exists():
        shutil.rmtree(reports)
        reports.mkdir(parents=True, exist_ok=True)

    return JSONResponse({"status": "reset"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7778)
