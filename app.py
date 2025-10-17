import os
import logging
from fastapi import FastAPI, Request
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("railway-slack-check")

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")

if not SLACK_BOT_TOKEN or not SLACK_SIGNING_SECRET:
    raise RuntimeError("Missing SLACK_BOT_TOKEN or SLACK_SIGNING_SECRET")

# IMPORTANT: single-workspace mode (no installation_store / authorize)
bolt_app = AsyncApp(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
handler = AsyncSlackRequestHandler(bolt_app)

@bolt_app.command("/hello")
async def hello_cmd(ack, respond, command):
    await ack()
    name = (command.get("text") or "").strip() or "world"
    await respond(f"Hi, {name}! ✅ Railway + Slack are wired up.")

@bolt_app.event("app_mention")
async def on_mention(body, say):
    user = body.get("event", {}).get("user", "there")
    await say(f"👋 Hey <@{user}> — I’m alive on Railway!")

api = FastAPI()

@api.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("→ %s %s", request.method, request.url.path)
    try:
        resp = await call_next(request)
        logger.info("← %s %s %d", request.method, request.url.path, resp.status_code)
        return resp
    except Exception as e:
        logger.exception("✖ Error handling %s %s: %s", request.method, request.url.path, e)
        raise

@api.get("/")
async def root():
    return {"ok": True, "service": "railway-slack-check", "status": "up"}

@api.get("/up")
async def up():
    return {"ok": True}

@api.post("/slack/commands")
async def slack_commands(request: Request):
    return await handler.handle(request)

@api.post("/slack/events")
async def slack_events(request: Request):
    return await handler.handle(request)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app:api", host="0.0.0.0", port=port)
