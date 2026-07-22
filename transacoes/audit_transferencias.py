"""
Auditoria de integridade de transferências entre contas.

Valida:
- cada transfer_id com exatamente 2 pernas
- uma origem e um destino
- mesmo valor/data/descrição
- contas distintas
- sem órfãos / incompletos / papéis duplicados
- patrimônio consistente (CON-SALDO-01) por usuário auditado
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Count

from contas.models import Conta
from financial_contracts.saldo_contracts import calcular_saldo_esperado
from transacoes.models import Transacao

User = get_user_model()


@dataclass
class ProblemaTransferencia:
    codigo: str
    transfer_id: str | None
    usuario_id: int | None
    detalhe: str


@dataclass
class ResultadoAuditoriaTransferencias:
    usuarios_auditados: int = 0
    transfer_ids_ok: int = 0
    problemas: list[ProblemaTransferencia] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problemas

    def add(
        self,
        codigo: str,
        *,
        detalhe: str,
        transfer_id=None,
        usuario_id: int | None = None,
    ) -> None:
        self.problemas.append(
            ProblemaTransferencia(
                codigo=codigo,
                transfer_id=str(transfer_id) if transfer_id else None,
                usuario_id=usuario_id,
                detalhe=detalhe,
            )
        )


def auditar_integridade_transferencias(
    *,
    usuario=None,
    verificar_patrimonio: bool = True,
) -> ResultadoAuditoriaTransferencias:
    """
    Varre transferências e reporta inconsistências.
    Se `usuario` for informado, limita ao usuário; senão audita todos com transferências.
    """
    resultado = ResultadoAuditoriaTransferencias()
    qs_base = Transacao.objects.filter(tipo="transferencia").exclude(transfer_id=None)
    if usuario is not None:
        qs_base = qs_base.filter(usuario=usuario)
        usuarios = [usuario]
    else:
        user_ids = qs_base.values_list("usuario_id", flat=True).distinct()
        usuarios = list(User.objects.filter(pk__in=user_ids).order_by("pk"))
        # Também usuários sem transferência mas com contas (só patrimônio) — skip

    resultado.usuarios_auditados = len(usuarios)

    for user in usuarios:
        tids = list(
            {
                tid
                for tid in qs_base.filter(usuario=user).values_list(
                    "transfer_id", flat=True
                )
                if tid is not None
            }
        )
        for tid in tids:
            pernas = list(
                Transacao.objects.filter(
                    usuario=user, transfer_id=tid, tipo="transferencia"
                ).select_related("conta")
            )
            if len(pernas) != 2:
                resultado.add(
                    "perna_count",
                    transfer_id=tid,
                    usuario_id=user.pk,
                    detalhe=f"esperado 2 lançamentos, encontrados {len(pernas)}",
                )
                continue

            papeis = [p.papel_transferencia for p in pernas]
            if sorted(papeis) != ["destino", "origem"]:
                resultado.add(
                    "papeis_invalidos",
                    transfer_id=tid,
                    usuario_id=user.pk,
                    detalhe=f"papéis={papeis}",
                )
                continue

            o = next(p for p in pernas if p.papel_transferencia == "origem")
            d = next(p for p in pernas if p.papel_transferencia == "destino")

            if o.valor != d.valor:
                resultado.add(
                    "valor_divergente",
                    transfer_id=tid,
                    usuario_id=user.pk,
                    detalhe=f"origem={o.valor} destino={d.valor}",
                )
            if o.data != d.data:
                resultado.add(
                    "data_divergente",
                    transfer_id=tid,
                    usuario_id=user.pk,
                    detalhe=f"origem={o.data} destino={d.data}",
                )
            if o.descricao != d.descricao:
                resultado.add(
                    "descricao_divergente",
                    transfer_id=tid,
                    usuario_id=user.pk,
                    detalhe=f"origem={o.descricao!r} destino={d.descricao!r}",
                )
            if o.conta_id == d.conta_id:
                resultado.add(
                    "mesma_conta",
                    transfer_id=tid,
                    usuario_id=user.pk,
                    detalhe=f"conta_id={o.conta_id}",
                )
            if o.conta and o.conta.usuario_id != user.pk:
                resultado.add(
                    "conta_origem_aliena",
                    transfer_id=tid,
                    usuario_id=user.pk,
                    detalhe=f"conta={o.conta_id}",
                )
            if d.conta and d.conta.usuario_id != user.pk:
                resultado.add(
                    "conta_destino_aliena",
                    transfer_id=tid,
                    usuario_id=user.pk,
                    detalhe=f"conta={d.conta_id}",
                )

            problemas_deste = [
                p for p in resultado.problemas if p.transfer_id == str(tid)
            ]
            if not problemas_deste:
                resultado.transfer_ids_ok += 1

        # Duplicidade de papel no mesmo transfer_id (constraint deve impedir, mas audita)
        dups = (
            Transacao.objects.filter(usuario=user, tipo="transferencia")
            .exclude(transfer_id=None)
            .values("transfer_id", "papel_transferencia")
            .annotate(n=Count("id"))
            .filter(n__gt=1)
        )
        for row in dups:
            resultado.add(
                "papel_duplicado",
                transfer_id=row["transfer_id"],
                usuario_id=user.pk,
                detalhe=f"papel={row['papel_transferencia']} n={row['n']}",
            )

        if verificar_patrimonio:
            for conta in Conta.objects.filter(usuario=user, ativa=True):
                esperado = calcular_saldo_esperado(conta)
                atual = conta.saldo_atual_calc
                if atual != esperado:
                    resultado.add(
                        "saldo_inconsistente",
                        usuario_id=user.pk,
                        detalhe=(
                            f"conta={conta.pk} ({conta.nome}): "
                            f"saldo_atual_calc={atual} esperado={esperado}"
                        ),
                    )

            # Patrimônio: soma dos saldos deve bater com ledger
            contas = list(Conta.objects.filter(usuario=user, ativa=True))
            if contas:
                patrimonio_calc = sum(
                    (calcular_saldo_esperado(c) for c in contas), Decimal("0")
                )
                patrimonio_prop = sum(
                    (c.saldo_atual_calc for c in contas), Decimal("0")
                )
                if patrimonio_calc != patrimonio_prop:
                    resultado.add(
                        "patrimonio_inconsistente",
                        usuario_id=user.pk,
                        detalhe=f"calc={patrimonio_calc} prop={patrimonio_prop}",
                    )

    return resultado
