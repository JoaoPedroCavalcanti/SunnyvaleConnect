# API Documentation
This documentation describes the API of a condominium system. The API is organized into 8 apps that control different functionalities, such as service management, reservations, notifications and News. Each app has endpoints for creating, viewing, updating, and deleting data.

## Apps
- Users
- Units
- Reservations
- Visitor Management
- Services Request
- Payment of the Condominium
- Delivery Notifications
- Condominium News
------------------------------------------------------------------------------------------

# Authentication
The API uses token authentication to secure some endpoints. To access protected endpoints, the authentication token must be included in the request header.

**Header Example:**
 `Authorization: Bearer {your_access_token}`

- The API uses **Simple JWT** to generate and manage tokens. There are three endpoints related to token authentication:

### Obtain Token
To generate a token
<details>
 <summary><code>POST</code> <code><b>/</b></code> <code>api/token/</code></summary>

##### Parameters

> | name      |  type     | data type               | description                                                           |
> |-----------|-----------|-------------------------|-----------------------------------------------------------------------|
> | username      |  required | object (JSON)   | user's username  |
> | password      |  required | object (JSON)   | user's password  |

##### Responses
Obtain an access token and a Refresh Token

> | http code     | content-type                      | response                                                            |
> |---------------|-----------------------------------|---------------------------------------------------------------------|
> | `200`         | `JSON`        | refresh: "refresh_token" / access: "access_token"|


</details>

### Refresh Token
To refresh a token
<details>
 <summary><code>POST</code> <code><b>/</b></code> <code>api/token/refresh/</code></summary>

##### Parameters

> | name      |  type     | data type               | description                                                           |
> |-----------|-----------|-------------------------|-----------------------------------------------------------------------|
> | refresh      |  required | object (JSON)   | refresh_token  |


##### Responses
A new access Token

> | http code     | content-type                      | response                                                            |
> |---------------|-----------------------------------|---------------------------------------------------------------------|
> | `200`         | `JSON`        | access: "access_token"|


</details>

### Verify Token
To verify an access token
<details>
 <summary><code>POST</code> <code><b>/</b></code> <code>api/token/verify/</code></summary>

##### Parameters

> | name      |  type     | data type               | description                                                           |
> |-----------|-----------|-------------------------|-----------------------------------------------------------------------|
> | acess      |  required | object (JSON)   | access_token  |


##### Responses

> | http code     | content-type                      | response                                                            |
> |---------------|-----------------------------------|---------------------------------------------------------------------|
> | `200`         | `None`        | `None`|
> | `401`         | `JSON`        | detail: "Token is invalid or expired"/ code: "token_not_valid"



</details>

------------------------------------------------------------------------------------------
# Apps and endpoints
## Users
For all endpoints of this app, you need to be ***Authenticated***. 
There are two diferent responses, if you are **staff user or not**.

Condominium admins can manage users through `PATCH /user/{id}/` and
`DELETE /user/{id}/`. PATCH supports every exposed account field except
password, including username, CPF, email, role, employee types and active
status. DELETE is a soft deletion (`is_active=false`), so the account and
its history remain stored. An admin cannot deactivate or demote itself.
When an owner is deactivated, ownership is transferred to the oldest active
member of each unit; if there is no other active member, the unit remains
without an owner.

- #### List Users

<details>
 <summary><code>GET</code> <code><b>/</b></code> <code>user/</code></summary>

##### Parameters

> None

##### Responses

> | staff user    | http code     | content-type                      | response                                                            |
> |---------------|---------------|-----------------------------------|---------------------------------------------------------------------|
> | `True`         | `200`         | `JSON`        | List of Users                                                         |
> | `False`         | `200`         | `JSON`        | **Your** Users                                                         |

##### JSON Response example:
```json
[
	{
		"id": 25,
		"username": "caca",
		"first_name": "caca1",
		"last_name": "Caca",
		"email": "carol@email.com"
	}
]
```
</details>

- #### Detail User
If not a staff, you can access **just itself**.

<details>
 <summary><code>GET</code> <code><b>/</b></code> <code>user/{id}</code></summary>

##### Parameters

> None

##### Responses

> | staff user    | http code     | content-type                      | response                                                            |
> |---------------|---------------|-----------------------------------|---------------------------------------------------------------------|
> | `True`         | `200`         | `JSON`        | Detail of any User                                                        |
> | `False`         | `200`         | `JSON`        | Detail of itself                                                        |

##### JSON Response example:
```json
[
	{
		"id": 25,pos
		"username": "caca",
		"first_name": "caca1",
		"last_name": "Caca",
		"email": "carol@email.com"
	}
]
```
</details>

