from transacoes.views import modal_transacao_context


def modal_transacao_global(request):
    """Formulário e categorias do modal de transação em todas as páginas autenticadas."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    return modal_transacao_context(request)
