# API Documentation
This documentation describes the API of a condominium system. The API is organized into 8 apps that control different functionalities, such as service management, reservations, notifications and News. Each app has endpoints for creating, viewing, updating, and deleting data.

## Apps
- Users
- Barbecue Reservations
- Hall Reservations
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

## Barbecue(BBQ) Reservations
For all endpoints of this app, you need to be ***Authenticated***. 
In some endpoints, there are two diferent responses, if you are **staff user or not**.

- #### List BBQ
List all of **user logged** in BBQ Reservations
<details>
 <summary><code>GET</code> <code><b>/</b></code> <code>bbq/</code></summary>

##### Parameters

> None

##### Responses

> | staff user    | http code     | content-type                      | response                                                            |
> |---------------|---------------|-----------------------------------|---------------------------------------------------------------------|
> | `True`         | `200`         | `JSON`        | List of all BBQ Reservations                                                         |
> | `False`         | `200`         | `JSON`        | **Yours** BBQ Reservations                                                         |

##### JSON Response example:
```json
[
	{
		"id": 5,
		"reservation_user": 34,
		"reservation_date": "2025-03-08",
		"guest_count": null
	},
	{
		"id": 4,
		"reservation_user": 34,
		"reservation_date": "2025-02-06",
		"guest_count": null
	},
	.
	.
	.
	
```
</details>

- #### Detail BBQ Reservation
If not a staff, you can access **just one of yours bbq reservations**.

<details>
 <summary><code>GET</code> <code><b>/</b></code> <code>bbq/{id}</code></summary>

##### Parameters

> None

##### Responses

> | staff user    | http code     | content-type                      | response                                                            |
> |---------------|---------------|-----------------------------------|---------------------------------------------------------------------|
> | `True`         | `200`         | `JSON`        | Detail of any BBQ Reservation                                                        |
> | `False`         | `200`         | `JSON`        | Detail of one of yours BBQ Reservation                                                        |

##### JSON Response example:
```json
{
	"id": 5,
	"reservation_user": 34,
	"reservation_date": "2025-03-08",
	"guest_count": null
}
```
</details>

</details>

- #### Create BBQ Reservation
- The reservations_user field is automatically filled with your user if you are not a staff member. If you are staff, you must fill it manually.
- Reservations cannot be created for past dates.
- The reservation date must be unique.
- There must be at least 30 days between each reservation.

<details>
 <summary><code>POST</code> <code><b>/</b></code> <code>bbq/</code></summary>

##### Parameters

> | name      |  type     | data type               | description                                                           |
> |-----------|-----------|-------------------------|-----------------------------------------------------------------------|
> | reservation_date      |  required | object (JSON)   | Reservation date  |
> | guest_count      |  optional | object (JSON)   | Number of guests  |
> | reservation_user      |  required(if staff) | object (JSON)   | Id of the user that will reservate  |



##### Responses

> | staff user    | http code     | content-type                      | response                                                            |
> |---------------|---------------|-----------------------------------|---------------------------------------------------------------------|
> | `True`         | `201`         | `JSON`        | BBQ Reservation you created                                                       |
> | `False`         | `200`         | `JSON`        | BBQ Reservation you created                                                       |

##### JSON Response example:
```json
{
	"id": 8,
	"reservation_user": 25,
	"reservation_date": "2025-04-09",
	"guest_count": 3
}
```
</details>



- #### Update BBQ Reservation
If you are not staff you can update **just one of yours** BBQ Reservations.

<details>
 <summary><code>POST</code> <code><b>/</b></code> <code>bbq/{id}</code></summary>

##### Parameters

> | name      |  type     | data type               | description                                                           |
> |-----------|-----------|-------------------------|-----------------------------------------------------------------------|
> | reservation_date      |  optional | object (JSON)   | Reservation date  |
> | guest_count      |  optional | object (JSON)   | Number of guests  |
> | reservation_user      |  optional(if staff) | object (JSON)   | Id of the user that will reservate  |


##### Responses

> | staff user    | http code     | content-type                      | response                                                            |
> |---------------|---------------|-----------------------------------|---------------------------------------------------------------------|
> | `True`         | `200`         | `JSON`        | `User updated `                                                     |
> | `False`         | `200`         | `JSON`        | `User updated`                                                      |

##### JSON Response example:
```json
{
	"id": 1,
	"reservation_user": 1,
	"reservation_date": "2024-12-12",
	"guest_count": 33
}
```
</details>



- #### Delete User
If you are not staff you can delete **just one of yours** BBQ Reservations.

<details>
 <summary><code>POST</code> <code><b>/</b></code> <code>bbq/{id}</code></summary>

##### Parameters

`None`


##### Responses

> | staff user    | http code     | content-type                      | response                                                            |
> |---------------|---------------|-----------------------------------|---------------------------------------------------------------------|
> | `True`         | `200`         | `None`        | `None`                                                      |
> | `False`         | `200`         | `None`        | `None`                                                     |
> | `True` / `False`         | `404`         | `JSON`        | `Detail of Not found `                                                     |



