from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.security import create_access_token, verify_password
from app.config import Settings, get_settings
from app.models.auth_models import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, settings: Settings = Depends(get_settings)) -> LoginResponse:
    if payload.username != settings.auth_username or not verify_password(
        payload.password, settings.auth_password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
        )

    token = create_access_token(subject=settings.auth_username, settings=settings)
    return LoginResponse(access_token=token)