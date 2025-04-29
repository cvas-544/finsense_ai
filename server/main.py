from fastapi import FastAPI
from server.notion_webhook import router as webhook_router

app = FastAPI()

@app.get("/")
def healthcheck():
    return {"status": "ok"}

# Mount all webhook routes under /notion-webhook
app.include_router(webhook_router, prefix="/notion-webhook")