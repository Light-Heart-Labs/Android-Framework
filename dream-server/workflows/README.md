# Dream Server n8n Workflows

Pre-built workflows for common local AI tasks. Import these directly into your n8n instance.

## How to Import

1. Open n8n at http://localhost:5678
2. Click **+ Add Workflow**
3. Click the menu (**⋮**) → **Import from file**
4. Select the `.json` file

## Quick Demo (curl examples)

```bash
# Chat
curl -X POST http://localhost:5678/webhook/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the meaning of life?"}'

# Voice-to-Voice (send audio, get audio back)
curl -X POST http://localhost:5678/webhook/voice-chat \
  -F "audio=@your-recording.wav" \
  -o response.wav

# Code Assistant
curl -X POST http://localhost:5678/webhook/code-assist \
  -H "Content-Type: application/json" \
  -d '{"code": "def add(a,b): return a+b", "task": "improve"}'

# RAG: Upload document
curl -X POST http://localhost:5678/webhook/upload-doc \
  -H "Content-Type: application/json" \
  -d '{"text": "Your document content here..."}'

# RAG: Ask question
curl -X POST http://localhost:5678/webhook/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?"}'
```

## Available Workflows

### 1. Chat API Endpoint (`01-chat-endpoint.json`)
Creates a REST API endpoint that forwards requests to your local vLLM.

**Use case:** Connect any application that expects an OpenAI-compatible API.

**Endpoints created:**
- `POST /webhook/chat` — Send messages, get completions

### 2. Document Q&A (`02-document-qa.json`)
Full RAG pipeline: upload documents, ask questions, get answers from content.

**Use case:** Internal knowledge base, document analysis.

**Endpoints created:**
- `POST /webhook/upload-doc` — Upload text, chunk, embed, store in Qdrant
- `POST /webhook/ask` — Ask questions, get RAG-powered answers

**Workflow:**
1. Upload: Text → Chunk (500 chars) → Embed → Store in Qdrant
2. Query: Question → Embed → Vector search → Context → LLM answer

**Note:** For PDF support, add a PDF parsing node (external service like Unstructured.io)

### 3. Voice Transcription (`03-voice-transcription.json`)
Receive audio, transcribe with Whisper, optionally process with LLM.

**Use case:** Meeting transcription, voice commands, audio analysis.

**Endpoints created:**
- `POST /webhook/transcribe` — Audio → Text
- `POST /webhook/voice-command` — Audio → LLM response

### 4. Text-to-Speech API (`04-tts-api.json`)
Convert text to speech using Piper.

**Use case:** Audiobook generation, accessibility, notifications.

**Endpoints created:**
- `POST /webhook/speak` — Text → Audio file

### 5. Voice-to-Voice Assistant (`05-voice-to-voice.json`)
Complete voice chat pipeline: speak → transcribe → LLM → speak back.

**Use case:** Hands-free AI assistant, accessibility, voice-first interfaces.

**Workflow:**
1. Receive audio (WAV/MP3/WebM)
2. Whisper transcribes to text
3. LLM generates concise response
4. Piper synthesizes speech
5. Returns audio response

**Endpoints created:**
- `POST /webhook/voice-chat` — Audio in → Audio out

**The "wow" demo:** Record a question, POST it, get a spoken answer back. Full local voice AI.

### 6. RAG Document Q&A (`06-rag-demo.json`)
Full RAG pipeline for document question-answering.

**Use case:** Upload documents, ask questions, get answers with source citations.

**Workflow:**
1. Upload: Text → Chunk (500 chars, 100 overlap) → Embed → Store in Qdrant
2. Query: Question → Embed → Vector search → Inject context → LLM answer

**Endpoints created:**
- `POST /webhook/upload-doc` — Upload and index a document
- `POST /webhook/ask` — Ask questions about indexed documents

**The "wow" demo:** Upload your company docs, ask questions, get accurate answers from your own data.

### 7. Code Assistant (`07-code-assistant.json`)
AI-powered code review and assistance.

**Use case:** Code explanation, improvement, debugging, documentation, test generation.

**Workflow:**
1. Receive code + task type (explain/improve/debug/document/test)
2. Build appropriate prompt for task
3. LLM generates response
4. Return structured result

**Endpoints created:**
- `POST /webhook/code-assist` — `{ "code": "...", "task": "improve", "language": "python" }`

**Tasks supported:** explain, improve, debug, document, test

### 8. Scheduled Summarizer (`daily-digest.json`)
Daily/weekly cron that summarizes specified content.

**Use case:** News digest, log analysis, report generation.

**Configurable:**
- Schedule (daily/weekly/custom)
- Content sources
- Output destination (email, Slack, file)

## Configuration

Most workflows need these credentials configured in n8n:

### Local LLM (HTTP Request)
- **Base URL:** `http://vllm:8000/v1`
- **Authentication:** None (internal network)

### Qdrant (HTTP Request)
- **Base URL:** `http://qdrant:6333`
- **Authentication:** None (internal network)

### Whisper (HTTP Request)
- **Base URL:** `http://whisper:9000`
- **Authentication:** None (internal network)

### Piper (HTTP Request)
- **Base URL:** `http://tts:8880`
- **Authentication:** None (internal network)

## Customization

Each workflow can be extended:
- Add authentication
- Change model parameters
- Connect to external services
- Add error handling

## Troubleshooting

**"Could not connect to vllm:8000"**
- Check if vLLM is running: `docker compose ps`
- Check logs: `docker compose logs vllm`
- Ensure container network is correct

**"Response too slow"**
- First request loads model (can take 30+ seconds)
- Subsequent requests should be fast
- Consider reducing context length

**"Out of memory"**
- Reduce `max-model-len` in docker-compose.yml
- Use smaller model (adjust `.env`)
- Check GPU memory: `nvidia-smi`
