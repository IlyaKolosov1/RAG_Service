# audit.py
from fastapi import FastAPI, Request
from pydantic import BaseModel
import json
import logging
from datetime import datetime
app = FastAPI()

logging.basicConfig(
    filename="system.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    encoding="utf-8"
)
logger = logging.getLogger("log_service")

@app.post("/log")
async def collect_log(record: Request):
    data = await record.json()  # получаем JSON как dict
    data["timestamp"] = datetime.now().isoformat()
    logger.info(json.dumps(data, ensure_ascii=False))
    return {"status": "ok"}
