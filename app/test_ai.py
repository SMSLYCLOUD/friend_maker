import asyncio
import logging
import sys
import os

# Add parent directory to sys.path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.openrouter_manager import OpenRouterManager
from app.ai.generator import MessageGenerator
from app.config import settings

async def test_ai():
    logging.basicConfig(level=logging.INFO)
    manager = OpenRouterManager()
    
    print(f"Testing OpenRouter with model: {settings.OPENROUTER_MODEL}")
    print(f"API Key set: {'Yes' if settings.OPENROUTER_API_KEY else 'No'}")
    
    generator = MessageGenerator(manager)
    
    profile = {
        "username": "tech_guru_2024",
        "bio": "Building the future of AI and robotics. Coffee enthusiast.",
        "niche": "Technology/AI"
    }
    
    instructions = "Talk like a robotic assistant from a 1980s sci-fi movie."
    template = "I am interested in your robotics work."
    
    print("\nGenerating message...")
    try:
        message = await generator.generate_dm(profile, template, instructions)
        if message:
            print(f"\nAI Response:\n{'-'*20}\n{message}\n{'-'*20}")
        else:
            print("\nAI Response: (Empty - Check API Key or Model Settings)")
    except Exception as e:
        print(f"AI Generation Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_ai())
