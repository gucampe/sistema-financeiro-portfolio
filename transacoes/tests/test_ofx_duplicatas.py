from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from categorias.models import Categoria
from contas.models import Conta

from transacoes.models import Transacao
from transacoes.ofx_duplicatas import (
    ResultadoDuplicata,
    avaliar_duplicatas_importacao,
    normalizar_descricao,
)
from transacoes.ofx_parse import LinhaOfx

User = get_user_model()


class NormalizarDescricaoTests(SimpleTestCase):
    def test_colapsa_espacos_e_casefold(self):
        self.assertEqual(normalizar_descricao("  PADARIA   Central  "), "padaria central")

    def test_vazio(self):
        self.assertEqual(normalizar_descricao(""), "")
        self.assertEqual(normalizar_descricao("   \n\t  "), "")


class AvaliarDuplicatasImportacaoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="dup_user@test.local",
            password="secret",
            nome="Usuário Dup",
        )
        self.outro = User.objects.create_user(
            email="outro@test.local",
            password="secret",
            nome="Outro",
        )
        self.conta = Conta.objects.create(
            usuario=self.user, nome="Conta principal", tipo="corrente"
        )
        self.cat_d = Categoria.objects.create(
            usuario=self.user,
            nome="Despesa teste",
            tipo="despesa",
            cor="#EF4444",
            padrao=False,
        )

    def _criar_transacao(
        self,
        *,
        data,
        valor,
        descricao,
        tipo="despesa",
        ofx_fitid=None,
        conta=None,
        usuario=None,
    ):
        return Transacao.objects.create(
            usuario=usuario or self.user,
            conta=conta or self.conta,
            categoria=self.cat_d,
            tipo=tipo,
            valor=valor,
            descricao=descricao,
            data=data,
            ofx_fitid=ofx_fitid,
        )

    def test_sem_linhas_retorna_vazio(self):
        self.assertEqual(avaliar_duplicatas_importacao(self.user, self.conta, []), [])

    def test_conta_de_outro_usuario_levanta(self):
        conta_outro = Conta.objects.create(
            usuario=self.outro, nome="Conta X", tipo="corrente"
        )
        linha = LinhaOfx(
            data=date(2024, 1, 1),
            valor=Decimal("1.00"),
            tipo="despesa",
            descricao="X",
            ofx_fitid=None,
        )
        with self.assertRaisesMessage(ValueError, "A conta não pertence ao usuário."):
            avaliar_duplicatas_importacao(self.user, conta_outro, [linha])

    def test_fitid_ja_no_banco(self):
        self._criar_transacao(
            data=date(2024, 2, 1),
            valor=Decimal("10.00"),
            descricao="Pix",
            ofx_fitid="fit-001",
        )
        linhas = [
            LinhaOfx(
                data=date(2024, 2, 1),
                valor=Decimal("10.00"),
                tipo="despesa",
                descricao="Pix",
                ofx_fitid="fit-001",
            )
        ]
        res = avaliar_duplicatas_importacao(self.user, self.conta, linhas)
        self.assertEqual(
            res,
            [ResultadoDuplicata(0, True, False)],
        )

    def test_fitid_novo_nao_duplica(self):
        linhas = [
            LinhaOfx(
                data=date(2024, 3, 1),
                valor=Decimal("5.00"),
                tipo="despesa",
                descricao="Lanche",
                ofx_fitid="novo-1",
            )
        ]
        res = avaliar_duplicatas_importacao(self.user, self.conta, linhas)
        self.assertEqual(res, [ResultadoDuplicata(0, False, False)])

    def test_heuristica_sem_fitid_igual_manual_no_banco(self):
        self._criar_transacao(
            data=date(2024, 4, 1),
            valor=Decimal("20.00"),
            descricao="  MERCADO  SAO   JOSE ",
            ofx_fitid=None,
        )
        linhas = [
            LinhaOfx(
                data=date(2024, 4, 1),
                valor=Decimal("20.00"),
                tipo="despesa",
                descricao="mercado sao jose",
                ofx_fitid=None,
            )
        ]
        res = avaliar_duplicatas_importacao(self.user, self.conta, linhas)
        self.assertEqual(res, [ResultadoDuplicata(0, False, True)])

    def test_com_fitid_nao_usa_heuristica_mesmo_igual_manual(self):
        self._criar_transacao(
            data=date(2024, 5, 1),
            valor=Decimal("15.00"),
            descricao="Padaria",
            ofx_fitid=None,
        )
        linhas = [
            LinhaOfx(
                data=date(2024, 5, 1),
                valor=Decimal("15.00"),
                tipo="despesa",
                descricao="Padaria",
                ofx_fitid="only-in-file",
            )
        ]
        res = avaliar_duplicatas_importacao(self.user, self.conta, linhas)
        self.assertEqual(res, [ResultadoDuplicata(0, False, False)])

    def test_duplicata_no_lote_mesmo_fitid(self):
        linhas = [
            LinhaOfx(
                data=date(2024, 6, 1),
                valor=Decimal("1.00"),
                tipo="despesa",
                descricao="A",
                ofx_fitid="dup-batch",
            ),
            LinhaOfx(
                data=date(2024, 6, 2),
                valor=Decimal("2.00"),
                tipo="despesa",
                descricao="B",
                ofx_fitid="dup-batch",
            ),
        ]
        res = avaliar_duplicatas_importacao(self.user, self.conta, linhas)
        self.assertEqual(
            res,
            [
                ResultadoDuplicata(0, False, False),
                ResultadoDuplicata(1, True, False),
            ],
        )

    def test_duplicata_no_lote_heuristica_sem_fitid(self):
        linhas = [
            LinhaOfx(
                data=date(2024, 7, 1),
                valor=Decimal("3.00"),
                tipo="despesa",
                descricao="Gasolina",
                ofx_fitid=None,
            ),
            LinhaOfx(
                data=date(2024, 7, 1),
                valor=Decimal("3.00"),
                tipo="despesa",
                descricao="GASOLINA",
                ofx_fitid=None,
            ),
        ]
        res = avaliar_duplicatas_importacao(self.user, self.conta, linhas)
        self.assertEqual(
            res,
            [
                ResultadoDuplicata(0, False, False),
                ResultadoDuplicata(1, False, True),
            ],
        )

    def test_outra_conta_nao_conta_para_duplicata(self):
        outra = Conta.objects.create(usuario=self.user, nome="Outra", tipo="poupanca")
        self._criar_transacao(
            conta=outra,
            data=date(2024, 8, 1),
            valor=Decimal("7.00"),
            descricao="Unico",
            ofx_fitid="fit-outra",
        )
        linhas = [
            LinhaOfx(
                data=date(2024, 8, 1),
                valor=Decimal("7.00"),
                tipo="despesa",
                descricao="Unico",
                ofx_fitid="fit-outra",
            )
        ]
        res = avaliar_duplicatas_importacao(self.user, self.conta, linhas)
        self.assertEqual(res, [ResultadoDuplicata(0, False, False)])
