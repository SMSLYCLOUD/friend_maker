import logging
from typing import List, Dict, Any, Optional

class CampaignPlanner:
    def __init__(self, ai_manager=None):
        self.ai = ai_manager
        self.logger = logging.getLogger("CampaignPlanner")

    async def _generate_with_provider(self, prompt: str) -> str:
        """Use ProviderManager fallback chain instead of hardcoded OpenRouter."""
        try:
            from app.llm.provider_manager import get_provider_manager
            import httpx

            pm = get_provider_manager()
            provider = pm.get_next_provider()
            if not provider:
                self.logger.error("No LLM providers available for planner")
                return ""

            config = provider.config
            self.logger.info(f"Planner using provider: {config.name}")

            payload = {
                "model": config.model,
                "messages": [{"role": "user", "content": prompt}]
            }
            headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    f"{config.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                if r.status_code == 200:
                    data = r.json()
                    choices = data.get("choices", [])
                    if choices:
                        pm.mark_success(config.name)
                        return choices[0].get("message", {}).get("content", "")
                    return ""
                else:
                    self.logger.error(f"Planner LLM error ({r.status_code}): {r.text[:200]}")
                    pm.mark_failed(config.name)
                    return ""
        except Exception as e:
            self.logger.error(f"Planner LLM failed: {e}")
            return ""

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
            response = await self._generate_with_provider(prompt)
            # Find JSON in response
            import json
            import re
            if response:
                match = re.search(r'\{.*\}', response, re.DOTALL)
                if match:
                    return json.loads(match.group())
            self.logger.error(f"Planner returned no valid JSON. Response: {response!r}")
            return {"keywords": [], "group_types": [], "target_accounts": [], "discovery_reasoning": "AI returned no valid plan"}
        except Exception as e:
            self.logger.error(f"Failed to generate discovery plan: {e}")
            return {"keywords": [], "group_types": [], "target_accounts": [], "discovery_reasoning": f"Error: {e}"}