</details>

------------------------------------------------------------------------------------------

## Barbecue(BBQ) Reservations
For all endpoints of this app, you need to be ***Authenticated***. 
In some endpoints, there are two diferent responses, if you are **staff user or not**.

- #### List BBQ
List all of **user logged** in BBQ Reservations
<details>
 <summary><code>GET</code> <code><b>/</b></code> <code>bbq/</code></summary>

##### Parameters

> None

##### Responses

> | staff user    | http code     | content-type                      | response                                                            |
> |---------------|---------------|-----------------------------------|---------------------------------------------------------------------|
> | `True`         | `200`         | `JSON`        | List of all BBQ Reservations                                                         |
> | `False`         | `200`         | `JSON`        | **Yours** BBQ Reservations                                                         |

##### JSON Response example:
```json
[
	{
		"id": 5,
		"reservation_user": 34,
		"reservation_date": "2025-03-08",
		"guest_count": null
	},
	{
		"id": 4,
		"reservation_user": 34,
		"reservation_date": "2025-02-06",
		"guest_count": null
	},
	.
	.
	.
	
```
</details>

- #### Detail BBQ Reservation
If not a staff, you can access **just one of yours bbq reservations**.

<details>
 <summary><code>GET</code> <code><b>/</b></code> <code>bbq/{id}</code></summary>

##### Parameters

> None

##### Responses

> | staff user    | http code     | content-type                      | response                                                            |
> |---------------|---------------|-----------------------------------|---------------------------------------------------------------------|
> | `True`         | `200`         | `JSON`        | Detail of any BBQ Reservation                                                        |
> | `False`         | `200`         | `JSON`        | Detail of one of yours BBQ Reservation                                                        |

##### JSON Response example:
```json
{
	"id": 5,
	"reservation_user": 34,
	"reservation_date": "2025-03-08",
	"guest_count": null
}
```
</details>

</details>

- #### Create BBQ Reservation
- The reservations_user field is automatically filled with your user if you are not a staff member. If you are staff, you must fill it manually.
- Reservations cannot be created for past dates.
- The reservation date must be unique.
- There must be at least 30 days between each reservation.

<details>
 <summary><code>POST</code> <code><b>/</b></code> <code>bbq/</code></summary>

##### Parameters

> | name      |  type     | data type               | description                                                           |
> |-----------|-----------|-------------------------|-----------------------------------------------------------------------|
> | reservation_date      |  required | object (JSON)   | Reservation date  |
> | guest_count      |  optional | object (JSON)   | Number of guests  |
> | reservation_user      |  required(if staff) | object (JSON)   | Id of the user that will reservate  |



##### Responses

> | staff user    | http code     | content-type                      | response                                                            |
> |---------------|---------------|-----------------------------------|---------------------------------------------------------------------|
> | `True`         | `201`         | `JSON`        | BBQ Reservation you created                                                       |
> | `False`         | `200`         | `JSON`        | BBQ Reservation you created                                                       |

##### JSON Response example:
```json
{
	"id": 8,
	"reservation_user": 25,
	"reservation_date": "2025-04-09",
	"guest_count": 3
}
```
</details>



- #### Update BBQ Reservation
If you are not staff you can update **just one of yours** BBQ Reservations.

<details>
 <summary><code>POST</code> <code><b>/</b></code> <code>bbq/{id}</code></summary>

##### Parameters

> | name      |  type     | data type               | description                                                           |
> |-----------|-----------|-------------------------|-----------------------------------------------------------------------|
> | reservation_date      |  optional | object (JSON)   | Reservation date  |
> | guest_count      |  optional | object (JSON)   | Number of guests  |
> | reservation_user      |  optional(if staff) | object (JSON)   | Id of the user that will reservate  |


##### Responses

> | staff user    | http code     | content-type                      | response                                                            |
> |---------------|---------------|-----------------------------------|---------------------------------------------------------------------|
> | `True`         | `200`         | `JSON`        | `User updated `                                                     |
> | `False`         | `200`         | `JSON`        | `User updated`                                                      |

##### JSON Response example:
```json
{
	"id": 1,
	"reservation_user": 1,
	"reservation_date": "2024-12-12",
	"guest_count": 33
}
```
</details>



- #### Delete User
If you are not staff you can delete **just one of yours** BBQ Reservations.

<details>
 <summary><code>POST</code> <code><b>/</b></code> <code>bbq/{id}</code></summary>

##### Parameters

`None`


##### Responses

> | staff user    | http code     | content-type                      | response                                                            |
> |---------------|---------------|-----------------------------------|---------------------------------------------------------------------|
> | `True`         | `200`         | `None`        | `None`                                                      |
> | `False`         | `200`         | `None`        | `None`                                                     |
> | `True` / `False`         | `404`         | `JSON`        | `Detail of Not found `                                                     |



</details>
