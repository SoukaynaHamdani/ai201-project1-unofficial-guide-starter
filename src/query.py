"""
Milestone 4 - Step 2: RETRIEVAL  +  Milestone 5: GROUNDED GENERATION

retrieve(query, k)  -> top-k chunks with text, metadata, and cosine distance.
ask(query, k)       -> grounded answer from Groq + a programmatically-built
                       source list (attribution is guaranteed in code, not left
                       to the LLM to remember).

The vector store and embedding model load lazily and are cached, so importing
this module is cheap and retrieval works even without a Groq API key (only
ask() needs the key).

Env: put GROQ_API_KEY in a .env file (see .env.example).
"""

import os

import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

DB_PATH = "chroma_db"
COLLECTION = "berkeley_guide"
MODEL_NAME = "all-MiniLM-L6-v2"
GROQ_MODEL = "llama-3.3-70b-versatile"

# If even the closest chunk is farther than this (cosine distance), we treat the
# query as out-of-scope and don't fabricate context. Tunable after seeing results.
RELEVANCE_CUTOFF = 0.85

_model = None
_collection = None


def _load():
    """Lazily load the embedding model and ChromaDB collection (cached)."""
    global _model, _collection
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    if _collection is None:
        client = chromadb.PersistentClient(path=DB_PATH)
        _collection = client.get_collection(COLLECTION)
    return _model, _collection


def retrieve(query, k=4):
    """Return the top-k most similar chunks as dicts: text, metadata, distance."""
    model, coll = _load()
    q_emb = model.encode([query]).tolist()
    res = coll.query(query_embeddings=q_emb, n_results=k)
    results = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        results.append({"text": doc, "metadata": meta, "distance": dist})
    return results


# --------------------------------------------------------------------------- #
# Grounded generation
# --------------------------------------------------------------------------- #

SYSTEM_PROMPT = """You are an assistant for an Unofficial UC Berkeley Housing & \
Campus Survival Guide. Answer the user's question using ONLY the information in \
the provided context documents below. Follow these rules strictly:

1. Use only facts found in the context. Do NOT use outside or general knowledge.
2. If the context does not contain enough information to answer, reply exactly: \
"I don't have enough information on that."
3. When the context comes from a community source (Reddit/student opinion), present \
it as unverified student opinion, not established fact.
4. Be concise and specific. Do not speculate."""


def _build_context(chunks):
    """Format retrieved chunks into a labeled context block for the prompt."""
    blocks = []
    for i, c in enumerate(chunks, 1):
        m = c["metadata"]
        blocks.append(
            f"[Document {i} | source: {m['source_name']} | type: {m['source_type']}]\n"
            f"{c['text']}"
        )
    return "\n\n".join(blocks)


def _format_sources(chunks):
    """Unique, ordered source list built in code (guaranteed attribution)."""
    seen = set()
    sources = []
    for c in chunks:
        m = c["metadata"]
        label = f"{m['source_name']} ({m['url']})"
        if label not in seen:
            seen.add(label)
            sources.append(label)
    return sources


def ask(question, k=4):
    """Full RAG: retrieve -> ground -> generate. Returns answer, sources, chunks."""
    chunks = retrieve(question, k=k)

    # Out-of-scope guard: if nothing is close, decline without calling the LLM.
    relevant = [c for c in chunks if c["distance"] <= RELEVANCE_CUTOFF]
    if not relevant:
        return {
            "answer": "I don't have enough information on that.",
            "sources": [],
            "chunks": chunks,  # still returned so you can inspect why it missed
        }

    from groq import Groq  # imported here so retrieval works without the key
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or api_key == "your_key_here":
        raise SystemExit("GROQ_API_KEY not set. Copy .env.example to .env and add your key.")

    client = Groq(api_key=api_key)
    context = _build_context(relevant)
    user_msg = f"Context documents:\n\n{context}\n\nQuestion: {question}"

    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=0,  # deterministic, less prone to drifting off the context
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )
    answer = resp.choices[0].message.content.strip()
    return {
        "answer": answer,
        "sources": _format_sources(relevant),
        "chunks": relevant,
    }


if __name__ == "__main__":
    # Quick manual smoke test of retrieval (no LLM call)
    import sys
    q = " ".join(sys.argv[1:]) or "What are common rental scam red flags?"
    print(f"Query: {q}\n")
    for r in retrieve(q, k=4):
        print(f"[{r['distance']:.3f}] {r['metadata']['source_name']}")
        print("   " + r["text"][:200].replace("\n", " ") + "...\n")
