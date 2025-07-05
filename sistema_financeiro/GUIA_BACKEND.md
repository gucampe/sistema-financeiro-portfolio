# 🐍 Guia Completo do Backend Django

## 📋 Visão Geral

O backend deste sistema financeiro é construído com **Django 4.2.20** e fornece uma API REST para o frontend React. O sistema é dividido em dois apps principais: `usuarios` (autenticação) e `dashboard` (funcionalidades financeiras).

## 🏗️ Arquitetura do Projeto

```
sistema_financeiro/
├── sistema_financeiro/          # Configurações principais do Django
│   ├── settings.py              # Configurações do projeto
│   ├── urls.py                  # URLs principais
│   └── wsgi.py                  # Configuração WSGI
├── usuarios/                    # App de autenticação
│   ├── models.py               # Modelo de usuário customizado
│   ├── views.py                # Views de login/cadastro
│   ├── urls.py                 # URLs de autenticação
│   ├── backends.py             # Backend de autenticação por email
│   └── managers.py             # Manager customizado
├── dashboard/                   # App principal do sistema
│   ├── models.py               # Modelos: Categoria, Conta, Transacao
│   ├── views.py                # Views e APIs do dashboard
│   ├── urls.py                 # URLs do dashboard
│   └── admin.py                # Configuração do admin
└── db.sqlite3                  # Banco de dados SQLite
```

## 🔧 Configurações Principais

### Dependências (`requirements.txt`)
- **Django 4.2.20**: Framework web principal
- **django-cors-headers**: Para permitir requisições do frontend React
- **django-tailwind**: Para estilização (usado no admin)

### Configurações (`settings.py`)

#### Apps Instalados
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',        # Para CORS
    'dashboard',          # App principal
    'usuarios',           # App de autenticação
]
```

#### Configuração CORS
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # Alternative dev server
]

CORS_ALLOW_CREDENTIALS = True
```

#### Autenticação Customizada
```python
AUTH_USER_MODEL = 'usuarios.Usuario'
AUTHENTICATION_BACKENDS = [
    'usuarios.backends.EmailBackend',  # Login por email
    'django.contrib.auth.backends.ModelBackend',
]
```

## 👤 Sistema de Usuários (`usuarios/`)

### Modelo de Usuário (`models.py`)
```python
class Usuario(AbstractUser):
    username = None  # Remove campo username padrão
    email = models.EmailField(unique=True)  # Email como identificador
    nome = models.CharField(max_length=100)
    data_nascimento = models.DateField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)

    USERNAME_FIELD = 'email'  # Email como campo de login
    REQUIRED_FIELDS = ['nome']
```

### Backend de Autenticação (`backends.py`)
```python
class EmailBackend(ModelBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        # Autentica usuário por email em vez de username
        Usuario = get_user_model()
        try:
            user = Usuario.objects.get(email=email)
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except Usuario.DoesNotExist:
            return None
        return None
```

### APIs de Autenticação

#### Login (`/api/auth/login/`)
- **Método**: POST
- **Dados**: `email`, `senha`
- **Retorna**: Dados do usuário logado

#### Cadastro (`/api/auth/cadastro/`)
- **Método**: POST
- **Dados**: `nome`, `email`, `senha`, `confirmar_senha`
- **Validações**: Email único, senha mínima 6 caracteres

#### Logout (`/api/auth/logout/`)
- **Método**: POST
- **Requer**: Usuário autenticado

#### Informações do Usuário (`/api/auth/user/`)
- **Método**: GET
- **Requer**: Usuário autenticado
- **Retorna**: Dados do usuário atual

## 💰 Sistema Financeiro (`dashboard/`)

### Modelos de Dados

#### Categoria (`models.py`)
```python
class Categoria(models.Model):
    TIPO_CHOICES = [
        ('receita', 'Receita'),
        ('despesa', 'Despesa'),
    ]
    
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    cor = models.CharField(max_length=7, default='#3B82F6')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['nome', 'usuario']  # Nome único por usuário
```

#### Conta (`models.py`)
```python
class Conta(models.Model):
    TIPO_CHOICES = [
        ('corrente', 'Conta Corrente'),
        ('poupanca', 'Conta Poupança'),
        ('investimento', 'Conta Investimento'),
        ('cartao', 'Cartão de Crédito'),
        ('dinheiro', 'Dinheiro'),
    ]
    
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES)
    saldo_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo_atual = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ativa = models.BooleanField(default=True)
```

#### Transação (`models.py`)
```python
class Transacao(models.Model):
    TIPO_CHOICES = [
        ('receita', 'Receita'),
        ('despesa', 'Despesa'),
        ('transferencia', 'Transferência'),
    ]
    
    descricao = models.CharField(max_length=200)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    conta = models.ForeignKey(Conta, on_delete=models.CASCADE, related_name='transacoes')
    conta_destino = models.ForeignKey(Conta, on_delete=models.SET_NULL, null=True, blank=True, related_name='transacoes_destino')
    data = models.DateField(default=timezone.now)
    observacoes = models.TextField(blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
```

### APIs do Dashboard