</details>

- #### Create User
- Just **Staff and not authenticated** users can create an account.
- You can not create two users with the same username or email
- The password need to have at least one uppercase letter, must be at least 8 characters long and must have at least 1 special character(ex: !$%*<)

<details>
 <summary><code>POST</code> <code><b>/</b></code> <code>user/</code></summary>

##### Parameters

> | name      |  type     | data type               | description                                                           |
> |-----------|-----------|-------------------------|-----------------------------------------------------------------------|
> | username      |  required | object (JSON)   | username  |
> | password      |  required | object (JSON)   | password  |
> | first_name      |  required | object (JSON)   | first_name  |
> | last_name      |  required | object (JSON)   | last_name  |
> | email      |  required | object (JSON)   | email  |


##### Responses

> | staff user    | http code     | content-type                      | response                                                            |
> |---------------|---------------|-----------------------------------|---------------------------------------------------------------------|
> | `True`         | `200`         | `JSON`        | User you created                                                       |
> | `False`         | `200`         | `JSON`        | User you created                                                       |

##### JSON Response example:
```json
[
	{
		"id": 25,pos
		"username": "caca",
		"first_name": "caca1",
		"last_name": "Caca",
		"email": "carol@email.com"
	}
]
```
</details>



- #### Update User
If you are not staff you can update **just yours** informations.

<details>
 <summary><code>POST</code> <code><b>/</b></code> <code>user/{id}</code></summary>

##### Parameters

> | name      |  type     | data type               | description                                                           |
> |-----------|-----------|-------------------------|-----------------------------------------------------------------------|
> | username      |  optional | object (JSON)   | username  |
> | password      |  optional | object (JSON)   | password  |
> | first_name      |  optional | object (JSON)   | first_name  |
> | last_name      |  optional | object (JSON)   | last_name  |
> | email      |  optional | object (JSON)   | email  |


##### Responses

> | staff user    | http code     | content-type                      | response                                                            |
> |---------------|---------------|-----------------------------------|---------------------------------------------------------------------|
> | `True`         | `200`         | `JSON`        | `User updated `                                                     |
> | `False`         | `200`         | `JSON`        | `User updated`                                                      |

##### JSON Response example:
```json
[
	{
		"id": 25,pos
		"username": "caca",
		"first_name": "caca1",
		"last_name": "Caca",
		"email": "carol@email.com"
	}
]
```
</details>



- #### Delete User
If you are not staff you can delete **just your** user.

<details>
 <summary><code>POST</code> <code><b>/</b></code> <code>user/{id}</code></summary>

##### Parameters

`None`


##### Responses

> | staff user    | http code     | content-type                      | response                                                            |
> |---------------|---------------|-----------------------------------|---------------------------------------------------------------------|
> | `True`         | `200`         | `None`        | `None`                                                      |
> | `False`         | `200`         | `None`        | `None`                                                     |
> | `True` / `False`         | `404`         | `JSON`        | `Detail of not found `                                                     |

##### JSON Response example:
```json
[
	{
		"id": 25,pos
		"username": "caca",
		"first_name": "caca1",
		"last_name": "Caca",
		"email": "carol@email.com"
	}
]
```
</details>





------------------------------------------------------------------------------------------

## Reservations
All endpoints require authentication.

### Reservable locations
- `GET /reservation-locations/` lists the catalog; `POST /reservation-locations/` creates a location.
- `PATCH /reservation-locations/{pk}/` updates a location; `DELETE` archives it instead of removing it permanently.
- `GET /reservation-locations/{pk}/availability/` returns that location's available slots, up to 93 days ahead.
- Only a platform superuser may create, update, or archive locations. Creation must identify the condominium with exactly one of `condominium_id` or `condominium_code`.
- `icon` is optional and accepts only: `outdoor_grill`, `celebration`, `sports_court`, `sports_field`, `meeting_room`, or `fitness_center`. The frontend uses a calendar fallback when it is empty.

### Reservations
- `GET/POST /reservations/` lists and creates reservations; `GET/PATCH/DELETE /reservations/{pk}/` handles one reservation.
- `GET /reservations/?period=future` returns reservations whose end is still ahead; `period=past` returns reservations whose end has elapsed; omitting `period` returns the full history.
- Condominium admins can approve or reject pending reservations through `POST /reservations/{pk}/approve/` and `POST /reservations/{pk}/reject/`.
- Residents create reservations with `PENDING` status; condominium admins create them with `APPROVED` status and can approve or reject pending requests.
- Residents may edit only their own `PENDING` reservations. Condominium admins may edit `PENDING` and `APPROVED` reservations; `REJECTED` reservations are immutable.
- A reservation's location is immutable; cancel/delete and create a new reservation to use another location.
- Conflicts and the 30-minute gap apply only to the same location and date. Different locations may be booked at the same time.
- `null` `start_time` and `end_time` represent an all-day reservation. Approved reservations block availability slots.
- Reservations for today must start after the current local time.

