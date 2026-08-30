import calendar
import io
import json
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from itertools import groupby
from types import SimpleNamespace

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import DateField, F, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from ofxparse.ofxparse import OfxParserException

from categorias.models import Categoria
from cartoes.models import Cartao, Fatura
from cartoes.services.gestao_faturas import (
    calcular_resumos_pagamento_bulk,
    totais_faturas_bulk,
)
from contas.models import Conta
from usuarios.models import Perfil
from usuarios.services.produto_eventos import registrar_evento_seguro

from relatorios.services.filtros import RelatorioFiltros, parse_relatorio_filtros

from .forms import TransacaoForm, TransferenciaForm
from .models import Transacao
from .ofx_duplicatas import avaliar_duplicatas_importacao, chave_fingerprint_linha
from .ofx_parse import LinhaOfx, parse_ofx_bytes
from .services import (
    atualizar_transferencia,
    criar_transferencia,
    excluir_transferencia,
    obter_par_transferencia,
)
from .xlsx_parse import gerar_workbook_modelo, parse_planilha_padrao_bytes

from categorizacao.services.learning import processar_feedback_transacao
from categorizacao.services.pipeline import sugerir

# Limite simples para OFX em memória (MVP síncrono).
_MAX_OFX_BYTES = 6 * 1024 * 1024
_MAX_XLSX_BYTES = 6 * 1024 * 1024
_MAX_LINHAS_IMPORT_OFX = 2000
HISTORICO_PAGE_SIZE = 50


def _redirect_ano_mes_transacao(t: Transacao) -> tuple[int, int]:
    if t.data_competencia:
        return t.data_competencia.year, t.data_competencia.month
    return t.data.year, t.data.month


def _filtro_mes_calendario(ano: int, mes: int) -> Q:
    return (
        Q(cartao__isnull=False, data_competencia__year=ano, data_competencia__month=mes)
        | Q(
            cartao__isnull=False,
            data_competencia__isnull=True,
            data__year=ano,
            data__month=mes,
        )
        | Q(cartao__isnull=True, data__year=ano, data__month=mes)
    )


def _filtro_periodo_calendario(data_inicial: date, data_fim: date) -> Q:
    return (
        Q(
            cartao__isnull=False,
            data_competencia__gte=data_inicial,
            data_competencia__lte=data_fim,
        )
        | Q(
            cartao__isnull=False,
            data_competencia__isnull=True,
            data__gte=data_inicial,
            data__lte=data_fim,
        )
        | Q(cartao__isnull=True, data__gte=data_inicial, data__lte=data_fim)
    )


def _anotar_data_exibicao(qs):
    return qs.annotate(data_exibicao=Coalesce(F("data_competencia"), F("data"), output_field=DateField()))


def _q_compras_em_fatura():
    """Lançamentos de compra no cartão vinculados a uma fatura (não são pagamento da fatura)."""
    return Q(cartao__isnull=False, fatura__isnull=False, pagamento_de_fatura__isnull=True)


def _q_pagamento_de_fatura():
    return Q(pagamento_de_fatura__isnull=False)


_MESES_PT_FATURA = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)


def _descricao_linha_historico_fatura(fatura: Fatura, status_pagamento: str) -> str:
    if status_pagamento == Fatura.StatusPagamento.PAGO:
        return "Pagamento da fatura"
    mes = _MESES_PT_FATURA[fatura.competencia.month - 1]
    return f"Fatura {mes.title()} {fatura.competencia.year}"


def _faturas_com_vencimento_no_periodo(usuario, *, ano=None, mes=None, data_inicial=None, data_fim=None):
    qs = Fatura.objects.filter(usuario=usuario, cartao__ativa=True).select_related(
        "cartao", "cartao__conta_padrao"
    )
    if data_inicial is not None:
        fim = data_fim or data_inicial
        qs = qs.filter(data_vencimento__gte=data_inicial, data_vencimento__lte=fim)
    else:
        qs = qs.filter(data_vencimento__year=ano, data_vencimento__month=mes)
    return qs.order_by("-data_vencimento", "-id")


