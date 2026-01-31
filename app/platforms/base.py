from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class UserProfile:
    platform_id: str
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    followers: int = 0
    following: int = 0
    posts: int = 0
    is_verified: bool = False
    avatar_url: Optional[str] = None

@dataclass
class ActionResult:
    success: bool
    action_type: str
    error: Optional[str] = None

class PlatformAdapter(ABC):
    platform_name: str = "base"

    @abstractmethod
    async def authenticate(self, session_data: str) -> bool:
        """Login using saved session/cookies"""
        pass

    @abstractmethod
    async def search_users(self, query: str, limit: int = 20) -> List[UserProfile]:
        """Search for users"""
        pass

    @abstractmethod
    async def get_followers(self, user_id: str, limit: int = 100) -> List[UserProfile]:
        """Get followers of a user"""
        pass

    @abstractmethod
    async def follow(self, user_id: str) -> ActionResult:
        """Follow a user"""
        pass

    @abstractmethod
    async def unfollow(self, user_id: str) -> ActionResult:
        """Unfollow a user"""
        pass

    @abstractmethod
    async def send_dm(self, user_id: str, message: str) -> ActionResult:
        """Send direct message"""
        pass
