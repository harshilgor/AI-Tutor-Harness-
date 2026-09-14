from fastapi.testclient import TestClient
import pytest

import backend.app.main as main
from backend.app.model_provider import GeneratedBlock, ModelProviderError


def make_lesson(client):
    session = client.post('/v1/sessions', json={'topic': 'neural networks'}).json()
    lesson = client.post(f"/v1/sessions/{session['id']}/actions", json={'intent': 'teach', 'gear': 'Deep'}).json()['lesson']
    return session, lesson


def test_explanation_uses_saved_passage_without_replacing_main_lesson(monkeypatch):
    client = TestClient(main.app)
    session, lesson = make_lesson(client)
    before = client.get(f"/v1/sessions/{session['id']}").json()
    block = lesson['blocks'][0]
    class Provider:
        def explain(self, *, selected_text, lesson_context):
            assert selected_text == block['heading']
            assert block['body'] in lesson_context
            return [GeneratedBlock('explanation', 'Closer look', 'Explanation'), GeneratedBlock('example', 'Example', 'A concrete example')]
    monkeypatch.setattr(main, 'lesson_provider', Provider())
    response = client.post(f"/v1/lessons/{lesson['id']}/explanations", json={'blockId': block['id'], 'selectedText': block['heading']})
    assert response.status_code == 200
    assert response.json()['blocks'][0]['body'] == 'Explanation'
    assert client.get(f"/v1/sessions/{session['id']}").json() == before
    assert client.get(f"/v1/lessons/{lesson['id']}").json() == lesson
    invalid = client.post(f"/v1/lessons/{lesson['id']}/explanations", json={'blockId': block['id'], 'selectedText': 'An unrelated instruction'})
    assert invalid.status_code == 422


def test_explanation_provider_failure_is_recoverable(monkeypatch):
    client = TestClient(main.app)
    _, lesson = make_lesson(client)
    block = lesson['blocks'][0]
    request = {'blockId': block['id'], 'selectedText': block['heading']}
    path = f"/v1/lessons/{lesson['id']}/explanations"
    assert client.post(path, json=request).status_code == 503
    class Provider:
        def explain(self, **kwargs):
            raise ModelProviderError('The free model is busy. Please retry.')
    monkeypatch.setattr(main, 'lesson_provider', Provider())
    response = client.post(path, json=request)
    assert response.status_code == 502
    assert 'free model is busy' in response.json()['detail']['message']


@pytest.mark.parametrize('mode,expected', [('simpler', 'simpler language'), ('example', 'numerical example'), ('symbols', 'each symbol'), ('why', 'every transformation')])
def test_reading_help_mode_preserves_source_and_learner_state(monkeypatch, mode, expected):
    client = TestClient(main.app)
    session, lesson = make_lesson(client)
    block = lesson['blocks'][0]
    before = client.get(f"/v1/sessions/{session['id']}").json()
    class Provider:
        def explain(self, *, selected_text, lesson_context):
            assert expected in lesson_context
            assert block['body'] in lesson_context
            return [GeneratedBlock('explanation', 'Explanation', '$x^2$')]
    monkeypatch.setattr(main, 'lesson_provider', Provider())
    response = client.post(f"/v1/lessons/{lesson['id']}/explanations", json={'blockId': block['id'], 'selectedText': block['body'][:500], 'mode': mode})
    assert response.status_code == 200
    assert response.json()['blocks'][0]['body'] == '$x^2$'
    assert client.get(f"/v1/sessions/{session['id']}").json() == before
    assert client.post(f"/v1/lessons/{lesson['id']}/explanations", json={'blockId': block['id'], 'selectedText': block['heading'], 'mode': 'unsupported'}).status_code == 422
