import hmac, io, json, os, uuid, glob
from html.parser import HTMLParser

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastembed import TextEmbedding
from groq import Groq
from pypdf import PdfReader
from qdrant_client import QdrantClient, models
import numpy as np

load_dotenv()
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
GUARD_MODEL = os.getenv("GUARD_MODEL", "openai/gpt-oss-20b")
ADMIN = os.getenv("ADMIN_TOKEN", "")
COL, TOP_K, CONFIDENT, MIN_SCORE = "cs_kb", 5, 0.62, 0.40

REFUSAL = ("This doesn't look like a technical question. I only answer questions about computer science "
           "and software development: programming, data structures & algorithms, OS, DBMS, networks, "
           "system design, web/backend/mobile, DevOps and similar topics. Try asking one of those.")

SYSTEM = """You are Bytewise, an expert assistant for computer science and software development.
Scope: programming languages, data structures, algorithms, complexity, operating systems, DBMS/SQL,
computer networks, OOP, design patterns, system design, compilers, computer architecture, web, backend,
mobile, DevOps/cloud, Git, testing, security, and AI/ML as it relates to software.
Rules:
- Give accurate, technical, well-structured answers in Markdown. Use fenced code blocks with language tags.
- State time/space complexity for algorithms. Show a short example when it helps.
- Use the provided CONTEXT when relevant; otherwise use your own knowledge. Prefer CONTEXT if they conflict.
- Never invent APIs or facts; say when you are unsure.
- If the question is not about computer science or software, reply only: "This is not a technical question." """

llm = Groq(api_key=os.environ["GROQ_API_KEY"])
embedder = TextEmbedding("BAAI/bge-small-en-v1.5", cache_dir="./models")
qc = (QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.getenv("QDRANT_API_KEY"))
      if os.getenv("QDRANT_URL") else QdrantClient(path="./qdrant_data"))

# ---------- knowledge base ----------
def embed(texts):
    v = np.array(list(embedder.embed(texts)), dtype="float32")
    return v / np.linalg.norm(v, axis=1, keepdims=True)

def chunk(text, size=900, overlap=150):
    out, cur = [], ""
    for p in (p.strip() for p in text.split("\n\n")):
        if not p:
            continue
        if len(cur) + len(p) > size and cur:
            out.append(cur)
            cur = cur[-overlap:] + "\n\n" + p
        else:
            cur = (cur + "\n\n" + p).strip()
    if cur:
        out.append(cur)
    return out

def delete_doc(doc):
    qc.delete(COL, points_selector=models.FilterSelector(filter=models.Filter(
        must=[models.FieldCondition(key="doc", match=models.MatchValue(value=doc))])))

def add_doc(doc, text):
    chunks = chunk(text)
    if not chunks:
        raise HTTPException(400, f"No text found in {doc}")
    delete_doc(doc)  # re-uploading the same name updates it
    vecs = embed(chunks)
    qc.upsert(COL, points=[models.PointStruct(id=str(uuid.uuid4()), vector=v.tolist(),
              payload={"doc": doc, "text": c}) for v, c in zip(vecs, chunks)])
    return len(chunks)

if not qc.collection_exists(COL):
    qc.create_collection(COL, vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE))
if qc.count(COL).count == 0:  # seed from ./data on first run
    for p in sorted(glob.glob("data/**/*.md", recursive=True) + glob.glob("data/**/*.txt", recursive=True)):
        add_doc(os.path.basename(p), open(p, encoding="utf-8").read())

def retrieve(q):
    vec = embed([q])[0].tolist()
    pts = qc.query_points(COL, query=vec, limit=TOP_K, with_payload=True).points
    return [(p.payload, p.score) for p in pts]

# ---------- topic guard ----------
def is_technical(msg, history):
    ctx = " | ".join(m.content[:200] for m in history[-2:])
    try:
        r = llm.chat.completions.create(
            model=GUARD_MODEL, temperature=0, max_tokens=400,
            extra_body={"reasoning_effort": "low"},
            messages=[
                {"role": "system", "content": "Classify the LAST user message. Answer TECH if it is about computer science, "
                 "programming, software development, IT/tech concepts, or is a follow-up to a technical conversation. "
                 "Answer OFF for anything else (general chat, politics, sports, cooking, medical, etc). Reply TECH or OFF only."},
                {"role": "user", "content": f"Recent conversation: {ctx or 'none'}\nLAST user message: {msg}"}])
        answer = (r.choices[0].message.content or "").strip().upper()
        return not answer.startswith("OFF")
    except Exception:
        return True

