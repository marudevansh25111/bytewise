# Bytewise

**Your CS & coding buddy.** Bytewise is an AI chatbot that answers technical questions about computer science and software development. It uses a free LLM and Retrieval-Augmented Generation (RAG), so you can keep teaching it new material by uploading documents.

Powered by **AMAY TechLab**.

## Features

- **Technical answers only.** Covers programming languages, data structures and algorithms, operating systems, databases, networks, system design, web and backend development, and more. Off-topic questions get a clear "not a technical question" notice.
- **RAG knowledge base.** Upload `.md`, `.txt` or `.pdf` files, paste text, or add a web page by URL. New content is used from the very next question.
- **Streaming answers** with syntax-highlighted code, a Copy button on every code block, and a Stop button.
- **Interactive UI.** Animated mascot, chat history with search, rename and undo-delete, command palette (`Ctrl/Cmd + K`), dark and light modes, three accent colours, Markdown export, voice input in supported browsers, and 👍/👎 feedback.
- **Responsive.** Works on phones, tablets, laptops and large monitors.
- **Private by design.** Chats are stored only in each visitor's own browser. The server keeps no conversations.
- **Free to run.** Every service used has a free plan.

## Tech stack

| Layer | Technology |
|---|---|
| LLM | Groq API with `openai/gpt-oss-120b` (answers) and `openai/gpt-oss-20b` (topic guard) |
| Embeddings | `fastembed` with `BAAI/bge-small-en-v1.5` (runs on CPU) |
| Vector database | Qdrant (local folder in development, Qdrant Cloud in production) |
| Backend | Python 3.11, FastAPI, Uvicorn |
| Frontend | Plain HTML, CSS and JavaScript, with marked, DOMPurify and highlight.js |

## How it works

```
Browser (Vercel)  ──question──▶  FastAPI (Render)
                                   │
                                   ├─ 1. Embed the question, search Qdrant for the closest passages
                                   ├─ 2. Topic guard: is it a technical question? (skipped if retrieval is confident)
                                   │       └─ no  → return the "not a technical question" notice
                                   ├─ 3. Send question + retrieved context + recent chat to the LLM (Groq)
                                   └─ 4. Stream the answer and the sources back to the browser
```

## Project structure

```
cs-chatbot/
├── backend/
│   ├── app.py              # FastAPI app: chat, topic guard, RAG, knowledge-base API
│   ├── requirements.txt
│   ├── .env.example        # template for your secrets (copy to .env)
│   └── data/               # starter knowledge files, indexed on first run
├── frontend/
│   ├── index.html          # the whole UI (set the API URL near the top of the script)
│   ├── bytewise-logo.png
│   ├── favicon.png
│   ├── apple-touch-icon.png
│   └── amay-logo.png
├── .gitignore
└── README.md
```

## Run it locally

You need Python 3.11 (3.12 also works; very new versions such as 3.13+ may fail to install `fastembed`) and a free Groq API key from [console.groq.com](https://console.groq.com).

```bash
# 1. Backend
cd backend
python3.11 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env              # then open .env and fill in GROQ_API_KEY and ADMIN_TOKEN
uvicorn app:app --reload          # http://localhost:8000
```

The first start downloads the embedding model (about 130 MB) and indexes the files in `backend/data/`.

```bash
# 2. Frontend (in a second terminal)
cd frontend
python3 -m http.server 5500       # open http://localhost:5500
```

Make sure the `API` constant near the top of the script in `frontend/index.html` is `http://localhost:8000`.

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | Your Groq API key |
| `LLM_MODEL` | No | Model for answers. Default `openai/gpt-oss-120b` |
| `GUARD_MODEL` | No | Model for the topic check. Default `openai/gpt-oss-20b` |
| `ADMIN_TOKEN` | For editing the knowledge base | Password you invent. Without it, knowledge-base editing is disabled |
| `QDRANT_URL` | For deployment | Qdrant Cloud cluster URL. If empty, a local `qdrant_data/` folder is used |
| `QDRANT_API_KEY` | For deployment | Qdrant Cloud API key |
| `ALLOWED_ORIGINS` | No | Comma-separated list of allowed site URLs. Default `*` |

Never commit your `.env` file. Model names change over time; if Groq returns `model_not_found`, pick a current model from [console.groq.com/docs/models](https://console.groq.com/docs/models) and update the variables.

## Managing the knowledge base

1. Click **Knowledge base** in the sidebar and enter your `ADMIN_TOKEN`.
2. Choose a tab: **Upload files**, **Paste text** or **From URL**.
3. Ask a question about the new content. Answers show which passages they used.
4. Uploading a file with the same name replaces the old version. Use the bin icon to delete a document.

You can also drop `.md` or `.txt` files into `backend/data/` before the first run to seed the knowledge base.

## API reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Health check and number of indexed passages |
| POST | `/chat/stream` | Streams an answer as newline-delimited JSON |
| GET | `/kb` | Lists knowledge-base documents |
| POST | `/kb/upload` | Uploads files (needs `x-admin-token` header) |
| POST | `/kb/text` | Adds pasted text (needs `x-admin-token`) |
| POST | `/kb/url` | Adds a web page (needs `x-admin-token`) |
| DELETE | `/kb?doc=NAME` | Deletes a document (needs `x-admin-token`) |

## Troubleshooting

| Problem | Fix |
|---|---|
| `pip install` fails on `fastembed` | Use Python 3.11 or 3.12 |
| `KeyError: 'GROQ_API_KEY'` | The file must be named `.env` (not `.env.example`) and sit inside `backend/` |
| `unexpected keyword argument 'proxies'` | Install `httpx==0.27.2` |
| Groq `model_not_found` | Update `LLM_MODEL` and `GUARD_MODEL` to current Groq models |
| Page says "server offline" | Start the backend, or wait for Render to wake up, and check the `API` URL |
| CORS error in the browser console | `ALLOWED_ORIGINS` must match your site URL exactly |
| Knowledge base says "disabled" or "wrong token" | Set `ADMIN_TOKEN` on the server and enter the same value in the UI |

## Safety and privacy

Bytewise is AI and can make mistakes. Double-check important answers, test generated code before using it, and never share passwords, API keys or personal data in the chat. Questions are sent to the server and to the LLM provider to generate answers.

## Credits

Built by **AMAY TechLab**.