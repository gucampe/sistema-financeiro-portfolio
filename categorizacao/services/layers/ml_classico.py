from __future__ import annotations

import io
import logging

import joblib
from django.utils import timezone

from categorizacao.models import ModeloClassificacaoUsuario
from categorizacao.types import ContextoCategorizacao, PredicaoCategorizacao

logger = logging.getLogger(__name__)

MIN_PROBA = 0.55


def classificar_ml(ctx: ContextoCategorizacao) -> PredicaoCategorizacao | None:
    try:
        modelo_obj = ModeloClassificacaoUsuario.objects.get(usuario=ctx.usuario)
    except ModeloClassificacaoUsuario.DoesNotExist:
        return None

    if not modelo_obj.artefato or modelo_obj.amostras_treino < 50:
        return None

    try:
        pipeline = joblib.load(io.BytesIO(modelo_obj.artefato))
    except Exception:
        logger.exception("Falha ao carregar modelo ML usuario=%s", ctx.usuario.pk)
        return None

    texto = ctx.descricao_normalizada or ctx.descricao
    if not texto:
        return None

    try:
        proba = pipeline.predict_proba([texto])[0]
        classes = pipeline.classes_
    except Exception:
        logger.exception("Falha na predição ML usuario=%s", ctx.usuario.pk)
        return None

    idx = proba.argmax()
    confianca = float(proba[idx])
    if confianca < MIN_PROBA:
        return None

    cat_id = int(classes[idx])
    cat_map = modelo_obj.metricas.get("categoria_map", {})
    cat_nome = cat_map.get(str(cat_id), cat_map.get(cat_id, "Categoria"))

    return PredicaoCategorizacao(
        categoria_id=cat_id,
        categoria_nome=cat_nome,
        confianca=confianca,
        fonte="ml",
        merchant_key=ctx.merchant_key or None,
        explicacao="Sugestão baseada no seu histórico de transações",
    )


def salvar_modelo(usuario, pipeline, amostras: int, metricas: dict) -> ModeloClassificacaoUsuario:
    buf = io.BytesIO()
    joblib.dump(pipeline, buf)
    existente = ModeloClassificacaoUsuario.objects.filter(usuario=usuario).first()
    nova_versao = (existente.versao if existente else 0) + 1
    obj, _ = ModeloClassificacaoUsuario.objects.update_or_create(
        usuario=usuario,
        defaults={
            "artefato": buf.getvalue(),
            "versao": nova_versao,
            "amostras_treino": amostras,
            "metricas": metricas,
            "treinado_em": timezone.now(),
        },
    )
    return obj