def _linha_historico_pagamento_fatura(fatura: Fatura, valor_total, *, descricao: str) -> SimpleNamespace:
    categoria = SimpleNamespace(nome="Cartão de crédito", cor="#6366f1", icone="fa-credit-card")
    return SimpleNamespace(
        is_resumo_fatura=True,
        fatura=fatura,
        id=None,
        data_exibicao=fatura.data_vencimento,
        data=fatura.data_vencimento,
        data_competencia=fatura.data_vencimento,
        descricao=descricao,
        tipo="despesa",
        valor=valor_total,
        categoria=categoria,
        conta=fatura.cartao.conta_padrao,
        cartao=fatura.cartao,
        cartao_id=fatura.cartao_id,
        pagamento_de_fatura_id=None,
    )


def _montar_itens_historico_com_faturas(
    usuario,
    transacoes_list: list,
    *,
    ano=None,
    mes=None,
    data_inicial=None,
    data_fim=None,
    conta_filtro_ids: list | None = None,
    categoria_filtro_ids: list | None = None,
):
    """
    Remove compras em fatura e pagamentos de fatura da lista; insere uma linha sintética
    por fatura (total das despesas) na data de vencimento.
    O valor retornado em extras (rodapé) só inclui faturas com status de pagamento Pago.
    """
    transacoes_filtradas = []
    for t in transacoes_list:
        if t.cartao_id and t.fatura_id and not t.pagamento_de_fatura_id:
            continue
        if t.pagamento_de_fatura_id:
            continue
        transacoes_filtradas.append(t)

    if categoria_filtro_ids:
        return transacoes_filtradas, Decimal("0")

    faturas_qs = _faturas_com_vencimento_no_periodo(
        usuario,
        ano=ano,
        mes=mes,
        data_inicial=data_inicial,
        data_fim=data_fim,
    )
    if conta_filtro_ids:
        faturas_qs = faturas_qs.filter(cartao__conta_padrao_id__in=conta_filtro_ids)

    faturas_list = list(faturas_qs.select_related("cartao", "cartao__conta_padrao"))
    totais_map = totais_faturas_bulk(faturas_list)
    resumos_map = calcular_resumos_pagamento_bulk(faturas_list)

    extras_valor = Decimal("0")
    sinteticas = []
    for fat in faturas_list:
        tot = totais_map.get(fat.id, Decimal("0"))
        if tot <= Decimal("0"):
            continue
        resumo = resumos_map[fat.id]
        desc = _descricao_linha_historico_fatura(fat, resumo.status_pagamento)
        sinteticas.append(_linha_historico_pagamento_fatura(fat, tot, descricao=desc))
        if resumo.status_pagamento == Fatura.StatusPagamento.PAGO:
            extras_valor += tot

    def _ord_key(item):
        d = getattr(item, "data_exibicao", item.data)
        if getattr(item, "is_resumo_fatura", False):
            sid = item.fatura.pk
        else:
            sid = item.id
        return (-d.toordinal(), -sid)

    merged = transacoes_filtradas + sinteticas
    merged.sort(key=_ord_key)
    return merged, extras_valor


def _anotar_contrapartes_transferencia(itens: list) -> None:
    """
    Anota em cada transferência da página a conta da outra perna (mesmo transfer_id),
    para UX do histórico sem N+1. Rótulos via rotulo_historico_transferencia()/contraparte().
    """
    tids = {
        t.transfer_id
        for t in itens
        if getattr(t, "tipo", None) == "transferencia"
        and getattr(t, "transfer_id", None)
        and not getattr(t, "is_resumo_fatura", False)
    }
    if not tids:
        return
    irmas = (
        Transacao.objects.filter(transfer_id__in=tids, tipo="transferencia")
        .select_related("conta")
    )
    por_tid: dict = {}
    for irma in irmas:
        por_tid.setdefault(irma.transfer_id, []).append(irma)

    for t in itens:
        if getattr(t, "tipo", None) != "transferencia" or not getattr(t, "transfer_id", None):
            continue
        pares = por_tid.get(t.transfer_id) or []
        outra = next((x for x in pares if x.pk != t.pk), None)
        t._contraparte_cache = outra
        t.contraparte_conta_nome = outra.conta.nome if outra and outra.conta_id else None
        t.rotulo_transferencia = t.rotulo_historico_transferencia()


