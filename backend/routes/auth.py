from fastapi import APIRouter, Depends
from database import get_db
from schemas import UserCreate, UserLogin, TokenResponse
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=TokenResponse)
async def signup(user: UserCreate, db = Depends(get_db)):
    return await AuthService.signup_user(user, db)

@router.post("/login", response_model=TokenResponse)
async def login(user: UserLogin, db = Depends(get_db)):
    return await AuthService.login_user(user, db)

@router.get("/users")
async def get_users(db = Depends(get_db)):
    return await AuthService.get_all_users(db)

@router.post("/users/{email}/role")
async def update_role(email: str, payload: dict, db = Depends(get_db)):
    return await AuthService.update_user_role(email, payload, db)

@router.post("/users/{email}/password")
async def update_password(email: str, payload: dict, db = Depends(get_db)):
    return await AuthService.update_user_password(email, payload, db)
