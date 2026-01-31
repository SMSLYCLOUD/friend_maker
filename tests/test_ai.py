import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.ai.ollama_manager import OllamaManager
from app.ai.classifier import ProfileClassifier
from app.ai.generator import MessageGenerator

@pytest.fixture
def mock_manager():
    manager = OllamaManager()
    manager.generate = AsyncMock()
    return manager

@pytest.mark.asyncio
async def test_classifier(mock_manager):
    # Mock AI response
    mock_manager.generate.return_value = """
    {
        "niche": "Tech",
        "account_type": "Personal",
        "match_score": 0.85,
        "reasoning": "Good match"
    }
    """

    classifier = ProfileClassifier(mock_manager)
    profile = {"username": "dev_jules", "bio": "Python Dev", "followers": 100}

    result = await classifier.classify(profile)

    assert result["niche"] == "Tech"
    assert result["match_score"] == 0.85
    mock_manager.generate.assert_called_once()

@pytest.mark.asyncio
async def test_classifier_json_cleanup(mock_manager):
    # Mock AI response with markdown
    mock_manager.generate.return_value = """
    ```json
    {
        "niche": "Art",
        "match_score": 0.1
    }
    ```
    """

    classifier = ProfileClassifier(mock_manager)
    result = await classifier.classify({"username": "artist"})

    assert result["niche"] == "Art"

@pytest.mark.asyncio
async def test_generator(mock_manager):
    mock_manager.generate.return_value = "Hey! Loved your post about Python."

    generator = MessageGenerator(mock_manager)
    msg = await generator.generate_dm({"username": "u"}, template="Hi")

    assert "Loved your post" in msg
