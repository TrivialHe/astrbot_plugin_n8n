"""Run with uv run --python 3.12 python -m unittest -v test_webhook.py.

Stub only the AstrBot SDK; exercise real aiohttp against a loopback test server.
"""
import asyncio
import importlib.util
import logging
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import patch

from aiohttp import web, ClientTimeout

for name in ['astrbot', 'astrbot.api', 'astrbot.api.event', 'astrbot.api.star', 'astrbot.core', 'astrbot.core.config', 'astrbot.core.config.astrbot_config']:
    sys.modules[name] = ModuleType(name)
sys.modules['astrbot.api'].logger = logging.getLogger('test_n8n')
sys.modules['astrbot.api.event'].filter = type('Filter', (), {'command':staticmethod(lambda _: lambda f: f)})
sys.modules['astrbot.api.event'].AstrMessageEvent = object
star = sys.modules['astrbot.api.star']
star.Context = object
star.Star = type('Star', (), {'__init__':lambda self, context: None})
star.register = lambda *args: lambda cls: cls
sys.modules['astrbot.core.config.astrbot_config'].AstrBotConfig = dict
spec = importlib.util.spec_from_file_location('plugin_under_test', Path(__file__).with_name('main.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class Event:
    session_id = 'group:allowed-user:attacker'
    def __init__(self, sender='allowed-user', message='/n8n payload n8n remains'):
        self.sender, self.message_str = sender, message
    def get_sender_id(self): return self.sender
    def get_sender_name(self): return 'test sender'
    def plain_result(self, text): return text

class WebhookTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.received = []
        self.response = {'data':'ok'}
        self.status = 200
        self.delay = 0
        self.body = None
        async def receive(request):
            self.received.append((await request.json(), request.headers.get('Authorization')))
            if self.delay: await asyncio.sleep(self.delay)
            if self.body is not None: return web.Response(text=self.body, status=self.status)
            return web.json_response(self.response, status=self.status)
        app = web.Application()
        app.router.add_post('/hook', receive)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '127.0.0.1', 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        self.plugin = module.MyPlugin(None, {'n8n':{'adminIds':' , allowed-user, ', 'n8n_webhook_url':f'http://127.0.0.1:{port}/hook', 'username':'demo', 'password':'test-only'}})
    async def asyncTearDown(self): await self.runner.cleanup()
    async def invoke(self, event=None): return [r async for r in self.plugin.call_n8n(event or Event())]
    async def test_payload_auth_and_prefix(self):
        self.assertEqual(await self.invoke(), ['n8n 返回结果: ok'])
        self.assertEqual(self.received, [({'message':'payload n8n remains','senderName':'test sender'}, 'Basic ZGVtbzp0ZXN0LW9ubHk=')])
    async def test_sender_substring_and_session_do_not_authorize(self):
        for sender in ['allowed', 'attacker', 'allowed-user-extra']:
            self.assertEqual(await self.invoke(Event(sender)), [])
        self.assertEqual(self.received, [])
    async def test_empty_whitelist(self):
        self.plugin.config['n8n']['adminIds'] = ' , , '
        self.assertIn('未配置', (await self.invoke())[0])
        self.assertEqual(self.received, [])
    async def test_non_command_payload_preserved(self):
        await self.invoke(Event(message='payload n8n inside'))
        self.assertEqual(self.received[0][0]['message'], 'payload n8n inside')
    async def test_no_slash_and_empty_command(self):
        for message, expected in [('n8n hello', 'hello'), ('/n8n', '')]:
            await self.invoke(Event(message=message))
            self.assertEqual(self.received[-1][0]['message'], expected)
    async def test_invalid_json_and_raw_error_body_hidden(self):
        self.body = 'private upstream body'
        with self.assertLogs('test_n8n', level='WARNING') as logs:
            result = await self.invoke()
        self.assertIn('有效 JSON', result[0])
        self.assertNotIn(self.body, str(result) + str(logs.output))
    async def test_array_missing_data(self):
        for body in [[], {}, ['private']]:
            self.response = body
            self.assertIn('响应格式', (await self.invoke())[0])
    async def test_http_failure_body_hidden(self):
        self.status, self.body = 500, 'private failure details'
        with self.assertLogs('test_n8n', level='ERROR') as logs:
            result = await self.invoke()
        self.assertIn('失败', result[0])
        self.assertNotIn(self.body, str(result) + str(logs.output))
    async def test_timeout_no_retry(self):
        self.delay = .1
        with patch.object(module.aiohttp, 'ClientTimeout', return_value=ClientTimeout(total=.01, connect=.01)):
            result = await self.invoke()
        self.assertIn('可能已受理', result[0])
        self.assertEqual(len(self.received), 1)
    async def test_network_error_hidden(self):
        from aiohttp import ClientConnectionError
        with patch.object(module.aiohttp.ClientSession, 'post', side_effect=ClientConnectionError('secret upstream url')):
            with self.assertLogs('test_n8n', level='ERROR') as logs:
                result = await self.invoke()
        self.assertNotIn('secret upstream url', str(result) + str(logs.output))

if __name__ == '__main__': unittest.main()
