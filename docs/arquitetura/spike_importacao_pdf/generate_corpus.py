#!/usr/bin/env python3
"""Gera corpus sintético (sem PII) para o spike de importação PDF.

Não é código de produção. PDFs ficam em --out (default /tmp/spike_pdf_corpus).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet


HEADERS = ["Data", "Historico", "Debito", "Credito", "Saldo"]

MOVIMENTOS = [
    ("02/03/2026", "SALDO ANTERIOR", "", "", "1.250,00"),
    ("03/03/2026", "PIX ENVIADO JOAO SILVA", "85,00", "", "1.165,00"),
    ("03/03/2026", "PAGTO CONTA LUZ", "210,40", "", "954,60"),
    ("05/03/2026", "PIX RECEBIDO PADARIA CENTRAL", "", "40,00", "994,60"),
    ("07/03/2026", "TED ENVIADA FORNECEDOR ALFA", "1.100,00", "", "-105,40"),
    ("10/03/2026", "SALARIO EMPRESA BETA LTDA", "", "3.200,00", "3.094,60"),
    ("12/03/2026", "DEBITO CARTAO SUPERMERCADO", "327,90", "", "2.766,70"),
    ("15/03/2026", "PIX ENVIADO MARIA SOUZA", "50,00", "", "2.716,70"),
    ("18/03/2026", "RENDIMENTO CONTA", "", "1,12", "2.717,82"),
    ("20/03/2026", "TARIFA PACOTE SERVICOS", "29,90", "", "2.687,92"),
]

POUPANCA = [
    ("02/03/2026", "SALDO ANTERIOR", "", "", "5.000,00"),
    ("10/03/2026", "APLICACAO POUPANCA", "", "200,00", "5.200,00"),
    ("28/03/2026", "RENDIMENTO POUPANCA", "", "12,35", "5.212,35"),
]

INVEST = [
    ("CDB 000111222", "Liquidez diaria", "10.000,00", "10.040,00", "Moderado"),
    ("TESOUURO SELIC 2029", "Aplicacao 998877", "2.500,00", "2.531,10", "Conservador"),
]


def _table(data, col_widths):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return t


def write_structured(path: Path) -> None:
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Banco Exemplo S.A. — Extrato Conta Corrente", styles["Title"]),
        Paragraph("Agencia 1234 Conta 00012345-6 Titular PESSOA SINTETICA", styles["Normal"]),
        Spacer(1, 8),
        Paragraph("Movimentacao — Periodo 01/03/2026 a 31/03/2026", styles["Heading2"]),
        _table([HEADERS] + [list(r) for r in MOVIMENTOS], [70, 220, 70, 70, 70]),
        Spacer(1, 8),
        Paragraph("Saldo inicial 1.250,00 | Saldo final 2.687,92", styles["Normal"]),
    ]
    doc.build(story)


def write_no_title(path: Path) -> None:
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    story = [_table([HEADERS] + [list(r) for r in MOVIMENTOS], [70, 220, 70, 70, 70])]
    doc.build(story)


def write_signed_amount(path: Path) -> None:
    rows = [["Data", "Historico", "Valor"]]
    for d, h, deb, cred, _saldo in MOVIMENTOS[1:]:
        if deb:
            rows.append([d, h, f"-{deb}"])
        else:
            rows.append([d, h, cred])
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Extrato", styles["Heading1"]),
        _table(rows, [70, 300, 90]),
    ]
    doc.build(story)


def write_multiline(path: Path) -> None:
    rows = [HEADERS]
    rows.append(
        [
            "11/03/2026",
            "PIX ENVIADO\nJOAO DA SILVA SANTOS\nCPF ***.111.222-**",
            "85,00",
            "",
            "1.165,00",
        ]
    )
    rows.extend([list(r) for r in MOVIMENTOS[2:5]])
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    doc.build([_table(rows, [70, 220, 70, 70, 70])])


def write_multipage(path: Path) -> None:
    rows = [HEADERS]
    saldo = 1000.0
    for i in range(80):
        deb = 10.0 + (i % 7)
        saldo -= deb
        rows.append(
            [
                f"{(i % 28) + 1:02d}/03/2026",
                f"LANCAMENTO AUTOMATICO {i:03d} COM DESCRICAO EXTENSA PARA TESTE",
                f"{deb:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "",
                f"{saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            ]
        )
    doc = SimpleDocTemplate(str(path), pagesize=A4, topMargin=20 * mm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Extrato multipagina com cabecalho repetido", styles["Heading2"]),
        _table(rows, [70, 220, 70, 70, 70]),
    ]
    doc.build(story)


def write_multi_section(path: Path) -> None:
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()
    inv_headers = ["Produto", "Descricao", "Aplicado", "Bruto", "Perfil risco"]
    story = [
        Paragraph("Comprovante consolidado — Banco Exemplo", styles["Title"]),
        Paragraph("Titular PESSOA SINTETICA | Agencia 1234 | Conta 00012345-6", styles["Normal"]),
        Spacer(1, 10),
        Paragraph("Conta corrente — Movimentacao", styles["Heading2"]),
        _table([HEADERS] + [list(r) for r in MOVIMENTOS], [70, 200, 70, 70, 70]),
        Spacer(1, 14),
        Paragraph("Poupanca", styles["Heading2"]),
        _table([HEADERS] + [list(r) for r in POUPANCA], [70, 200, 70, 70, 70]),
        PageBreak(),
        Paragraph("Investimentos", styles["Heading2"]),
        _table([inv_headers] + [list(r) for r in INVEST], [120, 120, 80, 80, 90]),
        Spacer(1, 14),
        Paragraph("Limite de credito: 4.000,00 | Pontuacao relacionamento: 812", styles["Normal"]),
        Paragraph("Pacote de servicos: Cesta Plus contratada em 01/01/2025", styles["Normal"]),
    ]
    doc.build(story)


def write_aligned_text(path: Path) -> None:
    """Texto selecionável alinhado em colunas, SEM objeto Table (app-like)."""
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    y = h - 40
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Extrato conta corrente (texto posicionado)")
    y -= 28
    c.setFont("Helvetica-Bold", 8)
    xs = [40, 100, 320, 400, 480]
    for x, head in zip(xs, HEADERS):
        c.drawString(x, y, head)
    y -= 16
    c.setFont("Helvetica", 8)
    for row in MOVIMENTOS:
        for x, cell in zip(xs, row):
            c.drawRightString(x + 60, y, cell) if x >= 320 else c.drawString(x, y, cell)
        y -= 14
    c.save()


def write_out_of_order(path: Path) -> None:
    """Mesmo visual, ordem de desenho invertida (reading-order vs visual)."""
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    y = h - 80
    xs = [40, 100, 320, 400, 480]
    c.setFont("Helvetica", 8)
    for row in reversed(MOVIMENTOS):
        for x, cell in zip(reversed(xs), reversed(row)):
            c.drawString(x, y, cell)
        y += 14
    c.setFont("Helvetica-Bold", 8)
    for x, head in zip(reversed(xs), reversed(HEADERS)):
        c.drawString(x, y + 10, head)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, h - 40, "Extrato com ordem de desenho invertida")
    c.save()


def write_linear_prose(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    y = A4[1] - 50
    c.setFont("Helvetica", 10)
    c.drawString(40, y, "Prezado cliente, segue o resumo do seu relacionamento.")
    y -= 20
    for row in MOVIMENTOS:
        line = " | ".join(row)
        c.drawString(40, y, line)
        y -= 14
    c.drawString(40, y - 20, "Agradecemos a preferencia. Perfil de risco: moderado.")
    c.save()


def write_image_only(path: Path) -> None:
    img = Image.new("RGB", (1200, 700), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        font_b = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
        font_b = font
    draw.text((20, 20), "EXTRATO (somente imagem — simula scan)", fill="black", font=font_b)
    y = 70
    draw.text((20, y), "  ".join(HEADERS), fill="black", font=font_b)
    y += 30
    for row in MOVIMENTOS:
        draw.text((20, y), "  ".join(row), fill="black", font=font)
        y += 24
    img_path = path.with_suffix(".png")
    img.save(img_path)
    c = canvas.Canvas(str(path), pagesize=A4)
    c.drawImage(str(img_path), 20, 200, width=550, height=320)
    c.save()
    img_path.unlink(missing_ok=True)


def write_password(path: Path, structured: Path) -> None:
    import pymupdf

    doc = pymupdf.open(structured)
    doc.save(
        str(path),
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="owner-secret",
        user_pw="user-secret",
    )
    doc.close()


def write_malformed(path: Path, structured: Path) -> None:
    data = structured.read_bytes()
    path.write_bytes(data[: max(64, len(data) // 5)])


def write_many_pages(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    for p in range(40):
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, 800, f"Pagina {p + 1} de 40 — extrato sintetico")
        c.setFont("Helvetica", 8)
        y = 770
        c.drawString(40, y, "Data     Historico                         Valor     Saldo")
        y -= 14
        for i in range(32):
            c.drawString(40, y, f"01/03/2026  LANCAMENTO P{p:02d} L{i:02d}           10,00     100,00")
            y -= 12
        c.showPage()
    c.save()


def write_vector_heavy(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Helvetica", 9)
    c.drawString(40, 800, "PDF com muitos paths vetoriais + uma tabela textual")
    for i in range(4000):
        x = 20 + (i * 7) % 500
        y = 20 + (i * 11) % 750
        c.setStrokeColorRGB((i % 10) / 10, 0.2, 0.5)
        c.line(x, y, x + 12, y + 8)
    y = 700
    for row in MOVIMENTOS:
        c.drawString(40, y, "  ".join(row))
        y -= 14
    c.save()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="/tmp/spike_pdf_corpus")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    write_structured(out / "01_structured_table.pdf")
    write_no_title(out / "02_no_title.pdf")
    write_signed_amount(out / "03_signed_amount.pdf")
    write_multiline(out / "04_multiline.pdf")
    write_multipage(out / "05_multipage_repeat_header.pdf")
    write_multi_section(out / "06_multi_section.pdf")
    write_aligned_text(out / "07_aligned_text_no_tableobj.pdf")
    write_out_of_order(out / "08_draw_order_inverted.pdf")
    write_linear_prose(out / "09_linear_prose.pdf")
    write_image_only(out / "10_image_only.pdf")
    write_password(out / "11_password.pdf", out / "01_structured_table.pdf")
    write_malformed(out / "12_malformed.pdf", out / "01_structured_table.pdf")
    write_many_pages(out / "13_many_pages_40.pdf")
    write_vector_heavy(out / "14_vector_heavy.pdf")
    print(f"corpus em {out}")


if __name__ == "__main__":
    main()
