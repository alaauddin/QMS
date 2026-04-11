from .models import SystemConfig

def branding(request):
    """
    Injects the system configuration (branding) into every template context.
    """
    return {
        'system_config': SystemConfig.get_config()
    }
