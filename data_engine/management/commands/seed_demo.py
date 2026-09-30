from django.core.management.base import BaseCommand

from services.demo_data import seed


class Command(BaseCommand):
    help = "Create the synthetic DEMO dataset (users, hotspots, readings, reports, alerts)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing demo data first")

    def handle(self, *args, **opts):
        seed(reset=opts["reset"], stdout=self.stdout)
