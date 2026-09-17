"""Shared command-line configuration for the two standalone examples."""
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


def configure(description):
    load_dotenv(Path(__file__).with_name('.env'))
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--model', default=os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'))
    parser.add_argument('--prompt', default='Say exactly: Hello World!')
    parser.add_argument('--events', action='store_true', help='Print each decoded SSE event as JSON')
    args = parser.parse_args()
    key = os.getenv('OPENAI_API_KEY', '').strip()
    if not key or key == 'your-api-key-here':
        parser.error('Set OPENAI_API_KEY in .env or your shell before running this example.')
    if not args.model.strip() or not args.prompt.strip():
        parser.error('--model and --prompt must not be blank')
    return args, OpenAI(api_key=key, timeout=60.0, max_retries=0)
