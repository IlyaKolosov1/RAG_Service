from fastapi import FastAPI
from pydantic import BaseModel
import requests, os

app = FastAPI()

AUDIT_URL = os.getenv("AUDIT_URL", "http://audit:8000/log")
VALIDATOR_URL = os.getenv("VALIDATOR_URL", "http://moderator:8000/validate")
RAG_URL = os.getenv("RAG_URL", "http://rag:8000/query")
LLM_URL = os.getenv("LLM_URL", "http://agent:8000/ask")


class Request(BaseModel):
    user_id: str
    text: str


@app.post("/process")
def handle(req: Request):
    # 1. Логируем факт обращения
    requests.post(AUDIT_URL, json={"user": req.user_id, "event": "request", "text": req.text})

    # 2. Валидация (модерация)
    res = requests.post(VALIDATOR_URL, json={"text": req.text}).json()
    if not res.get("allowed", True):
        requests.post(AUDIT_URL, json={"user": req.user_id, "event": "blocked", "risk": res.get("risk")})
        return {"error": f"Запрос отклонён: {res.get('risk')}"}

    # 3. Получаем контекст от RAG
    ctx = requests.post(RAG_URL, json={"text": req.text}).json().get("context", "")

    # 4. Спрашиваем у LLM-агента
    answer = requests.post(LLM_URL, json={"text": req.text, "context": ctx}).json().get("answer")

    # 5. Логируем ответ
    requests.post(AUDIT_URL, json={
        "user": req.user_id,
        "event": "response",
        "answer": answer,
        "risk": res.get("risk", 0.0)
    })

    return {"answer": answer}
