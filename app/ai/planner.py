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
            return self._fallback_plan(persona_instructions, platform)
        except Exception as e:
            self.logger.error(f"Failed to generate discovery plan: {e}")
            return self._fallback_plan(persona_instructions, platform)

    def _fallback_plan(self, persona_instructions: str, platform: str) -> Dict[str, Any]:
        """Smart fallback: extract accounts and keywords from instructions when AI fails."""
        import re
        text = persona_instructions.lower()

        # Extract @mentions
        mentions = re.findall(r'@(\w+)', persona_instructions)

        # Detect account names from common patterns: "followers of X", "members of X", "fans of X"
        account_patterns = [
            r'followers?\s+of\s+(.+?)(?:\s+on\s+\w+|\s*$)',
            r'members?\s+of\s+(.+?)(?:\s+on\s+\w+|\s*$)',
            r'fans?\s+of\s+(.+?)(?:\s+on\s+\w+|\s*$)',
            r'people\s+who\s+follow\s+(.+?)(?:\s+on\s+\w+|\s*$)',
        ]
        for pat in account_patterns:
            m = re.search(pat, text)
            if m:
                name = m.group(1).strip().title()
                # Convert name to likely handle: lowercase, no spaces
                handle = name.lower().replace(" ", "")
                mentions.append(handle)

        # Detect strategy hints
        strategy = "search"
        if any(w in text for w in ["followers", "fan base", "fanbase"]):
            strategy = "follower_mining"
        elif any(w in text for w in ["members", "group", "community"]):
            strategy = "group_combing"
        elif any(w in text for w in ["comments", "commenters"]):
            strategy = "post_auditing"

        # Extract meaningful keywords (skip stop words)
        stop_words = {"the", "and", "for", "that", "this", "with", "you", "your", "from",
                       "have", "has", "had", "was", "were", "are", "been", "being",
                       "will", "would", "could", "should", "may", "might", "can",
                       "message", "send", "post", "find", "get", "follow", "like",
                       "comment", "reply", "people", "who", "what", "where", "when",
                       "how", "all", "each", "every", "some", "any", "most", "other",
                       "into", "over", "such", "than", "too", "very", "just", "about",
                       "followers", "follower", "following", "members", "member",
                       "fans", "fan", "audience", "users", "people", "accounts"}
        words = [w.strip('.,!?') for w in persona_instructions.split()
                 if len(w) > 2 and w.lower() not in stop_words]
        keywords = list(dict.fromkeys(words[:10]))

        return {
            "keywords": keywords or [platform],
            "group_types": [],
            "target_accounts": mentions,
            "discovery_reasoning": f"Fallback: extracted from instructions (strategy={strategy}, accounts={mentions})"
        }
