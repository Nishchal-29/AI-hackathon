# build_index.py
"""
Build Pinecone index from CSV (one chunk per CSV row by default).
Functions:
  - build_index(csv_path=None, chunk_per_n_rows=1, force_recreate=False)
Usage:
  import build_index
  build_index.build_index("/mnt/data/dgms_accidents.csv", chunk_per_n_rows=1)
"""
import os
import time
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

# Config via env
class C:
    CSV_PATH = os.getenv("CSV_PATH", "/home/devcontainers/ai-hackathon-cl/data/dgms_accidents.csv")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_ENV = os.getenv("PINECONE_ENV")
    PINECONE_INDEX = os.getenv("PINECONE_INDEX", "mine-stats")
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "64"))
    DIMENSION = 384

# Imports (install packages if missing)
import pandas as pd
from sentence_transformers import SentenceTransformer
import pinecone
from pinecone import Pinecone, ServerlessSpec
from pinecone.exceptions import PineconeApiException

# ---------- Helper classes ----------
class Embedder:
    def __init__(self, model_name=C.EMBEDDING_MODEL):
        print("Loading embedding model:", model_name)
        self.model = SentenceTransformer(model_name)
        dim = self.model.get_sentence_embedding_dimension()
        if dim != C.DIMENSION:
            print(f"Adjusting expected dimension from {C.DIMENSION} -> {dim}")
            C.DIMENSION = dim
        print("Embedding model ready. dim =", C.DIMENSION)

    def embed_batch(self, texts: List[str], batch_size: int = C.BATCH_SIZE) -> List[List[float]]:
        out = []
        n = len(texts)
        for i in range(0, n, batch_size):
            batch = texts[i:i+batch_size]
            emb = self.model.encode(batch, convert_to_tensor=False, show_progress_bar=False)
            out.extend([list(map(float, e)) for e in emb])
            print(f"  embedded {min(i+batch_size,n)}/{n}", end="\r")
        print()
        return out

# Robust Pinecone wrapper that handles existing indexes and force-recreate option.
class PineconeStore:
    def __init__(self, api_key: str, environment: str, index_name: str, dimension: int, force_recreate: bool=False):
        if not api_key:
            raise ValueError("PINECONE_API_KEY missing in environment.")
        if not index_name or not index_name.strip():
            raise ValueError("PINECONE_INDEX is empty. Set PINECONE_INDEX env var.")

        index_name = index_name.strip()
        self.pc = Pinecone(api_key=api_key)
        self.index_name = index_name
        self.dimension = dimension

        try:
            existing = self.pc.list_indexes()
            print("Existing Pinecone indexes:", existing)
        except Exception as e:
            raise RuntimeError("Could not list Pinecone indexes: " + str(e))

        if force_recreate and (index_name in existing):
            print(f"force_recreate=True: deleting index {index_name} ...")
            try:
                self.pc.delete_index(name=index_name)
                time.sleep(3)
                existing = [ix for ix in existing if ix != index_name]
            except Exception as e:
                print("Warning: delete failed:", e)

        if index_name not in existing:
            print(f"Creating index '{index_name}' dim={dimension} ...")
            try:
                self.pc.create_index(
                    name=index_name,
                    dimension=dimension,
                    metric="cosine",
                    spec=ServerlessSpec(cloud='aws', region=environment)
                )
                time.sleep(3)
            except PineconeApiException as pex:
                # handle ALREADY_EXISTS gracefully
                print("PineconeApiException while creating index:", pex)
                existing = self.pc.list_indexes()
                if index_name not in existing:
                    raise
                else:
                    print("Index appeared after exception; continuing.")
            except Exception as e:
                print("Unexpected exception creating index:", e)
                raise
        else:
            print(f"Index '{index_name}' exists; skipping creation.")

        self.index = self.pc.Index(index_name)
        print("Connected to Pinecone index:", index_name)

    def upsert(self, ids: List[str], embeddings: List[List[float]], metadatas: List[Dict], namespace: str=""):
        assert len(ids) == len(embeddings) == len(metadatas)
        batch = 100
        for i in range(0, len(ids), batch):
            chunk_ids = ids[i:i+batch]
            chunk_emb = embeddings[i:i+batch]
            chunk_meta = metadatas[i:i+batch]
            to_upsert = [(chunk_ids[j], chunk_emb[j], chunk_meta[j]) for j in range(len(chunk_ids))]
            self.index.upsert(vectors=to_upsert, namespace=namespace)
            print(f"Upserted {i+len(chunk_ids)}/{len(ids)}")

# ---------- CSV -> chunks ----------
def load_csv(csv_path: str):
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, na_values=[''])
    df = df.fillna("")
    rows = df.to_dict(orient="records")
    return df, rows

def row_to_text(row: Dict[str,str], columns=None):
    if columns is None:
        columns = list(row.keys())
    parts = []
    for c in columns:
        v = str(row.get(c, "")).strip()
        if v:
            parts.append(f"{c}: {v}")
    return "\n".join(parts)

def build_index(csv_path: str = None, chunk_per_n_rows: int = 1, force_recreate: bool = False, namespace: str = ""):
    csv_path = csv_path or C.CSV_PATH
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    print("Loading CSV:", csv_path)
    df, rows = load_csv(csv_path)

    # build chunks
    chunks = []
    if chunk_per_n_rows <= 1:
        for i, r in enumerate(rows):
            txt = row_to_text(r)
            meta = dict(r)
            meta["row_index"] = i
            meta["source_csv"] = os.path.basename(csv_path)
            chunks.append({"id": f"row_{i}", "text": txt, "metadata": meta})
    else:
        for i in range(0, len(rows), chunk_per_n_rows):
            group = rows[i:i+chunk_per_n_rows]
            txts = [row_to_text(r) for r in group]
            text = "\n\n".join(txts)
            meta = {"row_indexes": list(range(i, min(i+chunk_per_n_rows, len(rows)))), "source_csv": os.path.basename(csv_path)}
            chunks.append({"id": f"rows_{i}_{min(i+chunk_per_n_rows,len(rows))-1}", "text": text, "metadata": meta})

    print(f"Created {len(chunks)} chunks")

    # embed
    embedder = Embedder()
    texts = [c["text"] for c in chunks]
    embeddings = embedder.embed_batch(texts)

    # init pinecone and upsert
    pine = PineconeStore(api_key=C.PINECONE_API_KEY, environment=C.PINECONE_ENV, index_name=C.PINECONE_INDEX,
                        dimension=C.DIMENSION, force_recreate=force_recreate)
    ids = [c["id"] for c in chunks]
    metas = [c["metadata"] for c in chunks]
    print("Upserting vectors...")
    pine.upsert(ids, embeddings, metas, namespace=namespace)
    print("Index build complete.")

# Allow running directly for quick test when executing file
if __name__ == "__main__":
    # basic run with defaults (no argparse)
    build_index(csv_path=os.getenv("CSV_PATH", C.CSV_PATH),
                chunk_per_n_rows=1,
                force_recreate=False,
                namespace=os.getenv("PINECONE_NAMESPACE", ""))
