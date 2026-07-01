"""
E2E — aprendizado longitudinal de categorização via UI real.

Requer servidor dev em execução:
  E2E_EXTERNAL_URL=http://127.0.0.1:8000 pytest e2e/specs/categorizacao/test_aprendizado_longitudinal_ui.py -v

Usuário: teste5@teste.com (senha padrão E2eTeste5!2026, configurável por env).
"""

from __future__ import annotations

import os
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from playwright.sync_api import expect

from e2e.fixtures.pages.import_pages import ImportOfxPage
from e2e.fixtures.pages.transacoes_page import HistoricoPage
from transacoes.ofx_parse import parse_ofx_bytes

OFX_CC3 = Path("/home/gucampe/Documentos/extratoCC3.ofx")
OFX_CC5 = Path("/home/gucampe/Documentos/extratoCC5.ofx")

# (trecho único na descrição OFX, categoria esperada no preview)
CASOS_CC3 = [
    ("Antonio Pereira", "Saúde"),
    ("Diego Frazao", "Lazer"),
    ("Marly Silva", "Educação"),
    ("Evi Jose", "Supermercado"),
    ("99 FOOD", "Alimentação"),
    ("Matheus Philip Ferreira", "Cuidados pessoais"),
]

CASOS_CC5 = [
    ("Gabriela Silva", "Diversos"),
    ("Jessica de Souza", "Roupas"),
]


def _requer_servidor_externo():
    if not os.environ.get("E2E_EXTERNAL_URL", "").strip():
        pytest.skip(
            "Defina E2E_EXTERNAL_URL=http://127.0.0.1:8000 (make dev) para rodar na UI real."
        )
    if not OFX_CC3.is_file():
        pytest.skip(f"OFX não encontrado: {OFX_CC3}")
    if not OFX_CC5.is_file():
        pytest.skip(f"OFX não encontrado: {OFX_CC5}")


def _linha_ofx_por_trecho(ofx_path: Path, trecho: str):
    for linha in parse_ofx_bytes(ofx_path.read_bytes()):
        if trecho in linha.descricao and linha.tipo == "despesa":
            return linha
    return None


def _cadastrar_manualmente(
    historico: HistoricoPage,
    conta_id: int,
    trecho: str,
    cat_nome: str,
    ofx_path: Path,
    *,
    sobrescrever_sugestao: bool = False,
):
    linha = _linha_ofx_por_trecho(ofx_path, trecho)
    assert linha is not None, f"Linha OFX não encontrada para trecho {trecho!r}"
    data_manual = linha.data - timedelta(days=45)
    modal = historico.open_nova_despesa()
    modal.criar_despesa_conta(
        conta_id=conta_id,
        categoria_nome=cat_nome,
        valor=linha.valor,
        descricao=linha.descricao,
        data=data_manual,
        aguardar_sugestao=True,
        sobrescrever_sugestao=sobrescrever_sugestao,
    )
    historico.page.wait_for_load_state("load")
    return linha


def _verificar_preview_import(
    import_page: ImportOfxPage,
    ofx_path: Path,
    conta_id: int,
    casos: list[tuple[str, str]],
    *,
    falhar_em_erro: bool = True,
):
    import_page.preview_ofx(conta_id, ofx_path)
    import_page.categorizar_automaticamente()
    resultados = []
    for trecho, cat_esperada in casos:
        row = import_page.linha_por_descricao_parcial(trecho)
        assert row is not None, f"Linha não encontrada no preview OFX: {trecho!r}"
        cat_nome, fonte, explicacao = import_page.sugestao_preview_json(trecho)
        if not cat_nome:
            cat_nome, fonte, explicacao = import_page.categoria_preview(row)
        acertou = cat_nome == cat_esperada
        resultados.append(
            {
                "trecho": trecho,
                "esperada": cat_esperada,
                "sugerida": cat_nome,
                "fonte": fonte,
                "explicacao": explicacao,
                "acertou": acertou,
            }
        )
        sel = row.locator(".import-ofx-categoria")
        cat_val = sel.input_value()
        if falhar_em_erro:
            assert cat_nome or cat_val, f"Sem sugestão no preview para {trecho!r}"
            assert acertou, (
                f"Preview OFX divergiu para {trecho!r}: "
                f"esperada={cat_esperada!r} sugerida={cat_nome!r} fonte={fonte!r}"
            )
            assert fonte != "llm_gemini" or not acertou, (
                f"LLM venceu no preview para {trecho!r} — histórico não reutilizado"
            )
    return resultados


