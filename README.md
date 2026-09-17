# OpenAI SSE Weather Chatbot

A local FastAPI demo that answers questions using local time and weather from
[Open-Meteo](https://open-meteo.com/), streaming text through OpenAI.

## Setup and run

Activate your Python environment, then install dependencies:

```bash
python -m pip install -r requirements.txt
```

Add your settings to `.env` (see `.env.example`):

```dotenv
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4.1-mini
```

Start the server and keep the terminal running:

```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open [Swagger UI](http://127.0.0.1:8000/docs) to try the endpoints.
OpenAI calls incur API charges; the local weather demo needs no weather API key.

## Endpoints

| Endpoint | Purpose |
| --- | --- |
| `POST /chat` | Stream an answer using the Responses API |
| `POST /chat/completions` | Compare with Chat Completions |
| `GET /health` | Check that the server is running |

```bash
curl -N http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"What is the current day and weather?","city":"Auckland","country":"NZ"}'
```

Change the URL to `/chat/completions` to compare the same question.

- `message`, `city`, and `country` are required.
- Country names and ISO codes work: `New Zealand`, `nz`, `Australia`, `aus`.
- `region` is optional. Omit it unless needed to distinguish cities; ambiguous
  matches return HTTP 409 with candidates. Don't leave Swagger's `"string"` example.

## Stream output

Both endpoints return SSE events containing JSON:

| Event | Contents |
| --- | --- |
| `context` | Resolved location, local date, weather, and source |
| `delta` | A piece of the answer in `text` |
| `done` | The complete readable answer in `text`, plus the API used |
| `error` | Generation failed or ended early |

Read `done.text` for the final answer, or append each `delta.text` for live output.
Don't append both. Swagger displays raw events; `curl -N` shows them as they arrive.
After streaming starts, errors appear as SSE events even with HTTP 200.

This is a single-turn demo: every request fetches model-based current weather,
with no conversation history. Check the resolved location in `context`.

## Standalone examples and tests

```bash
python responses_hello.py
python chat_completion_hello.py
python -m unittest discover -s tests -v
```

The examples accept `--events`, `--prompt`, and `--model`. Tests mock external
services and do not spend API credits.
