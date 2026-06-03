import logging
from typing import Dict, Any, Optional, List
from app.ai.openrouter_manager import OpenRouterManager

class MessageGenerator:
    def __init__(self, manager: OpenRouterManager):
        self.manager = manager
        self.logger = logging.getLogger("MessageGenerator")

    async def generate_dm(self, profile: Dict[str, Any], template: str = "", instructions: str = "", image_base64: Optional[str] = None, bot_instructions: str = "", ref_images: List[str] = None, conversation_history: str = "") -> str:
        global_rules = ""
        if bot_instructions:
            global_rules = f"\n\nGLOBAL BEHAVIOR RULES (always follow):\n{bot_instructions}"

        ref_hint = ""
        if ref_images:
            ref_hint = f"\n(I have attached {len(ref_images)} reference image(s) showing the visual style and aesthetic of our brand. Match the tone and style of the message to these references.)"

        history_block = ""
        if conversation_history:
            history_block = f"\n\nCONVERSATION HISTORY:\n{conversation_history}\n\nContinue the conversation naturally based on what was said before."

        prompt = f"""
{instructions if instructions else "Write a personalized direct message (DM) for Instagram. Keep it short, friendly, and authentic. No hashtags. Do not sound like a bot."}{global_rules}{ref_hint}

Target Profile:
Username: {profile.get('username')}
Display Name: {profile.get('display_name', '')}
Bio: {profile.get('bio', 'Not available')}
Follower Count: {profile.get('follower_count', 'Not available')}
Recent Posts: {', '.join(profile.get('recent_posts', [])[:3]) if profile.get('recent_posts') else 'Not available'}
{history_block}

{"(I have attached a screenshot of the user's profile for you to analyze visual elements like their profile picture, aesthetic, and recent posts.)" if image_base64 else ""}

Context/Goal:
{template if template else "Introduce myself as a software developer building cool tools."}

Write a message that references something specific from their bio or recent posts to make it feel personal and genuine. Do NOT use hashtags. Do NOT sound like a bot or salesperson.

Message:
"""
        response = await self.manager.generate(prompt, image_base64=image_base64, ref_images=ref_images)
        return response.strip().strip('"')

    async def generate_reply(self, profile: Dict[str, Any], template: str = "", instructions: str = "", image_base64: Optional[str] = None, bot_instructions: str = "", ref_images: List[str] = None, conversation_history: str = "", their_message: str = "") -> str:
        global_rules = ""
        if bot_instructions:
            global_rules = f"\n\nGLOBAL BEHAVIOR RULES (always follow):\n{bot_instructions}"

        history_block = ""
        if conversation_history:
            history_block = f"\n\nCONVERSATION HISTORY:\n{conversation_history}"

        prompt = f"""
You are continuing a conversation on social media. The other person has replied to your message.
{global_rules}

Target Profile:
Username: {profile.get('username')}
Display Name: {profile.get('display_name', '')}
Bio: {profile.get('bio', 'Not available')}
{history_block}

THEIR REPLY:
{their_message if their_message else "They replied but the content was not captured."}

TASK: Write a natural, friendly reply to their message. Keep it conversational. Do NOT use hashtags. Do NOT sound like a bot. Reference something from the conversation to show you're paying attention.

Reply:
"""
        response = await self.manager.generate(prompt, image_base64=image_base64, ref_images=ref_images)
        return response.strip().strip('"')

    async def generate_comment(self, profile: Dict[str, Any], template: str = "", instructions: str = "", image_base64: Optional[str] = None, bot_instructions: str = "", ref_images: List[str] = None) -> str:
        global_rules = ""
        if bot_instructions:
            global_rules = f"\n\nGLOBAL BEHAVIOR RULES (always follow):\n{bot_instructions}"

        prompt = f"""
Write a comment on {profile.get('username', 'a user')}'s post.
{global_rules}

Target Profile:
Username: {profile.get('username')}
Bio: {profile.get('bio', 'Not available')}
Recent Posts: {', '.join(profile.get('recent_posts', [])[:3]) if profile.get('recent_posts') else 'Not available'}

Context: {template if template else "Leave a genuine, engaging comment on their post."}

Write a comment that references something specific from their post. Keep it short and authentic. Do NOT use hashtags. Do NOT sound like a bot.

Comment:
"""
        response = await self.manager.generate(prompt, image_base64=image_base64, ref_images=ref_images)
        return response.strip().strip('"')
