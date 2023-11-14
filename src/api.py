import uuid
import time

from fastapi import FastAPI, Request, Depends, HTTPException, Security, status
from starlette.status import (
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from fastapi.responses import JSONResponse
from fastapi.security.api_key import APIKeyQuery, APIKeyCookie, APIKeyHeader, APIKey
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.websockets import WebSocket
from pydantic import BaseModel
from dotenv import find_dotenv, load_dotenv

import utils

load_dotenv(find_dotenv())


logger = utils.init_logger(__name__)

__version_info__ = (0, 1, 0)
__version__ = ".".join(str(v) for v in __version_info__)

API_KEY = "hackathon"
API_KEY_NAME = "access_token"
COOKIE_DOMAIN = "*"

description = """
## API Template

- API Key and OAuth2 Authentication
- /docs & /redoc is available
"""

tags_metadata = [
    {
        "name": "Security",
        "description": "Security endpoints.",
        "externalDocs": {
            "description": "Reference to an external resource",
            "url": "https://www.google.com",
        },
    },
]

app = FastAPI(
    title="Title API",
    description=description,
    summary="Summary API",
    version=__version__,
    openapi_tags=tags_metadata,
    swagger_ui_parameters={
        "syntaxHighlight.theme": "obsidian",
        "defaultModelsExpandDepth": -1,
    },
    json_schema_extra=None,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(name="Token", auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_api_key(
    api_key_header: str = Security(api_key_header),
):
    if api_key_header == API_KEY:
        return api_key_header
    else:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        )


class UserCredentials(BaseModel):
    user: str
    password: str


# Dependency to get current user based on the access token
def get_current_user(token: str = Depends(oauth2_scheme)):
    # You should validate the token here and retrieve the user from a database.
    # For this example, we are just using a hardcoded user database.
    # Mocked user database (replace with a real database in production)
    users_db = {
        "user1": {"username": "user1", "password": "password1"},
        "user2": {"username": "user2", "password": "password2"},
        "user": {
            "username": "user",
            "password": "pbkdf2_hmac_sha512$1000000$5ZLfZ5Shx/t+SWTBJ7Q3WNVwCj5cVl5LEoSocEGF17I=$404GY+jZTQcxsSQovUH4mpw13cTa76EocwvnmxRdQHql097RJA+GErSjGe9nVaiXv4VPWFFAeRcn1N44pen6Bg==",
        },
    }
    if token in users_db:
        return users_db[token]
    else:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.on_event("startup")
def startup_event():
    logger.info({"body": "API Service Started", "context": "startup_event"})


@app.on_event("shutdown")
def shutdown_event():
    logger.info({"body": "API Service Stopped", "context": "shutdown_event"})


@app.middleware("http")
async def add_context(request: Request, call_next):
    """
    Middleware that processes every request and response
    """
    start_time = time.time()
    request.state.request_id = request.query_params.get("request_id", str(uuid.uuid4()))

    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:0.6f}"
    response.headers["request_id"] = request.state.request_id
    response.headers["api_version"] = __version__
    return response


@app.get("/", include_in_schema=False)
def index():
    return JSONResponse(
        {"message": "ok", "timestamp": str(utils.now()), "version": __version__}
    )


@app.websocket("/ws2")
async def websocket(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"msg": "Hello WebSocket"})
    await websocket.close()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")


@app.get("/env", include_in_schema=True)
async def environment(api_key: APIKey = Depends(get_api_key)):
    """Environment endpoint"""
    return utils.os.environ


@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Token endpoint"""
    users_db = {
        "user": {
            "username": "user",
            "password": "pbkdf2_hmac_sha512$1000000$5ZLfZ5Shx/t+SWTBJ7Q3WNVwCj5cVl5LEoSocEGF17I=$404GY+jZTQcxsSQovUH4mpw13cTa76EocwvnmxRdQHql097RJA+GErSjGe9nVaiXv4VPWFFAeRcn1N44pen6Bg==",
        },
    }
    user = users_db.get(form_data.username)
    if user is None or form_data.password != user["password"]:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    return {"access_token": form_data.username, "token_type": "bearer"}


@app.get("/protected-resource", response_model=None, tags=["Security"])
async def protected_resource(current_user: dict = Depends(get_current_user)):
    """Protected resource endpoint"""
    return {
        "message": "You have access to this protected resource",
        "user": current_user["username"],
    }


@app.post("/generate_hash", response_model=str, tags=["Security"])
async def generate_hash_endpoint(credentials: UserCredentials):
    """Generate hash endpoint"""
    resp = None
    user = credentials.user
    password = credentials.password
    try:
        hashed_password = utils.generate_hash(password)
        resp = hashed_password
    except Exception as e:
        error = utils.get_exception_details()
        logger.error(error)
    finally:
        pass

    if resp:
        return resp
    else:
        return JSONResponse(
            status_code=500,
            content={
                "ERROR": {
                    "error": "Generate hash failed",
                    "detail": {"Error": error["message"].strip()},
                }
            },
        )


@app.post(
    "/authenticate",
    tags=["Security"],
    response_model=bool,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Authenticate user",
    response_description="Whether the user has been authenticated",
)
async def authenticate_endpoint(credentials: UserCredentials):
    """
    ## Authenticate user

    - Provide username as string
    - Provide password as string
    """
    user = credentials.user
    password = credentials.password
    if utils.authenticate(user, password):
        return True
    else:
        return False


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True, use_colors=True)
