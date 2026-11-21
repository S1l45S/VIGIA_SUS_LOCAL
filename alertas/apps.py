from django.apps import AppConfig


class AlertasConfig(AppConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"
    name = "alertas"
    verbose_name = "Alertas epidemiológicos"
