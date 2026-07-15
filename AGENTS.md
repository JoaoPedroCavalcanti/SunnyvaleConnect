# AGENTS.md — SunnyvaleConnect

Backend Django + DRF para gestão de condomínio. Este arquivo descreve **o padrão arquitetural obrigatório** do projeto. Toda criação ou edição de código deve seguir essas regras.

---

## Arquitetura: Service / Repository com DI manual

Fluxo de uma request:

```
HTTP request
   ↓
View (APIView)            ← roteamento + auth (IsAuthenticated/IsAdminUser/AllowAny)
   ↓
Serializer (Input)        ← valida APENAS forma/tipo. Nunca toca banco.
   ↓
container.<x>_service     ← injeção de dependência via shared/container.py
   ↓
Service                   ← TODA regra de negócio. Nunca toca ORM.
   ↓
Repository                ← dumb. SÓ ORM (Model.objects.*).
   ↓
Database
```

A View retorna `Response(<Output>Serializer(result).data)`. Acabou.

---

## Regras por camada (obrigatórias)

### View (`<app>/views.py`)

- Sempre `APIView` plain. **Nunca** `ModelViewSet`, `GenericAPIView`, `@api_view`.
- Responsabilidades: roteamento HTTP, autenticação (permission_classes), validar input com serializer, chamar service, devolver Response.
- **NÃO PODE**:
  - Importar `<app>.models`
  - Usar `Model.objects.*`, `get_object_or_404`
  - Conter regras de negócio (`if user.is_staff`, validações, transformações)
  - Chamar repository diretamente
- Decorar para o Swagger:
  - `@extend_schema(tags=["<app>"])` na classe
  - `@extend_schema(request=..., responses={200: ...})` em cada método HTTP

### Serializer (`<app>/serializers.py`)

- Padrão **plural** (`serializers.py`), nunca `serializer.py`.
- Existem 3 papéis. Use os necessários:
  - `<Name>InputSerializer` — POST (campos required)
  - `<Name>PatchSerializer` — PATCH (campos opcionais)
  - `<Name>OutputSerializer` — response (pode ser `ModelSerializer`)
- **Só valida forma/tipo**: `CharField`, `IntegerField`, `EmailField`, `max_length`, `required`, `allow_null`, `ChoiceField`.
- **NÃO PODE**:
  - Importar de `<app>.models` para fazer queries
  - Definir `validate_*` que faça queries (`Model.objects.filter(...)`)
  - Implementar `create()` / `update()` (isso é do service)
  - Salvar nada

### Service (`<app>/services/<name>_service.py`)

- Estrutura: `I<Name>Service(ABC)` + `<Name>Service(I<Name>Service)`.
- **Toda** regra de negócio vive aqui: unicidade, datas, permissões, transformações, side-effects (email, etc).
- Recebe `user` como primeiro parâmetro quando a operação depende de quem está executando.
- **NÃO PODE**:
  - Importar `Model.objects.*`
  - Chamar `instance.save()`, `instance.delete()`
  - Importar `rest_framework.exceptions`
  - Importar `django.shortcuts`
- Levanta apenas **domain exceptions** (ver abaixo) para sinalizar erro.
- Dependências (repository, email_sender, etc) são injetadas no `__init__`.

### Repository (`<app>/repositories/<name>_repository.py`)

- Estrutura: `I<Name>Repository(ABC)` + `Django<Name>Repository(I<Name>Repository)`.
- **Dumb**: cada método é 1-3 linhas de ORM puro.
- **NÃO PODE**:
  - Ter `if` de regra de negócio
  - Levantar exceções
  - Conhecer "user logado" (recebe ids primitivos)
  - Importar de `<app>.services`
- Padrão de métodos: `list_all`, `list_for_user(user_id)`, `get_by_id(pk)`, `exists_with_<field>(value)`, `create(data)`, `update(instance, data)`, `delete(instance)`.

---

## Domain Exceptions (`shared/exceptions.py`)

Services levantam **apenas** estas:

| Exception | HTTP | Quando |
|---|---|---|
| `BusinessRuleError(message, field=None)` | 400 | regra violada (data inválida, conflito, etc) |
| `NotFoundError(message)` | 404 | recurso não encontrado OU fora do escopo do user |
| `PermissionDeniedError(message)` | 403 | user não pode executar a operação |

O `custom_exception_handler` (em `shared/exception_handler.py`) converte tudo para a `ValidationError`/`NotFound`/`PermissionDenied` do DRF.

`message` pode ser `str` ou `list[str]` (ex: múltiplos erros de senha).

---

## Container de DI (`shared/container.py`)

Lazy singleton. Use **sempre** assim:

```python
from shared.container import container

instance = container.bbq_service.create(request.user, payload)
```

**Nunca** instancie `BBQReservationService()` direto na view.

Ao adicionar um service/repository novo, registre no `Container`:

```python
@property
def my_new_repository(self):
    from my_app.repositories.my_new_repository import DjangoMyNewRepository
    return self._resolve("my_new_repository", DjangoMyNewRepository)

@property
def my_new_service(self):
    from my_app.services.my_new_service import MyNewService
    return self._resolve(
        "my_new_service",
        lambda: MyNewService(repository=self.my_new_repository),
    )
```

**Imports dentro da property** (evita import circular).

Para testes: `container.override("key", fake_instance)`. O `conftest.py` tem fixture `autouse` que dá `container.reset()` entre testes.

---

## Testes

Estrutura **obrigatória** em cada app:

```
<app>/tests/
├── unit/               # service + fakes (sem DB)
│   ├── __init__.py
│   └── test_<name>_service.py
└── smoke/              # API end-to-end (com DB)
    ├── __init__.py
    └── test_<name>_api.py
```

