import logging
from typing import List, Dict, Any, Optional
from app.ai.openrouter_manager import OpenRouterManager

class CampaignPlanner:
    def __init__(self, ai_manager: OpenRouterManager):
        self.ai = ai_manager
        self.logger = logging.getLogger("CampaignPlanner")

    async def generate_discovery_plan(self, persona_instructions: str, platform: str, bot_instructions: str = "", ref_images: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Brainstorms the best groups, channels, and keywords to find a specific target audience.
        """
        constraints = ""
        if bot_instructions:
            constraints = f"\n\nCONSTRAINTS (must follow):\n{bot_instructions}\n\nOnly suggest sources that comply with these constraints."
        prompt = f"""
        ACT AS A SOCIAL MEDIA STRATEGIST AND LEAD GENERATION EXPERT.
        
        YOUR GOAL: Create a strategic "Discovery Map" to find this specific audience on {platform.upper()}:
        "{persona_instructions}"{constraints}
        
        TASKS:
        1. Identify 5-10 specific keywords this audience would use or follow.
        2. Identify types of groups or communities they would belong to.
        3. Identify potential "competitor" or "influencer" accounts they would follow.
        
        RETURN THE DATA IN JSON FORMAT:
        {{
            "keywords": ["kw1", "kw2"],
            "group_types": ["type1", "type2"],
            "target_accounts": ["handle1", "handle2"],
            "discovery_reasoning": "Brief explanation of why this plan will work."
        }}
        """
        
        try:
            response = await self.ai.generate(prompt)
            # Find JSON in response
            import json
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
            # Fallback: extract keywords from the instructions themselves
            import re as _re
            words = [w.strip('.,!?') for w in persona_instructions.split() if len(w) > 3]
            fallback_keywords = list(dict.fromkeys(words[:10]))
            return {
                "keywords": fallback_keywords or [platform],
                "group_types": [],
                "target_accounts": [],
                "discovery_reasoning": "Fallback: extracted keywords from instructions due to AI parsing error."
            }
        except Exception as e:
            self.logger.error(f"Failed to generate discovery plan: {e}")
            return {"error": str(e)}
