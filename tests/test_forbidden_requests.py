"""A provider's 403 must not be mistaken for an incompatible chat history."""
import json
import unittest
from unittest import mock

from ai_router import provider_defs, setup, upstream
from tests.fakes import FakeUpstream, install_fake
from tests.harness import StubCredentials, auth_file, post, start_server, test_state


class ForbiddenDescriptionTests(unittest.TestCase):
    def test_forbidden_status_names_provider_without_exposing_its_body(self):
        for provider in provider_defs.external_defs():
            for body in (b'', b'not json', json.dumps({'error': {
                    'message': 'private-prompt-marker', 'code': 403}}).encode()):
                with self.subTest(provider=provider.id, body=body):
                    status, message, _ = upstream.describe_failure(
                        None, {'status': 403, 'body': body},
                        {'model': 'model-id', 'provider': provider.id,
                         'protocol': 'responses', 'dialect': provider.dialect,
                         'routed': True})
                    self.assertEqual(status, 400)
                    self.assertIn(provider.label, message)
                    self.assertIn('model-id (403 Forbidden)', message)
                    self.assertIn('contact IT', message)
                    for misleading in ('previous model', 'new thread', 'key was rejected',
                                       'private-prompt-marker'):
                        self.assertNotIn(misleading, message)


class ForbiddenRelayTests(unittest.TestCase):
    def _send(self, rejected_key):
        recorded = install_fake(self, lambda: FakeUpstream(
            403, b'{"error":{"message":"private-prompt-marker","code":403}}',
            [('Content-Type', 'application/json')]))
        credentials = StubCredentials('test-key')
        credentials.key_rejected = mock.Mock(return_value=rejected_key)
        credentials.home = '/synthetic/router-home'
        server = start_server(test_state(auth_file(self)), credentials)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with mock.patch.object(setup, 'open_key_window') as window:
            response = post(server.server_port, '/test-token/responses', {
                'model': 'deepseek/deepseek-v4.1-flash-1017',
                'input': [{'role': 'user', 'content': 'Hello'}]})
            raw = response.read()
        self.assertEqual(len(recorded), 1)
        return response.status, json.loads(raw)['error'], window

    def test_valid_key_reports_provider_block_without_replacing_key(self):
        status, error, window = self._send(False)
        self.assertEqual(status, 400)
        self.assertIn('OpenRouter blocked the request', error['message'])
        self.assertIn('(403 Forbidden)', error['message'])
        self.assertNotIn('new thread', error['message'])
        self.assertNotIn('private-prompt-marker', error['message'])
        window.assert_not_called()

    def test_rejected_key_keeps_the_existing_key_recovery(self):
        status, error, window = self._send(True)
        self.assertEqual(status, 400)
        self.assertEqual(error['code'], 'CREDENTIAL_PROBLEM')
        self.assertIn('stored OpenRouter key was rejected', error['message'])
        window.assert_called_once()
