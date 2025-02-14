# URL Shortener & Authentication Microservices

This project implements two microservices using a RESTful design:

1. **Authentication Service** – Handles user registration, login, token verification, and password updates with hand-crafted JWTs.
2. **URL Shortener Service** – Creates, retrieves, updates, and deletes shortened URLs. All operations require a valid JWT passed via the `Authorization` header.

The project supports two deployment methods:

- **Normal Version**: Each service runs on its own port (e.g., Auth on 8001, URL Shortener on 8000).
- **Nginx Version**: Nginx serves as a single entry point and reverse-proxies requests to the appropriate service (using port 8080 as the unified endpoint).

------

## Project Structure

- **auth.py**
   Implements the authentication service. Endpoints include:

  - Create (Registration)

    :

    - **POST** `/users`
       Parameters: `username`, `password`
       Returns: **201** on success or **409** if the user already exists.

  - Read (Login)

    :

    - **POST** `/users/login`
       Parameters: `username`, `password`
       Returns: **200** with a JWT token on success or **403** on authentication failure.

  - Verify Token

    :

    - **POST** `/users/verify`
       Parameters: `token`
       Returns: **200** with the token payload on success or **403** if invalid.

  - Update (Change Password)

    :

    - **PUT** `/users`
       Parameters: `username`, `old_password`, `new_password`
       Returns: **200** on success or **403** if credentials are incorrect.

- **main.py** (with **database.py**)
   Implements the URL Shortener service. Endpoints include:

  - Create

    :

    - **POST** `/`
       JSON body parameter: `value` (the long URL)
       Returns: **201** with the new short URL ID on success, **400** if invalid URL, or **403** if unauthorized.

  - Read (Get All)

    :

    - **GET** `/`
       Returns: **200** with a list of all shortened URLs for the user or **403** if unauthorized.

  - Read (Get Single)

    :

    - **GET** `/<short_id>`
       Returns: **301** (redirect) with JSON containing the long URL (i.e., `{"value": "long URL"}`) or **404** if not found.

  - Update

    :

    - **PUT** `/<short_id>`
       JSON body parameter: `url` (or `value`) with the new long URL
       Returns: **200** on successful update, **400** if the URL is invalid, **404** if not found, or **403** if unauthorized.

  - Delete (Single)

    :

    - **DELETE** `/<short_id>`
       Returns: **204** on success, **404** if not found, or **403** if unauthorized.

  - Delete (All)

    :

    - **DELETE** `/`
       Deletes all shortened URLs for the authenticated user. Returns **404** to indicate that resources are now absent or **403** if unauthorized.

------

## Requirements & Dependencies

- **Python Version**: 3.9 or later

- Dependencies

  :

  Install using pip (preferably in a virtual environment):

  ```bash
  pip install flask flask_sqlalchemy requests werkzeug
  ```

- **Nginx**: Recommended version **1.24.0** or higher (only required for the Nginx deployment version).

------

## Usage Instructions

### 1. Normal Version

In this mode, run each service separately on its designated port.

#### Starting the Authentication Service

The authentication service listens on port **8001**. Open a command prompt and run:

```bash
python auth.py
```

#### Starting the URL Shortener Service

The URL shortener service listens on port **8000**. In a separate command prompt, run:

```bash
python main.py
```

#### Example API Calls (Using PowerShell)

**Authentication Service**

- Register User (Create)

  ```powershell
  $body = '{"username": "user456", "password": "pass456"}'
  Invoke-RestMethod -Uri "http://127.0.0.1:8001/users" -Method Post -ContentType "application/json" -Body $body
  ```

- Login (Read)

  ```powershell
  $body = '{"username": "user456", "password": "pass456"}'
  $response = Invoke-RestMethod -Uri "http://127.0.0.1:8001/users/login" -Method Post -ContentType "application/json" -Body $body
  $token = $response.token
  $token
  ```

- Verify Token

  ```powershell
  $body = '{"token": "' + $token + '"}'
  Invoke-RestMethod -Uri "http://127.0.0.1:8001/users/verify" -Method Post -ContentType "application/json" -Body $body
  ```

- Change Password (Update)

  ```powershell
  $body = '{"username": "user456", "old_password": "pass456", "new_password": "newpass456"}'
  Invoke-RestMethod -Uri "http://127.0.0.1:8001/users" -Method Put -ContentType "application/json" -Body $body
  ```

**URL Shortener Service** (all calls must include the `Authorization` header with the JWT)

- Create Short URL (Create)

  ```powershell
  $body = '{"value": "https://www.microsoft.com"}'
  $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/" -Method Post -ContentType "application/json" -Headers @{Authorization=$token} -Body $body
  $response
  $id = $response.id
  $id
  ```

- Get All Short URLs (Read)

  ```powershell
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/" -Method Get -Headers @{Authorization=$token}
  ```

- Get Single Short URL (Read)

  (Because the endpoint returns a 301 redirect, it is recommended to use Invoke-WebRequest)

  ```powershell
  $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/$id" -Method Get -Headers @{Authorization=$token} -ErrorAction SilentlyContinue
  $response.StatusCode  # Expected to be 301
  $content = $response.Content | ConvertFrom-Json
  $content
  ```

