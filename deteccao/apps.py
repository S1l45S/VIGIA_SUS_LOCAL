from django.apps import AppConfig


class DeteccaoConfig(AppConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"
    name = "deteccao"
    verbose_name = "Detecção estatística"
