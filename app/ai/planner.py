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
        TASK: Parse this instruction and extract ONLY what is literally written in it.

        INSTRUCTION: "{persona_instructions}"
        PLATFORM: {platform}{constraints}

        CRITICAL RULES — VIOLATION IS FAILURE:
        1. If the instruction says "followers of X" → target_accounts = ["X"] (ONE account, NOT more)
        2. If the instruction says "message people interested in Y" → keywords = ["Y"]
        3. NEVER add accounts that are "related to", "similar to", "fans of", or "associated with" the target
        4. NEVER add influencer accounts, celebrity accounts, or competitor accounts
        5. NEVER add accounts just because they are "popular" or "well-known" in the same space
        6. The ONLY accounts allowed in target_accounts are the ones LITERALLY NAMED in the instruction
        7. If the instruction names 1 account, target_accounts has EXACTLY 1 item
        8. If the instruction names 3 accounts, target_accounts has EXACTLY 3 items

        EXAMPLES:
        - "message the followers of donald trump on tiktok" → target_accounts: ["realdonaldtrump"] (ONE)
        - "message followers of elonmusk and billgates on twitter" → target_accounts: ["elonmusk", "billgates"] (TWO)
        - "find people interested in crypto on instagram" → keywords: ["crypto"]
        - "message members of python community on linkedin" → group_types: ["python community"]

        WRONG (DO NOT DO THIS):
        - "message the followers of donald trump" → target_accounts: ["realdonaldtrump", "charliekirk11", "seanhannity"] ❌
        - "message the followers of donald trump" → target_accounts: ["realdonaldtrump", "foxnews", "donaldtrumpjr"] ❌

        RIGHT (DO THIS):
        - "message the followers of donald trump" → target_accounts: ["realdonaldtrump"] ✅

        RETURN JSON:
        {{
            "target_accounts": ["only_accounts_literally_named_in_instruction"],
            "keywords": ["only_keywords_literally_named_in_instruction"],
            "group_types": ["only_groups_literally_named_in_instruction"],
            "limit": 20,
            "reasoning": "What was extracted and why (must reference specific words from the instruction)."
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


