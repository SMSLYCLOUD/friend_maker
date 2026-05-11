import logging
from typing import Dict, Any
from app.ai.openrouter_manager import OpenRouterManager

class MessageGenerator:
    def __init__(self, manager: OpenRouterManager):
        self.manager = manager
        self.logger = logging.getLogger("MessageGenerator")

    async def generate_dm(self, profile: Dict[str, Any], template: str = "", instructions: str = "", image_base64: Optional[str] = None) -> str:
        prompt = f"""
{instructions if instructions else "Write a personalized direct message (DM) for Instagram. Keep it short, friendly, and authentic. No hashtags. Do not sound like a bot."}

Target Profile:
Username: {profile.get('username')}
Bio: {profile.get('bio')}
Niche: {profile.get('niche', 'General')}

{"(I have attached a screenshot of the user's profile for you to analyze visual elements like their profile picture, aesthetic, and recent posts.)" if image_base64 else ""}

Context/Goal:
{template if template else "Introduce myself as a software developer building cool tools."}

Message:
"""
        response = await self.manager.generate(prompt, image_base64=image_base64)
        return response.strip().strip('"')
