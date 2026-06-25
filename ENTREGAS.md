# Entregas — fluxo e contrato de API

Documento para prototipagem e implementação das telas no front.

**Público:** porteiro e admin. Morador **não** tem tela de entregas nesta versão.

---

## Conceito

1. Chega uma encomenda na portaria.
2. Porteiro/admin seleciona o **apartamento** (apto + bloco).
3. Backend resolve o **titular (holder)** daquele apartamento e envia **e-mail** só para ele.
4. O registro fica salvo no histórico de entregas.

A entrega é sempre por **unidade (household)**, não por morador individual.

---

## Fluxo (porteiro/admin)

```
[Home porteiro] ──► deliveries_today (opcional)
       │
       ▼
[Nova entrega] ──► GET /delivery_notification/apartments/
       │            (lista aptos ativos + nome do titular)
       ▼
[Formulário] ──► seleciona apto/bloco + preenche dados da encomenda
       │
       ▼
[Confirmar] ──► POST /delivery_notification/
       │
       ├── 200 → sucesso (e-mail disparado pro titular)
       └── 400/404 → erro (ver tabela abaixo)

[Histórico] ──► GET /delivery_notification/list/
       │
       ▼
[Detalhe] ──► GET /delivery_notification/{id}/
```

---

## Telas sugeridas

### 1. Nova entrega

- Carregar lista de apartamentos (`GET /delivery_notification/apartments/`).
- Exibir busca/filtro local por apto, bloco ou nome do titular.
- Campos do formulário:

| Campo | Obrigatório | Observação |
|-------|-------------|------------|
| Apartamento | sim | vem da seleção (`apartment`) |
| Bloco | não | string vazia se não houver bloco |
| Título | sim | ex.: "Pacote", "Comida" |
| Origem (`delivery_from`) | sim | ex.: "Amazon", "iFood" |
| Plataforma | não | select (ver opções abaixo) |
| Descrição | não | texto livre |
| Prioridade | não | `low` / `medium` / `high` |

- Botão enviar → `POST /delivery_notification/`.
- Feedback de sucesso ou mensagem de erro da API.

### 2. Histórico de entregas

- Lista todas as entregas (`GET /delivery_notification/list/`).
- Ordenação: mais recentes primeiro (já vem assim do backend).
- Exibir: apto/bloco, título, origem, plataforma, prioridade, data (`created_at`).
- Toque em item → detalhe (`GET /delivery_notification/{id}/`).

### 3. Home do porteiro (opcional, já existe)

- `GET /employee_dashboard/day_summary/` → campo `deliveries_today` (entregas registradas hoje).

---

## Autenticação e permissão

- Todas as rotas de entrega exigem **JWT** (`Authorization: Bearer …`).
- Apenas **admin** ou **porteiro** (`employee` com tipo `DOORMAN`).
- Morador recebe **403**.

---

## Endpoints

Base URL (local): `http://localhost:8000`

| Método | Rota | Uso |
|--------|------|-----|
| `GET` | `/delivery_notification/apartments/` | Lista aptos para o select |
| `POST` | `/delivery_notification/` | Registra entrega + envia e-mail |
| `GET` | `/delivery_notification/list/` | Histórico |
| `GET` | `/delivery_notification/{id}/` | Detalhe |
| `GET` | `/employee_dashboard/day_summary/` | Contador do dia |

Swagger: `/api/docs/` (tag `delivery_notification`).

---

## Contratos

### `GET /delivery_notification/apartments/`

**Response 200:**
```json
[
  {
    "id": 1,
    "apartment": "101",
    "block": "A",
    "holder_name": "João Silva",
    "status": "ACTIVE"
  }
]
```

- Inclui households **ACTIVE** e **PENDING_ADMIN** (exclui `ARCHIVED`).
- `status`: `ACTIVE` | `PENDING_ADMIN` — use para badge no select; só `ACTIVE` aceita cadastro de entrega.

---

### `POST /delivery_notification/`

**Request:**
```json
{
  "apartment": "101",
  "block": "A",
  "title": "Pacote",
  "delivery_from": "Amazon",
  "delivery_platform": "other",
  "description": "",
  "delivery_to": "",
  "priority_level": "low"
}
```

**Response 200:**
```json
{
  "id": 12,
  "household": 1,
  "apartment": "101",
  "block": "A",
  "notified_to": {
    "name": "João Silva",
    "email": "joao@example.com"
  },
  "title": "Pacote",
  "description": "",
  "delivery_platform": "other",
  "delivery_from": "Amazon",
  "delivery_to": "",
  "created_at": "2026-06-25T14:30:00Z",
  "priority_level": "low"
}
```

`notified_to` é snapshot do titular notificado no momento do cadastro.

**Opções de `delivery_platform`:** `ifood`, `rappi`, `amazon`, `mercado_livre`, `magalu`, `shopee`, `correios`, `other`

**Opções de `priority_level`:** `low`, `medium`, `high`

---

### `GET /delivery_notification/list/` e `GET /delivery_notification/{id}/`

Mesmo shape do response do `POST` (lista = array).

---

## E-mail

- **Destinatário:** titular (holder) ativo do apartamento.
- **Assunto:** `Delivery notification`
- Conteúdo inclui unidade (apto/bloco), origem, plataforma e horário de recebimento.
- O morador **não** precisa abrir o app — a notificação é por e-mail.

---

## Erros comuns (front deve tratar)

| HTTP | Quando |
|------|--------|
| `403` | Usuário sem permissão (morador, zelador, etc.) |
| `404` | Apartamento/bloco não encontrado; ou detalhe com id inexistente |
| `400` | Household não está ACTIVE; sem titular ativo; titular sem e-mail; payload inválido |

Mensagens vêm no body padrão do DRF (`detail` ou erros por campo).

---

## Fora do escopo (não implementado)

- Morador ver entregas no app
- Marcar como “retirado” / status da encomenda
- Notificar outros moradores do apartamento (só o titular)
- Push notification (só e-mail hoje)
