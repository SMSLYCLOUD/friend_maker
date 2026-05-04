from app.platforms.instagram import InstagramAdapter
from app.platforms.twitter import TwitterAdapter
from app.platforms.facebook import FacebookAdapter
from app.platforms.linkedin import LinkedInAdapter
from app.platforms.tiktok import TiktokAdapter
from app.platforms.substack import SubstackAdapter

def get_platform_adapter(platform_name, page):
    if platform_name == "instagram":
        return InstagramAdapter(page)
    elif platform_name == "twitter":
        return TwitterAdapter(page)
    elif platform_name == "facebook":
        return FacebookAdapter(page)
    elif platform_name == "linkedin":
        return LinkedInAdapter(page)
    elif platform_name == "tiktok":
        return TiktokAdapter(page)
    elif platform_name == "substack":
        return SubstackAdapter(page)
    else:
        raise ValueError(f"Unknown platform: {platform_name}")
