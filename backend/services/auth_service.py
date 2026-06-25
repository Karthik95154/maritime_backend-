from fastapi import HTTPException
from datetime import datetime, timedelta
from schemas import UserCreate, UserLogin
from services.security import verify_password, get_password_hash, create_access_token
from config import settings
from services.app_activity_logger import log_app_event, log_app_error

class AuthService:
    @staticmethod
    async def signup_user(user: UserCreate, db):
        existing_user = await db.users.find_one({"email": user.email})
        if existing_user:
            log_app_error("signup_failed", "signup blocked because email already exists", user_email=user.email)
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed_password = get_password_hash(user.password)
        user_dict = {
            "name": user.name,
            "email": user.email,
            "hashed_password": hashed_password,
            "role": "Platform Administrator" if user.isAdmin else "Regional Survey Lead",
            "organization": user.organization,
            "isAdmin": user.isAdmin,
            "created_at": datetime.utcnow()
        }
        
        await db.users.insert_one(user_dict)
        log_app_event(
            "signup_success",
            "new user signed up",
            user_email=user.email,
            role=user_dict["role"],
            organization=user.organization,
            is_admin=user.isAdmin,
        )
        
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "user": {
                "name": user.name,
                "email": user.email,
                "role": user_dict["role"],
                "organization": user.organization,
                "isAdmin": user.isAdmin
            }
        }

    @staticmethod
    async def login_user(user: UserLogin, db):
        db_user = await db.users.find_one({"email": user.email})
        if not db_user:
            log_app_error("login_failed", "login failed because user was not found", user_email=user.email)
            raise HTTPException(status_code=400, detail="Incorrect email or password")
            
        if not verify_password(user.password, db_user["hashed_password"]):
            log_app_error("login_failed", "login failed because password mismatch", user_email=user.email)
            raise HTTPException(status_code=400, detail="Incorrect email or password")
            
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        log_app_event(
            "login_success",
            "user logged in",
            user_email=user.email,
            role=db_user.get("role"),
            organization=db_user.get("organization"),
            is_admin=db_user.get("isAdmin", False),
        )
        
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "user": {
                "name": db_user.get("name"),
                "email": db_user.get("email"),
                "role": db_user.get("role"),
                "organization": db_user.get("organization"),
                "isAdmin": db_user.get("isAdmin", False)
            }
        }

    @staticmethod
    async def get_all_users(db):
        users = await db.users.find().to_list(length=None)
        if not users:
            return [
                {"id": "u1", "name": "System Admin", "email": "admin@maritime.com", "role": "Platform Administrator", "status": "Active"},
                {"id": "u2", "name": "John Inspector", "email": "john@maritime.com", "role": "Regional Survey Lead", "status": "Active"}
            ]
        return [{"id": str(u["_id"]), "name": u.get("name"), "email": u.get("email"), "role": u.get("role", "Regional Survey Lead"), "status": "Active"} for u in users]

    @staticmethod
    async def update_user_role(email: str, payload: dict, db):
        new_role = payload.get("role")
        if not new_role:
            raise HTTPException(status_code=400, detail="Role is required")
        await db.users.update_one({"email": email}, {"$set": {"role": new_role}})
        log_app_event("user_role_updated", "user role updated", user_email=email, new_role=new_role)
        return {"status": "success", "message": f"User {email} role updated to {new_role}"}

    @staticmethod
    async def update_user_password(email: str, payload: dict, db):
        new_password = payload.get("password")
        if not new_password:
            raise HTTPException(status_code=400, detail="Password is required")
        
        hashed_password = get_password_hash(new_password)
        result = await db.users.update_one(
            {"email": email}, 
            {"$set": {"hashed_password": hashed_password}}
        )
        if result.matched_count == 0:
            log_app_error("password_update_failed", "password update failed because user was not found", user_email=email)
            raise HTTPException(status_code=404, detail="User not found")
        log_app_event("password_updated", "user password updated", user_email=email)
            
        return {"status": "success", "message": f"Password updated successfully for {email}"}
