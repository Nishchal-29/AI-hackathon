# query_bot.py
"""
Query the Pinecone index and generate an answer with Gemini.
Functions:
  - answer_question(question: str, top_k: int = 6) -> str
Usage:
  import query_bot
  query_bot.answer_question("How many fatal accidents in 2015?")
"""
import os
from dotenv import load_dotenv
load_dotenv()

# Config
class Cq:
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_ENV = os.getenv("PINECONE_ENV")
    PINECONE_INDEX = os.getenv("PINECONE_INDEX", "mine-stats")
    TOP_K = int(os.getenv("TOP_K", "43"))
    DIMENSION = 384

# Imports
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
import google.generativeai as genai
import pinecone
import time

# init gemini for generation (embeddings are local)
if Cq.GEMINI_API_KEY:
    genai.configure(api_key=Cq.GEMINI_API_KEY)

# embedder (same model)
class EmbedderQ:
    def __init__(self, model_name=Cq.EMBEDDING_MODEL):
        print("Loading embedder:", model_name)
        self.model = SentenceTransformer(model_name)
        dim = self.model.get_sentence_embedding_dimension()
        if dim != Cq.DIMENSION:
            print("Adjusting dimension", dim)
            Cq.DIMENSION = dim

    def embed(self, text: str):
        return list(map(float, self.model.encode([text], convert_to_tensor=False)[0]))

# Pinecone connector
class PineconeReader:
    def __init__(self, api_key, environment, index_name):
        if not api_key:
            raise ValueError("PINECONE_API_KEY missing.")
        self.pc = Pinecone(api_key=api_key)
        self.index_name = index_name
        self.index = self.pc.Index(index_name)
        print("Connected to Pinecone index:", index_name)

    def query(self, vector, top_k=6, namespace=""):
        res = self.index.query(vector=vector, top_k=top_k, include_metadata=True, namespace=namespace)
        # Pinecone may return matches under res["matches"] or different structure
        matches = res.get("matches") or res.get("results") or []
        # Normalize
        out = []
        for m in matches:
            out.append({
                "id": m.get("id"),
                "score": m.get("score") or m.get("similarity"),
                "metadata": m.get("metadata") or {}
            })
        return out

# Build the Gemini prompt from retrieved rows
def build_prompt(question: str, retrieved: list):
    context_pieces = []
    for r in retrieved:
        meta = r.get("metadata", {})
        # prefer flattened text if available
        if "text" in meta and isinstance(meta["text"], str):
            snippet = meta["text"][:1500]
        else:
            kvs = []
            for k,v in meta.items():
                kvs.append(f"{k}: {v}")
            snippet = "; ".join(kvs)[:1500]
        src = meta.get("source_csv", meta.get("source", "csv"))
        idx = meta.get("row_index", meta.get("row_indexes", meta.get("id", "?")))
        context_pieces.append(f"[Source:{src} id:{idx}]\n{snippet}")
    context = "\n\n".join(context_pieces)
    prompt = f"""You are an expert analyst of mine safety statistics using only the retrieved CSV rows below.
Context:
{context}

Question: {question}

Instructions:
- Answer using ONLY facts found in the context above.
- If the exact answer is not present, say: "Not available in retrieved reports."
- Cite explanations of each row in a detailed manner using your own brain where you reference a row and explain about that also. But don't include any row id or id about that row as it should be given in a good format to the user, so maintain that.
- Do not include any name of source or row id
Answer:"""
    return prompt

def answer_question(question: str, top_k: int = Cq.TOP_K, namespace: str = "") -> str:
    # embed query
    embedder = EmbedderQ()
    q_emb = embedder.embed(question)

    # connect to pinecone
    reader = PineconeReader(api_key=Cq.PINECONE_API_KEY, environment=Cq.PINECONE_ENV, index_name=Cq.PINECONE_INDEX)
    matches = reader.query(q_emb, top_k=top_k, namespace=namespace)

    # prepare prompt and call Gemini
    prompt = build_prompt(question, matches)
    if not Cq.GEMINI_API_KEY:
        # If Gemini key missing, return the retrieved matches as fallback
        return {"error":"GEMINI_API_KEY missing", "retrieved": matches}

    model = genai.GenerativeModel(os.getenv("GENERATION_MODEL", "gemini-2.5-flash"))
    response = model.generate_content(prompt)
    text = getattr(response, "text", None)
    if text is None:
        try:
            text = response.candidates[0].content[0].text
        except Exception:
            text = str(response)
    return text

if __name__ == "__main__":
    demo_q = "Which state had most number of accidents and how much ?"
    print("Question:", demo_q)
    ans = answer_question(demo_q, top_k=Cq.TOP_K, namespace=os.getenv("PINECONE_NAMESPACE",""))
    print("Answer:\n", ans)