- Update Short URL (Update)

  ```powershell
  $body = '{"url": "https://www.github.com"}'
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/$id" -Method Put -ContentType "application/json" -Headers @{Authorization=$token} -Body $body
  ```

- Delete Single Short URL (Delete)

  ```powershell
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/$id" -Method Delete -Headers @{Authorization=$token}
  ```

- Delete All Short URLs (Delete)

  ```powershell
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/" -Method Delete -Headers @{Authorization=$token}
  ```

------

### 2. Nginx Deployment Version

In this mode, Nginx acts as a single entry point and reverse-proxies requests to the appropriate service.

#### Nginx Configuration

Save the following configuration as `nginx.conf` (Nginx recommended version 1.24.0 or above):

```nginx
worker_processes  1;

events {
    worker_connections  1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;
    sendfile        on;
    keepalive_timeout  65;

    upstream auth_service {
        server localhost:8001;
    }
    upstream url_service {
        server localhost:8000;
    }

    server {
        listen       8080;
        server_name  localhost;

        # Forward all requests starting with /users to the Authentication Service
        location /users {
            proxy_pass http://auth_service;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # All other requests go to the URL Shortener Service
        location / {
            proxy_pass http://url_service;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

#### Starting Nginx

1. Download and extract Nginx (if not already installed).

2. Place the above configuration in the Nginx configuration directory (typically in the `conf` folder) or specify the configuration file when starting Nginx.

3. Open a command prompt or PowerShell in the Nginx installation directory and start Nginx by running:

   ```powershell
   nginx
   ```

4. To reload the configuration after changes:

   ```powershell
   nginx -s reload
   ```

#### Example API Calls via Nginx (Using Port 8080)

All requests now use `http://localhost:8080` as the base URL.

**Authentication Service**

- Register User

  ```powershell
  $body = '{"username": "user456", "password": "pass456"}'
  Invoke-RestMethod -Uri "http://localhost:8080/users" -Method Post -ContentType "application/json" -Body $body
  ```

- Login

  ```powershell
  $body = '{"username": "user456", "password": "pass456"}'
  $response = Invoke-RestMethod -Uri "http://localhost:8080/users/login" -Method Post -ContentType "application/json" -Body $body
  $token = $response.token
  $token
  ```

- Verify Token

  ```powershell
  $body = '{"token": "' + $token + '"}'
  Invoke-RestMethod -Uri "http://localhost:8080/users/verify" -Method Post -ContentType "application/json" -Body $body
  ```

- Change Password

  ```powershell
  $body = '{"username": "user456", "old_password": "pass456", "new_password": "newpass456"}'
  Invoke-RestMethod -Uri "http://localhost:8080/users" -Method Put -ContentType "application/json" -Body $body
  ```

**URL Shortener Service** (with Authorization header)

- Create Short URL

  ```powershell
  $body = '{"value": "https://www.microsoft.com"}'
  $response = Invoke-RestMethod -Uri "http://localhost:8080/" -Method Post -ContentType "application/json" -Headers @{Authorization=$token} -Body $body
  $response
  $id = $response.id
  $id
  ```

- Get All Short URLs

  ```powershell
  Invoke-RestMethod -Uri "http://localhost:8080/" -Method Get -Headers @{Authorization=$token}
  ```

- Get Single Short URL

  ```powershell
  $response = Invoke-WebRequest -Uri "http://localhost:8080/$id" -Method Get -Headers @{Authorization=$token} -ErrorAction SilentlyContinue
  $response.StatusCode  # Expected 301
  $content = $response.Content | ConvertFrom-Json
  $content
  ```

- Update Short URL

  ```powershell
  $body = '{"url": "https://www.github.com"}'
  Invoke-RestMethod -Uri "http://localhost:8080/$id" -Method Put -ContentType "application/json" -Headers @{Authorization=$token} -Body $body
  ```

- Delete Single Short URL

  ```powershell
  Invoke-RestMethod -Uri "http://localhost:8080/$id" -Method Delete -Headers @{Authorization=$token}
  ```

- Delete All Short URLs

  ```powershell
  Invoke-RestMethod -Uri "http://localhost:8080/" -Method Delete -Headers @{Authorization=$token}
  ```

------

## Testing

A test script `test_app.py` is included and uses Python's `unittest` framework to perform integration testing on all endpoints.
 To run the tests:

```bash
python test_app.py
```

*Make sure that the relevant services are running (either the normal version or via Nginx) before executing the tests.*

------

## Troubleshooting

- **404 Not Found**:
   Verify that you are using the correct URL. For the normal version, use `http://127.0.0.1:8001/users` for authentication requests and `http://127.0.0.1:8000/` for URL Shortener requests. In the Nginx version, use `http://localhost:8080` with the appropriate paths.
- **Content-Type Issues**:
   Ensure you include `-ContentType "application/json"` in your requests when sending JSON bodies.
- **Nginx Not Starting**:
   Confirm that you are in the correct directory and that your `nginx.conf` is properly configured. Test by visiting `http://localhost:8080` in a browser.

------

## Additional Notes

- The JWT token includes only essential information to reduce payload size.
- The secret key used for JWT signing is maintained within the authentication service and is not shared with the URL Shortener service.
- The project is designed following microservices principles, ensuring each service focuses on a single responsibility to allow for easier maintenance and scalability.

------