Create payload:
```json
{
  "location_id": 1,
  "reservation_date": "2026-07-20",
  "start_time": "14:00:00",
  "end_time": "16:00:00",
  "guest_count": 12
}
```

## My service requests
- `GET /service_requests/` continues to list every request in the caller's condominium.
- `GET /service_requests/my-requests/` lists only requests created by the authenticated user.
- The personal endpoint accepts `status`, `priority`, `service_type`, and `period=future|past`. Period compares `request_scheduled_date` with the current time.

Para rodar:
```
docker compose \
  -f docker-compose.yml \
  -f docker-compose-debug.override.yml \
  up -d --build
```

Pra gerar documentacao de rotas para o front:
```
make schema
```


---

## Units — catálogo público (signup)

Sem auth. Inferência de andar: últimos 2 dígitos = porta (`1501` → andar `15`, label `01`). Códigos curtos (`1`…`90`) ficam flat (casas).

### Filtros disponíveis

```
GET {{base_url}}/units/filters/?condominium_code=CHACON
```

Retorna `layout` (`blocks` | `floors` | `flat`) e `filters.{block,floor,apartment,name}` com `enabled` + `options` (e `options_by_block` no floor).

### Lista agrupada

```
GET {{base_url}}/units/?condominium_code=CHACON
GET {{base_url}}/units/?condominium_code=CHACON&block=A&floor=17
GET {{base_url}}/units/?condominium_code=FOO&apartment=12
```

Query opcional (strings): `block`, `floor`, `apartment`, `name`.

Shape:
- `layout=blocks` → `blocks[].floors[].units[]`
- `layout=floors` → `floors[].units[]` (prédio sem bloco)
- `layout=flat` → `units[]` (casas / números curtos)
- `named[]` sempre separado (Pool House, etc.)

Cada item tem `id`, `label`, `apartment`, `block`, `floor`, `is_occupied`, `display_name`.

---

## Units — bulk provision (platform superuser)

Cria várias units de uma vez a partir de uma “receita” JSON.  
**Só `is_superuser`** (admin de condomínio / staff comum → 403).  
CRUD pontual continua no Django Admin.

### Rota

```
POST {{base_url}}/units/bulk-provision/
```

Header: `Authorization: Bearer {{access_token}}`  
(`{{access_token}}` vem de `POST {{base_url}}/api/token/`)

Body: `application/json`. Informe **`condominium_code`** ou **`condominium_id`** (não os dois).  
`skip_existing` default `true` (idempotente).

Números de andar viram `{floor}{unit}` — ex.: andar `15` + `"01"` → `"1501"`.

<details>
 <summary><code>POST</code> <code><b>/</b></code> <code>units/bulk-provision/</code></summary>

##### Auth
> Platform superuser only (`is_superuser=True`).

##### Body fields
> | name | required | description |
> |------|----------|-------------|
> | `condominium_code` **ou** `condominium_id` | one of | Target condominium |
> | `skip_existing` | no (default `true`) | Skip duplicates instead of 400 |
> | `blocks` | no | Named towers/wings → `APARTMENT_BLOCK` |
> | `towers` | no | Single building, no block → `APARTMENT` |
> | `number_range` | no | Sequential houses/apts (`start`/`end`/`pad`/`as_named`) |
> | `apartments` | no | Explicit apartment number list → `APARTMENT` |
> | `named_units` | no | Explicit named units → `NAMED` |

##### Responses
> | http code | content-type | response |
> |-----------|--------------|----------|
> | `201` | `JSON` | `created_count`, `skipped_count`, `created[]` |
> | `403` | `JSON` | Not a platform superuser |

</details>

#### Exemplos de body

**Chacon (blocos A/B/C):**
```json
{
  "condominium_code": "CHACON",
  "blocks": [
    { "block": "A", "floors": 15, "units": ["01", "02"] },
    { "block": "B", "floors": 18, "units": ["01", "02"] },
    { "block": "C", "floors": 15, "units": ["01", "02"] }
  ]
}
```

**Prédio único sem bloco (17 andares, 2 por andar):**
```json
{
  "condominium_code": "FOO",
  "towers": [{ "floors": 17, "units": ["01", "02"] }]
}
```

