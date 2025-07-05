# 🐍 Explicação Detalhada do Backend Django

## 1. Visão Geral
O backend deste sistema é feito em Django e serve como API para um frontend em React. Ele é responsável por autenticação, controle financeiro (transações, contas, categorias) e integrações com o frontend via endpoints REST.

---

## 2. Estrutura do Projeto
```
sistema_financeiro/
├── sistema_financeiro/   # Configurações globais do Django
│   ├── settings.py       # Configurações do projeto
│   ├── urls.py           # URLs principais
├── usuarios/             # App de autenticação
│   ├── models.py         # Usuário customizado
│   ├── views.py          # APIs de login/cadastro/logout
│   ├── backends.py       # Autenticação por email
│   ├── urls.py           # URLs de autenticação
├── dashboard/            # App financeiro
│   ├── models.py         # Categoria, Conta, Transacao
│   ├── views.py          # APIs do dashboard
│   ├── urls.py           # URLs do dashboard
└── db.sqlite3            # Banco de dados SQLite
```

---

## 3. Autenticação e Usuários
### 3.1 Usuário Customizado
- O modelo `Usuario` herda de `AbstractUser`, mas remove `username` e usa `email` como identificador.
- Campos: `email`, `nome`, `data_nascimento`, `criado_em`, `ativo`.
- Login é feito por email e senha.

### 3.2 Backend de Autenticação
- Arquivo: `usuarios/backends.py`
- Permite login usando email e senha.
- Exemplo de uso:
```python
usuario = authenticate(request, email=email, password=senha)
```

### 3.3 APIs de Autenticação
- **POST `/api/auth/login/`**: Login do usuário
- **POST `/api/auth/cadastro/`**: Cadastro de novo usuário
- **POST `/api/auth/logout/`**: Logout
- **GET `/api/auth/user/`**: Dados do usuário autenticado

---

## 4. Modelos Financeiros
### 4.1 Categoria
- Tipos: `receita` ou `despesa`
- Cada usuário pode ter suas próprias categorias

### 4.2 Conta
- Tipos: corrente, poupança, investimento, cartão, dinheiro
- Cada conta tem saldo inicial e saldo atual

### 4.3 Transação
- Tipos: receita, despesa, transferência
- Relaciona-se a uma conta, categoria e pode ter conta de destino (transferência)
- Campos: descrição, valor, tipo, data, observações

---

## 5. APIs do Dashboard
- **GET `/api/dashboard/data/`**: Dados resumidos do dashboard (totais, gráficos, transações recentes)
- **GET `/api/transacoes/`**: Lista todas as transações do usuário
- **POST `/api/transacoes/criar/`**: Cria uma nova transação
- **GET `/api/categorias/`**: Lista categorias do usuário
- **GET `/api/contas/`**: Lista contas ativas do usuário

---

## 6. Fluxo de Dados (Exemplo)
1. Usuário faz login pelo frontend → `/api/auth/login/`
2. Frontend armazena sessão/cookie
3. Frontend requisita `/api/dashboard/data/` para mostrar resumo financeiro
4. Usuário adiciona uma transação via `/api/transacoes/criar/`
5. Backend atualiza saldos e retorna confirmação

---

## 7. Segurança
- **@login_required**: Protege APIs para exigir autenticação
- **CORS**: Permite requisições do frontend (origens permitidas em `settings.py`)
- **Sessão**: Cookies de sessão são usados para manter o login
- **Validações**: Todas as entradas são validadas (ex: email único, senha mínima, campos obrigatórios)

---

## 8. Exemplos de Uso
### 8.1 Login
```bash
curl -X POST -d "email=teste@email.com&senha=123456" http://localhost:8000/api/auth/login/
```

### 8.2 Criar Transação
```bash
curl -X POST -H "Content-Type: application/json" \
     -d '{"descricao":"Salário","valor":1000,"tipo":"receita","conta_id":1,"data":"2024-06-01"}' \
     http://localhost:8000/api/transacoes/criar/
```

---

## 9. Dicas para Desenvolvedores
- Use o admin do Django para gerenciar dados rapidamente (`/admin/`)
- Consulte logs no terminal para debug de autenticação e erros
- Use o shell do Django para testar queries:
```bash
python manage.py shell
from usuarios.models import Usuario
from dashboard.models import Transacao
Transacao.objects.filter(usuario__email='seu@email.com')
```
- Para criar dados de exemplo: `python manage.py create_sample_data --username seu_usuario`

---

## 10. Personalização
- Para adicionar campos: edite o modelo, faça `makemigrations` e `migrate`
- Para novas APIs: crie uma view, adicione no `urls.py` e proteja com autenticação se necessário
- Para novos tipos de transação: edite `TIPO_CHOICES` em `Transacao`

---

## 11. Referências
- [Documentação Django](https://docs.djangoproject.com/pt-br/4.2/)
- [Django REST Framework](https://www.django-rest-framework.org/)

---

Este arquivo serve como referência rápida e detalhada para desenvolvedores que desejam entender, manter ou expandir o backend deste sistema financeiro. 