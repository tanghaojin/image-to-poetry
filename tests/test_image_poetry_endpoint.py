from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.db.session import get_db_session
from app.poetry.schemas import MatchInfo, MatchResponse, PoemResponse, UnderstandingInput
from app.poetry.service import PoetryMatchingService
from app.vision.providers import VisionResult, vision_provider_router
from app.common.services.rate_limiter import fingerprint_rate_limiter
from main import app


def image_fixture() -> bytes:
    output = BytesIO()
    Image.new("RGB", (80, 40), (210, 220, 225)).save(output, "PNG")
    return output.getvalue()


async def fake_session():
    yield object()


def test_unified_image_endpoint_returns_understanding_and_poem(monkeypatch) -> None:
    understanding = UnderstandingInput(
        subjects=["小舟", "寒江"],
        season="冬季",
        time="清晨",
        weather="薄雾",
        mood="孤寂",
        sceneSummary="冬日清晨，小舟停在薄雾笼罩的江面。",
        confidence=0.94,
    )
    calls = {"quota": 0, "vision": 0, "match": 0}

    async def consume(fingerprint: str | None):
        assert fingerprint == "browser_fixture_123456"
        calls["quota"] += 1

    async def analyze(image_bytes: bytes):
        calls["vision"] += 1
        with Image.open(BytesIO(image_bytes)) as prepared:
            assert prepared.format == "JPEG"
            assert prepared.mode == "RGB"
        return VisionResult(understanding, "gemini", "gemini-3.6-flash")

    async def match(self, received: UnderstandingInput, request_id: str | None):
        assert received == understanding
        calls["match"] += 1
        return MatchResponse(
            requestId=request_id,
            understanding=received,
            poem=PoemResponse(
                id="jiang-xue",
                title="江雪",
                author="柳宗元",
                dynasty="唐",
                genre="五言绝句",
                lines=["千山鸟飞绝，", "万径人踪灭。", "孤舟蓑笠翁，", "独钓寒江雪。"],
                selectedLineIndexes=[2, 3],
            ),
            match=MatchInfo(
                score=0.91,
                matchedTags=["孤寂", "舟船", "冬"],
                reason="画面中的孤寂、舟船、冬与《江雪》的意象相合。",
                algorithmVersion="fixture-v1",
            ),
        )

    monkeypatch.setattr(fingerprint_rate_limiter, "consume", consume)
    monkeypatch.setattr(vision_provider_router, "analyze", analyze)
    monkeypatch.setattr(PoetryMatchingService, "match", match)
    app.dependency_overrides[get_db_session] = fake_session
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/poetry/match",
                headers={
                    "X-Device-Fingerprint": "browser_fixture_123456",
                    "X-Request-ID": "req_endpoint_fixture",
                },
                files={"image": ("winter.png", image_fixture(), "image/png")},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["requestId"] == "req_endpoint_fixture"
    assert payload["understanding"]["mood"] == "孤寂"
    assert payload["poem"]["title"] == "江雪"
    assert payload["poem"]["selectedLineIndexes"] == [2, 3]
    assert payload["match"]["algorithmVersion"] == "fixture-v1"
    assert payload["meta"]["processingMs"] >= 0
    assert calls == {"quota": 1, "vision": 1, "match": 1}