# ---------- API ----------
app = FastAPI(title="Bytewise RAG chatbot")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
                   allow_methods=["*"], allow_headers=["*"])

class Msg(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[Msg] = []

def auth(token):
    if not ADMIN:
        raise HTTPException(403, "Knowledge editing is disabled: set ADMIN_TOKEN on the server.")
    if not hmac.compare_digest(token or "", ADMIN):
        raise HTTPException(401, "Wrong admin token.")

@app.get("/")
def health():
    return {"status": "ok", "chunks": qc.count(COL).count}

@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    def ev(o):
        return json.dumps(o, ensure_ascii=False) + "\n"

    def gen():
        try:
            if not req.message.strip():
                return
            hits = retrieve(req.message)
            top = hits[0][1] if hits else 0
            if top < CONFIDENT and not is_technical(req.message, req.history):
                yield ev({"type": "refusal", "t": REFUSAL})
                return
            good = [(p, s) for p, s in hits if s >= MIN_SCORE]
            yield ev({"type": "sources", "items": [{"doc": p["doc"], "text": p["text"][:320]} for p, _ in good]})
            ctx = "\n\n---\n\n".join(f"[{p['doc']}]\n{p['text']}" for p, _ in good) or "No relevant context."
            msgs = [{"role": "system", "content": SYSTEM}]
            msgs += [m.model_dump() for m in req.history[-8:] if m.role in ("user", "assistant")]
            msgs.append({"role": "user", "content": f"CONTEXT:\n{ctx}\n\nQUESTION:\n{req.message}"})
            for c in llm.chat.completions.create(model=MODEL, messages=msgs, temperature=0.2,
                                                  max_tokens=4000, stream=True):
                t = c.choices[0].delta.content
                if t:
                    yield ev({"type": "token", "t": t})
        except Exception as e:
            yield ev({"type": "error", "t": f"Server error: {e}"})
        finally:
            yield ev({"type": "done"})
    return StreamingResponse(gen(), media_type="application/x-ndjson")

# ---------- knowledge base admin ----------
@app.get("/kb")
def kb_list():
    counts = {}
    offset = None
    while True:
        pts, offset = qc.scroll(COL, limit=500, offset=offset, with_payload=["doc"], with_vectors=False)
        for p in pts:
            counts[p.payload["doc"]] = counts.get(p.payload["doc"], 0) + 1
        if offset is None:
            break
    return [{"doc": d, "chunks": n} for d, n in sorted(counts.items())]

@app.post("/kb/upload")
def kb_upload(files: list[UploadFile] = File(...), x_admin_token: str = Header(None)):
    auth(x_admin_token)
    done = []
    for f in files:
        raw = f.file.read()
        if f.filename.lower().endswith(".pdf"):
            text = "\n\n".join((pg.extract_text() or "") for pg in PdfReader(io.BytesIO(raw)).pages)
        else:
            text = raw.decode("utf-8", errors="ignore")
        done.append({"doc": f.filename, "chunks": add_doc(f.filename, text)})
    return done

class TextIn(BaseModel):
    title: str
    text: str

@app.post("/kb/text")
def kb_text(b: TextIn, x_admin_token: str = Header(None)):
    auth(x_admin_token)
    return {"doc": b.title, "chunks": add_doc(b.title, b.text)}

class UrlIn(BaseModel):
    url: str

class _Text(HTMLParser):
    skip = {"script", "style", "nav", "footer", "header", "noscript"}
    def __init__(self):
        super().__init__(); self.out, self.depth = [], 0
    def handle_starttag(self, t, a):
        if t in self.skip: self.depth += 1
        if t in ("p", "div", "br", "li", "h1", "h2", "h3", "pre", "tr"): self.out.append("\n\n" if t in ("h1","h2","h3","p") else "\n")
    def handle_endtag(self, t):
        if t in self.skip and self.depth: self.depth -= 1
    def handle_data(self, d):
        if not self.depth: self.out.append(d)

@app.post("/kb/url")
def kb_url(b: UrlIn, x_admin_token: str = Header(None)):
    auth(x_admin_token)
    try:
        r = httpx.get(b.url, timeout=20, follow_redirects=True, headers={"User-Agent": "BytewiseBot/1.0"})
        r.raise_for_status()
    except Exception as e:
        raise HTTPException(400, f"Could not fetch URL: {e}")
    p = _Text(); p.feed(r.text)
    return {"doc": b.url, "chunks": add_doc(b.url, "".join(p.out))}

@app.delete("/kb")
def kb_delete(doc: str, x_admin_token: str = Header(None)):
    auth(x_admin_token)
    delete_doc(doc)
    return {"deleted": doc}