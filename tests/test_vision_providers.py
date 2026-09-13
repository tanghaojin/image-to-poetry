import json

import httpx
import pytest

from app.vision.providers import VisionProviderRouter, parse_understanding
from core.config import settings


def test_parse_understanding_extracts_json_and_clamps_values() -> None:
    result = parse_understanding('```json\n{"subjects":["山","月"],"season":"秋","time":"夜晚",'
                                 '"weather":"晴","mood":"宁静","sceneSummary":"月照秋山",'
                                 '"confidence":1.4}\n```')
    assert result.subjects == ["山", "月"]
    assert result.scene_summary == "月照秋山"
    assert result.confidence == 1


@pytest.mark.asyncio
async def test_router_falls_back_from_gemini_to_glm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "vision_model_order", "gemini-3.7-flash,glm-4.6v-flash")
    monkeypatch.setattr(settings, "google_ai_api_key", "gemini-test-key")
    monkeypatch.setattr(settings, "big_model_api_key", "glm-test-key")
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        body = json.loads(request.content)
        if "googleapis" in str(request.url):
            assert request.headers["x-goog-api-key"] == "gemini-test-key"
            return httpx.Response(404, json={"error": {"status": "NOT_FOUND"}})
        assert request.headers["authorization"] == "Bearer glm-test-key"
        assert body["model"] == "glm-4.6v-flash"
        content = json.dumps({"subjects": ["孤舟"], "season": "冬", "time": "清晨",
                              "weather": "雪", "mood": "孤寂", "sceneSummary": "寒江孤舟",
                              "confidence": 0.95}, ensure_ascii=False)
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    result = await VisionProviderRouter(httpx.MockTransport(handler)).analyze(b"jpeg")
    assert len(requests) == 2
    assert result.provider == "glm" and result.model == "glm-4.6v-flash"
    assert result.understanding.subjects == ["孤舟"]
