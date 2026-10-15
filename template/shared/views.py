from django.db import Error, connection
from django.http import JsonResponse
from django.views import View


class HealthView(View):
    """Endpoint de saúde: verifica a conectividade com o banco de dados."""

    def get(self, request, *args, **kwargs):
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
        except Error:
            return JsonResponse({'status': 'error'}, status=500)
        return JsonResponse({'status': 'ok'})
