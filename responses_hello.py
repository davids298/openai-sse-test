"""Call POST /v1/responses directly and print its streamed output."""
import sys

from openai import OpenAIError

from sse_config import configure


def main():
    args, client = configure(__doc__)
    try:
        with client, client.responses.create(
            model=args.model,
            input=args.prompt,
            stream=True,
            max_output_tokens=256,
        ) as stream:
            completed = False
            for event in stream:
                if args.events:
                    print(event.model_dump_json(), flush=True)
                elif event.type in ('response.output_text.delta', 'response.refusal.delta'):
                    print(event.delta, end='', flush=True)
                if event.type == 'response.completed':
                    completed = True
                elif event.type in ('response.failed', 'response.incomplete', 'error'):
                    raise RuntimeError(f'{event.type}: {event.model_dump_json()}')
            if not completed:
                raise RuntimeError('Stream ended without response.completed.')
        if not args.events:
            print()
        return 0
    except (OpenAIError, RuntimeError) as exc:
        print(f'\nResponses failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
