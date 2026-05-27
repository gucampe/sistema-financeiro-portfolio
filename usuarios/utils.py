def primeiro_nome(nome: str) -> str:
    nome = (nome or "").strip()
    if not nome:
        return ""
    return nome.split()[0]


def iniciais_avatar(nome: str) -> str:
    nome = (nome or "").strip()
    if not nome:
        return "?"
    partes = nome.split()
    if len(partes) >= 2:
        return f"{partes[0][0]}{partes[-1][0]}".upper()
    p = partes[0]
    return (p[:2] if len(p) >= 2 else p[:1]).upper()
