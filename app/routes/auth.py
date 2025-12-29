from app.schemas.user import UserCreate, UserResponse, UserLogin, Token
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.security import get_current_user

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.core.security import hash_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    # check if user already exists
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # password policy
    if len(user_in.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    # create user
    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
)

from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends

@router.post("/login", response_model=Token)
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token_data = {"sub": str(user.id)}
    access_token = create_access_token(data=token_data)

    refresh_token = create_refresh_token()
    user.refresh_token = refresh_token
    db.commit()

    return {
    "access_token": access_token,
    "refresh_token": refresh_token,
    "token_type": "bearer",
    }

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


from app.core.security import require_admin

@router.get("/admin/users", response_model=list[UserResponse])
def get_all_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return db.query(User).all()

@router.post("/refresh", response_model=Token)
def refresh_access_token(
    refresh_token: str,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.refresh_token == refresh_token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    token_data = {"sub": str(user.id)}
    access_token = create_access_token(data=token_data)

    return {
        "access_token": access_token,
        "refresh_token": user.refresh_token,
        "token_type": "bearer",
    }



@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.refresh_token = None
    db.commit()
