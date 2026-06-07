from app.platforms.facebook.adapter import FacebookCamoufoxAdapter

# Backward-compat alias for code that previously imported the legacy
# FacebookAdapter (no Camoufox) from app.platforms.facebook.
FacebookAdapter = FacebookCamoufoxAdapter

__all__ = ["FacebookAdapter", "FacebookCamoufoxAdapter"]
