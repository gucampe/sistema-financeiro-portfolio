from __future__ import annotations

import hashlib
import json
import logging
import time
import urllib.error
import urllib.request

from django.conf import settings

from categorizacao.schemas.llm_response import LLMRawResult

logger = logging.getLogger("categorizacao.llm")


class GeminiProvider:
    """Provider Gemini via REST API (sem SDK obrigatório)."""

    def __init__(self, model_id: str | None = None, api_key: str | None = None):
        self.model_id = model_id or getattr(
            settings, "CATEGORIZACAO_LLM_MODEL", "gemini-2.5-flash-lite"
        )
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", "")

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict,
        timeout_s: float,
    ) -> LLMRawResult:
        if not self.api_key:
            return LLMRawResult(
                text="",
                model=self.model_id,
                latency_ms=0,
                error="GEMINI_API_KEY não configurada",
            )

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model_id}:generateContent?key={self.api_key}"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseSchema": schema,
            },
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                raw_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")[:500]
            latency = (time.perf_counter() - t0) * 1000
            logger.warning("Gemini HTTP %s: %s", exc.code, err_body[:200])
            return LLMRawResult(
                text="",
                model=self.model_id,
                latency_ms=latency,
                error=f"HTTP {exc.code}",
                raw={"body": err_body},
            )
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000
            logger.exception("Gemini request failed")
            return LLMRawResult(
                text="",
                model=self.model_id,
                latency_ms=latency,
                error=str(exc)[:200],
            )

        latency = (time.perf_counter() - t0) * 1000
        text = ""
        try:
            candidates = raw_data.get("candidates") or []
            if candidates:
                parts = candidates[0].get("content", {}).get("parts") or []
                if parts:
                    text = parts[0].get("text", "")
        except (KeyError, IndexError, TypeError):
            pass

        usage = raw_data.get("usageMetadata") or {}
        return LLMRawResult(
            text=text,
            model=self.model_id,
            latency_ms=latency,
            input_tokens=int(usage.get("promptTokenCount") or 0),
            output_tokens=int(usage.get("candidatesTokenCount") or 0),
            finish_reason=(raw_data.get("candidates") or [{}])[0].get("finishReason", ""),
            raw=raw_data,
        )


class MockLLMProvider:
    """Provider determinístico para testes e CI."""

    model_id = "mock-llm"

    def __init__(self, responses: dict[str, dict] | None = None):
        self._responses = responses or {}

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict,
        timeout_s: float,
    ) -> LLMRawResult:
        key = hashlib.sha256(user.encode()).hexdigest()[:16]
        for pattern, resp in self._responses.items():
            if pattern in user.lower():
                return LLMRawResult(
                    text=json.dumps(resp, ensure_ascii=False),
                    model=self.model_id,
                    latency_ms=5.0,
                    input_tokens=100,
                    output_tokens=50,
                )
        default = {
            "categoria_slug": "diversos",
            "confianca": 0.6,
            "motivo": "Mock fallback",
            "merchant_detectado": "",
            "tipo_merchant": "desconhecido",
            "ambigua": False,
            "categorias_alternativas": [],
        }
        return LLMRawResult(
            text=json.dumps(default),
            model=self.model_id,
            latency_ms=5.0,
            input_tokens=80,
            output_tokens=40,
        )
