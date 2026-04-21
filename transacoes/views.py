import io
import json
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from itertools import groupby

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from ofxparse.ofxparse import OfxParserException

from categorias.models import Categoria
from contas.models import Conta
from usuarios.models import Perfil

from .forms import TransacaoForm
from .models import Transacao
from .ofx_duplicatas import avaliar_duplicatas_importacao, chave_fingerprint_linha
from .ofx_parse import LinhaOfx, parse_ofx_bytes
from .xlsx_parse import gerar_workbook_modelo, parse_planilha_padrao_bytes

# Limite simples para OFX em memória (MVP síncrono).
_MAX_OFX_BYTES = 6 * 1024 * 1024
_MAX_XLSX_BYTES = 6 * 1024 * 1024
_MAX_LINHAS_IMPORT_OFX = 2000


def _payload_preview_importacao(usuario, conta, linhas_parse: list[LinhaOfx]) -> dict:
    """JSON comum aos previews de importação (OFX e planilha)."""
    dup_flags = avaliar_duplicatas_importacao(usuario, conta, linhas_parse)
    por_indice = {d.indice: d for d in dup_flags}

    linhas_json = []
    for i, linha in enumerate(linhas_parse):
        d = por_indice[i]
        linhas_json.append(
            {
                "indice": i,
                "data": linha.data.isoformat(),
                "valor": str(linha.valor),
                "tipo": linha.tipo,
                "descricao": linha.descricao,
                "ofx_fitid": linha.ofx_fitid,
                "duplicata_por_fitid": d.duplicata_por_fitid,
                "duplicata_por_heuristica": d.duplicata_por_heuristica,
            }
        )

    categorias = _categorias_importacao_preview_payload(usuario)
    return {
        "status": "ok",
        "conta_id": conta.pk,
        "linhas": linhas_json,
        "categorias": categorias,
        "categorias_chave_por_tipo_transacao": {
            "receita": "receita",
            "despesa": "despesa",
            "ajuste": "receita",
        },
    }


def _upload_filename_is_xlsx(upload) -> bool:
    name = (getattr(upload, "name", None) or "").strip().lower()
    return name.endswith(".xlsx")


def _normalizar_fitid_confirmacao(val):
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _categoria_compativel_com_tipo_transacao(categoria, tipo_transacao):
    """Alinhado ao TransacaoForm para receita/despesa; ajuste usa categoria tipo receita (saldo inicial)."""
    if tipo_transacao in ("receita", "despesa"):
        return categoria.tipo == tipo_transacao
    if tipo_transacao == "ajuste":
        return categoria.tipo == "receita"
    return False


def _categoria_fallback_import_ofx(usuario, tipo_transacao: str) -> Categoria | None:
    """
    Categoria quando o import OFX não envia categoria_id: despesa → "Diversos";
    receita ou ajuste → "Diversos" ou "Receitas diversas" (cadastro padrão do app).
    """
    if tipo_transacao == "despesa":
        tipo_c = "despesa"
        nomes = ("Diversos",)
    elif tipo_transacao in ("receita", "ajuste"):
        tipo_c = "receita"
        nomes = ("Diversos", "Receitas diversas")
    else:
        return None
    qs = Categoria.objects.filter(
        Q(usuario=usuario) | Q(padrao=True),
        ativa=True,
        tipo=tipo_c,
    )
    for nome in nomes:
        hit = qs.filter(nome=nome).first()
        if hit:
            return hit
    return None


def _validation_error_para_json(exc: ValidationError):
    if hasattr(exc, "message_dict") and exc.message_dict:
        out = {}
        for k, v in exc.message_dict.items():
            out[k] = list(v) if isinstance(v, (list, tuple)) else [str(v)]
        return out
    return {"__all__": [m for m in exc.messages]}


def _categorias_importacao_preview_payload(usuario):
    """Listas de categorias ativas (usuário + padrão) para montar selects no preview."""
    qs = Categoria.objects.filter(
        Q(usuario=usuario) | Q(padrao=True),
        ativa=True,
    )
    receita = [
        {"id": c.id, "nome": c.nome, "tipo": c.tipo}
        for c in qs.filter(tipo="receita").order_by("nome")
    ]
    despesa = [
        {"id": c.id, "nome": c.nome, "tipo": c.tipo}
        for c in qs.filter(tipo="despesa").order_by("nome")
    ]
    return {"receita": receita, "despesa": despesa}


