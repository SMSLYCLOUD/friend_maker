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
        Extract the specific targets and strategy from the user's instruction.
        Do NOT invent extra accounts — only use what is explicitly mentioned.
        """
        constraints = ""
        if bot_instructions:
            constraints = f"\n\nCONSTRAINTS (must follow):\n{bot_instructions}"

        prompt = f"""
        Analyze this instruction and extract the discovery targets:

        INSTRUCTION: "{persona_instructions}"
        PLATFORM: {platform}{constraints}

        RULES:
        - ONLY extract accounts, keywords, or groups EXPLICITLY mentioned in the instruction.
        - Do NOT invent, suggest, or hallucinate additional accounts.
        - If the instruction says "followers of X", then X is the ONLY target_account.
        - If the instruction says "people interested in Y", then Y is a keyword.
        - Extract any numeric limits mentioned (e.g. "20 followers" → limit: 20).

        RETURN JSON:
        {{
            "target_accounts": ["only_accounts_explicitly_mentioned"],
            "keywords": ["only_keywords_explicitly_mentioned"],
            "group_types": ["only_groups_explicitly_mentioned"],
            "limit": 20,
            "reasoning": "Brief explanation of what was extracted and why."
        }}
        """

        try:
            response = await self._generate_with_provider(prompt)
            import json
            import re
            if response:
                match = re.search(r'\{.*\}', response, re.DOTALL)
                if match:
                    plan = json.loads(match.group())
                    # Sanitize: strip @ from accounts, filter empty
                    plan["target_accounts"] = [a.lstrip("@") for a in plan.get("target_accounts", []) if a.strip()]
                    plan["keywords"] = [k for k in plan.get("keywords", []) if k.strip()]
                    plan["group_types"] = [g for g in plan.get("group_types", []) if g.strip()]
                    plan.setdefault("limit", 20)
                    self.logger.info(f"Planner extracted: accounts={plan['target_accounts']}, keywords={plan['keywords']}, limit={plan['limit']}")
                    return plan
            self.logger.error(f"Planner returned no valid JSON. Response: {response!r}")
            return {"keywords": [], "group_types": [], "target_accounts": [], "limit": 20, "reasoning": "AI returned no valid plan"}
        except Exception as e:
            self.logger.error(f"Failed to generate discovery plan: {e}")
            return {"keywords": [], "group_types": [], "target_accounts": [], "limit": 20, "reasoning": f"Error: {e}"}


