"""Normalização da busca da Ajuda — espelhada em `usuarios/static/usuarios/js/ajuda.js`."""

from __future__ import annotations

import unicodedata

from usuarios.ajuda.catalogo import ArtigoAjuda


def normalizar_texto_ajuda(texto: str | None) -> str:
    decomposto = unicodedata.normalize("NFD", texto or "")
    sem_acento = "".join(ch for ch in decomposto if unicodedata.category(ch) != "Mn")
    return sem_acento.casefold()


def artigo_corresponde_busca(artigo: ArtigoAjuda, query: str) -> bool:
    q = normalizar_texto_ajuda(query).strip()
    if not q:
        return True
    haystack = normalizar_texto_ajuda(
        " ".join((artigo.titulo, artigo.resumo, *artigo.tags, artigo.grupo, artigo.tipo))
    )
    return q in haystack
