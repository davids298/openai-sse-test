import json
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from openai import AsyncOpenAI

from main import app

PLACE = {'name': 'Auckland', 'country_code': 'NZ', 'feature_code': 'PPLA',
         'admin1': 'Auckland', 'latitude': -36.85, 'longitude': 174.76}
WEATHER = {'timezone': 'Pacific/Auckland', 'current': {
    'time': '2026-09-17T12:00', 'temperature_2m': 15, 'apparent_temperature': 14,
    'weather_code': 2, 'wind_speed_10m': 10},
    'current_units': {'temperature_2m': '°C', 'apparent_temperature': '°C', 'wind_speed_10m': 'km/h'}}
BODY = {'message': 'What is the day and weather?', 'city': 'Auckland', 'country': 'New Zealand'}


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict('os.environ', {'OPENAI_API_KEY': 'test-only', 'OPENAI_MODEL': 'gpt-4.1-mini'})
        self.env.start()
        self.client = TestClient(app)
        self.client.__enter__()
        self.places = [PLACE]
        self.mode = 'success'
        self.calls = []
        self.stream_closed = False
        self.original_http = app.state.http
        self.original_openai = app.state.openai
        app.state.http = httpx.AsyncClient(transport=httpx.MockTransport(self.weather))
        app.state.openai = AsyncOpenAI(api_key='test-only', http_client=httpx.AsyncClient(transport=httpx.MockTransport(self.ai)))

    def tearDown(self):
        self.client.portal.call(app.state.http.aclose)
        self.client.portal.call(self.original_openai.close)
        self.client.__exit__(None, None, None)
        self.env.stop()

    def weather(self, request):
        if self.mode == 'timeout':
            raise httpx.ReadTimeout('timeout', request=request)
        if 'geocoding' in request.url.host:
            self.assertEqual(request.url.params['countryCode'], 'NZ')
            return httpx.Response(200, json={'results': self.places})
        return httpx.Response(200, json={} if self.mode == 'bad_weather' else WEATHER)

    def ai(self, request):
        payload = json.loads(request.content)
        self.calls.append(request.url.path)
        self.assertTrue(payload['stream'])
        self.assertIn('Pacific/Auckland', request.content.decode())
        if self.mode == 'auth_error':
            return httpx.Response(401, json={'error': {'message': 'private-provider-detail', 'type': 'authentication_error'}})
        if request.url.path.endswith('/responses'):
            events = [{'type': 'response.output_text.delta', 'delta': 'Hello\nworld', 'item_id': 'i',
                       'output_index': 0, 'content_index': 0, 'sequence_number': 0}]
            if self.mode != 'eof':
                events.append({'type': 'response.incomplete' if self.mode == 'incomplete' else 'response.completed',
                               'response': {'id': 'r', 'status': 'completed'}, 'sequence_number': 1})
        else:
            events = [{'id': 'c', 'object': 'chat.completion.chunk', 'created': 0, 'model': 'gpt-4.1-mini',
                       'choices': [{'index': 0, 'delta': {'content': 'Hello\nworld'}, 'finish_reason': None}]}]
            if self.mode != 'eof':
                events.append({**events[0], 'choices': [{'index': 0, 'delta': {},
                               'finish_reason': 'length' if self.mode == 'incomplete' else 'stop'}]})
        data = ''.join('data: ' + json.dumps(e) + '\n\n' for e in events) + 'data: [DONE]\n\n'
        owner = self
        class Body(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield data.encode()
            async def aclose(self):
                owner.stream_closed = True
        return httpx.Response(200, headers={'content-type': 'text/event-stream'}, stream=Body())

    def test_both_success_streams(self):
        for path in ('/chat', '/chat/completions'):
            with self.subTest(path=path):
                response = self.client.post(path, json=BODY)
                self.assertEqual(response.status_code, 200)
                self.assertIn('text/event-stream', response.headers['content-type'])
                frames = response.text.strip().split('\n\n')
                self.assertEqual([f.splitlines()[0] for f in frames], ['event: context', 'event: delta', 'event: done'])
                self.assertEqual(json.loads(frames[1].split('\ndata: ')[1])['text'], 'Hello\nworld')
                self.assertEqual(json.loads(frames[-1].split('\ndata: ')[1])['text'], 'Hello\nworld')
                self.assertTrue(self.stream_closed)
        self.assertEqual(self.calls, ['/v1/responses', '/v1/chat/completions'])

    def test_validation(self):
        for changes in ({'message': ' '}, {'country': 'nonsense'}, {'city': ' '}, {'extra': 1}):
            self.assertEqual(self.client.post('/chat', json={**BODY, **changes}).status_code, 422)
        self.assertEqual(self.calls, [])

    def test_country_code_and_whitespace(self):
        self.assertEqual(self.client.post('/chat', json={**BODY, 'city': ' Auckland ', 'country': ' nz '}).status_code, 200)

    def test_not_found_and_ambiguity(self):
        self.places = [{**PLACE, 'country_code': 'AU'}]
        self.assertEqual(self.client.post('/chat', json=BODY).status_code, 404)
        self.places = [PLACE, {**PLACE, 'admin1': 'Another region'}]
        self.assertEqual(self.client.post('/chat', json=BODY).status_code, 409)
        self.assertEqual(self.client.post('/chat', json={**BODY, 'region': 'Auckland'}).status_code, 200)

    def test_weather_errors(self):
        for mode, status in (('timeout', 504), ('bad_weather', 502)):
            self.mode = mode
            self.assertEqual(self.client.post('/chat', json=BODY).status_code, status)
        self.assertEqual(self.calls, [])

    def test_failed_streams_have_no_done(self):
        for path in ('/chat', '/chat/completions'):
            for mode in ('auth_error', 'eof', 'incomplete'):
                with self.subTest(path=path, mode=mode):
                    self.mode = mode
                    response = self.client.post(path, json=BODY)
                    self.assertIn('event: error', response.text)
                    self.assertNotIn('event: done', response.text)
                    self.assertNotIn('private-provider-detail', response.text)
                    if mode != 'auth_error':
                        self.assertTrue(self.stream_closed)

    def test_missing_configuration_and_health(self):
        client = app.state.openai
        app.state.openai = None
        try:
            self.assertEqual(self.client.post('/chat', json=BODY).status_code, 503)
            self.assertEqual(self.client.get('/health').json(), {'status': 'ok'})
        finally:
            app.state.openai = client

    def test_docs(self):
        schema = self.client.get('/openapi.json').json()
        for path in ('/chat', '/chat/completions'):
            self.assertIn('text/event-stream', schema['paths'][path]['post']['responses']['200']['content'])


if __name__ == '__main__':
    unittest.main()
