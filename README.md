# OpenAI SSE: local Hello World tests

This stage runs Python locally against OpenAI's hosted endpoints:

- `chat_completion_hello.py`: `POST https://api.openai.com/v1/chat/completions`
- `responses_hello.py`: `POST https://api.openai.com/v1/responses`

## Setup

```bash
python -m pip install -r requirements.txt
```

Copy the settings from `.env.example` into your existing `.env`, replacing
`your-api-key-here` with your OpenAI API key.

## Test both endpoints

```bash
python chat_completion_hello.py
python responses_hello.py
```

Expected text: `Hello World!` (exact wording/chunk boundaries may vary).
Text is flushed as it arrives. A short response may arrive almost instantly.
These are real API calls and incur API usage charges.

Inspect individual decoded SSE events:

```bash
python chat_completion_hello.py --events
python responses_hello.py --events
python responses_hello.py --prompt 'Count from one to twenty, one number per line.'
```
