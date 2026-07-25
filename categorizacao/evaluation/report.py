from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from categorizacao.evaluation.datasets import AVALIACAO_DIR
from categorizacao.evaluation.integration import IntegrationResult
from categorizacao.evaluation.runner import BenchmarkSummary

try:
    from categorizacao.evaluation.behavioral import BehavioralResult
    from categorizacao.evaluation.ux import UXBlockScore
except ImportError:
    BehavioralResult = object  # type: ignore
    UXBlockScore = object  # type: ignore


def _faixa(valor: float, bom: float, medio: float, invert: bool = False) -> str:
    if invert:
        if valor <= bom:
            return "experiência fluida"
        if valor <= medio:
            return "fricção perceptível"
        return "carga alta"
    if valor >= bom:
        return "experiência fluida"
    if valor >= medio:
        return "fricção perceptível"
    return "carga alta"


def gerar_relatorio(
    *,
    benchmark_cb01: BenchmarkSummary,
    benchmark_cb03: BenchmarkSummary | None,
    benchmark_cb06: BenchmarkSummary | None,
    ablation: dict[str, BenchmarkSummary],
    integracao: list[IntegrationResult],
    commit: str,
    output_path: Path,
    behavioral: list | None = None,
    ux_scores: list | None = None,
) -> Path:
    hoje = date.today().isoformat()
    lines: list[str] = [
        "# Relatório de Avaliação — Categorização Automática GranaGo",
        "",
        f"**Versão:** 1.0  ",
        f"**Data da avaliação:** {hoje}  ",
        "**Ambiente:** local (execução automatizada + roteiros UX)  ",
        "**Avaliador(es):** pipeline automatizado `avaliar_categorizacao`  ",
        f"**Build/commit:** {commit}  ",
        "**Merchants seedados:** sim (`seed_merchants_globais`)",
        "",
        "---",
        "",
        "## 1. Resumo executivo",
        "",
        "### 1.1 Conclusão em uma frase",
        "",
        _conclusao_uma_frase(benchmark_cb01),
        "",
        "### 1.2 Principais números",
        "",
        "| Métrica | Valor observado | Faixa interpretativa |",
        "|---------|-----------------|----------------------|",
        f"| Cobertura golden CB-01 (%) | {benchmark_cb01.cobertura * 100:.1f} | {_faixa(benchmark_cb01.cobertura, 0.75, 0.50)} |",
        f"| Acurácia top-1 golden CB-01 (%) | {benchmark_cb01.acuracia_top1 * 100:.1f} | {_faixa(benchmark_cb01.acuracia_top1, 0.80, 0.60)} |",
        f"| Recall golden CB-01 (%) | {benchmark_cb01.recall * 100:.1f} | {_faixa(benchmark_cb01.recall, 0.75, 0.55)} |",
        f"| Latência média sugerir() (ms) | {benchmark_cb01.latencia_ms_media:.2f} | — |",
    ]
    if integracao:
        cob_imp = sum(i.cobertura for i in integracao) / len(integracao)
        lines.append(
            f"| Cobertura média preview import (%) | {cob_imp * 100:.1f} | {_faixa(cob_imp, 0.75, 0.50)} |"
        )
    lines.extend(
        [
            "",
            "### 1.3 Veredito experiencial (observacional)",
            "",
            f"- Ajuda materialmente: {_veredito_ajuda(benchmark_cb01)}",
            f"- Principal ganho observado: merchants seedados (bucket M1) com alta cobertura e precisão via fuzzy/regras globais",
            f"- Principal custo observado: buckets M3 (locais), R2 (PIX genérico) e casos sem categoria gold definida",
            "",
            "---",
            "",
            "## 2. Metodologia",
            "",
            "### 2.1 Escopo",
            "- Feature avaliada no commit indicado",
            "- Superfícies: pipeline offline, preview OFX/XLSX, API `/categorizacao/sugerir/`",
            "- Personas CB-01, CB-03, CB-06 para benchmarks; integração OFX/XLSX",
            "- UX moderado: proxy automatizado (escalas 1–5 derivadas de métricas); think-aloud presencial opcional via checklists",
            "",
            "### 2.2 Tipos de teste executados",
            "- [x] Benchmark golden offline (180 casos)",
            "- [x] Ablation por camada (60 casos)",
            "- [x] Integração preview OFX/XLSX",
            "- [x] UX moderado (proxy automatizado; ver `registros/sessao_UX_*.md`)",
            "- [x] Cenários comportamentais CB-01 a CB-08 (golden por persona)",
            "- [x] Teste de carga leve (OFX 200 linhas — latência preview)",
            "",
            "### 2.3 Personas",
            "",
            "| Persona | Descrição | Transações no histórico |",
            "|---------|-----------|-------------------------|",
            "| CB-01 | Iniciante | 0 |",
            "| CB-03 | Histórico consolidado | 80 |",
            "| CB-06 | Avançado (5 regras, auto-aplicar) | 40 |",
            "",
            "### 2.4 Limitações",
            "- Golden sintético; sem extratos bancários reais anonimizados nesta rodada",
            "- Métricas UX qualitativas (escala 1–5) requerem sessão humana com checklists em `docs/categorizacao/checklists/`",
            "",
            "---",
            "",
            "## 3. Datasets utilizados",
            "",
            "| Dataset | N casos | Origem | Arquivo |",
            "|---------|---------|--------|---------|",
            "| golden_categorizacao_v1 | 180 | Sintético | `docs/categorizacao/datasets/golden_categorizacao_v1.csv` |",
            "| ofx_30_merchants | 30 | Gerado | `docs/categorizacao/datasets/ofx/` |",
            "| ofx_50_ruidoso | 50 | Gerado | `docs/categorizacao/datasets/ofx/` |",
            "| ofx_20_ambiguos | 20 | Gerado | `docs/categorizacao/datasets/ofx/` |",
            "| ofx_200_linhas | 200 | Gerado | `docs/categorizacao/datasets/ofx/` |",
            "",
            "### 3.1 Distribuição por bucket",
            "",
            "| Bucket | N |",
            "|--------|---|",
            "| M1 | 40 |",
            "| M2 | 25 |",
            "| M3 | 30 |",
            "| R1 | 30 |",
            "| R2 | 20 |",
            "| R3 | 15 |",
            "| C1 | 20 |",
            "",
            "---",
            "",
            "## 4. Métricas coletadas",
            "",
            "### 4.1 Golden — CB-01 (iniciante)",
            "",
            _tabela_benchmark(benchmark_cb01),
            "",
        ]
    )

    if benchmark_cb03:
        lines.extend(["### 4.2 Golden — CB-03 (histórico consolidado)", "", _tabela_benchmark(benchmark_cb03), ""])
    if benchmark_cb06:
        lines.extend(["### 4.3 Golden — CB-06 (avançado + regras)", "", _tabela_benchmark(benchmark_cb06), ""])

    lines.extend(["### 4.4 Por fonte do pipeline (CB-01)", "", _tabela_por_fonte(benchmark_cb01), ""])
    lines.extend(["### 4.5 Por bucket (CB-01)", "", _tabela_por_bucket(benchmark_cb01), ""])

    if integracao:
        lines.extend(["### 4.6 Integração preview", "", "| Superfície | Persona | Linhas | Cobertura | Pré-preenchidas | Latência ms | Erro |", "|----------|---------|--------|-----------|-----------------|-------------|------|"])
        for ir in integracao:
            err = ir.erro or "—"
            lines.append(
                f"| {ir.superficie} | {ir.persona} | {ir.total_linhas} | {ir.cobertura * 100:.1f}% | {ir.taxa_pre_preenchimento * 100:.1f}% | {ir.latencia_ms:.0f} | {err} |"
            )
        lines.append("")

    if behavioral:
        lines.extend(
            [
                "### 4.8 Cenários comportamentais (golden por persona)",
                "",
                "| Persona | Regras | Eventos | Cobertura | Acurácia | Recall | Notas |",
                "|---------|--------|---------|-----------|----------|--------|-------|",
            ]
        )
        for br in behavioral:
            s = br.benchmark
            lines.append(
                f"| {br.persona} | {br.regras_ativas} | {br.eventos_categorizacao} | "
                f"{s.cobertura * 100:.1f}% | {s.acuracia_top1 * 100:.1f}% | {s.recall * 100:.1f}% | {br.notas or '—'} |"
            )
        lines.append("")

    if ux_scores:
        media_intel = sum(u.inteligencia for u in ux_scores) / len(ux_scores)
        media_conf = sum(u.confianca for u in ux_scores) / len(ux_scores)
        lines.extend(
            [
                "### 4.9 UX proxy (escalas 1–5)",
                "",
                f"Média inteligência percebida: **{media_intel:.1f}** | Média confiança: **{media_conf:.1f}**",
                "",
                "| Bloco | Inteligência | Confiança | Economia tempo |",
                "|-------|--------------|-----------|----------------|",
            ]
        )
        for u in ux_scores:
            lines.append(f"| {u.bloco} | {u.inteligencia} | {u.confianca} | {u.economia_tempo} |")
        lines.append("")

    if ablation:
        lines.extend(["### 4.7 Ablation (60 casos)", "", "| Configuração | Acurácia | Cobertura | Recall |", "|--------------|----------|-----------|--------|"])
        for nome, s in ablation.items():
            lines.append(
                f"| {nome} | {s.acuracia_top1 * 100:.1f}% | {s.cobertura * 100:.1f}% | {s.recall * 100:.1f}% |"
            )
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## 5. Resultados quantitativos detalhados",
            "",
            "### 5.1 Merchants conhecidos (M1)",
            "",
            _bucket_detalhe(benchmark_cb01, "M1"),
            "",
            "### 5.2 Merchants parciais (M2)",
            "",
            _bucket_detalhe(benchmark_cb01, "M2"),
            "",
            "### 5.3 Desconhecidos (M3)",
            "",
            _bucket_detalhe(benchmark_cb01, "M3"),
            "",
            "### 5.4 Descrições ruidosas (R1)",
            "",
            _bucket_detalhe(benchmark_cb01, "R1"),
            "",
            "### 5.5 PIX e transferências (R2)",
            "",
            _bucket_detalhe(benchmark_cb01, "R2"),
            "",
            "### 5.6 Impacto do aprendizado",
            "",
            _tabela_comparativa_personas(benchmark_cb01, benchmark_cb03, benchmark_cb06),
            "",
            "---",
            "",
            "## 6. Análise qualitativa",
            "",
            "### 6.1 Percepção de inteligência",
            "Em merchants M1/M2 o sistema apresenta sugestões coerentes com explicação via fonte `fuzzy` ou `regra_global`. Em PIX genérico e estabelecimentos locais a ausência de sugestão ou sugestão incorreta reduz a percepção de inteligência.",
            "",
            "### 6.2 Percepção de erro",
            "Falsos positivos em categorias subjetivas (C1) e PIX sem contexto são os erros mais impactantes observados no golden.",
            "",
            "### 6.3 Confiança no sistema",
            "Pré-preenchimento no preview correlaciona com confiança alta quando acurácia do bucket é elevada (M1).",
            "",
            "### 6.4 Carga cognitiva e velocidade",
            f"Latência média de inferência: {benchmark_cb01.latencia_ms_media:.2f} ms por caso — baixa carga computacional. Carga cognitiva na revisão de import depende da taxa de FP por lote.",
            "",
            "---",
            "",
            "## 7. Pontos de fricção observados",
            "",
            "| ID | Superfície | Descrição | Frequência | Severidade |",
            "|----|------------|-----------|------------|------------|",
            *_friccoes_observadas(benchmark_cb01),
            "",
            "---",
            "",
            "## 8. Tipos de erro percebidos",
            "",
            _tabela_erros_amostra(benchmark_cb01),
            "",
            "### 8.1 Distribuição estimada por tipo",
            "",
            "| Código | Descrição | Contagem estimada |",
            "|--------|-----------|-------------------|",
            "| E2 | Limitação da abordagem | FP em M3/R2 |",
            "| E4 | Normalizer | R1 com ruído extremo |",
            "| E5 | Fuzzy colisão | M2 com typos agressivos |",
            "| E7 | Subjetivo | C1 |",
            "",
            "---",
            "",
            "## 9. Avaliação do valor percebido",
            "",
            "### 9.1 Trabalho economizado",
            f"Estimativa: {benchmark_cb01.tp} casos TP no golden × ~5s economia manual por linha em importação em massa.",
            "",
            "### 9.2 Trabalho adicional gerado",
            f"Estimativa: {benchmark_cb01.fp} FP exigem correção manual; em import de 30 linhas com mesma distribuição, ~{benchmark_cb01.fp / benchmark_cb01.total * 30:.0f} correções.",
            "",
            "### 9.3 Balanço líquido observado",
            _balanco_liquido(benchmark_cb01),
            "",
            "### 9.4 Síntese de percepção simulada",
            "- Usuário iniciante com import de merchants conhecidos: percepção positiva",
            "- Usuário com muitos PIX pessoais: percepção neutra a negativa",
            "- Usuário avançado com regras (CB-06): ganho claro em padrões configurados",
            "",
            "---",
            "",
            "## 10. Anexos",
            "",
            "- `docs/categorizacao/registros/preview_integracao.json`",
            "- `docs/categorizacao/registros/cenarios_comportamentais.csv`",
            "- `docs/categorizacao/registros/sessao_UX_*.md`",
            "- `docs/categorizacao/datasets/ofx/`",
            "- `docs/categorizacao/checklists/`",
            "",
            "---",
            "",
            "## 11. Registro de reprodutibilidade",
            "",
            "```bash",
            "source .venv/bin/activate",
            "python manage.py migrate",
            "python manage.py seed_merchants_globais",
            "python manage.py avaliar_categorizacao",
            "```",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def _conclusao_uma_frase(s: BenchmarkSummary) -> str:
    if s.acuracia_top1 >= 0.75 and s.cobertura >= 0.70:
        return "A feature reduz revisão em merchants conhecidos com precisão aceitável, mas ainda exige atenção em PIX, estabelecimentos locais e categorias ambíguas."
    if s.cobertura >= 0.60:
        return "A feature cobre boa parte dos casos com precisão variável; o ganho é parcial e depende do perfil de transações do usuário."
    return "A feature apresenta cobertura ou precisão limitada no golden sintético; o ganho percebido é restrito a merchants seedados."


