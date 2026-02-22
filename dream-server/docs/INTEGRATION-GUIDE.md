# Dream Server Integration Guide

You've got Dream Server running. Now what? This guide shows how to connect your apps.

---

## 1. OpenAI SDK Compatibility

Dream Server exposes an OpenAI-compatible API. Just point your SDK at localhost.

### Python

```bash
pip install openai
```

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",  # Dream Server vLLM
    api_key="not-needed"  # Local, no auth required
)

response = client.chat.completions.create(
    model="Qwen/Qwen2.5-32B-Instruct-AWQ",  # Your running model
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)
print(response.choices[0].message.content)
```

### Node.js / TypeScript

```bash
npm install openai
```

```javascript
import OpenAI from 'openai';

const openai = new OpenAI({
  baseURL: 'http://localhost:8000/v1',
  apiKey: 'not-needed',
});

const response = await openai.chat.completions.create({
  model: 'Qwen/Qwen2.5-32B-Instruct-AWQ',
  messages: [{ role: 'user', content: 'Hello!' }],
});

console.log(response.choices[0].message.content);
```

### curl

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-32B-Instruct-AWQ",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

---

## 2. LangChain Integration

```bash
pip install langchain langchain-openai
```

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed",
    model="Qwen/Qwen2.5-32B-Instruct-AWQ",
    temperature=0.7,
)

response = llm.invoke("Explain quantum computing in one sentence.")
print(response.content)
```

### With RAG (Qdrant + Embeddings)

```python
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import Qdrant

embeddings = OpenAIEmbeddings(
    base_url="http://localhost:9103/v1",  # TEI embeddings service
    api_key="not-needed",
)

# Connect to Dream Server's Qdrant
qdrant = Qdrant.from_existing_collection(
    embeddings=embeddings,
    collection_name="documents",
    url="http://localhost:6333",
)

# Query documents
results = qdrant.similarity_search("What is the policy on refunds?")
```

---

## 3. Continue.dev Setup

Continue is an open-source AI code assistant that works in VS Code.

1. Install Continue extension in VS Code
2. Edit `~/.continue/config.json`:

```json
{
  "models": [
    {
      "title": "Dream Server",
      "provider": "openai",
      "model": "Qwen/Qwen2.5-32B-Instruct-AWQ",
      "apiBase": "http://localhost:8000/v1",
      "apiKey": "not-needed"
    }
  ]
}
```

3. Restart VS Code, select "Dream Server" in Continue panel

---

## 4. Cursor IDE Integration

Cursor supports custom API endpoints.

1. Open Cursor Settings → Models
2. Add custom model:
   - **API Base:** `http://localhost:8000/v1`
   - **API Key:** `not-needed`
   - **Model:** `Qwen/Qwen2.5-32B-Instruct-AWQ`

---

## 5. n8n Workflow Examples

Dream Server includes n8n for workflow automation. Access at `http://localhost:5678`.

### Example: Document Q&A Workflow

Import `workflows/02-document-qa.json`:
1. Open n8n UI
2. Click Import → From File
3. Select the workflow JSON
4. Configure your document source
5. Activate

### Pre-built Workflows

| Workflow | File | Description |
|----------|------|-------------|
| Chat Endpoint | `01-chat-endpoint.json` | HTTP webhook to LLM |
| Document Q&A | `02-document-qa.json` | RAG with Qdrant |
| Voice Transcription | `03-voice-transcription.json` | Whisper → Text |
| TTS API | `04-tts-api.json` | Text → Speech |
| Voice-to-Voice | `05-voice-to-voice.json` | Full voice pipeline |
| RAG Demo | `06-rag-demo.json` | Document upload → query |
| Code Assistant | `07-code-assistant.json` | Code generation workflow |

---

## 6. REST API Reference

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /v1/chat/completions` | Chat (OpenAI compatible) |
| `POST /v1/completions` | Text completion |
| `GET /v1/models` | List available models |
| `GET /health` | Health check |

### Streaming

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="x")

stream = client.chat.completions.create(
    model="Qwen/Qwen2.5-32B-Instruct-AWQ",
    messages=[{"role": "user", "content": "Write a poem"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

---

## 7. Environment Variables

Key variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `VLLM_PORT` | 8000 | vLLM API port |
| `WEBUI_PORT` | 3000 | Open WebUI port |
| `N8N_PORT` | 5678 | n8n workflows port |
| `LLM_MODEL` | Qwen/Qwen2.5-32B-Instruct-AWQ | Model to load |
| `MAX_CONTEXT` | 8192 | Context window size |
| `GPU_UTIL` | 0.9 | GPU memory utilization |

---

## 8. Authentication Options

### No Auth (Default)

Local-only, no auth required. Good for development.

### API Key Auth

Set in `.env`:
```
VLLM_API_KEY=your-secret-key
```

Then include in requests:
```python
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="your-secret-key"
)
```

### Open WebUI Auth

WebUI has built-in user management:
1. First user becomes admin
2. Configure auth in WebUI settings
3. Set `WEBUI_AUTH=true` in `.env`

---

## Common Issues

### "Model not found"

Check running model name:
```bash
curl http://localhost:8000/v1/models
```

Use the exact model name in your requests.

### Connection refused

Ensure services are running:
```bash
docker compose ps
```

Check vLLM is ready:
```bash
docker compose logs vllm | tail -20
```

### Slow first response

First request after start triggers model warm-up. Wait 30-60 seconds.

---

*Built by The Collective*
