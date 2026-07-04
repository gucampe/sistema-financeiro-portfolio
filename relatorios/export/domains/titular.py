from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone

from django.db.models import Count

from categorizacao.models import LLMRequestLog, RegraCategorizacao
from relatorios.export.base import ExportContext, ExportResult


def build_lgpd_pacote(ctx: ExportContext) -> ExportResult:
    """Pacote ZIP com dados do titular (LGPD art. 18)."""
    usuario = ctx.usuario
    perfil = getattr(usuario, "perfil", None)
    now = datetime.now(timezone.utc)

    perfil_data = {
        "email": usuario.email,
        "nome": usuario.nome,
        "data_nascimento": usuario.data_nascimento.isoformat() if usuario.data_nascimento else None,
        "moeda": getattr(perfil, "moeda", None),
        "ocultar_valores_dashboard": getattr(perfil, "ocultar_valores_dashboard", False),
        "criado_em": usuario.criado_em.isoformat() if usuario.criado_em else None,
    }

    from cartoes.models import Cartao
    from contas.models import Conta
    from relatorios.models import OrcamentoCategoria
    from transacoes.models import Transacao

    contas = list(
        Conta.objects.filter(usuario=usuario).values(
            "id", "nome", "tipo", "icone", "ativa", "criada_em"
        )
    )
    cartoes = list(
        Cartao.objects.filter(usuario=usuario).values(
            "id", "nome", "limite", "dia_fechamento", "dia_vencimento", "ativa"
        )
    )
    orcamentos = list(
        OrcamentoCategoria.objects.filter(usuario=usuario).values(
            "categoria_id", "valor_planejado", "ativo"
        )
    )
    regras = list(
        RegraCategorizacao.objects.filter(usuario=usuario).values(
            "tipo_regra", "padrao", "categoria_id", "origem", "ativa"
        )
    )

    llm_stats = LLMRequestLog.objects.filter(usuario=usuario).aggregate(total=Count("id"))
    llm_uso = {
        "total_chamadas": llm_stats.get("total") or 0,
        "periodo": "desde_cadastro",
    }

    metadata = {
        "versao_pacote": "1.0",
        "gerado_em": now.isoformat(),
        "usuario_id": usuario.pk,
    }
    metadata["sha256"] = hashlib.sha256(
        json.dumps(perfil_data, sort_keys=True).encode()
    ).hexdigest()[:16]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("perfil.json", json.dumps(perfil_data, ensure_ascii=False, indent=2))

        tx_buf = io.StringIO()
        writer = csv.writer(tx_buf)
        writer.writerow(["id", "data", "tipo", "valor", "descricao", "categoria_id", "conta_id"])
        for tx in Transacao.objects.filter(usuario=usuario).iterator():
            writer.writerow([
                tx.pk,
                tx.data.isoformat() if tx.data else "",
                tx.tipo,
                str(tx.valor),
                tx.descricao,
                tx.categoria_id,
                tx.conta_id,
            ])
        zf.writestr("transacoes.csv", tx_buf.getvalue())

        zf.writestr("contas.json", json.dumps(contas, ensure_ascii=False, indent=2, default=str))
        zf.writestr("cartoes.json", json.dumps(cartoes, ensure_ascii=False, indent=2, default=str))
        zf.writestr("orcamentos.csv", _orcamentos_csv(orcamentos))
        zf.writestr(
            "categorizacao_regras.json",
            json.dumps(regras, ensure_ascii=False, indent=2, default=str),
        )
        zf.writestr("llm_uso.json", json.dumps(llm_uso, ensure_ascii=False, indent=2))
        zf.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))

    content = buf.getvalue()
    tx_count = Transacao.objects.filter(usuario=usuario).count()
    nome = f"granago_dados_{usuario.pk}_{now.strftime('%Y%m%d')}.zip"
    return ExportResult(
        content=content,
        nome_arquivo=nome,
        linhas_count=tx_count,
        tamanho_bytes=len(content),
        content_type="application/zip",
    )


def _orcamentos_csv(rows: list) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["categoria_id", "valor_planejado", "ativo"])
    for row in rows:
        w.writerow([row.get("categoria_id"), row.get("valor_planejado"), row.get("ativo")])
    return buf.getvalue()


def count_lgpd_linhas(ctx: ExportContext) -> int:
    from transacoes.models import Transacao

    return Transacao.objects.filter(usuario=ctx.usuario).count()
