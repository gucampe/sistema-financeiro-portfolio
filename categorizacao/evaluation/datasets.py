from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

AVALIACAO_DIR = Path(__file__).resolve().parents[2] / "docs" / "categorizacao"
GOLDEN_CSV = AVALIACAO_DIR / "datasets" / "golden_categorizacao_v1.csv"

CSV_HEADER = [
    "id",
    "descricao",
    "tipo",
    "valor",
    "categoria_esperada",
    "categorias_aceitaveis",
    "bucket",
    "banco_origem",
    "notas_avaliador",
]


@dataclass(frozen=True)
class GoldenCase:
    id: str
    descricao: str
    tipo: str
    valor: str
    categoria_esperada: str
    categorias_aceitaveis: str
    bucket: str
    banco_origem: str
    notas_avaliador: str


def _row(
    cid: str,
    descricao: str,
    cat: str,
    bucket: str,
    *,
    tipo: str = "despesa",
    valor: str = "-50.00",
    notas: str = "",
) -> GoldenCase:
    aceitaveis = cat
    esperada = cat.split("|")[0] if cat else ""
    if "|" in cat:
        aceitaveis = cat
        esperada = cat.split("|")[0]
    return GoldenCase(
        id=cid,
        descricao=descricao,
        tipo=tipo,
        valor=valor,
        categoria_esperada=esperada,
        categorias_aceitaveis=aceitaveis,
        bucket=bucket,
        banco_origem="sintetico",
        notas_avaliador=notas,
    )


