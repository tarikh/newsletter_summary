import pytest
from fetch import get_ai_newsletters
from unittest.mock import MagicMock
import fetch

class DummyMessages:
    def __init__(self, messages_data=None):
        self._messages_data = messages_data or []
    def list(self, userId, q):
        # Simulate filtering by 'from:' and 'to:' in the query string
        filtered = self._messages_data
        if 'from:' in q:
            from_email = q.split('from:')[1].split()[0]
            filtered = [m for m in filtered if m['from'] == from_email]
        if 'to:' in q:
            to_email = q.split('to:')[1].split()[0]
            filtered = [m for m in filtered if m['to'] == to_email]
        # Return only the ids
        return MagicMock(execute=MagicMock(return_value={'messages': [{'id': m['id']} for m in filtered]}))
    def get(self, userId, id, format):
        # Return the message with the given id
        msg = next(m for m in self._messages_data if m['id'] == id)
        return MagicMock(execute=MagicMock(return_value={
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': msg['subject']},
                    {'name': 'Date', 'value': msg['date']},
                    {'name': 'From', 'value': msg['from']},
                    {'name': 'To', 'value': msg['to']},
                ],
                'body': {'data': b'VGVzdCBib2R5'}
            }
        }))

class DummyUsers:
    def __init__(self, messages_data=None):
        self._messages = DummyMessages(messages_data)
    def messages(self):
        return self._messages

class DummyService:
    def __init__(self, messages_data=None):
        self._users = DummyUsers(messages_data)
    def users(self):
        return self._users

# Patch points for the static methods

def test_get_ai_newsletters_success(monkeypatch):
    # Simulate two messages
    messages_data = [
        {'id': '1', 'subject': 'Test 1', 'date': 'Mon, 1 Jan 2024 10:00:00 +0000', 'from': 'sender1@example.com', 'to': 'me@example.com'},
        {'id': '2', 'subject': 'Test 2', 'date': 'Tue, 2 Jan 2024 10:00:00 +0000', 'from': 'sender2@example.com', 'to': 'me@example.com'},
    ]
    monkeypatch.setattr(fetch, 'tqdm', lambda x, **kwargs: x)  # Disable progress bar
    service = DummyService(messages_data)
    newsletters = get_ai_newsletters(service, days=1)
    assert len(newsletters) == 2
    assert newsletters[0]['subject'] == 'Test 1'
    assert newsletters[1]['subject'] == 'Test 2'

def test_get_ai_newsletters_no_messages(monkeypatch):
    messages_data = []
    monkeypatch.setattr(fetch, 'tqdm', lambda x, **kwargs: x)
    service = DummyService(messages_data)
    newsletters = get_ai_newsletters(service, days=1)
    assert newsletters == []

def test_get_ai_newsletters_api_error(monkeypatch):
    class ErrorMessages:
        def list(self, userId, q):
            raise Exception('API error')
        def get(self, userId, id, format):
            raise Exception('Should not be called')
    class ErrorUsers:
        def messages(self):
            return ErrorMessages()
    class ErrorService:
        def users(self):
            return ErrorUsers()
    monkeypatch.setattr(fetch, 'tqdm', lambda x, **kwargs: x)
    service = ErrorService()
    with pytest.raises(Exception) as excinfo:
        get_ai_newsletters(service, days=1)
    assert 'API error' in str(excinfo.value)

def test_get_ai_newsletters_from_and_to_filters(monkeypatch):
    messages_data = [
        {'id': '1', 'subject': 'Test 1', 'date': 'Mon, 1 Jan 2024 10:00:00 +0000', 'from': 'sender1@example.com', 'to': 'me@example.com'},
        {'id': '2', 'subject': 'Test 2', 'date': 'Tue, 2 Jan 2024 10:00:00 +0000', 'from': 'sender2@example.com', 'to': 'me@example.com'},
        {'id': '3', 'subject': 'Test 3', 'date': 'Wed, 3 Jan 2024 10:00:00 +0000', 'from': 'sender1@example.com', 'to': 'other@example.com'},
    ]
    monkeypatch.setattr(fetch, 'tqdm', lambda x, **kwargs: x)
    service = DummyService(messages_data)
    # Only from sender1@example.com
    newsletters = get_ai_newsletters(service, days=1, from_email='sender1@example.com')
    assert len(newsletters) == 2
    assert all(nl['sender'] == 'sender1@example.com' for nl in newsletters)
    # Only to me@example.com
    newsletters = get_ai_newsletters(service, days=1, to_email='me@example.com')
    assert len(newsletters) == 2
    assert all(nl['sender'] in ['sender1@example.com', 'sender2@example.com'] for nl in newsletters)
    # Both from and to
    newsletters = get_ai_newsletters(service, days=1, from_email='sender1@example.com', to_email='me@example.com')
    assert len(newsletters) == 1
    assert newsletters[0]['sender'] == 'sender1@example.com'
    assert newsletters[0]['subject'] == 'Test 1'

def test_get_ai_newsletters_missing_headers(monkeypatch):
    # Simulate a message missing Subject and From headers
    messages_data = [
        {'id': '1', 'subject': None, 'date': 'Mon, 1 Jan 2024 10:00:00 +0000', 'from': None, 'to': 'me@example.com'},
    ]
    class DummyMessagesMissing:
        def list(self, userId, q):
            return MagicMock(execute=MagicMock(return_value={'messages': [{'id': '1'}]}))
        def get(self, userId, id, format):
            return MagicMock(execute=MagicMock(return_value={
                'payload': {
                    'headers': [
                        {'name': 'Date', 'value': 'Mon, 1 Jan 2024 10:00:00 +0000'},
                        {'name': 'To', 'value': 'me@example.com'},
                    ],
                    'body': {'data': b'VGVzdCBib2R5'}
                }
            }))
    class DummyUsersMissing:
        def messages(self):
            return DummyMessagesMissing()
    class DummyServiceMissing:
        def users(self):
            return DummyUsersMissing()
    monkeypatch.setattr(fetch, 'tqdm', lambda x, **kwargs: x)
    service = DummyServiceMissing()
    newsletters = get_ai_newsletters(service, days=1)
    assert len(newsletters) == 1
    assert newsletters[0]['subject'] == 'No Subject'
    assert newsletters[0]['sender'] == 'Unknown Sender' 