from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LLMClassificationResponse:
    categoria_slug: str
    confianca: float
    motivo: str = ""
    merchant_detectado: str = ""
    tipo_merchant: str = "desconhecido"
    ambigua: bool = False
    categorias_alternativas: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> LLMClassificationResponse:
        conf = float(data.get("confianca", 0))
        conf = max(0.0, min(1.0, conf))
        slug = (data.get("categoria_slug") or "").strip().lower()
        if not slug:
            raise ValueError("categoria_slug obrigatório")
        alts = data.get("categorias_alternativas") or []
        if not isinstance(alts, list):
            alts = []
        return cls(
            categoria_slug=slug,
            confianca=conf,
            motivo=str(data.get("motivo", ""))[:500],
            merchant_detectado=str(data.get("merchant_detectado", ""))[:120],
            tipo_merchant=str(data.get("tipo_merchant", "desconhecido"))[:40],
            ambigua=bool(data.get("ambigua", False)),
            categorias_alternativas=[str(a)[:80] for a in alts[:5]],
        )


@dataclass
class LLMRawResult:
    text: str
    model: str
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = ""
    raw: dict | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.text)


LLM_RESPONSE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "categoria_slug": {"type": "string"},
        "confianca": {"type": "number"},
        "motivo": {"type": "string"},
        "merchant_detectado": {"type": "string"},
        "tipo_merchant": {
            "type": "string",
            "enum": [
                "local",
                "pix_pessoal",
                "digital",
                "ambigua",
                "ruido_bancario",
                "desconhecido",
            ],
        },
        "ambigua": {"type": "boolean"},
        "categorias_alternativas": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["categoria_slug", "confianca"],
}
