from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from pydantic import BaseModel

from .database import get_db
from .models import User
from .auth import get_current_user

# Response models
class UserSearchResponse(BaseModel):
    id: str
    username: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    profileImageUrl: Optional[str] = None
    isOnline: Optional[bool] = False

# Create router
user_router = APIRouter(prefix="/api/users", tags=["users"])

@user_router.get("/search", response_model=List[UserSearchResponse])
def search_users(
    q: str = Query(..., min_length=1, max_length=50, description="Search query"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum number of results"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search for users by username, first name, or last name"""
    
    # Don't return the current user in search results
    search_query = q.strip().lower()
    
    # Search in username, firstName, and lastName fields
    users = db.query(User).filter(
        User.id != current_user.id,  # Exclude current user
        or_(
            User.username.ilike(f"%{search_query}%"),
            User.first_name.ilike(f"%{search_query}%") if search_query else False,
            User.last_name.ilike(f"%{search_query}%") if search_query else False
        )
    ).limit(limit).all()
    
    # Convert to response format
    user_responses = []
    for user in users:
        user_responses.append(UserSearchResponse(
            id=user.id,
            username=user.username,
            firstName=user.first_name,
            lastName=user.last_name,
            profileImageUrl=user.profile_image_url,
            isOnline=False  # TODO: Integrate with Redis presence system
        ))
    
    return user_responses

@user_router.get("/profile/{user_id}", response_model=UserSearchResponse)
def get_user_profile(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get public profile information for a specific user"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserSearchResponse(
        id=user.id,
        username=user.username,
        firstName=user.first_name,
        lastName=user.last_name,
        profileImageUrl=user.profile_image_url,
        isOnline=False  # TODO: Integrate with Redis presence system
    )