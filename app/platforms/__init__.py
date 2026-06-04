from app.platforms.skyvern_adapter import SkyvernAdapter

# Platforms that use Camoufox (anti-detection) instead of Skyvern
CAMOUFOX_PLATFORMS = {"tiktok", "facebook"}

def get_platform_adapter(platform_name, page=None):
    if platform_name.lower() in CAMOUFOX_PLATFORMS:
        if platform_name.lower() == "facebook":
            from app.platforms.facebook_camoufox_adapter import FacebookCamoufoxAdapter
            return FacebookCamoufoxAdapter(platform=platform_name)
        from app.platforms.camoufox_adapter import CamoufoxAdapter
        return CamoufoxAdapter(platform=platform_name)
    return SkyvernAdapter(platform=platform_name)