### Unit tests
- Marker: `pytestmark = pytest.mark.unit`
- Cria um `FakeXRepository(IXRepository)` in-memory inline no arquivo de teste
- Testa o service isoladamente (sem subir Django ORM nem HTTP)
- Cobre regras de negócio + permissões + erros

### Smoke tests
- Marker: `pytestmark = pytest.mark.api`
- Herda `BaseTestsUsers` (em `tests_base/`)
- 1-3 testes por endpoint: happy path + sad path principal
- Não duplica testes de regra (isso é unit). Foca em "está plugado".

### Fakes de infraestrutura
Já existem em `shared/test_doubles/fakes.py`:
- `FakeEmailSender`
- `FakeCodeGenerator`
- `FakeStringMixer`

---

## Workflow: criar feature/CRUD novo

Para uma nova entidade `Foo`:

1. **Model**: `<app>/models.py` (Django padrão)
2. **Migration**: `python manage.py makemigrations`
3. **Repository**: `<app>/repositories/foo_repository.py` com `IFooRepository` + `DjangoFooRepository`
4. **Service**: `<app>/services/foo_service.py` com `IFooService` + `FooService`
5. **Serializers**: `<app>/serializers.py` com `FooInputSerializer`, `FooPatchSerializer` (se houver PATCH), `FooOutputSerializer`
6. **View**: `<app>/views.py` com `FooListCreateView`, `FooDetailView`, anotadas com `@extend_schema`
7. **URL**: `<app>/urls.py` com `path("", ...)` e `path("<int:pk>/", ...)`
8. **Container**: registrar `foo_repository` + `foo_service` em `shared/container.py`
9. **App em `settings.py`**: se for app novo, adicionar em `INSTALLED_APPS` e em `[tool.coverage.run].source` no `pyproject.toml`
10. **URL root**: incluir em `sunnyValeConnect/urls.py`
11. **Testes**:
    - `<app>/tests/unit/test_foo_service.py` (com FakeFooRepository)
    - `<app>/tests/smoke/test_foo_api.py`
12. **Rodar**: `make test` (ou `cd myapp && TESTING=1 .venv/bin/pytest`)

---

## Workflow: editar feature existente

| Tipo de mudança | Onde mexer |
|---|---|
| Adicionar campo no model | model + migration + serializers + (talvez) service |
| Nova validação de forma/tipo | apenas serializer |
| Nova regra de negócio | apenas service + teste unit |
| Nova query ao banco | repository (método novo) + service que usa |
| Nova permissão por user | service usando `PermissionDeniedError` |
| Novo side-effect (email, etc) | service injetando interface do `shared/infrastructure/` |
| Novo endpoint | view + url + service (se tiver lógica nova) |

**Antes de mexer em qualquer lugar, pergunte: "isso é forma, regra, banco ou roteamento?"** Cada resposta cai em uma camada distinta.

---

## Naming conventions

| Coisa | Padrão | Exemplo |
|---|---|---|
| App | snake_case | `bbq_reservations` |
| Interface | `I<Name><Tipo>` | `IBBQRepository`, `IBBQReservationService` |
| Impl Django repo | `Django<Name>Repository` | `DjangoBBQRepository` |
| Service | `<Name>Service` | `BBQReservationService` |
| Serializer input | `<Name>InputSerializer` | `BBQReservationInputSerializer` |
| Serializer patch | `<Name>PatchSerializer` | `BBQReservationPatchSerializer` |
| Serializer output | `<Name>OutputSerializer` | `BBQReservationOutputSerializer` |
| View list/create | `<Name>ListCreateView` | `BBQReservationListCreateView` |
| View detail | `<Name>DetailView` | `BBQReservationDetailView` |
| View ação custom | `<Name><Acao>View` | `SetPaidStatusView` |
| URL name | kebab-case | `list-create`, `set-paid-status` |

---

## Don'ts (red flags em PR)

- ❌ `Model.objects.<algo>` em view, serializer ou service
- ❌ `get_object_or_404` em view ou service
- ❌ `if user.is_staff` em view (vai pro service via `PermissionDeniedError`)
- ❌ `validate_<x>` em serializer fazendo query
- ❌ `instance.save()` em view ou service (só repository)
- ❌ `ModelViewSet`, `ModelSerializer.create()`, `perform_create`
- ❌ Importar serviço com `MyService()` direto (use sempre `container.my_service`)
- ❌ View retornando dados que não passaram por um `<X>OutputSerializer` (exceto endpoints muito simples como checkin/checkout)
- ❌ Adicionar lib externa de DI (`dependency-injector`, `injector`, etc) — o container manual é proposital

---

## Exemplos canônicos

Olhe estes arquivos como referência ao criar coisa nova:

- **App simples (sem regra)**: `myapp/sunny_vale_news/`
- **App com regras + permissões**: `myapp/condo_payments/`
- **App com regra de data + ownership**: `myapp/reservations/`
- **App com side-effect (email)**: `myapp/delivery_notification/`
- **App complexa (links, codes, multi-action)**: `myapp/visitor_access/`

---

## Comandos úteis

```bash
make test              # roda toda a suite (SQLite in-memory, ~0.4s)
make test-cov          # com coverage report
make test-fast         # para no primeiro erro
make test-docker       # roda na imagem 'test'

# gerar schema OpenAPI pra mandar pro front
cd myapp && TESTING=1 .venv/bin/python manage.py spectacular --file ../schema.yml
```

URLs locais:
- Swagger UI: `http://localhost:8000/api/docs/`
- ReDoc: `http://localhost:8000/api/redoc/`
- Schema YAML: `http://localhost:8000/api/schema/`