def all_golden_cases() -> list[GoldenCase]:
    cases: list[GoldenCase] = []

    m1_data = [
        ("M1-001", "COMPRA CARTAO IFOOD 12/03", "Alimentação"),
        ("M1-002", "DEBITO IFOOD RESTAURANTE SAO PAULO BR", "Alimentação"),
        ("M1-003", "UBER TRIP SAO PAULO", "Transporte e locomoção"),
        ("M1-004", "UBER *TRIP HELP", "Transporte e locomoção"),
        ("M1-005", "NETFLIX.COM", "Serviços e Assinaturas"),
        ("M1-006", "SPOTIFY BR", "Serviços e Assinaturas"),
        ("M1-007", "DROGASIL 1234", "Saúde"),
        ("M1-008", "DROGA RAIA FILIAL", "Saúde"),
        ("M1-009", "CARREFOUR COM", "Supermercado"),
        ("M1-010", "PAO DE ACUCAR", "Supermercado"),
        ("M1-011", "MERCADO LIVRE", "Compras"),
        ("M1-012", "AMAZON BR", "Compras"),
        ("M1-013", "SHOPEE BR", "Compras"),
        ("M1-014", "SHELL POSTO", "Transporte e locomoção"),
        ("M1-015", "IPIRANGA POSTO", "Transporte e locomoção"),
        ("M1-016", "MCDONALDS", "Restaurantes e bares"),
        ("M1-017", "STARBUCKS BR", "Restaurantes e bares"),
        ("M1-018", "ENEL SP", "Moradia"),
        ("M1-019", "CLARO MOVEL", "Serviços e Assinaturas"),
        ("M1-020", "CINEMARK", "Lazer"),
        ("M1-021", "PETZ LOJA", "Animais de estimação"),
        ("M1-022", "RENNER LOJAS", "Roupas"),
        ("M1-023", "SMART FIT", "Cuidados pessoais"),
        ("M1-024", "LATAM AIRLINES", "Viagens"),
        ("M1-025", "BOOKING.COM", "Viagens"),
        ("M1-026", "ALURA CURSOS", "Educação"),
        ("M1-027", "RECEITA FEDERAL DARF", "Taxas e tributos"),
        ("M1-028", "99 POP", "Transporte e locomoção"),
        ("M1-029", "RAPPI BRASIL", "Alimentação"),
        ("M1-030", "HBO MAX", "Serviços e Assinaturas"),
        ("M1-031", "DISNEY PLUS", "Serviços e Assinaturas"),
        ("M1-032", "ATACADAO SA", "Supermercado"),
        ("M1-033", "ASSAI ATACADISTA", "Supermercado"),
        ("M1-034", "MAGAZINE LUIZA", "Compras"),
        ("M1-035", "CASAS BAHIA", "Compras"),
        ("M1-036", "COBASI PET", "Animais de estimação"),
        ("M1-037", "BURGER KING", "Restaurantes e bares"),
        ("M1-038", "OUTBACK STEAKHOUSE", "Restaurantes e bares"),
        ("M1-039", "CPFL ENERGIA", "Moradia"),
        ("M1-040", "SABESP", "Moradia"),
    ]
    for cid, desc, cat in m1_data:
        cases.append(_row(cid, desc, cat, "M1", notas="merchant seed"))

    m2_data = [
        ("M2-001", "IFOOD*REST PIZZA", "Alimentação"),
        ("M2-002", "IF00D DELIVERY", "Alimentação"),
        ("M2-003", "UBER DO BRASIL TRIP", "Transporte e locomoção"),
        ("M2-004", "NETFLIX SUBSCRIPTION", "Serviços e Assinaturas"),
        ("M2-005", "DROGASIL SA LOJA", "Saúde"),
        ("M2-006", "CARREFOUR BARRA", "Supermercado"),
        ("M2-007", "AMAZON MARKETPLACE", "Compras"),
        ("M2-008", "SPOTIFY PREMIUM", "Serviços e Assinaturas"),
        ("M2-009", "POSTO BR DISTRIBUIDORA", "Transporte e locomoção"),
        ("M2-010", "MERCADOLIVRE COMPRA", "Compras"),
        ("M2-011", "99 TAXI RIDE", "Transporte e locomoção"),
        ("M2-012", "RAPPI PRO", "Alimentação"),
        ("M2-013", "NUBANK NU PAGAMENTOS", "Diversos"),
        ("M2-014", "GOOGLE PLAY STORAGE", "Serviços e Assinaturas"),
        ("M2-015", "APPLE COM BILL", "Serviços e Assinaturas"),
        ("M2-016", "MICROSOFT 365", "Serviços e Assinaturas"),
        ("M2-017", "STEAM GAMES", "Lazer"),
        ("M2-018", "PLAYSTATION NETWORK", "Lazer"),
        ("M2-019", "DECATHLON BR", "Compras"),
        ("M2-020", "ZARA BRASIL", "Roupas"),
        ("M2-021", "FLEURY MEDICINA", "Saúde"),
        ("M2-022", "LOCALIZA RENT", "Viagens"),
        ("M2-023", "UDEMY CURSO", "Educação"),
        ("M2-024", "GITHUB INC", "Trabalho"),
        ("M2-025", "FIGMA SUBSCRIPTION", "Trabalho"),
    ]
    for cid, desc, cat in m2_data:
        cases.append(_row(cid, desc, cat, "M2", notas="variacao ortografica"))

    m3_specs = [
        ("M3-001", "PADARIA CENTRAL LTDA", ""),
        ("M3-002", "BARBEARIA DO ZE", "Cuidados pessoais"),
        ("M3-003", "MERCADO MUNICIPAL", "Supermercado|Compras"),
        ("M3-004", "LANCHONETE DA ESQUINA", "Alimentação|Restaurantes e bares"),
        ("M3-005", "OFICINA MECANICA SILVA", "Transporte e locomoção|Diversos"),
        ("M3-006", "ACADEMIA FORMA", "Cuidados pessoais"),
        ("M3-007", "LOJA DE CONVENIENCIA 24H", "Diversos"),
        ("M3-008", "FEIRA LIVRE PRODUTOR", "Supermercado"),
        ("M3-009", "ESTUDIO TATUAGEM ARTE", "Cuidados pessoais|Lazer"),
        ("M3-010", "SERVICOS GERAIS JOAO", ""),
        ("M3-011", "DEPOSITO DE BEBIDAS", "Restaurantes e bares|Diversos"),
        ("M3-012", "PAPELARIA ESCOLAR", "Educação|Compras"),
        ("M3-013", "HORTIFRUTI BOM PRECO", "Supermercado"),
        ("M3-014", "CONSERTO CELULAR EXPRESS", "Compras|Diversos"),
        ("M3-015", "ESTACIONAMENTO CENTRO", "Transporte e locomoção"),
        ("M3-016", "LAVANDERIA EXPRESS", "Moradia|Diversos"),
        ("M3-017", "PET SHOP AMIGO", "Animais de estimação"),
        ("M3-018", "CONSTRUCAO MATERIAIS", "Moradia|Compras"),
        ("M3-019", "DENTISTA DR CARLOS", "Saúde"),
        ("M3-020", "PSICOLOGA ANA CLINICA", "Saúde"),
        ("M3-021", "ESCOLA INFANTIL ABC", "Educação"),
        ("M3-022", "ASSISTENCIA TECNICA TV", "Compras"),
        ("M3-023", "DELIVERY SUSHI HOUSE", "Restaurantes e bares|Alimentação"),
        ("M3-024", "CHURRASCARIA BOI NOBRE", "Restaurantes e bares"),
        ("M3-025", "LOJA DE ROUPAS FASHION", "Roupas"),
        ("M3-026", "PRESENTES E ARTESANATO", "Presentes e doações|Compras"),
        ("M3-027", "CONDOMINIO TAXA EXTRA", "Moradia"),
        ("M3-028", "SEGURO RESIDENCIAL", "Moradia"),
        ("M3-029", "CONSULTORIA FREELANCE", "Trabalho|Receitas diversas"),
        ("M3-030", "DOACAO ONG LOCAL", "Presentes e doações"),
    ]
    for cid, desc, cat in m3_specs:
        cases.append(_row(cid, desc, cat, "M3", notas="estabelecimento local"))

    r1_specs = [
        ("R1-001", "DEBITO COMPRA ELECTRON CARREFOUR BARRA 15/01 SAO PAULO BR", "Supermercado"),
        ("R1-002", "COMPRA CARTAO - IFOOD *PIZZARIA SAO PAULO BR", "Alimentação"),
        ("R1-003", "PAGAMENTO CARTAO CREDITO FATURA", "Taxas e tributos|Diversos"),
        ("R1-004", "COMPRA CARTAO NETFLIX 03/24", "Serviços e Assinaturas"),
        ("R1-005", "DEBITO AUTOMATICO SPOTIFY", "Serviços e Assinaturas"),
        ("R1-006", "COMPRA INTERNACIONAL AMAZON COM 123456", "Compras"),
        ("R1-007", "TED DOC TARIFA BANCARIA", "Taxas e tributos"),
        ("R1-008", "COMPRA CARTAO UBER TRIP 22/06 RIO DE JANEIRO BR", "Transporte e locomoção"),
        ("R1-009", "DEBITO DROGASIL SA 98765", "Saúde"),
        ("R1-010", "COMPRA CARTAO MCDONALDS BRASIL", "Restaurantes e bares"),
        ("R1-011", "PAGTO ENEL DISTRIBUICAO", "Moradia"),
        ("R1-012", "COMPRA CARTAO SHOPEE 554433", "Compras"),
        ("R1-013", "DEBITO SHELL BOX 15/12", "Transporte e locomoção"),
        ("R1-014", "COMPRA CARTAO PETZ 7788", "Animais de estimação"),
        ("R1-015", "CREDITO ESTORNO COMPRA", "Diversos|Receitas diversas"),
        ("R1-016", "COMPRA CARTAO LATAM AIR 01/08", "Viagens"),
        ("R1-017", "DEBITO CLARO MOVEL FATURA", "Serviços e Assinaturas"),
        ("R1-018", "COMPRA CARTAO RENNER 3344", "Roupas"),
        ("R1-019", "PAGAMENTO BOLETO SABESP", "Moradia"),
        ("R1-020", "COMPRA CARTAO SMARTFIT", "Cuidados pessoais"),
        ("R1-021", "DEBITO AUTOMATICO ALURA", "Educação"),
        ("R1-022", "COMPRA CARTAO CINEMARK INGRESSO", "Lazer"),
        ("R1-023", "TRANSFERENCIA ENVIADA TAR", "Taxas e tributos|Diversos"),
        ("R1-024", "COMPRA CARTAO ASSAI 5566", "Supermercado"),
        ("R1-025", "DEBITO ATACADAO 7788", "Supermercado"),
        ("R1-026", "COMPRA CARTAO MAGALU 9900", "Compras"),
        ("R1-027", "PAGTO IPVA DETRAN", "Taxas e tributos"),
        ("R1-028", "COMPRA CARTAO OUTBACK", "Restaurantes e bares"),
        ("R1-029", "DEBITO VIVO TELEFONICA", "Serviços e Assinaturas"),
        ("R1-030", "COMPRA CARTAO COBASI", "Animais de estimação"),
    ]
    for cid, desc, cat in r1_specs:
        tipo = "receita" if "CREDITO ESTORNO" in desc else "despesa"
        valor = "45.00" if tipo == "receita" else "-45.00"
        cases.append(_row(cid, desc, cat, "R1", tipo=tipo, valor=valor, notas="ruido bancario"))

    r2_specs = [
        ("R2-001", "PIX ENVIADO JOAO SILVA", "", "despesa"),
        ("R2-002", "PIX RECEBIDO MARIA", "Receitas diversas", "receita"),
        ("R2-003", "PIX MARIA SILVA", "", "despesa"),
        ("R2-004", "PIX ENVIADO PEDRO SANTOS", "", "despesa"),
        ("R2-005", "TED ENVIADA EMPRESA XYZ", "Trabalho|Diversos", "despesa"),
        ("R2-006", "DOC TRANSFERENCIA CONTA", "Diversos", "despesa"),
        ("R2-007", "PIX RECEBIDO REEMBOLSO", "Receitas diversas", "receita"),
        ("R2-008", "PIX ENVIADO ALUGUEL PROPRIETARIO", "Moradia", "despesa"),
        ("R2-009", "PIX ENVIADO DIARISTA", "Moradia|Diversos", "despesa"),
        ("R2-010", "PIX RECEBIDO SALARIO EMPRESA", "Salário", "receita"),
        ("R2-011", "PIX ENVIADO PRESENTE ANIVERSARIO", "Presentes e doações", "despesa"),
        ("R2-012", "PIX ENVIADO CURSO PAGAMENTO", "Educação", "despesa"),
        ("R2-013", "TRANSFERENCIA ENTRE CONTAS", "Diversos", "despesa"),
        ("R2-014", "PIX ENVIADO UBER DO BRASIL", "Transporte e locomoção", "despesa"),
        ("R2-015", "PIX ENVIADO IFOOD", "Alimentação", "despesa"),
        ("R2-016", "PIX RECEBIDO DIVIDENDOS", "Retorno de investimentos", "receita"),
        ("R2-017", "PIX ENVIADO MECANICO", "Transporte e locomoção|Diversos", "despesa"),
        ("R2-018", "PIX ENVIADO VETERINARIO", "Animais de estimação|Saúde", "despesa"),
        ("R2-019", "PIX RECEBIDO FREELANCE", "Receitas diversas|Trabalho", "receita"),
        ("R2-020", "PIX ENVIADO ACADEMIA", "Cuidados pessoais", "despesa"),
    ]
    for cid, desc, cat, tipo in r2_specs:
        valor = "100.00" if tipo == "receita" else "-80.00"
        cases.append(_row(cid, desc, cat, "R2", tipo=tipo, valor=valor, notas="pix/transferencia"))

    r3_specs = [
        ("R3-001", "LOJAS AMERICANAS 03/10", "Compras"),
        ("R3-002", "PARCELA 5/12 MAGALU", "Compras"),
        ("R3-003", "CASAS BAHIA PARC 2/6", "Compras"),
        ("R3-004", "RENNER PARCELA 4/4", "Roupas"),
        ("R3-005", "AMAZON PARC 1/3", "Compras"),
        ("R3-006", "CARREFOUR PARCELAMENTO 2/2", "Supermercado"),
        ("R3-007", "NETFLIX MENSAL RECORRENTE", "Serviços e Assinaturas"),
        ("R3-008", "SPOTIFY RECORRENTE", "Serviços e Assinaturas"),
        ("R3-009", "CLARO FATURA MENSAL", "Serviços e Assinaturas"),
        ("R3-010", "ENEL CONTA LUZ MENSAL", "Moradia"),
        ("R3-011", "ALUGUEL CONDOMINIO MENSAL", "Moradia"),
        ("R3-012", "FINANCIAMENTO VEICULO PARC", "Empréstimos e financiamentos"),
        ("R3-013", "EMPRESTIMO PARCELA 8/24", "Empréstimos e financiamentos"),
        ("R3-014", "SEGURO AUTO MENSAL", "Transporte e locomoção|Moradia"),
        ("R3-015", "ASSINATURA GYM MENSAL", "Cuidados pessoais"),
    ]
    for cid, desc, cat in r3_specs:
        cases.append(_row(cid, desc, cat, "R3", notas="parcelamento/recorrente"))

    c1_specs = [
        ("C1-001", "AMAZON BR", "Compras|Supermercado"),
        ("C1-002", "MERCADO LIVRE ELETRONICOS", "Compras"),
        ("C1-003", "RAPPI CONVENIENCIA", "Alimentação|Restaurantes e bares"),
        ("C1-004", "IFOOD MERCADO", "Alimentação|Supermercado"),
        ("C1-005", "UBER EATS", "Alimentação|Restaurantes e bares"),
        ("C1-006", "MERCADO MUNICIPAL FEIRA", "Supermercado|Compras"),
        ("C1-007", "POSTO IPIRANGA CONVENIENCIA", "Transporte e locomoção|Alimentação"),
        ("C1-008", "FARMACIA POPULAR DROGASIL", "Saúde"),
        ("C1-009", "APPLE STORE COMPRA", "Compras|Trabalho"),
        ("C1-010", "GOOGLE ONE STORAGE", "Serviços e Assinaturas|Trabalho"),
        ("C1-011", "NUBANK TARIFA PACOTE", "Taxas e tributos|Diversos"),
        ("C1-012", "ITAU ANUIDADE CARTAO", "Taxas e tributos"),
        ("C1-013", "SUPERMERCADO EXTRA PAES", "Supermercado|Alimentação"),
        ("C1-014", "RESTAURANTE JAPONES SUSHI", "Restaurantes e bares|Alimentação"),
        ("C1-015", "PRESENTE AMAZON", "Presentes e doações|Compras"),
        ("C1-016", "DOACAO INSTITUICAO", "Presentes e doações"),
        ("C1-017", "CURSO ONLINE UDEMY", "Educação|Trabalho"),
        ("C1-018", "MATERIAL ESCRITORIO", "Trabalho|Compras"),
        ("C1-019", "VIAGEM HOTEL AIRBNB", "Viagens"),
        ("C1-020", "PASSAGEM GOL LINHAS", "Viagens"),
    ]
    for cid, desc, cat in c1_specs:
        cases.append(_row(cid, desc, cat, "C1", notas="categoria subjetiva"))

    return cases


def write_golden_csv(path: Path | None = None) -> Path:
    path = path or GOLDEN_CSV
    path.parent.mkdir(parents=True, exist_ok=True)
    cases = all_golden_cases()
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        for c in cases:
            writer.writerow(
                {
                    "id": c.id,
                    "descricao": c.descricao,
                    "tipo": c.tipo,
                    "valor": c.valor,
                    "categoria_esperada": c.categoria_esperada,
                    "categorias_aceitaveis": c.categorias_aceitaveis,
                    "bucket": c.bucket,
                    "banco_origem": c.banco_origem,
                    "notas_avaliador": c.notas_avaliador,
                }
            )
    return path


def load_golden_csv(path: Path | None = None) -> list[GoldenCase]:
    path = path or GOLDEN_CSV
    cases = []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cases.append(GoldenCase(**row))
    return cases


def categorias_aceitaveis_set(case: GoldenCase) -> set[str]:
    if not case.categorias_aceitaveis:
        if case.categoria_esperada:
            return {case.categoria_esperada}
        return set()
    return {p.strip() for p in case.categorias_aceitaveis.split("|") if p.strip()}
