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

## Files
**`sse_config.py` — shared configuration**

Both examples call its `configure()` function before making a request. It:

1. Loads `.env` from the project directory.
2. Reads command-line options:
    - `--model`: defaults to `OPENAI_MODEL`, or `gpt-4.1-mini`.
    - `--prompt`: defaults to `Say exactly: Hello World!`.
    - `--events`: displays complete decoded events instead of only text.
3. Checks that an API key exists and the model and prompt aren’t blank.
4. Creates an `OpenAI` client with a 60-second timeout and automatic retries disabled.
5. Returns the options and client to the calling script.

Loading configuration separately keeps both examples consistent.

**`chat_completion_hello.py` — Chat Completions streaming**

This sends the prompt to OpenAI’s `/v1/chat/completions` endpoint:

```
client.chat.completions.create(
    model=args.model,
    messages=[{'role': 'user', 'content': args.prompt}],
    stream=True,
    max_completion_tokens=256,
)
```

`messages` holds the conversation. Currently, it contains one user message.

`stream=True` asks OpenAI to send chunks as generation progresses. The SDK reads the SSE stream and turns those chunks into Python objects.

The loop extracts new text from:

```
choice.delta.content
```

It prints each piece immediately:

```
print(text, end='', flush=True)
```

- `end=''` prevents a newline after every piece.
- `flush=True` makes the text appear immediately instead of waiting in Python’s output buffer.

The script also checks the finish reason. A normal `stop` means success; truncation or an unexpected ending produces an error.

**`responses_hello.py` — Responses streaming**

This sends the prompt to OpenAI’s `/v1/responses` endpoint:

```
client.responses.create(
    model=args.model,
    input=args.prompt,
    stream=True,
    max_output_tokens=256,
)
```

Here, the simple prompt goes into `input`.

Instead of reading `choices`, this script checks each event’s `type`:

|Event|Script behavior|
|---|---|
|`response.output_text.delta`|Prints the newly generated text|
|`response.refusal.delta`|Prints refusal text|
|`response.completed`|Records successful completion|
|`response.failed`, `response.incomplete`, `error`|Reports failure|

Other events are ignored in normal text mode. With `--events`, you can see every decoded event.

The script also detects a stream that closes without a completion event, so it doesn’t silently report partial output as successful.

**Patterns shared by both examples**

```
with client, ... as stream:
```

This closes the stream and client when finished, including when an error occurs.

```
if __name__ == '__main__':
    raise SystemExit(main())
```

This runs `main()` when you execute the file directly. Importing the file from another Python file won’t automatically make an API request.

The exit code is `0` for success and `1` for a handled API or streaming failure. Invalid configuration exits with code `2`.

**`main.py` — currently empty**

This is reserved for the future FastAPI application.

Right now, the flow is:

```
Your terminal → Python script → OpenAI endpoint
Your terminal ← printed text ← OpenAI SSE stream
```

There is no local HTTP server yet. These scripts let you test the OpenAI calls before wrapping them in your own `/chat` endpoint.