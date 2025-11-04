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
        year = "2015"

        if not date_str or date_str.lower() == "2015":
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
                year = "2015"

        year_counts[year] += 1

    return dict(sorted(year_counts.items()))


def classify_by_cause(data):
    """
    Robust classifier for accident causes.
    - If explicit 'Cause' (or 'cause') field exists, use it.
    - Else, inspect textual fields (Description, Narrative, Accident Details, Summary, Remarks)
      and classify using keyword heuristics.
    - Returns:
      {
        "counts": { category: int, ... },
        "examples": { category: [ {idx, snippet, full_record}, ... ] }
      }
    - If `llm` is configured and you want to force LLM-based classification, you can call
      the LLM branch by setting USE_LLM=True (not default).
    """
    # categories used previously
    categories = [
        "Fall of Roof",
        "Machinery Accident",
        "Explosion",
        "Electrical Accident",
        "Fire Incident",
        "Transportation Accident",
        "Other"
    ]

    # keyword -> category mapping (lowercase)
    keyword_map = {
        "fall of roof": "Fall of Roof",
        "roof fall": "Fall of Roof",
        "fall of side": "Fall of Roof",
        "slip": "Fall of Roof",
        "collapse": "Fall of Roof",
        "machine": "Machinery Accident",
        "machinery": "Machinery Accident",
        "crush": "Machinery Accident",
        "caught in": "Machinery Accident",
        "entangled": "Machinery Accident",
        "explosion": "Explosion",
        "blast": "Explosion",
        "gas": "Explosion",
        "electr": "Electrical Accident",   # matches electrical, electricity, etc
        "short circuit": "Electrical Accident",
        "fire": "Fire Incident",
        "burn": "Fire Incident",
        "transport": "Transportation Accident",
        "vehicle": "Transportation Accident",
        "truck": "Transportation Accident",
        "trolley": "Transportation Accident",
        "collision": "Transportation Accident",
        "diesel": "Machinery Accident",
        "compressor": "Machinery Accident",
        "fall from": "Fall of Roof",
        "fall": "Fall of Roof",
        "gas leak": "Explosion",
        "methane": "Explosion",
        "oxygen deficiency": "Explosion",
        "inrush": "Fall of Roof",
    }

    # helper to extract text content from a record
    def extract_text_fields(rec):
        texts = []
        for k in ("Cause", "cause", "Description", "description", "Narrative", "narrative", 
                  "Accident Details", "accident_details", "Summary", "summary", "Remarks", "remarks"):
            if k in rec and rec.get(k):
                texts.append(str(rec.get(k)))
        # also join all values as fallback
        if not texts:
            # small fallback: join a few fields
            for k in ("Details", "details", "Remarks", "remarks"):
                if k in rec and rec.get(k):
                    texts.append(str(rec.get(k)))
        return " ".join(texts).strip()

    counts = defaultdict(int)
    examples = {cat: [] for cat in categories}

    # Optionally use LLM if configured and desired (disabled by default)
    USE_LLM = False

    if USE_LLM and llm:
        # Build a small prompt to classify - but keep it limited to avoid rate limits
        # We'll call LLM on batches to get predicted categories, fallback to heuristic for failures
        try:
            # prepare a small JSON input with index and text snippet
            sample_payload = []
            for idx, rec in enumerate(data):
                txt = extract_text_fields(rec)
                sample_payload.append({"idx": idx, "text": txt[:1000]})
            prompt = f"""You are an expert mining safety analyst. Classify each record into one of these categories: {', '.join(categories)}.
            Return a JSON list of objects like: {{ "idx": <index>, "category": "<one of categories>" }}.
            Here are the records: {json.dumps(sample_payload)}"""
            resp = llm.complete(prompt)
            text = resp.text.strip()
            mapped = json.loads(text)
            # mapped = list of {idx, category}
            for m in mapped:
                idx = int(m.get("idx"))
                cat = m.get("category") or "Other"
                if cat not in categories:
                    cat = "Other"
                counts[cat] += 1
                if len(examples[cat]) < 6:
                    rec = data[idx]
                    snippet = extract_text_fields(rec)[:300]
                    examples[cat].append({"idx": idx, "snippet": snippet, "record": rec})
            return {"counts": dict(counts), "examples": examples}
        except Exception as e:
            # fallback to heuristic below
            print("LLM classification failed, falling back to heuristic:", e)

    # Heuristic (keyword-based) classification
    for idx, rec in enumerate(data):
        # prefer explicit Cause field if present and non-empty
        explicit = (rec.get("Cause") or rec.get("cause") or "").strip()
        assigned = None
        if explicit:
            # try to map explicit value to canonical categories (simple mapping)
            ex_lower = explicit.lower()
            # direct matches
            for cat in categories:
                if cat.lower() in ex_lower:
                    assigned = cat
                    break
            # some heuristics for common words
            if not assigned:
                if any(w in ex_lower for w in ("machin", "equip", "vehicle", "compressor", "diesel")):
                    assigned = "Machinery Accident"
                elif any(w in ex_lower for w in ("roof", "fall", "collapse", "inrush", "slip")):
                    assigned = "Fall of Roof"
                elif any(w in ex_lower for w in ("elect", "short", "circuit")):
                    assigned = "Electrical Accident"
                elif any(w in ex_lower for w in ("explosion", "blast", "gas", "methane", "leak")):
                    assigned = "Explosion"
                elif any(w in ex_lower for w in ("fire", "burn")):
                    assigned = "Fire Incident"
                elif any(w in ex_lower for w in ("transport", "vehic", "truck", "collision", "trolley")):
                    assigned = "Transportation Accident"
        # If not assigned yet, inspect text fields
        if not assigned:
            text = extract_text_fields(rec).lower()
            # check keyword map in order of specificity
            for kw, cat in keyword_map.items():
                if kw in text:
                    assigned = cat
                    break
        if not assigned:
            assigned = "Other"

        counts[assigned] += 1
        # keep a few representative examples per category
        if len(examples[assigned]) < 6:
            snippet = extract_text_fields(rec)[:300]
            examples[assigned].append({"idx": idx, "snippet": snippet, "record": rec})

    # convert counts to normal dict
    counts = dict(counts)
    print(examples)
    return {"counts": counts, "examples": examples}


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


@app.get("/classify_by_cause")
def api_cause():
    return {"data": classify_by_cause(data)}


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