#### Dados do Dashboard (`/api/dashboard/data/`)
- **Método**: GET
- **Requer**: Usuário autenticado
- **Retorna**: 
  - Resumo financeiro do mês
  - Transações recentes
  - Categorias com totais
  - Saldo total das contas

#### Listar Transações (`/api/transacoes/`)
- **Método**: GET
- **Requer**: Usuário autenticado
- **Retorna**: Lista de todas as transações do usuário

#### Criar Transação (`/api/transacoes/criar/`)
- **Método**: POST
- **Requer**: Usuário autenticado
- **Dados**: `descricao`, `valor`, `tipo`, `conta_id`, `data`, `categoria_id` (opcional)

#### Listar Categorias (`/api/categorias/`)
- **Método**: GET
- **Requer**: Usuário autenticado
- **Retorna**: Categorias do usuário

#### Listar Contas (`/api/contas/`)
- **Método**: GET
- **Requer**: Usuário autenticado
- **Retorna**: Contas ativas do usuário

## 🔐 Segurança e Autenticação

### Middleware de Segurança
```python
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]
```

### Proteção de Views
- **`@login_required`**: Decorator para views que requerem autenticação
- **`@csrf_exempt`**: Para APIs que não precisam de CSRF token
- **`@require_http_methods`**: Para restringir métodos HTTP

### Sessões
```python
SESSION_COOKIE_AGE = 60 * 60 * 24  # 1 dia
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
```

## 🚀 Como Executar

### 1. Instalar Dependências
```bash
cd sistema_financeiro
pip install -r requirements.txt
```

### 2. Configurar Banco de Dados
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Criar Superusuário (Opcional)
```bash
python manage.py createsuperuser
```

### 4. Executar Servidor
```bash
python manage.py runserver
```

### 5. Acessar Admin (Opcional)
- URL: `http://localhost:8000/admin/`
- Use o superusuário criado

## 📊 Fluxo de Dados

### 1. Autenticação
1. Frontend envia `email` e `senha` para `/api/auth/login/`
2. Backend valida credenciais usando `EmailBackend`
3. Se válido, cria sessão e retorna dados do usuário
4. Frontend armazena dados do usuário no contexto

### 2. Dashboard
1. Frontend faz requisição para `/api/dashboard/data/`
2. Backend calcula resumos financeiros do mês atual
3. Retorna dados formatados para o frontend
4. Frontend renderiza dashboard com os dados

### 3. Transações
1. Frontend envia dados da transação para `/api/transacoes/criar/`
2. Backend valida dados e cria transação no banco
3. Retorna confirmação com dados da transação criada
4. Frontend atualiza lista de transações

## 🔧 Comandos Úteis

### Gerenciamento de Dados
```bash
# Criar dados de exemplo
python manage.py create_sample_data --username seu_usuario

# Backup do banco
python manage.py dumpdata > backup.json

# Restaurar backup
python manage.py loaddata backup.json
```

### Desenvolvimento
```bash
# Verificar erros
python manage.py check

# Shell interativo
python manage.py shell

# Criar migrações
python manage.py makemigrations dashboard usuarios

# Aplicar migrações
python manage.py migrate
```

## 🐛 Debug e Logs

### Logs de Autenticação
O sistema imprime logs no console para debug:
```python
print(f"Tentativa de login - Email: {email}")
print(f"Login bem-sucedido para: {usuario.email}")
```

### Verificar Banco de Dados
```bash
# Acessar shell do Django
python manage.py shell

# Exemplos de consultas
from usuarios.models import Usuario
from dashboard.models import Transacao, Categoria, Conta

# Listar usuários
Usuario.objects.all()

# Listar transações de um usuário
Transacao.objects.filter(usuario__email='exemplo@email.com')
```

## 🔄 Integração com Frontend

### URLs de Redirecionamento
```python
LOGIN_URL = 'http://localhost:5173'
LOGIN_REDIRECT_URL = 'http://localhost:5173'
LOGOUT_REDIRECT_URL = 'http://localhost:5173'
```

### CORS Configurado
- Permite requisições do frontend React
- Suporta credenciais (cookies/sessões)
- Headers necessários configurados

## 📈 Funcionalidades Futuras

- [ ] Relatórios avançados
- [ ] Metas financeiras
- [ ] Orçamentos por categoria
- [ ] Exportação de dados (CSV/PDF)
- [ ] Notificações de vencimentos
- [ ] Integração com APIs bancárias
- [ ] Backup automático
- [ ] Cache para performance

## 🛠️ Personalização

### Adicionar Novos Campos
1. Modifique o modelo em `models.py`
2. Execute `python manage.py makemigrations`
3. Execute `python manage.py migrate`

### Novas APIs
1. Crie a view em `views.py`
2. Adicione a URL em `urls.py`
3. Teste a API

### Novos Tipos de Transação
1. Modifique `TIPO_CHOICES` no modelo `Transacao`
2. Atualize as views que processam transações
3. Execute migrações se necessário

Este backend fornece uma base sólida e escalável para o sistema financeiro, com autenticação segura, APIs bem estruturadas e um modelo de dados flexível. 