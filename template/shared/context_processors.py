from django.conf import settings


def site_name(request):
    """Expõe settings.SITE_NAME aos templates: marca em navbar, títulos e rodapé."""
    return {'site_name': settings.SITE_NAME}
