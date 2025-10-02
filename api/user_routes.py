from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from pydantic import BaseModel, HttpUrl

from .database import get_db
from .models import User, Follower
from .auth import get_current_user

# Response models
class UserSearchResponse(BaseModel):
    id: str
    username: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    profileImageUrl: Optional[str] = None
    isOnline: Optional[bool] = False

# Profile update model
class UpdateProfileRequest(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    companyName: Optional[str] = None
    linkedinUrl: Optional[str] = None

class UpdateProfileResponse(BaseModel):
    success: bool
    message: str
    user: UserSearchResponse

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
            isOnline=False
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
        isOnline=False
    )

@user_router.put("/profile", response_model=UpdateProfileResponse)
def update_profile(
    profile_data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the current user's profile information"""
    
    # Update user fields
    if profile_data.firstName is not None:
        current_user.first_name = profile_data.firstName.strip() if profile_data.firstName else None
    
    if profile_data.lastName is not None:
        current_user.last_name = profile_data.lastName.strip() if profile_data.lastName else None
    
    if profile_data.companyName is not None:
        current_user.company_name = profile_data.companyName.strip() if profile_data.companyName else None
    
    if profile_data.linkedinUrl is not None:
        current_user.linkedin_url = profile_data.linkedinUrl.strip() if profile_data.linkedinUrl else None
    
    # Commit changes
    db.commit()
    db.refresh(current_user)
    
    return UpdateProfileResponse(
        success=True,
        message="Profile updated successfully",
        user=UserSearchResponse(
            id=current_user.id,
            username=current_user.username,
            firstName=current_user.first_name,
            lastName=current_user.last_name,
            profileImageUrl=current_user.profile_image_url,
            isOnline=False
        )
    )

# Follower endpoints

class FollowerResponse(BaseModel):
    id: str
    username: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    companyName: Optional[str] = None
    linkedinUrl: Optional[str] = None
    profileImageUrl: Optional[str] = None
    problemsSolved: int = 0

class FollowStatusResponse(BaseModel):
    isFollowing: bool
    followersCount: int
    followingCount: int

@user_router.post("/follow/{user_id}")
def follow_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Follow a user"""
    
    # Check if user exists
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Cannot follow yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow yourself"
        )
    
    # Check if already following
    existing_follow = db.query(Follower).filter(
        Follower.follower_id == current_user.id,
        Follower.following_id == user_id
    ).first()
    
    if existing_follow:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already following this user"
        )
    
    # Create follow relationship
    new_follow = Follower(
        follower_id=current_user.id,
        following_id=user_id
    )
    db.add(new_follow)
    db.commit()
    
    return {"success": True, "message": "Successfully followed user"}

@user_router.delete("/unfollow/{user_id}")
def unfollow_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unfollow a user"""
    
    # Find follow relationship
    follow = db.query(Follower).filter(
        Follower.follower_id == current_user.id,
        Follower.following_id == user_id
    ).first()
    
    if not follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not following this user"
        )
    
    db.delete(follow)
    db.commit()
    
    return {"success": True, "message": "Successfully unfollowed user"}

@user_router.get("/follow-status/{user_id}", response_model=FollowStatusResponse)
def get_follow_status(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get follow status for a user"""
    
    # Check if current user is following the target user
    is_following = db.query(Follower).filter(
        Follower.follower_id == current_user.id,
        Follower.following_id == user_id
    ).first() is not None
    
    # Get followers count (people following the target user)
    followers_count = db.query(Follower).filter(
        Follower.following_id == user_id
    ).count()
    
    # Get following count (people the target user follows)
    following_count = db.query(Follower).filter(
        Follower.follower_id == user_id
    ).count()
    
    return FollowStatusResponse(
        isFollowing=is_following,
        followersCount=followers_count,
        followingCount=following_count
    )

@user_router.get("/followers/{user_id}", response_model=List[FollowerResponse])
def get_followers(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of followers for a user"""
    
    followers = db.query(User).join(
        Follower, Follower.follower_id == User.id
    ).filter(
        Follower.following_id == user_id
    ).limit(limit).all()
    
    return [
        FollowerResponse(
            id=user.id,
            username=user.username,
            firstName=user.first_name,
            lastName=user.last_name,
            companyName=user.company_name,
            linkedinUrl=user.linkedin_url,
            profileImageUrl=user.profile_image_url,
            problemsSolved=user.problems_solved
        )
        for user in followers
    ]

@user_router.get("/following/{user_id}", response_model=List[FollowerResponse])
def get_following(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of users that a user is following"""
    
    following = db.query(User).join(
        Follower, Follower.following_id == User.id
    ).filter(
        Follower.follower_id == user_id
    ).limit(limit).all()
    
    return [
        FollowerResponse(
            id=user.id,
            username=user.username,
            firstName=user.first_name,
            lastName=user.last_name,
            companyName=user.company_name,
            linkedinUrl=user.linkedin_url,
            profileImageUrl=user.profile_image_url,
            problemsSolved=user.problems_solved
        )
        for user in following
    ]