"""Dicas de primeiro uso — id estável + versão inteira (cartao_v1 conceitual)."""

from __future__ import annotations

from dataclasses import dataclass

from usuarios.models import Perfil


@dataclass(frozen=True)
class DicaPrimeiroUso:
    id: str
    versao: int
    titulo: str
    corpo: str
    cta_label: str
    artigo_id: str


DICAS: dict[str, DicaPrimeiroUso] = {
    "cartao": DicaPrimeiroUso(
        id="cartao",
        versao=1,
        titulo="Cartão de crédito funciona diferente de uma conta",
        corpo="A compra aparece na fatura. O dinheiro sai da conta quando você paga essa fatura.",
        cta_label="Entender cartões",
        artigo_id="cartao",
    ),
}


def deve_mostrar_dica(perfil: Perfil, dica_id: str) -> bool:
    dica = DICAS.get(dica_id)
    if dica is None:
        return False
    dispensadas = perfil.dicas_dispensadas or {}
    try:
        vista = int(dispensadas.get(dica_id, 0))
    except (TypeError, ValueError):
        vista = 0
    return vista < dica.versao


def marcar_dica_dispensada(perfil: Perfil, dica_id: str) -> DicaPrimeiroUso | None:
    dica = DICAS.get(dica_id)
    if dica is None:
        return None
    atual = dict(perfil.dicas_dispensadas or {})
    try:
        vista = int(atual.get(dica_id, 0))
    except (TypeError, ValueError):
        vista = 0
    if vista < dica.versao:
        atual[dica_id] = dica.versao
        perfil.dicas_dispensadas = atual
        perfil.save(update_fields=["dicas_dispensadas"])
    return dica
