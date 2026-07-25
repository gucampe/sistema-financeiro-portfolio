"""
Validação pré-produção — OFX reais + pipeline de categorização.
"""
from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from categorias.models import Categoria
from categorizacao.services.import_suggestions import aplicar_sugestao_em_linha
from categorizacao.services.pipeline import sugerir, sugerir_batch
from categorizacao.services.trust_tiers import classificar_trust_tier
from contas.models import Conta
from transacoes.ofx_parse import parse_ofx_bytes

User = get_user_model()

OFX_REAL_GLOB = "/home/gucampe/Documentos/extratoCC*.ofx"
OFX_DATASET_DIR = "docs/categorizacao/datasets/ofx"


@dataclass
class OfxValidationResult:
    arquivo: str
    total_linhas: int = 0
    com_sugestao: int = 0
    pre_preenchidas: int = 0
    por_nivel: dict = field(default_factory=dict)
    por_fonte: dict = field(default_factory=dict)
    por_tier: dict = field(default_factory=dict)
    latencia_ms: float = 0.0
    amostras: list = field(default_factory=list)
    erro: str | None = None


class Command(BaseCommand):
    help = "Validação pré-produção: OFX reais + cold start + métricas pipeline"

    def add_arguments(self, parser):
        parser.add_argument(
            "--ofx-glob",
            default=OFX_REAL_GLOB,
            help="Glob de OFX reais (default: ~/Documentos/extratoCC*.ofx)",
        )
        parser.add_argument(
            "--output",
            default="docs/categorizacao/registros/validacao_pre_producao.json",
        )
        parser.add_argument("--limit-linhas", type=int, default=0, help="0 = todas")

    def handle(self, *args, **options):
        from glob import glob

        ofx_paths = sorted(Path(p) for p in glob(options["ofx_glob"]))
        dataset_dir = Path(OFX_DATASET_DIR)
        if dataset_dir.is_dir():
            ofx_paths.extend(sorted(dataset_dir.glob("*.ofx")))

        user = self._ensure_cold_start_user()
        conta = Conta.objects.filter(usuario=user).first()
        if not conta:
            conta = Conta.objects.create(usuario=user, nome="Validação", tipo="corrente")

        resultados: list[OfxValidationResult] = []
        for path in ofx_paths:
            if not path.is_file():
                continue
            self.stdout.write(f"  OFX: {path.name}...")
            resultados.append(self._validar_ofx(user, path, options["limit_linhas"]))

        # Aprendizado longitudinal sintético (PIX)
        aprendizado = self._testar_aprendizado_pix(user)

        # Merchant variantes
        merchants = self._testar_variantes_merchant(user)

        payload = {
            "data": str(date.today()),
            "ofx_validados": [asdict(r) for r in resultados],
            "aprendizado_pix": aprendizado,
            "variantes_merchant": merchants,
            "resumo": self._resumo(resultados),
        }

        out = Path(options["output"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Registro: {out}"))
        self._print_resumo(payload["resumo"])

    def _ensure_cold_start_user(self):
        email = "validacao_cold@test.local"
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"nome": "Validação Cold Start"},
        )
        if created:
            user.set_password("validacao123")
            user.save()
        return user

    def _validar_ofx(self, user, path: Path, limit: int) -> OfxValidationResult:
        result = OfxValidationResult(arquivo=path.name)
        try:
            linhas = parse_ofx_bytes(path.read_bytes())
            if limit:
                linhas = linhas[:limit]
            result.total_linhas = len(linhas)

            batch_in = [
                {
                    "descricao": l.descricao,
                    "tipo": l.tipo,
                    "valor": str(l.valor),
                }
                for l in linhas
            ]
            t0 = time.perf_counter()
            sugestoes = sugerir_batch(user, batch_in)
            result.latencia_ms = round((time.perf_counter() - t0) * 1000, 1)

            niveis = Counter()
            fontes = Counter()
            tiers = Counter()

            for linha_ofx, sug in zip(linhas, sugestoes, strict=True):
                item = {"descricao": linha_ofx.descricao, "tipo": linha_ofx.tipo}
                if sug:
                    aplicar_sugestao_em_linha(item, sug)
                    result.com_sugestao += 1
                    if item.get("categoria_sugerida_pre_preencher"):
                        result.pre_preenchidas += 1
                    nivel = item.get("categoria_sugerida_nivel_confianca", "?")
                    fonte = item.get("categoria_sugerida_fonte", "?")
                    niveis[nivel] += 1
                    fontes[fonte] += 1
                    tiers[classificar_trust_tier(linha_ofx.descricao)] += 1
                    if len(result.amostras) < 8:
                        result.amostras.append(
                            {
                                "descricao": linha_ofx.descricao[:60],
                                "categoria": item.get("categoria_sugerida_nome"),
                                "confianca": item.get("categoria_sugerida_confianca"),
                                "fonte": fonte,
                                "nivel": nivel,
                                "pre_preencher": item.get("categoria_sugerida_pre_preencher"),
                            }
                        )

            result.por_nivel = dict(niveis)
            result.por_fonte = dict(fontes)
            result.por_tier = {str(k): v for k, v in tiers.items()}
        except Exception as e:
            result.erro = str(e)
        return result

    def _testar_aprendizado_pix(self, user) -> dict:
        """Simula memória humana + re-sugestão para PIX PF."""
        from categorizacao.models import MemoriaMerchantUsuario
        from categorizacao.services.pix_identity import fingerprint_pix_person

        desc = "PIX ENVIADO                        Matheus Philip Ferreira R"
        cat, _ = Categoria.objects.get_or_create(
            usuario=user, nome="Cuidados pessoais", tipo="despesa", defaults={"ativa": True}
        )

        sug1 = sugerir(user, desc, "despesa", Decimal("50.00"))
        antes = {"categoria": sug1.categoria_nome if sug1 else None, "fonte": sug1.fonte if sug1 else None}

        MemoriaMerchantUsuario.objects.update_or_create(
            usuario=user,
            merchant_key=fingerprint_pix_person(desc),
            defaults={
                "categoria": cat,
                "confirmacoes": 2,
                "correcoes": 0,
                "score": 1.0,
                "origem": "human",
            },
        )

        sug2 = sugerir(user, desc, "despesa", Decimal("50.00"))
        depois = {"categoria": sug2.categoria_nome if sug2 else None, "fonte": sug2.fonte if sug2 else None}

        desc_cpf = "PIX ENVIADO                        54 017 824 Matheus Philip"
        sug3 = sugerir(user, desc_cpf, "despesa", Decimal("30.00"))
        variante = {"categoria": sug3.categoria_nome if sug3 else None, "fonte": sug3.fonte if sug3 else None}

        return {
            "descricao": desc[:40],
            "antes": antes,
            "depois_memoria": depois,
            "variante_cpf": variante,
            "historico_prioritario": depois.get("fonte") in ("historico", "regra_usuario"),
            "sem_familia_arbitraria": depois.get("categoria") != "Família",
        }

    def _testar_variantes_merchant(self, user) -> dict:
        variantes = [
            "AmazonPrimeBR",
            "Amazon Prime",
            "AMZN MKTP",
            "Amazon.com.br",
            "NETFLIX.COM",
            "NETFLIX SERVICOS",
        ]
        out = {}
        for v in variantes:
            sug = sugerir(user, v, "despesa", Decimal("39.90"))
            out[v] = {
                "categoria": sug.categoria_nome if sug else None,
                "fonte": sug.fonte if sug else None,
                "confianca": round(sug.confianca, 3) if sug else None,
            }
        return out

    def _resumo(self, resultados: list[OfxValidationResult]) -> dict:
        total = sum(r.total_linhas for r in resultados)
        com = sum(r.com_sugestao for r in resultados)
        pre = sum(r.pre_preenchidas for r in resultados)
        fontes: Counter = Counter()
        niveis: Counter = Counter()
        for r in resultados:
            fontes.update(r.por_fonte)
            niveis.update(r.por_nivel)
        return {
            "arquivos": len(resultados),
            "total_linhas": total,
            "cobertura_sugestao_pct": round(com / max(total, 1) * 100, 1),
            "taxa_pre_preenchimento_pct": round(pre / max(com, 1) * 100, 1),
            "por_fonte": dict(fontes),
            "por_nivel": dict(niveis),
            "latencia_media_ms": round(
                sum(r.latencia_ms for r in resultados) / max(len(resultados), 1), 1
            ),
            "erros": [r.arquivo for r in resultados if r.erro],
        }

    def _print_resumo(self, resumo: dict):
        self.stdout.write("")
        self.stdout.write(f"Linhas: {resumo['total_linhas']} | Cobertura: {resumo['cobertura_sugestao_pct']}%")
        self.stdout.write(f"Pré-preenchidas: {resumo['taxa_pre_preenchimento_pct']}%")
        self.stdout.write(f"Fontes: {resumo['por_fonte']}")
        self.stdout.write(f"Níveis: {resumo['por_nivel']}")
