# app_with_rag.py
import json
import os
import traceback
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any, Dict

# Llama index / Gemini import from your original file
from llama_index.llms.google_genai import GoogleGenAI
# from llama_index.llms.gemini import Gemini

# Load environment
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Initialize LLM wrapper (same variable name as original)
llm = None
if GOOGLE_API_KEY:
    llm = GoogleGenAI(model="gemini-2.5-flash", api_key=GOOGLE_API_KEY)

# -----------------------------------------------------
# Load dataset (original)
# -----------------------------------------------------
with open("dgms.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# -----------------------------------------------------
# Try import of build_index and query_bot modules (RAG)
# -----------------------------------------------------
try:
    import build_index
    _build_index_err = None
except Exception as e:
    build_index = None
    _build_index_err = str(e)

try:
    import query_bot
    _query_bot_err = None
except Exception as e:
    query_bot = None
    _query_bot_err = str(e)

# -----------------------------------------------------
# Initialize FastAPI app (original)
# -----------------------------------------------------
app = FastAPI(title="DGMS Accident Data Classifier + RAG")

# Enable CORS for frontend (React on localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------
# Helper functions (original)
# -----------------------------------------------------
def classify_by_state(data):
    """Return accidents grouped by state."""
    state_counts = defaultdict(int)
    for item in data:
        state = item.get("State") or item.get("state") or "Unknown"
        state_counts[state] += 1
    return dict(state_counts)


def classify_by_year(data):
    """Return accidents grouped by year (handles '16/05/15' etc)."""
    year_counts = defaultdict(int)

    for item in data:
        date_str = str(item.get("Date") or item.get("date") or "").strip()
        year = "Unknown"

        if not date_str or date_str.lower() == "unknown":
            year_counts[year] += 1
            continue

        try:
            # Try formats: DD/MM/YY, DD-MM-YYYY, YYYY/MM/DD
            if "-" in date_str and len(date_str.split("-")[-1]) == 4:
                date_obj = datetime.strptime(date_str, "%d-%m-%Y")
            elif "/" in date_str and len(date_str.split("/")[-1]) == 2:
                date_obj = datetime.strptime(date_str, "%d/%m/%y")
            elif "/" in date_str and len(date_str.split("/")[-1]) == 4:
                date_obj = datetime.strptime(date_str, "%Y/%m/%d")
            else:
                raise ValueError("Unrecognized format")
            
            year = str(date_obj.year)

        except Exception:
            parts = [p for p in date_str.replace("-", "/").split("/") if p.isdigit()]
            if parts and len(parts[-1]) in (2, 4):
                yy = int(parts[-1])
                year = str(2000 + yy) if yy < 50 else str(1900 + yy)
            else:
                year = "Unknown"

        year_counts[year] += 1

    return dict(sorted(year_counts.items()))


def classify_by_cause(data):
    """
    Use Gemini to classify accidents by cause (from Description text).
    Fallback to dataset's 'Cause' field if no Gemini key available.
    """
    # If Gemini is not configured, fallback to manual field-based counting
    if not llm:
        cause_counts = defaultdict(int)
        for item in data:
            cause = item.get("Cause") or item.get("cause") or "Unknown"
            cause_counts[cause] += 1
        return dict(cause_counts)

    # Predefined cause categories for Gemini classification
    cause_labels = [
        "Fall of Roof",
        "Machinery Accident",
        "Explosion",
        "Electrical Accident",
        "Fire Incident",
        "Transportation Accident",
        "Other"
    ]

    # Limit sample size for efficiency

    prompt = f"""
    You are a mining accident analysis expert.
    Given the following accident records, classify each accident by its CAUSE using these categories:
    {', '.join(cause_labels)}.

    Return the result as a JSON object where each key is a cause and each value is the count.

    Here are the records:
    {json.dumps(data, indent=2)}
    """
    try:
        response = llm.complete(prompt)
        text = response.text.strip()
        result = json.loads(text)
        return result
    except Exception as e:
        print("⚠️ Gemini classification failed:", e)
        return {"error": "Gemini classification failed", "fallback": True}


def classify_by_district(data):
    """Return nested data: {state: {district: count}}"""
    district_data = defaultdict(lambda: defaultdict(int))
    for item in data:
        state = item.get("State") or "Unknown"
        district = item.get("District") or "Unknown"
        district_data[state][district] += 1
    return {k: dict(v) for k, v in district_data.items()}


# -----------------------------------------------------
# Original API Endpoints (unchanged)
# -----------------------------------------------------
@app.get("/")
def root():
    return {"message": "DGMS Accident Classification API is running 🚀"}


@app.get("/classify_by_state")
def api_state():
    return {"data": classify_by_state(data)}


@app.get("/classify_by_year")
def api_year():
    return {"data": classify_by_year(data)}


# @app.get("/classify_by_cause")
# def api_cause():
#     return {"data": classify_by_cause(data)}


@app.get("/classify_by_district")
def api_district():
    return {"data": classify_by_district(data)}


# -----------------------------------------------------
# New: RAG-related models and endpoints (do not remove original endpoints)
# -----------------------------------------------------
class BuildIndexRequest(BaseModel):
    csv_path: Optional[str] = None
    chunk_per_n_rows: Optional[int] = 1
    force_recreate: Optional[bool] = False
    namespace: Optional[str] = ""


class QueryRAGRequest(BaseModel):
    question: str
    top_k: Optional[int] = 6
    namespace: Optional[str] = ""


@app.get("/health")
def health():
    msgs = []
    ok = True
    if build_index is None:
        ok = False
        msgs.append(f"build_index module missing: {_build_index_err}")
    if query_bot is None:
        ok = False
        msgs.append(f"query_bot module missing: {_query_bot_err}")
    return {"ok": ok, "messages": msgs}


@app.post("/build-index")
def build_index_endpoint(req: BuildIndexRequest):
    """
    Trigger building (or updating) the Pinecone index from a CSV file.
    - csv_path: path to CSV on server (optional, default set via env)
    - chunk_per_n_rows: how many rows to combine per chunk (default 1)
    - force_recreate: if True, attempt to delete and recreate the index
    - namespace: Pinecone namespace (optional)
    """
    if build_index is None:
        raise HTTPException(status_code=500, detail=f"build_index module not available: {_build_index_err}")

    csv_path = req.csv_path or os.getenv("CSV_PATH", "/mnt/data/dgms_accidents.csv")
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=400, detail=f"CSV not found: {csv_path}")

    try:
        # call the build_index function from build_index.py
        build_index.build_index(csv_path=csv_path,
                                chunk_per_n_rows=req.chunk_per_n_rows or 1,
                                force_recreate=bool(req.force_recreate),
                                namespace=req.namespace or "")
        return {"status": "ok", "message": f"Index build triggered for {csv_path}"}
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Failed to build index: {e}\n{tb}")


@app.post("/query-rag")
def query_rag_endpoint(req: QueryRAGRequest):
    """
    Query the RAG index and generate an answer using Gemini.
    - question: the natural language question
    - top_k: number of retrieved rows to pass to generator
    - namespace: Pinecone namespace (optional)
    """
    if query_bot is None:
        raise HTTPException(status_code=500, detail=f"query_bot module not available: {_query_bot_err}")

    question = (req.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        # call query_bot.answer_question which returns a text answer (or fallback dict)
        answer = query_bot.answer_question(question, top_k=req.top_k or 6, namespace=req.namespace or "")
        return {"status": "ok", "question": question, "answer": answer}
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Query failed: {e}\n{tb}")


# -----------------------------------------------------
# Keep original module behaviour for direct run
# -----------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    print("Starting DGMS API with RAG endpoints on http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
