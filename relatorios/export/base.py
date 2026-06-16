from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class ExportColumn:
    key: str
    label: str
    formatter: Callable[[Any], Any] | None = None


@dataclass
class ExportContext:
    usuario: Any
    dominio: str
    formato: str
    filtros_raw: dict[str, Any]
    job_id: int | None = None

    def is_cancelled(self) -> bool:
        if not self.job_id:
            return False
        from relatorios.models import ExportJob

        job = ExportJob.objects.filter(pk=self.job_id).only("status", "cancelado_em").first()
        if not job:
            return True
        return job.status == ExportJob.STATUS_CANCELLED or job.cancelado_em is not None


@dataclass
class ExportDataset:
    titulo: str
    colunas: list[ExportColumn]
    linhas: Iterable[dict[str, Any]]
    metadados: dict[str, Any] = field(default_factory=dict)

    def column_keys(self) -> list[str]:
        return [c.key for c in self.colunas]

    def column_labels(self) -> list[str]:
        return [c.label for c in self.colunas]


@dataclass
class ExportResult:
    content: bytes
    nome_arquivo: str
    linhas_count: int
    tamanho_bytes: int
    content_type: str
