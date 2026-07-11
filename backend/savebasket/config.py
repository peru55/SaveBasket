from django.core.exceptions import ImproperlyConfigured


REQUIRED_PRODUCTION_SETTINGS = (
    "SECRET_KEY",
    "ALLOWED_HOSTS",
    "SCRAPER_API_KEY",
    "CORS_ALLOWED_ORIGINS",
)


def split_env_list(value):
    """Return a trimmed list from a comma-separated environment value."""
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def validate_production_settings(debug, values):
    """Reject incomplete production configuration without exposing values."""
    if debug:
        return

    missing = [name for name in REQUIRED_PRODUCTION_SETTINGS if not values.get(name)]
    if missing:
        names = ", ".join(missing)
        raise ImproperlyConfigured(
            f"Missing required production settings: {names}. See docs/deployment.md."
        )
