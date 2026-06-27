import logging
from typing import List, Dict, Any, Optional

class CampaignPlanner:
    def __init__(self, ai_manager=None):
        self.ai = ai_manager
        self.logger = logging.getLogger("CampaignPlanner")

    async def _generate_with_provider(self, prompt: str) -> str:
        """Use ProviderManager fallback chain — try each provider until one succeeds."""
        from app.llm.provider_manager import get_provider_manager
        import httpx

        pm = get_provider_manager()
        max_attempts = pm.provider_count

        for attempt in range(max_attempts):
            provider = pm.get_next_provider()
            if not provider:
                self.logger.error("No LLM providers available for planner")
                return ""

            config = provider.config
            self.logger.info(f"Planner using provider: {config.name} (attempt {attempt + 1}/{max_attempts})")

            payload = {
                "model": config.model,
                "messages": [{"role": "user", "content": prompt}]
            }
            headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json"
            }

            try:
                async with httpx.AsyncClient(timeout=300) as client:
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
                    elif r.status_code == 429:
                        retry_after = int(r.headers.get("retry-after", 60))
                        self.logger.warning(f"Planner: {config.name} rate-limited (429), retrying next provider")
                        pm.mark_rate_limited(config.name, retry_after=retry_after)
                    else:
                        self.logger.error(f"Planner LLM error ({r.status_code}): {r.text[:200]}")
                        pm.mark_failed(config.name)
            except Exception as e:
                self.logger.error(f"Planner LLM failed ({config.name}): {e}")
                pm.mark_failed(config.name)

        self.logger.error("All planner LLM providers exhausted")
        return ""

    async def generate_discovery_plan(self, persona_instructions: str, platform: str, bot_instructions: str = "", ref_images: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Extract the specific targets and strategy from the user's instruction.
        Do NOT invent extra accounts — only use what is explicitly mentioned.
        """
        constraints = ""
        if bot_instructions:
            constraints = f"\n\nCONSTRAINTS (must follow):\n{bot_instructions}"

        # Detect strategy from instructions
        instructions_lower = persona_instructions.lower()
        strategy = "comment_engage"
        if any(phrase in instructions_lower for phrase in [
            "follow back", "followback", "follow them first",
            "wait for follow back", "dm when they follow",
            "only dm if they follow", "follow then dm",
        ]):
            strategy = "follow_back_dm"
            self.logger.info(f"Detected follow_back_dm strategy from instructions")

        prompt = f"""
Parse this instruction and extract targets. Return JSON only.

INSTRUCTION: "{persona_instructions}"
PLATFORM: {platform}

RULES:
- Only include accounts LITERALLY named in the instruction
- "followers of X" → target_accounts = ["X"]
- "DM commenters of X" or "engage with commenters of X" → target_accounts = ["X"]
- "message people interested in Y" → keywords = ["Y"]
- Do NOT add related, similar, or popular accounts

RETURN:
{{"target_accounts": ["account1"], "keywords": [], "group_types": [], "limit": 20, "strategy": "{strategy}"}}
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


