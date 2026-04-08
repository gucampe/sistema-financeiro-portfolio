from datetime import date
from decimal import Decimal
from pathlib import Path

from django.test import SimpleTestCase
from ofxparse.ofxparse import OfxParserException

from transacoes.ofx_parse import LinhaOfx, parse_ofx_bytes

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SAMPLE_OFX = FIXTURES / "sample.ofx"


class ParseOfxBytesTests(SimpleTestCase):
    def test_sample_ofx_extrai_tres_linhas(self):
        raw = SAMPLE_OFX.read_bytes()
        linhas = parse_ofx_bytes(raw)

        self.assertEqual(len(linhas), 3)

        self.assertEqual(
            linhas[0],
            LinhaOfx(
                data=date(2024, 1, 15),
                valor=Decimal("42.50"),
                tipo="despesa",
                descricao="PADARIA CENTRAL COMPRA DEB",
                ofx_fitid="sample-fitid-1",
            ),
        )

        self.assertEqual(linhas[1].tipo, "receita")
        self.assertEqual(linhas[1].valor, Decimal("1000.00"))
        self.assertEqual(linhas[1].ofx_fitid, "sample-fitid-2")
        self.assertEqual(linhas[1].descricao, "SALARIO")

        self.assertEqual(linhas[2].tipo, "despesa")
        self.assertEqual(linhas[2].valor, Decimal("10.00"))
        self.assertIsNone(linhas[2].ofx_fitid)
        self.assertIn("SEM FITID", linhas[2].descricao)

    def test_arquivo_vazio_levanta(self):
        with self.assertRaisesMessage(ValueError, "Arquivo OFX vazio."):
            parse_ofx_bytes(b"   \n")

    def test_stmttrn_sem_fitid_levanta_ofxparse(self):
        """O ofxparse exige FITID; arquivos sem a tag falham (fail_fast padrão)."""
        raw = (
            b"OFXHEADER:100\nDATA:OFXSGML\nVERSION:102\nSECURITY:NONE\n"
            b"ENCODING:USASCII\nCHARSET:1252\nCOMPRESSION:NONE\n"
            b"OLDFILEUID:NONE\nNEWFILEUID:NONE\n\n"
            b"<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKTRANLIST>"
            b"<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20240101120000"
            b"<TRNAMT>-1.00<NAME>X</STMTTRN>"
            b"</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>"
        )
        with self.assertRaises(OfxParserException):
            parse_ofx_bytes(raw)
