from __future__ import annotations

import logging

from django.db.models import Q

from categorias.models import Categoria
from categorizacao.services.layers.ml_classico import salvar_modelo
from categorizacao.services.normalizer import normalizar_texto
from transacoes.models import Transacao

logger = logging.getLogger(__name__)

MIN_AMOSTRAS_DEFAULT = 50


def treinar_modelo_usuario(usuario, min_amostras: int = MIN_AMOSTRAS_DEFAULT) -> bool:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
    except ImportError:
        logger.warning("scikit-learn não instalado; treino ML ignorado.")
        return False

    transacoes = (
        Transacao.objects.filter(usuario=usuario)
        .exclude(tipo="ajuste")
        .select_related("categoria")
        .order_by("-data")[:2000]
    )
    textos = []
    labels = []
    cat_map = {}
    for tx in transacoes:
        if not tx.descricao or not tx.categoria_id:
            continue
        if not tx.categoria.ativa:
            continue
        textos.append(normalizar_texto(tx.descricao))
        labels.append(tx.categoria_id)
        cat_map[str(tx.categoria_id)] = tx.categoria.nome

    if len(textos) < min_amostras:
        return False

    if len(set(labels)) < 2:
        return False

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
        ("clf", LogisticRegression(max_iter=500, multi_class="auto")),
    ])

    try:
        pipeline.fit(textos, labels)
    except Exception:
        logger.exception("Falha no treino ML usuario=%s", usuario.pk)
        return False

    from sklearn.model_selection import cross_val_score
    import numpy as np

    try:
        scores = cross_val_score(pipeline, textos, labels, cv=min(3, len(set(labels))))
        accuracy = float(np.mean(scores))
    except Exception:
        accuracy = 0.0

    metricas = {
        "accuracy": round(accuracy, 4),
        "categoria_map": cat_map,
        "amostras": len(textos),
    }
    salvar_modelo(usuario, pipeline, len(textos), metricas)
    return True
