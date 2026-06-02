from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

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
    async def authenticate(self, session_data: Optional[str], username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """Login using saved session/cookies or credentials"""
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

    @abstractmethod
    async def get_group_members(self, group_id: str, limit: int = 100) -> List[UserProfile]:
        """Scrape members from a group, community, or channel"""
        pass

    @abstractmethod
    async def get_post_commenters(self, post_url: str, limit: int = 50) -> List[UserProfile]:
        """Scrape users who commented on a specific post or video"""
        pass

    @abstractmethod
    async def capture_screenshot(self) -> Optional[str]:
        """Capture a screenshot of the current page as a base64 string"""
        pass

    @abstractmethod
    async def get_post_comments(self, post_url: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get comments from a specific post or video"""
        pass

    @abstractmethod
    async def reply_to_comment(self, comment_id: str, message: str) -> ActionResult:
        """Reply to a specific comment"""
        pass

    @abstractmethod
    async def get_user_recent_posts(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent posts from a user"""
        pass

    @abstractmethod
    async def comment_on_post(self, post_url: str, message: str) -> ActionResult:
        """Comment on a specific post"""
        pass

    @abstractmethod
    async def comment_on_recent_post(self, user_id: str, message: str) -> ActionResult:
        """Comment on a user's most recent post"""
        pass
