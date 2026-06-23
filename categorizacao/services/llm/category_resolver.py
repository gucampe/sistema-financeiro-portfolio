from __future__ import annotations

from django.db.models import Q

from categorias.models import Categoria
from categorizacao.schemas.llm_response import LLMClassificationResponse
from categorizacao.services.llm.prompt_builder import slugify_categoria
from categorizacao.types import PredicaoCategorizacao


def listar_categorias_usuario(usuario, tipo: str) -> list[dict]:
    tipo_filtro = tipo if tipo in ("receita", "despesa") else "despesa"
    if tipo == "ajuste":
        tipo_filtro = "receita"
    qs = (
        Categoria.objects.filter(ativa=True, tipo=tipo_filtro)
        .filter(Q(usuario=usuario) | Q(padrao=True))
        .distinct()
    )
    seen_slugs: set[str] = set()
    out: list[dict] = []
    for cat in qs.order_by("nome"):
        slug = slugify_categoria(cat.nome)
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        out.append({"id": cat.pk, "nome": cat.nome, "slug": slug, "tipo": cat.tipo})
    return out


def categorias_hash(categorias: list[dict]) -> str:
    import hashlib

    payload = "|".join(f"{c['id']}:{c['slug']}" for c in sorted(categorias, key=lambda x: x["id"]))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def resolve_categoria(
    usuario,
    llm_resp: LLMClassificationResponse,
    tipo: str,
) -> Categoria | None:
    cats = listar_categorias_usuario(usuario, tipo)
    slug_map = {c["slug"]: c for c in cats}
    nome_map = {c["nome"].lower(): c for c in cats}

    if llm_resp.categoria_slug in slug_map:
        return Categoria.objects.filter(pk=slug_map[llm_resp.categoria_slug]["id"]).first()

    for cat in cats:
        if slugify_categoria(cat["nome"]) == llm_resp.categoria_slug:
            return Categoria.objects.filter(pk=cat["id"]).first()

    for alt in llm_resp.categorias_alternativas:
        alt_slug = slugify_categoria(alt)
        if alt_slug in slug_map:
            return Categoria.objects.filter(pk=slug_map[alt_slug]["id"]).first()

    return None


def llm_response_to_predicao(
    llm_resp: LLMClassificationResponse,
    categoria: Categoria,
    merchant_key: str | None,
    *,
    llm_contexto: dict | None = None,
) -> PredicaoCategorizacao:
    explicacao = f"Sugestão por IA: {llm_resp.motivo}" if llm_resp.motivo else "Sugestão por IA"
    if len(explicacao) > 250:
        explicacao = explicacao[:247] + "..."
    return PredicaoCategorizacao(
        categoria_id=categoria.pk,
        categoria_nome=categoria.nome,
        confianca=llm_resp.confianca,
        fonte="llm_gemini",
        merchant_key=merchant_key or llm_resp.merchant_detectado or None,
        explicacao=explicacao,
        contexto=llm_contexto or {},
    )