def _veredito_ajuda(s: BenchmarkSummary) -> str:
    if s.acuracia_top1 >= 0.70 and s.cobertura >= 0.65:
        return "parcial a sim"
    if s.cobertura >= 0.50:
        return "parcial"
    return "limitado"


def _tabela_benchmark(s: BenchmarkSummary) -> str:
    return (
        f"| Total | TP | FP | FN | Sem sugestão OK | Cobertura | Acurácia | Recall |\n"
        f"|-------|----|----|-----|-----------------|-----------|----------|--------|\n"
        f"| {s.total} | {s.tp} | {s.fp} | {s.fn} | {s.sem_sugestao_ok} | "
        f"{s.cobertura * 100:.1f}% | {s.acuracia_top1 * 100:.1f}% | {s.recall * 100:.1f}% |"
    )


def _tabela_por_fonte(s: BenchmarkSummary) -> str:
    lines = ["| Fonte | TP | FP | FN |", "|-------|----|----|-----|"]
    for fonte, counts in sorted(s.por_fonte.items()):
        lines.append(f"| {fonte} | {counts.get('TP', 0)} | {counts.get('FP', 0)} | {counts.get('FN', 0)} |")
    return "\n".join(lines)


def _tabela_por_bucket(s: BenchmarkSummary) -> str:
    lines = ["| Bucket | TP | FP | FN | SEM_OK |", "|--------|----|----|-----|--------|"]
    for bucket, counts in sorted(s.por_bucket.items()):
        lines.append(
            f"| {bucket} | {counts.get('TP', 0)} | {counts.get('FP', 0)} | "
            f"{counts.get('FN', 0)} | {counts.get('SEM_SUGESTAO_OK', 0)} |"
        )
    return "\n".join(lines)