def _payload_preview_importacao(usuario, conta, linhas_parse: list[LinhaOfx]) -> dict:
    """JSON comum aos previews de importação (OFX e planilha). Sem categorização automática."""
    dup_flags = avaliar_duplicatas_importacao(usuario, conta, linhas_parse)
    por_indice = {d.indice: d for d in dup_flags}

    linhas_json = []
    for i, linha in enumerate(linhas_parse):
        d = por_indice[i]
        item = {
            "indice": i,
            "data": linha.data.isoformat(),
            "valor": str(linha.valor),
            "tipo": linha.tipo,
            "descricao": linha.descricao,
            "ofx_fitid": linha.ofx_fitid,
            "duplicata_por_fitid": d.duplicata_por_fitid,
            "duplicata_por_heuristica": d.duplicata_por_heuristica,
        }
        linhas_json.append(item)

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
        "categorizacao_pendente": True,
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
    for nome in nomes:
        hit = _categorias_ativas_unicas_por_nome(usuario, tipo=tipo_c)
        for cat in hit:
            if cat.nome == nome:
                return cat
    return None


def _validation_error_para_json(exc: ValidationError):
    if hasattr(exc, "message_dict") and exc.message_dict:
        out = {}
        for k, v in exc.message_dict.items():
            out[k] = list(v) if isinstance(v, (list, tuple)) else [str(v)]
        return out
    return {"__all__": [m for m in exc.messages]}


_HISTORICO_FILTRO_GET_KEYS = frozenset(
    {"preset", "inicio", "fim", "conta", "categoria", "tipo"}
)


def _historico_usa_filtros_relatorio(get) -> bool:
    return bool(_HISTORICO_FILTRO_GET_KEYS & set(get.keys()))


def _filtros_historico_para_exibicao(ano: int, mes: int, get, usuario) -> RelatorioFiltros:
    if _historico_usa_filtros_relatorio(get):
        return parse_relatorio_filtros(get, usuario=usuario)
    _, ultimo_dia = calendar.monthrange(ano, mes)
    return RelatorioFiltros(
        data_inicio=date(ano, mes, 1),
        data_fim=date(ano, mes, ultimo_dia),
        preset="este_mes",
    )


def _categorias_ativas_unicas_por_nome(usuario, *, tipo: str | None = None):
    """
    Categorias ativas (usuário + padrão global), uma por nome/tipo.
    Se existir cópia do usuário e categoria padrão com o mesmo nome, mantém a do usuário.
    """
    qs = Categoria.objects.filter(
        Q(usuario=usuario) | Q(padrao=True),
        ativa=True,
    )
    if tipo:
        qs = qs.filter(tipo=tipo)
    por_chave: dict[tuple[str, str], Categoria] = {}
    for cat in qs.order_by("tipo", "nome", "padrao", "pk"):
        chave = (cat.tipo, cat.nome.strip().casefold())
        atual = por_chave.get(chave)
        if atual is None:
            por_chave[chave] = cat
            continue
        if cat.usuario_id == usuario.id and atual.usuario_id != usuario.id:
            por_chave[chave] = cat
    return sorted(por_chave.values(), key=lambda c: (c.tipo, c.nome))


def _categorias_importacao_preview_payload(usuario):
    """Listas de categorias ativas (usuário + padrão) para montar selects no preview."""
    receita = [
        {"id": c.id, "nome": c.nome, "tipo": c.tipo, "icone": c.icone, "cor": c.cor}
        for c in _categorias_ativas_unicas_por_nome(usuario, tipo="receita")
    ]
    despesa = [
        {"id": c.id, "nome": c.nome, "tipo": c.tipo, "icone": c.icone, "cor": c.cor}
        for c in _categorias_ativas_unicas_por_nome(usuario, tipo="despesa")
    ]
    return {"receita": receita, "despesa": despesa}


