"""Call POST /v1/chat/completions directly and print its streamed output."""
import sys

from openai import OpenAIError

from sse_config import configure


def main():
    args, client = configure(__doc__)
    try:
        with client, client.chat.completions.create(
            model=args.model,
            messages=[{'role': 'user', 'content': args.prompt}],
            stream=True,
            max_completion_tokens=256,
        ) as stream:
            finished = False
            for chunk in stream:
                if args.events:
                    print(chunk.model_dump_json(), flush=True)
                for choice in chunk.choices:
                    if not args.events:
                        print(choice.delta.content or choice.delta.refusal or '', end='', flush=True)
                    if choice.finish_reason:
                        if choice.finish_reason != 'stop':
                            raise RuntimeError(f'Generation ended with: {choice.finish_reason}')
                        finished = True
            if not finished:
                raise RuntimeError('Stream ended without a completion marker.')
        if not args.events:
            print()
        return 0
    except (OpenAIError, RuntimeError) as exc:
        print(f'\nChat Completions failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
