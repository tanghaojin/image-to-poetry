from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from loguru import logger

from app.poetry.schemas import UnderstandingInput
from core.config import settings


GLM_ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
GEMINI_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
ANALYSIS_PROMPT = """请只根据这张图片分析画面，不要虚构具体地点、人物身份或图片之外的故事。
只返回一个 JSON 对象，不要使用 Markdown 代码块，不要附加解释。格式必须是：
{"subjects":["主体景物，最多5个"],"season":"季节，不明确时写无法确定","time":"时段，不明确时写无法确定","weather":"天气，不明确时写无法确定","mood":"只从宁静、孤寂、思乡、思念、惜别、壮阔、喜悦、感伤中选最可信的一种","sceneSummary":"40个汉字以内的客观画面总结","confidence":0.0}
confidence 必须是 0 到 1 之间的数字。"""

ProviderName = Literal["gemini", "glm"]
FailureReason = Literal["auth", "busy", "unavailable", "network", "response-format", "request"]


@dataclass(frozen=True)
class VisionResult:
    understanding: UnderstandingInput
    provider: ProviderName
    model: str


class VisionProviderError(Exception):
    def __init__(self, reason: FailureReason, provider: ProviderName, model: str) -> None:
        super().__init__(reason)
        self.reason = reason
        self.provider = provider
        self.model = model


def parse_understanding(content: Any) -> UnderstandingInput:
    if isinstance(content, list):
        content = "".join(str(item.get("text", "")) for item in content if isinstance(item, dict))
    if not isinstance(content, str):
        raise ValueError("response content is not text")
    matched = re.search(r"\{[\s\S]*\}", content)
    if not matched:
        raise ValueError("JSON object missing")
    raw = json.loads(matched.group(0))
    if not isinstance(raw, dict):
        raise ValueError("JSON result is not an object")
    subjects = raw.get("subjects") if isinstance(raw.get("subjects"), list) else []
    raw["subjects"] = [str(item).strip()[:20] for item in subjects if str(item).strip()][:5]
    for field in ("season", "time", "weather"):
        if not isinstance(raw.get(field), str) or not raw[field].strip():
            raw[field] = "无法确定"
    if not isinstance(raw.get("mood"), str) or not raw["mood"].strip():
        raw["mood"] = "意境不明确"
    if not isinstance(raw.get("sceneSummary"), str) or not raw["sceneSummary"].strip():
        raw["sceneSummary"] = "画面信息较少，暂未形成明确描述。"
    raw["sceneSummary"] = raw["sceneSummary"].strip()[:40]
    try:
        raw["confidence"] = min(1.0, max(0.0, float(raw.get("confidence", 0))))
    except (TypeError, ValueError):
        raw["confidence"] = 0.0
    return UnderstandingInput.model_validate(raw)


class VisionProviderRouter:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.transport = transport

    async def analyze(self, image_bytes: bytes) -> VisionResult:
        disabled: set[ProviderName] = set()
        attempted = 0
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.vision_read_timeout, connect=settings.vision_connect_timeout),
            transport=self.transport,
        ) as client:
            for model in settings.vision_models:
                provider: ProviderName = "gemini" if model.startswith("gemini-") else "glm"
                key = settings.google_ai_api_key if provider == "gemini" else settings.big_model_api_key
                if not key or provider in disabled:
                    continue
                attempted += 1
                try:
                    understanding = await (
                        self._request_gemini(client, key, model, image_bytes)
                        if provider == "gemini"
                        else self._request_glm(client, key, model, image_bytes)
                    )
                    logger.info("Vision model succeeded: provider={} model={}", provider, model)
                    return VisionResult(understanding, provider, model)
                except VisionProviderError as exc:
                    logger.warning("Vision model failed: provider={} model={} reason={}", provider, model, exc.reason)
                    if exc.reason == "auth":
                        disabled.add(provider)
        if attempted == 0:
            logger.error("No configured vision provider is available")
        raise VisionProviderError("unavailable", "glm", "none")

    async def _request_glm(self, client: httpx.AsyncClient, key: str, model: str, image_bytes: bytes) -> UnderstandingInput:
        data_url = "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode("ascii")
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": ANALYSIS_PROMPT},
            ]}],
            "stream": False,
            "max_tokens": 2048 if "thinking" in model else 512,
        }
        if model == "glm-4.6v-flash":
            body["thinking"] = {"type": "disabled"}
        response = await self._post(client, GLM_ENDPOINT, {"Authorization": f"Bearer {key}"}, body, "glm", model)
        try:
            return parse_understanding(response["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise VisionProviderError("response-format", "glm", model) from exc

    async def _request_gemini(self, client: httpx.AsyncClient, key: str, model: str, image_bytes: bytes) -> UnderstandingInput:
        body = {
            "contents": [{"role": "user", "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode("ascii")}},
                {"text": ANALYSIS_PROMPT},
            ]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 2048, "responseMimeType": "application/json"},
        }
        response = await self._post(client, f"{GEMINI_ROOT}/{model}:generateContent", {"x-goog-api-key": key}, body,
                                    "gemini", model)
        try:
            parts = response["candidates"][0]["content"]["parts"]
            content = "".join(str(part.get("text", "")) for part in parts if not part.get("thought"))
            return parse_understanding(content)
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise VisionProviderError("response-format", "gemini", model) from exc

    async def _post(self, client: httpx.AsyncClient, url: str, headers: dict[str, str], body: dict[str, Any],
                    provider: ProviderName, model: str) -> dict[str, Any]:
        try:
            response = await client.post(url, headers={**headers, "Content-Type": "application/json"}, json=body)
        except httpx.TimeoutException as exc:
            raise VisionProviderError("network", provider, model) from exc
        except httpx.HTTPError as exc:
            raise VisionProviderError("network", provider, model) from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise VisionProviderError("response-format" if response.is_success else "request", provider, model) from exc
        if not response.is_success or payload.get("error"):
            if response.status_code in {401, 403}:
                reason: FailureReason = "auth"
            elif response.status_code in {404}:
                reason = "unavailable"
            elif response.status_code in {429, 503}:
                reason = "busy"
            else:
                reason = "request"
            raise VisionProviderError(reason, provider, model)
        return payload


vision_provider_router = VisionProviderRouter()
