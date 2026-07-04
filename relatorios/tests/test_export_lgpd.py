"""Testes de exportação LGPD (pacote titular)."""

from __future__ import annotations

import io
import json
import zipfile

import pytest
from django.test import TestCase

from relatorios.export.base import ExportContext
from relatorios.export.domains.titular import build_lgpd_pacote
from relatorios.models import ExportJob
from relatorios.services.export.jobs import executar_job
from usuarios.tests.helpers.seguranca_fixtures import par_usuarios


@pytest.mark.seguranca
class TestExportLgpdTitular(TestCase):
    def test_build_lgpd_pacote_contem_arquivos_esperados(self):
        par = par_usuarios()
        ctx = ExportContext(
            usuario=par.user_a,
            dominio=ExportJob.DOMINIO_TITULAR_LGPD,
            formato=ExportJob.FORMATO_ZIP,
            filtros_raw={},
        )
        result = build_lgpd_pacote(ctx)
        assert result.content_type == "application/zip"
        with zipfile.ZipFile(io.BytesIO(result.content)) as zf:
            names = set(zf.namelist())
            expected = {
                "perfil.json",
                "transacoes.csv",
                "contas.json",
                "cartoes.json",
                "orcamentos.csv",
                "categorizacao_regras.json",
                "llm_uso.json",
                "metadata.json",
            }
            assert expected.issubset(names)
            perfil = json.loads(zf.read("perfil.json"))
        assert perfil["email"] == par.user_a.email

    def test_export_job_titular_lgpd_pronto(self):
        par = par_usuarios()
        from relatorios.services.export.jobs import criar_export_job

        job, msg, _ = criar_export_job(
            usuario=par.user_a,
            dominio=ExportJob.DOMINIO_TITULAR_LGPD,
            formato=ExportJob.FORMATO_ZIP,
            filtros_json="{}",
        )
        assert job is not None, msg
        executar_job(job.pk)
        job.refresh_from_db()
        assert job.status == ExportJob.STATUS_READY
        assert job.arquivo
        assert job.nome_arquivo.endswith(".zip")