**Condomínio de casas (1…90):**
```json
{
  "condominium_code": "FOO",
  "number_range": { "start": 1, "end": 90 }
}
```
Com nome: `"as_named": true, "name_prefix": "Casa "` → `Casa 1`…

**Blocos com nome (ex. Arabaiana, 14×7):**
```json
{
  "condominium_code": "FOO",
  "blocks": [
    {
      "block": "Arabaiana",
      "floors": 14,
      "units": ["01", "02", "03", "04", "05", "06", "07"]
    }
  ]
}
```

---

## E-mails disparados

Todos os e-mails do sistema passam por `shared/infrastructure/email_sender.py` (`DjangoEmailSender`). Falhas de SMTP são logadas e **não** quebram a request que disparou o envio. Destinatário vazio é ignorado (exceto entrega, que retorna erro antes de criar o registro).

| # | Assunto | Destinatário | Gatilho (endpoint) | Condições / observações |
|---|---------|--------------|--------------------|-------------------------|
| 1 | `Welcome to Sunnyvale` | E-mail do visitante | `POST /visitor_access/` | Enviado após criar a visita. Visita solo: `email` do payload. Se vazio, **não envia**. |
| 1b | `Welcome to Sunnyvale` | E-mail de cada membro do grupo | `POST /visitor_access/groups/{id}/schedule/` | Um convite por membro que tenha e-mail cadastrado no grupo. |
| 2 | `Check-in notification` | Mesmo(s) e-mail(s) do convite | `GET /visitor_access/checkin/{link}/` | Só no **primeiro** check-in bem-sucedido, dentro da janela `checkin_date_time` → `checkout_date_time`. |
| 3 | `Check-out notification` | Mesmo(s) e-mail(s) do convite | `GET /visitor_access/checkout/{link}/` | Só no **primeiro** check-out bem-sucedido; visita precisa estar `CHECKED_IN` e dentro da janela de checkout (10 h antes do `scheduled_date`). |
| 4 | `Delivery notification` | Titular (holder) do apartamento | `POST /delivery_notification/` | Staff registra entrega por apto/bloco. Backend notifica só o holder. **Falha com 400** se não houver holder ativo ou sem e-mail. |
| 5 | `New resident request` | Titular(es) ativo(s) da unidade | `POST /user/` (signup com `household_request` → `join_existing`) | Novo morador pede entrada numa household já existente. Um e-mail por titular com e-mail. |
| 6 | `New household creation request` | Todos os admins (`is_staff=True`, ativos, com e-mail) | `POST /user/` (signup com `household_request` → `create_new`) | Novo morador pede criação de household nova (aguarda aprovação admin). |
| 7 | `Your account is approved` | Morador aprovado | `POST /households/{pk}/approve/` **ou** `POST /households/{pk}/memberships/{mid}/approve/` | Admin aprova household nova → todos os memberships `PENDING_ADMIN` com e-mail. Titular aprova entrada → requester com e-mail. |
| 8 | `Your request was rejected` | Morador rejeitado | `POST /households/{pk}/reject/` **ou** `POST /households/{pk}/memberships/{mid}/reject/` | Admin rejeita household → todos os membros com e-mail (motivo opcional no body). Titular rejeita entrada → requester com e-mail (motivo opcional). |
| 9 | `Your reservation is approved` | `reservation_user` da reserva | `POST /reservations/{pk}/approve/` | Admin aprova reserva `PENDING`. Se sem e-mail, **não envia** (aprovação segue). Idempotente: re-aprovar não reenvia. |
| 10 | `Your reservation was rejected` | `reservation_user` da reserva | `POST /reservations/{pk}/reject/` | Admin rejeita reserva `PENDING`. Motivo obrigatório no body (`reason`). Idempotente: re-rejeitar não reenvia. |

### O que **não** envia e-mail

- Login, refresh/verify de token, CRUD de usuário (exceto signup com `household_request`)
- Criação de reservas em locais configuráveis, pagamentos, notícias, solicitações de serviço
- Cancelamento de visita (`DELETE /visitor_access/{id}/`)
- Promover/rebaixar/remover membro, sair da household, transferir titularidade
- Cadastro de dependentes

### Configuração

Variáveis em `.env` (ver `sunnyValeConnect/settings.py`):

| Variável | Uso |
|----------|-----|
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL` | SMTP |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Credenciais |
| `DEFAULT_FROM_EMAIL` | Remetente (`From`) |
| `EMAIL_BACKEND` | Override opcional do backend Django |

Sem `EMAIL_HOST_USER` em dev, os e-mails vão para o **console** (stdout). Em testes, usa `locmem` (`mail.outbox`).
