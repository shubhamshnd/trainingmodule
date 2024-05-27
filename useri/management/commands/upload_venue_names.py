import pandas as pd
from django.core.management.base import BaseCommand
from useri.models import VenueMaster  # replace 'yourapp' with the name of your app

class Command(BaseCommand):
    help = 'Upload venue names from an Excel file'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Path to the Excel file containing venue names')

    def handle(self, *args, **kwargs):
        excel_file = kwargs['excel_file']
        df = pd.read_excel(excel_file)

        for index, row in df.iterrows():
            name = row['NAME']  # Adjust the column name to match the Excel file
            VenueMaster.objects.create(name=name)
            self.stdout.write(self.style.SUCCESS(f'Successfully added: {name}'))

        self.stdout.write(self.style.SUCCESS('All venue names have been uploaded successfully'))