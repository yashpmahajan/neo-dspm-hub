
# Backend API for neo-dspm-cursor (Structured)

This backend is built with FastAPI and MongoDB, organized for scalability.

## Folder Structure

```
backend/
  app/
    main.py           # FastAPI app entrypoint
    models/
      user.py         # User model
    db/
      mongodb.py      # MongoDB connection
    auth/
      jwt_handler.py  # JWT token creation/validation
    routes/
      user.py         # User-related endpoints
```


## Setup

1. Create a `.env` file in the backend folder:
  ```env
  MONGODB_URL=your_online_mongodb_url
  JWT_SECRET=your_jwt_secret
  CORS_ORIGINS=http://localhost:5173,http://your-frontend-url.com
  ```

2. (Recommended) Create a Python virtual environment:
  ```powershell
  python -m venv venv
  .\venv\Scripts\activate
  ```

3. Install dependencies:
  ```powershell
  pip install fastapi uvicorn pymongo pydantic python-dotenv python-multipart fpdf boto3 PyJWT
  ```

4. Start the server:
  ```powershell
  uvicorn app.main:app --reload
  ```

## Endpoints

### 1. Create User
- **POST** `/create-user`
- **Body:**
  ```json
  {
    "username": "string",
    "password": "string",
    "name": "string" // optional
  }
  ```
- **Response:** `{ "msg": "User created successfully" }`

### 2. Login User
- **POST** `/login`
- **Form Data:**
  - `username`: string
  - `password`: string
- **Response:** `{ "access_token": "<token>", "token_type": "bearer" }`

### 3. Hii (Greet User)
- **GET** `/hii`
- **Header:** `Authorization: Bearer <token>`
- **Response:** `{ "msg": "Hii <name>" }`

> The `/hii` endpoint returns the name of the user if the token is valid and the user exists in the database.

---
No tests are included as requested.