def modal_transacao_context(request, *, pre_select_cartao_id=None):
    """
    Contexto mínimo para incluir `transacoes/partials/adicionar_transacao.html`
    fora do histórico (ex.: faturas do cartão), com cartão opcional pré-selecionado.
    """
    categorias_despesa = Categoria.objects.filter(
        Q(usuario=request.user) | Q(padrao=True),
        tipo="despesa",
        ativa=True,
    ).order_by("nome")
    categorias_receita = Categoria.objects.filter(
        Q(usuario=request.user) | Q(padrao=True),
        tipo="receita",
        ativa=True,
    ).order_by("nome")
    perfil, _ = Perfil.objects.get_or_create(usuario=request.user)
    initial_tx, tipo_padrao_perfil = perfil.defaults_transacao_form()
    if pre_select_cartao_id is not None:
        initial_tx = {**initial_tx, "cartao": int(pre_select_cartao_id)}
    form = TransacaoForm(
        usuario=request.user,
        tipo_inicial=tipo_padrao_perfil,
        initial=initial_tx,
    )
    return {
        "form": form,
        "categorias_despesa": categorias_despesa,
        "categorias_receita": categorias_receita,
    }


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

    usa_filtros_relatorio = _historico_usa_filtros_relatorio(request.GET)
    filtros = _filtros_historico_para_exibicao(ano, mes, request.GET, request.user)

    data_inicial = None
    data_fim = None
    if usa_filtros_relatorio:
        data_inicial = filtros.data_inicio
        data_fim = filtros.data_fim

    if data_inicial is not None:
        transacoes = (
            Transacao.objects.filter(usuario=request.user)
            .filter(_filtro_periodo_calendario(data_inicial, data_fim or data_inicial))
            .select_related("categoria", "conta", "cartao", "fatura")
        )
        transacoes = _anotar_data_exibicao(transacoes).order_by("-data_exibicao", "-id")
    else:
        transacoes = (
            Transacao.objects.filter(usuario=request.user)
            .filter(_filtro_mes_calendario(ano, mes))
            .select_related("categoria", "conta", "cartao", "fatura")
        )
        transacoes = _anotar_data_exibicao(transacoes).order_by("-data_exibicao", "-id")

    conta_filtro_ids = list(filtros.conta_ids) if usa_filtros_relatorio else []
    categoria_filtro_ids = list(filtros.categoria_ids) if usa_filtros_relatorio else []
    if conta_filtro_ids:
        transacoes = transacoes.filter(conta_id__in=conta_filtro_ids)
    if categoria_filtro_ids:
        transacoes = transacoes.filter(categoria_id__in=categoria_filtro_ids)
    if usa_filtros_relatorio and filtros.tipos:
        transacoes = transacoes.filter(tipo__in=filtros.tipos)

    transacoes_list = list(transacoes)
    if data_inicial is not None:
        transacoes_list, despesas_resumo_fatura = _montar_itens_historico_com_faturas(
            request.user,
            transacoes_list,
            data_inicial=data_inicial,
            data_fim=data_fim or data_inicial,
            conta_filtro_ids=conta_filtro_ids or None,
            categoria_filtro_ids=categoria_filtro_ids or None,
        )
    else:
        transacoes_list, despesas_resumo_fatura = _montar_itens_historico_com_faturas(
            request.user,
            transacoes_list,
            ano=ano,
            mes=mes,
            conta_filtro_ids=conta_filtro_ids or None,
            categoria_filtro_ids=categoria_filtro_ids or None,
        )

    total_itens = len(transacoes_list)
    try:
        page = max(1, int(request.GET.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    total_pages = max(1, (total_itens + HISTORICO_PAGE_SIZE - 1) // HISTORICO_PAGE_SIZE)
    if page > total_pages:
        page = total_pages
    inicio_pag = (page - 1) * HISTORICO_PAGE_SIZE
    transacoes_pagina = transacoes_list[inicio_pag : inicio_pag + HISTORICO_PAGE_SIZE]
    _anotar_contrapartes_transferencia(transacoes_pagina)

    transacoes_por_dia = [
        {"data": data, "transacoes": list(grupo)}
        for data, grupo in groupby(
            transacoes_pagina,
            key=lambda t: getattr(t, "data_exibicao", t.data),
        )
    ]

    if data_inicial is not None:
        tqs = Transacao.objects.filter(usuario=request.user).filter(
            _filtro_periodo_calendario(data_inicial, data_fim or data_inicial)
        )
    else:
        tqs = Transacao.objects.filter(usuario=request.user).filter(_filtro_mes_calendario(ano, mes))
    if conta_filtro_ids:
        tqs = tqs.filter(conta_id__in=conta_filtro_ids)
    if categoria_filtro_ids:
        tqs = tqs.filter(categoria_id__in=categoria_filtro_ids)
    if usa_filtros_relatorio and filtros.tipos:
        tqs = tqs.filter(tipo__in=filtros.tipos)
    tqs = tqs.exclude(_q_compras_em_fatura()).exclude(_q_pagamento_de_fatura())
    totais = tqs.aggregate(
        total_receitas=Sum("valor", filter=Q(tipo="receita")),
        total_despesas=Sum("valor", filter=Q(tipo="despesa")),
    )
    total_receitas = totais["total_receitas"] or Decimal("0")
    total_despesas = (totais["total_despesas"] or Decimal("0")) + despesas_resumo_fatura
    saldo_mes = total_receitas - total_despesas

    categorias_despesa = Categoria.objects.filter(
        Q(usuario=request.user) | Q(padrao=True),
        tipo="despesa",
        ativa=True,
    ).order_by("nome")
    categorias_receita = Categoria.objects.filter(
        Q(usuario=request.user) | Q(padrao=True),
        tipo="receita",
        ativa=True,
    ).order_by("nome")
    contas = Conta.objects.filter(usuario=request.user, ativa=True).order_by("nome")
    cartoes = Cartao.objects.filter(usuario=request.user, ativa=True).order_by("nome")
    contas_ativas = contas
    categorias_filtro = Categoria.objects.filter(
        Q(usuario=request.user) | Q(padrao=True),
        ativa=True,
    ).order_by("tipo", "nome")

    perfil, _ = Perfil.objects.get_or_create(usuario=request.user)
    initial_tx, tipo_padrao_perfil = perfil.defaults_transacao_form()

    if request.method == 'POST':
        tipo_inicial = request.POST.get('tipo', tipo_padrao_perfil)
        form = TransacaoForm(request.POST, usuario=request.user, tipo_inicial=tipo_inicial)
        if form.is_valid():
            transacao = form.save(commit=False)
            transacao.usuario = request.user
            cat_sug_id = request.POST.get("categorizacao_sugerida_id")
            if cat_sug_id:
                try:
                    transacao._categorizacao_meta = {
                        "categoria_sugerida_id": int(cat_sug_id),
                        "confianca": float(request.POST.get("categorizacao_confianca") or 0),
                        "fonte": request.POST.get("categorizacao_fonte") or "",
                        "merchant_key": request.POST.get("categorizacao_merchant_key") or "",
                    }
                except (TypeError, ValueError):
                    pass
            transacao.save()
            transacao.refresh_from_db()
            if transacao.tipo in ("receita", "despesa"):
                registrar_evento_seguro(request.user, "first_transaction_created")

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                data_exib = transacao.data_competencia or transacao.data
                resp = {
                    'status': 'ok',
                    'id': transacao.id,
                    'tipo': transacao.tipo,
                    'descricao': transacao.descricao,
                    'valor': str(transacao.valor),
                    'data': transacao.data.strftime('%Y-%m-%d'),
                    'data_exibicao': data_exib.strftime('%Y-%m-%d'),
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
                if transacao.cartao_id:
                    resp['cartao'] = {
                        'id': transacao.cartao.id,
                        'nome': transacao.cartao.nome,
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

    filtros_query_extra = ""
    if usa_filtros_relatorio:
        filtros_query_extra = "&" + filtros.to_query_string()

    icon_fallback_url = static("contas/icons/genericos/bank.svg")

    context = {
        "transacoes_por_dia": transacoes_por_dia,
        "page": page,
        "total_pages": total_pages,
        "total_itens": total_itens,
        "filtros_query_extra": filtros_query_extra,
        "icon_fallback_url": icon_fallback_url,
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
        "cartoes": cartoes,
        "total_receitas": total_receitas,
        "total_despesas": total_despesas,
        "saldo_mes": saldo_mes,
        "meses_dropdown": meses_dropdown,
        "filtros": filtros,
        "filtros_ativos_count": filtros.contagem_filtros_ativos() if usa_filtros_relatorio else 0,
        "filtros_limpar_url": f"{reverse('transacoes:historico')}?ano={ano}&mes={mes}",
        "contas_ativas": contas_ativas,
        "categorias_filtro": categorias_filtro,
        "usa_filtros_relatorio": usa_filtros_relatorio,
    }
    if getattr(request, "htmx", False) and request.GET.get("page"):
        return render(request, "transacoes/partials/historico_linhas.html", context)
    return render(request, "transacoes/partials/historico.html", context)


@login_required
def editar_transacao(request, pk):
    transacao = get_object_or_404(
        Transacao.objects.select_related("categoria", "conta", "cartao", "fatura"),
        pk=pk,
        usuario=request.user,
    )

    if transacao.tipo == "transferencia" and request.method == "POST":
        # Sempre bloqueia edição de perna isolada (AJAX e form clássico).
        msg = "Edite a transferência pelo fluxo dedicado (origem e destino)."
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(
                {"status": "error", "errors": {"__all__": [msg]}},
                status=400,
            )
        from django.contrib import messages

        messages.error(request, msg)
        ano_atual, mes_atual = _redirect_ano_mes_transacao(transacao)
        return redirect(f"/transacoes/?ano={ano_atual}&mes={mes_atual}")

    if request.method == "POST":
        form = TransacaoForm(
            request.POST, instance=transacao, usuario=request.user, tipo_inicial=transacao.tipo
        )
        if form.is_valid():
            with transaction.atomic():
                transacao_salva = form.save()

            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({'status': 'ok'})

            ano_atual, mes_atual = _redirect_ano_mes_transacao(transacao_salva)
            return redirect(f"/transacoes/?ano={ano_atual}&mes={mes_atual}")
        else:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    else:
        if request.GET.get("ajax"):
            data_exib = transacao.data_competencia or transacao.data
            payload = {
                "id": transacao.id,
                "tipo": transacao.tipo,
                "valor": str(transacao.valor),
                "descricao": transacao.descricao,
                "data": transacao.data.strftime("%Y-%m-%d"),
                "data_exibicao": data_exib.strftime("%Y-%m-%d"),
                "data_competencia": transacao.data_competencia.strftime("%Y-%m-%d")
                if transacao.data_competencia
                else None,
                "fatura_id": transacao.fatura_id,
                "categoria": {
                    "id": transacao.categoria.id,
                    "nome": transacao.categoria.nome
                },
                "conta": {
                    "id": transacao.conta.id,
                    "nome": transacao.conta.nome
                } if transacao.conta else None,
                "cartao": {
                    "id": transacao.cartao.id,
                    "nome": transacao.cartao.nome,
                    "conta_padrao_id": transacao.cartao.conta_padrao_id,
                }
                if transacao.cartao
                else None,
            }
            if transacao.tipo == "transferencia" and transacao.transfer_id:
                try:
                    tx_o, tx_d = obter_par_transferencia(request.user, transacao.transfer_id)
                    payload["transfer_id"] = str(transacao.transfer_id)
                    payload["papel_transferencia"] = transacao.papel_transferencia
                    payload["conta_origem"] = {
                        "id": tx_o.conta_id,
                        "nome": tx_o.conta.nome,
                    }
                    payload["conta_destino"] = {
                        "id": tx_d.conta_id,
                        "nome": tx_d.conta.nome,
                    }
                except ValidationError:
                    pass
            return JsonResponse(payload)

    form = TransacaoForm(instance=transacao, usuario=request.user, tipo_inicial=transacao.tipo)
    return render(request, "transacoes/editar_transacao.html", {"form": form, "transacao": transacao})


@require_POST
@login_required
def excluir_transacao(request, pk):
    transacao = get_object_or_404(Transacao, pk=pk, usuario=request.user)
    ano_atual, mes_atual = _redirect_ano_mes_transacao(transacao)
    if request.method == "POST":
        transfer_id = (
            transacao.transfer_id
            if transacao.tipo == "transferencia" and transacao.transfer_id
            else None
        )
        try:
            with transaction.atomic():
                if transfer_id:
                    excluir_transferencia(request.user, transfer_id)
                else:
                    transacao.delete()
        except ValidationError as exc:
            # Exclusão concorrente: se o par já sumiu, trata como sucesso idempotente.
            if transfer_id and not Transacao.objects.filter(
                usuario=request.user, transfer_id=transfer_id
            ).exists():
                pass
            elif request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(_json_erros_validation(exc), status=400)
            else:
                from django.contrib import messages

                messages.error(request, "; ".join(exc.messages))
                return redirect(f"/transacoes/?ano={ano_atual}&mes={mes_atual}")
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "ok"})
        return redirect(f"/transacoes/?ano={ano_atual}&mes={mes_atual}")
    return redirect(f"/transacoes/?ano={ano_atual}&mes={mes_atual}")


def _json_erros_form(form):
    return {"status": "error", "errors": form.errors}


def _json_erros_validation(exc: ValidationError):
    if hasattr(exc, "message_dict") and exc.message_dict:
        return {"status": "error", "errors": exc.message_dict}
    return {"status": "error", "errors": {"__all__": list(exc.messages)}}


@require_POST
@login_required
def transferir(request):
    """Cria ou atualiza transferência (duas pernas com o mesmo transfer_id)."""
    form = TransferenciaForm(request.POST, usuario=request.user)
    if not form.is_valid():
        return JsonResponse(_json_erros_form(form), status=400)

    data = form.cleaned_data
    idem_raw = (
        request.headers.get("X-Idempotency-Key")
        or request.POST.get("idempotency_key")
        or ""
    ).strip()
    idempotency_key = None
    if idem_raw:
        try:
            idempotency_key = uuid.UUID(str(idem_raw))
        except ValueError:
            return JsonResponse(
                {"status": "error", "errors": {"idempotency_key": ["Chave de idempotência inválida."]}},
                status=400,
            )

    try:
        if data.get("transfer_id"):
            tx_origem, tx_destino = atualizar_transferencia(
                request.user,
                data["transfer_id"],
                conta_origem=data["conta_origem"],
                conta_destino=data["conta_destino"],
                valor=data["valor"],
                data=data["data"],
                descricao=data.get("descricao") or "Transferência",
            )
        else:
            tx_origem, tx_destino = criar_transferencia(
                request.user,
                conta_origem=data["conta_origem"],
                conta_destino=data["conta_destino"],
                valor=data["valor"],
                data=data["data"],
                descricao=data.get("descricao") or "Transferência",
                idempotency_key=idempotency_key,
            )
    except ValidationError as exc:
        return JsonResponse(_json_erros_validation(exc), status=400)

    return JsonResponse(
        {
            "status": "ok",
            "transfer_id": str(tx_origem.transfer_id),
            "origem_id": tx_origem.id,
            "destino_id": tx_destino.id,
            "tipo": "transferencia",
            "valor": str(tx_origem.valor),
            "data": tx_origem.data.strftime("%Y-%m-%d"),
            "descricao": tx_origem.descricao,
            "conta_origem": {"id": tx_origem.conta_id, "nome": tx_origem.conta.nome},
            "conta_destino": {"id": tx_destino.conta_id, "nome": tx_destino.conta.nome},
        }
    )


@login_required
def dados_grafico_receitas_despesas(request):
    transacoes = (
        Transacao.objects.filter(usuario=request.user, tipo__in=["receita", "despesa"])
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

    registrar_evento_seguro(request.user, "first_import_started")

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
        registrar_evento_seguro(request.user, "first_import_failed")
        return JsonResponse(
            {"status": "error", "message": "Arquivo muito grande."},
            status=400,
        )

    try:
        linhas_parse = parse_ofx_bytes(raw)
    except ValueError as exc:
        registrar_evento_seguro(request.user, "first_import_failed")
        return JsonResponse({"status": "error", "message": str(exc)}, status=400)
    except OfxParserException:
        registrar_evento_seguro(request.user, "first_import_failed")
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
    registrar_evento_seguro(request.user, "first_import_started")
    if not _upload_filename_is_xlsx(upload):
        registrar_evento_seguro(request.user, "first_import_failed")
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
        registrar_evento_seguro(request.user, "first_import_failed")
        return JsonResponse(
            {"status": "error", "message": "Arquivo muito grande."},
            status=400,
        )

    try:
        linhas_parse = parse_planilha_padrao_bytes(raw)
    except ValueError as exc:
        registrar_evento_seguro(request.user, "first_import_failed")
        return JsonResponse({"status": "error", "message": str(exc)}, status=400)

    if len(linhas_parse) > _MAX_LINHAS_IMPORT_OFX:
        registrar_evento_seguro(request.user, "first_import_failed")
        return JsonResponse(
            {
                "status": "error",
                "message": f"Limite de {_MAX_LINHAS_IMPORT_OFX} linhas por importação.",
            },
            status=400,
        )
    if len(linhas_parse) == 0:
        registrar_evento_seguro(request.user, "first_import_failed")
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
    metadados_import: list[dict] = []
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
                Transacao.objects.filter(usuario=request.user, conta=conta, ofx_fitid=fitid)
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
        metadados_import.append({
            "categoria_sugerida_id": row.get("categoria_sugerida_id"),
            "confianca": row.get("categoria_sugerida_confianca"),
            "fonte": row.get("categoria_sugerida_fonte") or "",
            "merchant_key": row.get("categoria_sugerida_merchant_key") or "",
        })

    if erros_por_chave:
        registrar_evento_seguro(request.user, "first_import_failed")
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
                usuario=request.user,
                conta=conta,
                ofx_fitid__in=fitids_inserir,
            ).values_list("ofx_fitid", flat=True)
        )
        if existentes:
            registrar_evento_seguro(request.user, "first_import_failed")
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
            criadas = Transacao.objects.bulk_create(instancias)
            for tx, meta in zip(criadas, metadados_import, strict=True):
                cat_sug = meta.get("categoria_sugerida_id")
                try:
                    cat_sug_int = int(cat_sug) if cat_sug not in (None, "") else None
                except (TypeError, ValueError):
                    cat_sug_int = None
                conf = meta.get("confianca")
                try:
                    conf_float = float(conf) if conf not in (None, "") else None
                except (TypeError, ValueError):
                    conf_float = None
                processar_feedback_transacao(
                    usuario=request.user,
                    transacao=tx,
                    descricao=tx.descricao,
                    categoria_final=tx.categoria,
                    categoria_sugerida_id=cat_sug_int,
                    confianca=conf_float,
                    fonte=str(meta.get("fonte") or ""),
                    merchant_key=str(meta.get("merchant_key") or ""),
                )
    except IntegrityError:
        registrar_evento_seguro(request.user, "first_import_failed")
        return JsonResponse(
            {
                "status": "error",
                "message": "Conflito ao gravar (ex.: FITID duplicado). Tente novamente.",
            },
            status=400,
        )

    registrar_evento_seguro(request.user, "first_import_completed")
    if any(t.tipo in ("receita", "despesa") for t in instancias):
        registrar_evento_seguro(request.user, "first_transaction_created")
    return JsonResponse({"status": "ok", "criadas": len(instancias)})
