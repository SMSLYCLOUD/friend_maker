import logging
from typing import Dict, Any, Optional, List
from app.ai.openrouter_manager import OpenRouterManager

class MessageGenerator:
    def __init__(self, manager: OpenRouterManager):
        self.manager = manager
        self.logger = logging.getLogger("MessageGenerator")

    async def generate_dm(self, profile: Dict[str, Any], template: str = "", instructions: str = "", image_base64: Optional[str] = None, bot_instructions: str = "", ref_images: List[str] = None) -> str:
        global_rules = ""
        if bot_instructions:
            global_rules = f"\n\nGLOBAL BEHAVIOR RULES (always follow):\n{bot_instructions}"

        ref_hint = ""
        if ref_images:
            ref_hint = f"\n(I have attached {len(ref_images)} reference image(s) showing the visual style and aesthetic of our brand. Match the tone and style of the message to these references.)"

        prompt = f"""
{instructions if instructions else "Write a personalized direct message (DM) for Instagram. Keep it short, friendly, and authentic. No hashtags. Do not sound like a bot."}{global_rules}{ref_hint}

Target Profile:
Username: {profile.get('username')}
Bio: {profile.get('bio')}
Niche: {profile.get('niche', 'General')}

{"(I have attached a screenshot of the user's profile for you to analyze visual elements like their profile picture, aesthetic, and recent posts.)" if image_base64 else ""}

Context/Goal:
{template if template else "Introduce myself as a software developer building cool tools."}

Message:
"""
        response = await self.manager.generate(prompt, image_base64=image_base64, ref_images=ref_images)
        return response.strip().strip('"')
