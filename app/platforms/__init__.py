from app.platforms.browser_use_adapter import BrowserUseAdapter

# Platforms that use Camoufox (anti-detection) instead of Browser Use
CAMOUFOX_PLATFORMS = {"tiktok", "facebook"}


def get_platform_adapter(platform_name, page=None):
    if platform_name.lower() in CAMOUFOX_PLATFORMS:
        if platform_name.lower() == "facebook":
            from app.platforms.facebook import FacebookCamoufoxAdapter
            return FacebookCamoufoxAdapter(platform=platform_name)
        from app.platforms.tiktok import TikTokCamoufoxAdapter
        return TikTokCamoufoxAdapter(platform=platform_name)
    return BrowserUseAdapter(platform=platform_name)
