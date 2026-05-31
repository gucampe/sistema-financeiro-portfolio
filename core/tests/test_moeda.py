from decimal import Decimal

from django.test import SimpleTestCase

from core.moeda import parse_decimal_moeda_br


class ParseDecimalMoedaBrTests(SimpleTestCase):
    def test_vazio_retorna_zero(self):
        self.assertEqual(parse_decimal_moeda_br(""), Decimal("0"))

    def test_decimal_com_ponto(self):
        self.assertEqual(parse_decimal_moeda_br("1234.56"), Decimal("1234.56"))

    def test_formato_brasileiro(self):
        self.assertEqual(parse_decimal_moeda_br("1.234,56"), Decimal("1234.56"))

    def test_com_prefixo_moeda(self):
        self.assertEqual(parse_decimal_moeda_br("R$ 10,50"), Decimal("10.50"))