@login_required
def adicionar_transacao(request):
    ano = request.GET.get("ano")
    mes = request.GET.get("mes")
    hoje = date.today()
    ano = ano or hoje.year
    mes = mes or hoje.month
    ano = int(ano)
    mes = int(mes)
    data_mes = date(ano, mes, 1)

    if mes == 1:
        mes_anterior = 12
        ano_anterior = ano - 1
    else:
        mes_anterior = mes - 1
        ano_anterior = ano

    if mes == 12:
        mes_proximo = 1
        ano_proximo = ano + 1
    else:
        mes_proximo = mes + 1
        ano_proximo = ano

    data_inicial = None
    data_fim = None
    inicio_str = request.GET.get("inicio")
    fim_str = request.GET.get("fim")
    if inicio_str and fim_str:
        try:
            data_inicial = datetime.strptime(inicio_str, "%Y-%m-%d").date()
            data_fim = datetime.strptime(fim_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            data_inicial = None
            data_fim = None

    if data_inicial is None:
        periodo = request.GET.get("periodo")
        if periodo == "hoje":
            data_inicial = hoje
            data_fim = hoje
        elif periodo == "semana":
            # segunda-feira da semana atual (weekday: 0=segunda, 6=domingo)
            data_inicial = hoje - timedelta(days=hoje.weekday())
        elif periodo == "mes":
            data_inicial = date(hoje.year, hoje.month, 1)
        elif periodo == "ano":
            data_inicial = date(hoje.year, 1, 1)
        elif periodo == "3m":
            total_meses = hoje.year * 12 + (hoje.month - 1) - 3
            data_inicial = date(total_meses // 12, (total_meses % 12) + 1, 1)
        elif periodo == "12m":
            total_meses = hoje.year * 12 + (hoje.month - 1) - 12
            data_inicial = date(total_meses // 12, (total_meses % 12) + 1, 1)
        else:
            data_inicial = None

    if data_inicial is not None:
        filtro_periodo = {"usuario": request.user, "data__gte": data_inicial}
        if data_fim is not None:
            filtro_periodo["data__lte"] = data_fim
        transacoes = Transacao.objects.filter(
            **filtro_periodo
        ).select_related("categoria", "conta").order_by("-data", "-id")
    else:
        transacoes = Transacao.objects.filter(
            usuario=request.user,
            data__year=ano,
            data__month=mes,
        ).select_related("categoria", "conta").order_by("-data", "-id")

    transacoes_list = list(transacoes)
    transacoes_por_dia = [
        {"data": data, "transacoes": list(grupo)}
        for data, grupo in groupby(
            transacoes_list,
            key=lambda t: t.data if isinstance(t.data, date) else t.data.date(),
        )
    ]

    if data_inicial is not None:
        filtro_totais = {"usuario": request.user, "data__gte": data_inicial}
        if data_fim is not None:
            filtro_totais["data__lte"] = data_fim
        totais = Transacao.objects.filter(
            **filtro_totais
        ).aggregate(
            total_receitas=Sum("valor", filter=Q(tipo="receita")),
            total_despesas=Sum("valor", filter=Q(tipo="despesa")),
        )
    else:
        totais = Transacao.objects.filter(
            usuario=request.user,
            data__year=ano,
            data__month=mes,
        ).aggregate(
            total_receitas=Sum("valor", filter=Q(tipo="receita")),
            total_despesas=Sum("valor", filter=Q(tipo="despesa")),
        )
    total_receitas = totais["total_receitas"] or 0
    total_despesas = totais["total_despesas"] or 0
    saldo_mes = total_receitas - total_despesas

    categorias_despesa = Categoria.objects.filter(
        Q(usuario=request.user) | Q(padrao=True),
        tipo="despesa",
        ativa=True
    ).order_by("nome")
    categorias_receita = Categoria.objects.filter(
        Q(usuario=request.user) | Q(padrao=True),
        tipo="receita",
        ativa=True
    ).order_by("nome")
    contas = Conta.objects.filter(usuario=request.user, ativa=True).order_by("nome")

    perfil, _ = Perfil.objects.get_or_create(usuario=request.user)
    initial_tx, tipo_padrao_perfil = perfil.defaults_transacao_form()

    if request.method == 'POST':
        tipo_inicial = request.POST.get('tipo', tipo_padrao_perfil)
        form = TransacaoForm(request.POST, usuario=request.user, tipo_inicial=tipo_inicial)
        if form.is_valid():
            transacao = form.save(commit=False)
            transacao.usuario = request.user
            transacao.save()

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                resp = {
                    'status': 'ok',
                    'id': transacao.id,
                    'tipo': transacao.tipo,
                    'descricao': transacao.descricao,
                    'valor': str(transacao.valor),
                    'data': transacao.data.strftime('%Y-%m-%d'),
                    'categoria': {
                        'id': transacao.categoria.id,
                        'nome': transacao.categoria.nome,
                        'icone': transacao.categoria.icone,
                        'cor': transacao.categoria.cor,
                    }
                }
                if transacao.conta_id:
                    resp['conta'] = {
                        'id': transacao.conta.id,
                        'nome': transacao.conta.nome,
                        'icone': transacao.conta.icone,
                    }
                return JsonResponse(resp)

            return redirect('relatorios:home')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    else:
        form = TransacaoForm(
            usuario=request.user,
            tipo_inicial=tipo_padrao_perfil,
            initial=initial_tx,
        )

    hoje = date.today()
    ano_hoje = hoje.year
    mes_hoje = hoje.month

    datas_distintas = Transacao.objects.filter(
        usuario=request.user
    ).dates("data", "month", order="DESC")
    meses_dropdown = [
        {"ano": d.year, "mes": d.month, "data_mes": d}
        for d in datas_distintas
    ]

    context = {
        "transacoes_por_dia": transacoes_por_dia,
        "ano": ano,
        "mes": mes,
        "ano_hoje": ano_hoje,
        "mes_hoje": mes_hoje,
        "data_mes": data_mes,
        "mes_anterior": mes_anterior,
        "ano_anterior": ano_anterior,
        "mes_proximo": mes_proximo,
        "ano_proximo": ano_proximo,
        "form": form,
        "categorias_despesa": categorias_despesa,
        "categorias_receita": categorias_receita,
        "contas": contas,
        "total_receitas": total_receitas,
        "total_despesas": total_despesas,
        "saldo_mes": saldo_mes,
        "meses_dropdown": meses_dropdown,
    }
    return render(request, 'transacoes/partials/historico.html', context)


@login_required
def editar_transacao(request, pk):
    transacao = get_object_or_404(Transacao, pk=pk, usuario=request.user)

    if request.method == "POST":
        form = TransacaoForm(
            request.POST, instance=transacao, usuario=request.user, tipo_inicial=transacao.tipo
        )
        if form.is_valid():
            with transaction.atomic():
                form.save()

            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({'status': 'ok'})
            
            ano_atual = transacao.data.year
            mes_atual = transacao.data.month
            return redirect(f"/transacoes/?ano={ano_atual}&mes={mes_atual}")
        else:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    else:
        if request.GET.get("ajax"):
            # Retornar JSON com os dados da transação
            return JsonResponse({
                "id": transacao.id,
                "tipo": transacao.tipo,
                "valor": str(transacao.valor),
                "descricao": transacao.descricao,
                "data": transacao.data.strftime("%Y-%m-%d"),
                "categoria": {
                    "id": transacao.categoria.id,
                    "nome": transacao.categoria.nome
                },
                "conta": {
                    "id": transacao.conta.id,
                    "nome": transacao.conta.nome
                } if transacao.conta else None
            })

    form = TransacaoForm(instance=transacao, usuario=request.user, tipo_inicial=transacao.tipo)
    return render(request, "transacoes/editar_transacao.html", {"form": form, "transacao": transacao})


@require_POST
@login_required
def excluir_transacao(request, pk):
    transacao = get_object_or_404(Transacao, pk=pk, usuario=request.user)
    if request.method == "POST":
        ano_atual = transacao.data.year
        mes_atual = transacao.data.month
        with transaction.atomic():
            transacao.delete()
        return redirect(f"/transacoes/?ano={ano_atual}&mes={mes_atual}")
    ano_atual = transacao.data.year
    mes_atual = transacao.data.month
    return redirect(f"/transacoes/?ano={ano_atual}&mes={mes_atual}")


@login_required
def dados_grafico_receitas_despesas(request):
    transacoes = (
        Transacao.objects.filter(usuario=request.user)
        .annotate(mes=TruncMonth('data'))
        .values('mes', 'tipo')
        .annotate(total=Sum('valor'))
        .order_by('mes')
    )

    dados = {}
    for item in transacoes:
        mes_str = item['mes'].strftime('%b %Y')
        if mes_str not in dados:
            dados[mes_str] = {'receita': 0, 'despesa': 0}
        dados[mes_str][item['tipo']] = float(item['total'])

    meses_labels = []
    receitas = []
    despesas = []

    hoje = datetime.today().replace(day=1)
    for i in range(11, -1, -1):
        mes_data = hoje - timedelta(days=30 * i)
        mes_label = mes_data.strftime('%b %Y')
        meses_labels.append(mes_label)
        receitas.append(dados.get(mes_label, {}).get('receita', 0))
        despesas.append(dados.get(mes_label, {}).get('despesa', 0))

    return JsonResponse({
        'labels': meses_labels,
        'receitas': receitas,
        'despesas': despesas,
    })


@login_required
@require_POST
def importar_ofx_preview(request):
    """
    Multipart: conta_id, arquivo (campo `arquivo` ou `file`).
    Retorna JSON com linhas parseadas, flags de duplicata e categorias para o preview.
    """
    conta_id = request.POST.get("conta_id")
    upload = request.FILES.get("arquivo") or request.FILES.get("file")

    if not conta_id:
        return JsonResponse(
            {"status": "error", "message": "Informe a conta."},
            status=400,
        )
    if not upload:
        return JsonResponse(
            {"status": "error", "message": "Envie um arquivo OFX."},
            status=400,
        )

    try:
        conta_pk = int(conta_id)
    except (TypeError, ValueError):
        return JsonResponse(
            {"status": "error", "message": "Conta inválida."},
            status=400,
        )

    conta = get_object_or_404(Conta, pk=conta_pk, usuario=request.user, ativa=True)

    raw = upload.read()
    if len(raw) > _MAX_OFX_BYTES:
        return JsonResponse(
            {"status": "error", "message": "Arquivo muito grande."},
            status=400,
        )

    try:
        linhas_parse = parse_ofx_bytes(raw)
    except ValueError as exc:
        return JsonResponse({"status": "error", "message": str(exc)}, status=400)
    except OfxParserException:
        return JsonResponse(
            {"status": "error", "message": "OFX inválido ou não suportado."},
            status=400,
        )

    payload = _payload_preview_importacao(request.user, conta, linhas_parse)
    return JsonResponse(payload)


@login_required
@require_POST
def importar_planilha_preview(request):
    """
    Multipart: conta_id, arquivo (campo `arquivo` ou `file`).
    Planilha .xlsx no layout fixo (primeira aba: data | descricao | valor).
    """
    conta_id = request.POST.get("conta_id")
    upload = request.FILES.get("arquivo") or request.FILES.get("file")

    if not conta_id:
        return JsonResponse(
            {"status": "error", "message": "Informe a conta."},
            status=400,
        )
    if not upload:
        return JsonResponse(
            {"status": "error", "message": "Envie um arquivo Excel (.xlsx)."},
            status=400,
        )
    if not _upload_filename_is_xlsx(upload):
        return JsonResponse(
            {"status": "error", "message": "Envie um arquivo Excel (.xlsx)."},
            status=400,
        )

    try:
        conta_pk = int(conta_id)
    except (TypeError, ValueError):
        return JsonResponse(
            {"status": "error", "message": "Conta inválida."},
            status=400,
        )

    conta = get_object_or_404(Conta, pk=conta_pk, usuario=request.user, ativa=True)

    raw = upload.read()
    if len(raw) > _MAX_XLSX_BYTES:
        return JsonResponse(
            {"status": "error", "message": "Arquivo muito grande."},
            status=400,
        )

    try:
        linhas_parse = parse_planilha_padrao_bytes(raw)
    except ValueError as exc:
        return JsonResponse({"status": "error", "message": str(exc)}, status=400)

    if len(linhas_parse) > _MAX_LINHAS_IMPORT_OFX:
        return JsonResponse(
            {
                "status": "error",
                "message": f"Limite de {_MAX_LINHAS_IMPORT_OFX} linhas por importação.",
            },
            status=400,
        )
    if len(linhas_parse) == 0:
        return JsonResponse(
            {"status": "error", "message": "Nenhuma linha de lançamento na planilha."},
            status=400,
        )

    payload = _payload_preview_importacao(request.user, conta, linhas_parse)
    return JsonResponse(payload)


@login_required
@require_GET
def importar_planilha_modelo(request):
    """Gera .xlsx modelo com cabeçalhos oficiais (mesma ordem esperada pelo parser)."""
    wb = gerar_workbook_modelo()
    buf = io.BytesIO()
    wb.save(buf)
    data = buf.getvalue()
    resp = HttpResponse(
        data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = (
        'attachment; filename="modelo_importacao_lancamentos.xlsx"'
    )
    return resp


@login_required
@require_POST
def importar_ofx_confirmar(request):
    """
    JSON: { "conta_id": int, "linhas": [ { data, valor, tipo, descricao, categoria_id?, ofx_fitid? }, ... ] }
    categoria_id opcional: se omitido ou vazio, usa "Diversos" (despesa) ou "Diversos"/"Receitas diversas" (receita/ajuste).
    Cria transações com bulk_create dentro de transaction.atomic().
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"status": "error", "message": "JSON inválido."},
            status=400,
        )

    conta_id = payload.get("conta_id")
    linhas = payload.get("linhas")

    if conta_id is None:
        return JsonResponse(
            {"status": "error", "message": "Informe conta_id."},
            status=400,
        )
    if not isinstance(linhas, list):
        return JsonResponse(
            {"status": "error", "message": "linhas deve ser uma lista."},
            status=400,
        )
    if len(linhas) > _MAX_LINHAS_IMPORT_OFX:
        return JsonResponse(
            {
                "status": "error",
                "message": f"Limite de {_MAX_LINHAS_IMPORT_OFX} linhas por importação.",
            },
            status=400,
        )

    try:
        conta_pk = int(conta_id)
    except (TypeError, ValueError):
        return JsonResponse(
            {"status": "error", "message": "Conta inválida."},
            status=400,
        )

    conta = get_object_or_404(Conta, pk=conta_pk, usuario=request.user, ativa=True)

    if len(linhas) == 0:
        return JsonResponse({"status": "ok", "criadas": 0})

    erros_por_chave: dict[str, dict] = {}
    instancias: list[Transacao] = []
    fitids_no_lote: dict[str, tuple[date, Decimal, str]] = {}
    fallback_categoria_por_tipo: dict[str, Categoria | None] = {}

    tipos_validos = {c[0] for c in Transacao.TIPO_CHOICES}

    for pos, row in enumerate(linhas):
        if not isinstance(row, dict):
            erros_por_chave[str(pos)] = {"__all__": ["Item inválido (objeto esperado)."]}
            continue

        chave_erro = str(row.get("indice", pos))

        erros_linha: dict[str, list[str]] = {}

        tipo = row.get("tipo")
        if tipo not in tipos_validos:
            erros_linha.setdefault("tipo", []).append("Tipo de transação inválido.")

        try:
            data_tx = datetime.strptime(str(row.get("data", "")), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            erros_linha.setdefault("data", []).append("Data inválida (use YYYY-MM-DD).")

        try:
            valor = Decimal(str(row.get("valor")))
        except (InvalidOperation, TypeError, ValueError):
            erros_linha.setdefault("valor", []).append("Valor inválido.")

        if "valor" not in erros_linha:
            if valor < 0:
                erros_linha.setdefault("valor", []).append("Valor não pode ser negativo.")
            if abs(valor) >= Decimal("1000000000"):
                erros_linha.setdefault("valor", []).append("Valor fora do limite permitido.")

        descricao = row.get("descricao", "")
        if descricao is None:
            descricao = ""
        descricao = str(descricao).strip()
        if not descricao:
            erros_linha.setdefault("descricao", []).append("Informe a descrição.")
        elif len(descricao) > 255:
            erros_linha.setdefault("descricao", []).append("Descrição muito longa.")

        cat_id = row.get("categoria_id")
        categoria = None
        cat_pk = None
        cat_omitida = cat_id is None or cat_id == "" or (
            isinstance(cat_id, str) and not str(cat_id).strip()
        )

        if not cat_omitida:
            try:
                cat_pk = int(cat_id)
            except (TypeError, ValueError):
                erros_linha.setdefault("categoria_id", []).append("Categoria inválida.")
            else:
                if cat_pk <= 0:
                    cat_pk = None
                    cat_omitida = True

        if cat_pk is not None:
            categoria = (
                Categoria.objects.filter(
                    pk=cat_pk,
                    ativa=True,
                )
                .filter(Q(usuario=request.user) | Q(padrao=True))
                .first()
            )
            if categoria is None:
                erros_linha.setdefault("categoria_id", []).append("Categoria não encontrada.")
            elif tipo in tipos_validos and not _categoria_compativel_com_tipo_transacao(
                categoria, tipo
            ):
                erros_linha.setdefault("categoria_id", []).append(
                    "Categoria incompatível com o tipo da transação."
                )

        if categoria is None and "categoria_id" not in erros_linha and tipo in tipos_validos:
            if tipo not in fallback_categoria_por_tipo:
                fallback_categoria_por_tipo[tipo] = _categoria_fallback_import_ofx(
                    request.user, tipo
                )
            categoria = fallback_categoria_por_tipo[tipo]
            if categoria is None:
                erros_linha.setdefault("categoria_id", []).append(
                    'Sem categoria: cadastre "Diversos" (despesa) ou "Receitas diversas"/"Diversos" (receita).'
                )

        if erros_linha:
            erros_por_chave[chave_erro] = erros_linha
            continue

        fingerprint = chave_fingerprint_linha(data_tx, valor, descricao)

        fitid = _normalizar_fitid_confirmacao(row.get("ofx_fitid"))
        if fitid:
            existente = (
                Transacao.objects.filter(conta=conta, ofx_fitid=fitid)
                .only("data", "valor", "descricao")
                .first()
            )
            if existente is not None:
                # Permite manter linhas marcadas como duplicadas no preview:
                # em conflito de FITID com registro existente, grava sem FITID.
                fitid = None
            elif fitid in fitids_no_lote:
                # Mesmo FITID no lote (chave igual ou diferente): mantém a primeira
                # com FITID e salva as próximas sem FITID para evitar conflito único.
                fitid = None
            else:
                fitids_no_lote[fitid] = fingerprint

        assert categoria is not None
        t = Transacao(
            usuario=request.user,
            conta=conta,
            categoria=categoria,
            tipo=tipo,
            valor=valor,
            data=data_tx,
            descricao=descricao,
            ofx_fitid=fitid,
        )
        try:
            t.full_clean()
        except ValidationError as exc:
            erros_por_chave[chave_erro] = _validation_error_para_json(exc)
            continue

        instancias.append(t)

    if erros_por_chave:
        return JsonResponse(
            {
                "status": "error",
                "message": "Corrija os erros nas linhas indicadas.",
                "erros": erros_por_chave,
            },
            status=400,
        )

    fitids_inserir = [t.ofx_fitid for t in instancias if t.ofx_fitid]
    if fitids_inserir:
        existentes = set(
            Transacao.objects.filter(
                conta=conta,
                ofx_fitid__in=fitids_inserir,
            ).values_list("ofx_fitid", flat=True)
        )
        if existentes:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Já existem lançamentos com um ou mais FITID informados.",
                    "fitids_em_conflito": sorted(existentes),
                },
                status=400,
            )

    try:
        with transaction.atomic():
            Transacao.objects.bulk_create(instancias)
    except IntegrityError:
        return JsonResponse(
            {
                "status": "error",
                "message": "Conflito ao gravar (ex.: FITID duplicado). Tente novamente.",
            },
            status=400,
        )

    return JsonResponse({"status": "ok", "criadas": len(instancias)})