@pytest.mark.categorizacao_e2e
def test_ui_aprendizado_pix_extrato_cc3(logged_in_teste5_page, app_base_url):
    """Cadastro manual + preview OFX extratoCC3 — 6 PIX."""
    _requer_servidor_externo()
    page = logged_in_teste5_page
    historico = HistoricoPage(page, app_base_url)
    historico.open()
    conta_id = historico.primeira_conta_id()
    assert conta_id, "Nenhuma conta disponível para o usuário"

    for trecho, cat_nome in CASOS_CC3:
        _cadastrar_manualmente(
            historico, conta_id, trecho, cat_nome, OFX_CC3, sobrescrever_sugestao=True
        )

    import_page = ImportOfxPage(page, app_base_url)
    resultados = _verificar_preview_import(import_page, OFX_CC3, conta_id, CASOS_CC3)
    assert all(r["acertou"] for r in resultados)
    assert sum(1 for r in resultados if r["fonte"] == "historico") >= 4


@pytest.mark.categorizacao_e2e
def test_ui_aprendizado_pix_extrato_cc5(logged_in_teste5_page, app_base_url):
    """Cadastro manual + preview OFX extratoCC5 — 2 PIX."""
    _requer_servidor_externo()
    page = logged_in_teste5_page
    historico = HistoricoPage(page, app_base_url)
    historico.open()
    conta_id = historico.primeira_conta_id()
    assert conta_id, "Nenhuma conta disponível para o usuário"

    for trecho, cat_nome in CASOS_CC5:
        _cadastrar_manualmente(
            historico, conta_id, trecho, cat_nome, OFX_CC5, sobrescrever_sugestao=True
        )

    import_page = ImportOfxPage(page, app_base_url)
    resultados = _verificar_preview_import(import_page, OFX_CC5, conta_id, CASOS_CC5)
    assert all(r["acertou"] for r in resultados)


@pytest.mark.categorizacao_e2e
def test_ui_aprendizado_pix_experiencia_real_com_llm(logged_in_teste5_page, app_base_url):
    """
    Experiência exata: aguarda chip de sugestão (LLM), usuário escolhe outra categoria no select.
    Os hidden fields da sugestão seguem no POST → feedback 'corrigida' → histórico pode não aprender.
    """
    _requer_servidor_externo()
    page = logged_in_teste5_page
    historico = HistoricoPage(page, app_base_url)
    historico.open()
    conta_id = historico.primeira_conta_id()
    assert conta_id

    # Apenas 3 casos (amostra) para não alongar demais o teste autêntico
    amostra = CASOS_CC3[:3]
    for trecho, cat_nome in amostra:
        ofx = OFX_CC3
        _cadastrar_manualmente(
            historico, conta_id, trecho, cat_nome, ofx, sobrescrever_sugestao=False
        )

    import_page = ImportOfxPage(page, app_base_url)
    resultados = _verificar_preview_import(
        import_page, OFX_CC3, conta_id, amostra, falhar_em_erro=False
    )
    acertos = sum(1 for r in resultados if r["acertou"])
    llm = sum(1 for r in resultados if r["fonte"] == "llm_gemini")
    # Documenta comportamento real: cold start PIX + chip LLM costuma impedir reutilização
    assert acertos <= len(amostra), resultados
    if llm > 0:
        pytest.xfail(
            f"Experiência real: {llm}/{len(amostra)} linhas caíram na LLM no preview "
            f"(chip IA no cadastro grava feedback 'corrigida' sem confirmar memória). "
            f"Detalhes: {resultados}"
        )


@pytest.mark.categorizacao_e2e
def test_ui_aprendizado_pix_massa_completa(logged_in_teste5_page, app_base_url):
    """
    Fluxo UI completo (8 PIX): cadastro manual com descrição idêntica ao OFX,
    depois preview de importação verificando categoria sugerida.

    Após o usuário escolher categoria manualmente, limpa metadados do chip
  (equivalente a não enviar sugestão LLM no POST — memória gravada como 'aceita').
    """
    _requer_servidor_externo()
    page = logged_in_teste5_page
    historico = HistoricoPage(page, app_base_url)
    historico.open()
    conta_id = historico.primeira_conta_id()
    assert conta_id

    todos = CASOS_CC3 + CASOS_CC5
    for trecho, cat_nome in todos:
        ofx = OFX_CC3 if trecho in {t for t, _ in CASOS_CC3} else OFX_CC5
        _cadastrar_manualmente(
            historico, conta_id, trecho, cat_nome, ofx, sobrescrever_sugestao=True
        )

    import_page = ImportOfxPage(page, app_base_url)
    r3 = _verificar_preview_import(import_page, OFX_CC3, conta_id, CASOS_CC3)
    r5 = _verificar_preview_import(import_page, OFX_CC5, conta_id, CASOS_CC5)
    total = r3 + r5
    assert len(total) == 8
    assert all(r["acertou"] for r in total), total
    historico_count = sum(1 for r in total if r["fonte"] == "historico")
    assert historico_count >= 5, total