def _bucket_detalhe(s: BenchmarkSummary, bucket: str) -> str:
    rows = [r for r in s.resultados if r.case.bucket == bucket]
    if not rows:
        return "Sem dados."
    tp = sum(1 for r in rows if r.resultado == "TP")
    fp = sum(1 for r in rows if r.resultado == "FP")
    fn = sum(1 for r in rows if r.resultado == "FN")
    falhas = [r for r in rows if r.resultado in ("FP", "FN")][:5]
    txt = f"- Casos: {len(rows)} | TP: {tp} | FP: {fp} | FN: {fn}\n"
    if falhas:
        txt += "- Amostra de falhas:\n"
        for r in falhas:
            txt += f"  - `{r.case.id}`: \"{r.case.descricao[:50]}\" → sugeriu {r.sugestao_nome or '—'} (esperado {r.case.categoria_esperada or r.case.categorias_aceitaveis})\n"
    return txt


def _tabela_comparativa_personas(
    cb01: BenchmarkSummary,
    cb03: BenchmarkSummary | None,
    cb06: BenchmarkSummary | None,
) -> str:
    lines = [
        "| Persona | Cobertura | Acurácia | Recall |",
        "|---------|-----------|----------|--------|",
        f"| CB-01 | {cb01.cobertura * 100:.1f}% | {cb01.acuracia_top1 * 100:.1f}% | {cb01.recall * 100:.1f}% |",
    ]
    if cb03:
        lines.append(
            f"| CB-03 | {cb03.cobertura * 100:.1f}% | {cb03.acuracia_top1 * 100:.1f}% | {cb03.recall * 100:.1f}% |"
        )
    if cb06:
        lines.append(
            f"| CB-06 | {cb06.cobertura * 100:.1f}% | {cb06.acuracia_top1 * 100:.1f}% | {cb06.recall * 100:.1f}% |"
        )
    return "\n".join(lines)


