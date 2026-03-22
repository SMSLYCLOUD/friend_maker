import logging
from typing import Dict, Any
from app.ai.openrouter_manager import OpenRouterManager

class MessageGenerator:
    def __init__(self, manager: OpenRouterManager):
        self.manager = manager
        self.logger = logging.getLogger("MessageGenerator")

    async def generate_dm(self, profile: Dict[str, Any], template: str = "") -> str:
        prompt = f"""
Write a personalized direct message (DM) for Instagram.
Keep it short, friendly, and authentic. No hashtags.
Do not sound like a bot.

Target Profile:
Username: {profile.get('username')}
Bio: {profile.get('bio')}
Niche: {profile.get('niche', 'General')}

Context/Goal:
{template if template else "Introduce myself as a software developer building cool tools."}

Message:
"""
        response = await self.manager.generate(prompt)
        return response.strip().strip('"')
