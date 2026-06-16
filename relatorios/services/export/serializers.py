from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from relatorios.services.filtros import RelatorioFiltros, parse_relatorio_filtros


def payload_from_filtros(filtros: RelatorioFiltros) -> dict[str, Any]:
  return {
    "inicio": filtros.data_inicio.isoformat(),
    "fim": filtros.data_fim.isoformat(),
    "conta_ids": list(filtros.conta_ids),
    "categoria_ids": list(filtros.categoria_ids),
    "tipos": list(filtros.tipos),
    "preset": filtros.preset,
    "meio_pagamento": filtros.meio_pagamento,
    "modo_data": filtros.modo_data,
  }


def filtros_from_payload(raw: dict[str, Any]) -> RelatorioFiltros:
  meio = (raw.get("meio_pagamento") or "todos").strip().lower()
  if meio not in ("todos", "debito", "credito"):
    meio = "todos"
  modo = (raw.get("modo_data") or "fluxo").strip().lower()
  if modo not in ("fluxo", "competencia_cartao"):
    modo = "fluxo"
  return RelatorioFiltros(
    data_inicio=datetime.strptime(raw["inicio"], "%Y-%m-%d").date(),
    data_fim=datetime.strptime(raw["fim"], "%Y-%m-%d").date(),
    conta_ids=tuple(raw.get("conta_ids", [])),
    categoria_ids=tuple(raw.get("categoria_ids", [])),
    tipos=tuple(raw.get("tipos", [])),
    preset=raw.get("preset", "custom"),
    meio_pagamento=meio,
    modo_data=modo,
  )


def build_export_filtros_from_request(get_params, usuario) -> RelatorioFiltros:
  return parse_relatorio_filtros(get_params, usuario=usuario)


def serialize_job_filtros(get_params, usuario) -> str:
  filtros = build_export_filtros_from_request(get_params, usuario)
  return json.dumps(payload_from_filtros(filtros))