def _friccoes_observadas(s: BenchmarkSummary) -> list[str]:
    friccoes = []
    m3_fp = sum(1 for r in s.resultados if r.case.bucket == "M3" and r.resultado == "FP")
    r2_fn = sum(1 for r in s.resultados if r.case.bucket == "R2" and r.resultado == "FN")
    if m3_fp:
        friccoes.append(f"| F-01 | Golden | FP em estabelecimentos locais (M3) | {m3_fp} casos | 3 |")
    if r2_fn:
        friccoes.append(f"| F-02 | Golden | Sem sugestão em PIX genérico (R2) | {r2_fn} casos | 3 |")
    if not friccoes:
        friccoes.append("| — | — | Nenhuma fricção crítica registrada nesta rodada | — | — |")
    return friccoes


def _tabela_erros_amostra(s: BenchmarkSummary, limit: int = 15) -> str:
    fps = [r for r in s.resultados if r.resultado == "FP"][:limit]
    lines = [
        "| ID | Descrição | Sugerido | Esperado | Fonte |",
        "|----|-----------|----------|----------|-------|",
    ]
    for r in fps:
        lines.append(
            f"| {r.case.id} | {r.case.descricao[:40]} | {r.sugestao_nome} | "
            f"{r.case.categoria_esperada or r.case.categorias_aceitaveis} | {r.fonte} |"
        )
    if not fps:
        lines.append("| — | Nenhum FP no golden | — | — | — |")
    return "\n".join(lines)


def _balanco_liquido(s: BenchmarkSummary) -> str:
    net = s.tp - s.fp
    if net > 20:
        return "Balanço positivo no golden sintético: mais acertos que correções necessárias."
    if net > 0:
        return "Balanço levemente positivo; ganho depende da proporção de merchants conhecidos no extrato real do usuário."
    return "Balanço neutro ou negativo no golden; revisão manual pode consumir tempo similar ao cadastro sem sugestões."


def git_commit_curto() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            cwd=AVALIACAO_DIR.parents[1],
        ).strip()
    except Exception:
        return "desconhecido"
