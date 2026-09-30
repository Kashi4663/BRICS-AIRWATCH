import json

from django.core.management.base import BaseCommand

from services.bigquery_service import schema_json


class Command(BaseCommand):
    help = "Print BigQuery table schemas (JSON) for the AIRWATCH dataset."

    def handle(self, *args, **opts):
        self.stdout.write(json.dumps(schema_json(), indent=2))
