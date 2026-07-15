# API Documentation
This documentation describes the API of a condominium system. The API is organized into 8 apps that control different functionalities, such as service management, reservations, notifications and News. Each app has endpoints for creating, viewing, updating, and deleting data.

## Apps
- Users
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
