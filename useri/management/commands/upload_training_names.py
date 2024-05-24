import pandas as pd
from django.core.management.base import BaseCommand
from useri.models import TrainingProgramme

class Command(BaseCommand):
    help = 'Upload training names from an Excel file'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Path to the Excel file containing training names')

    def handle(self, *args, **kwargs):
        excel_file = kwargs['excel_file']
        df = pd.read_excel(excel_file)

        for index, row in df.iterrows():
            title = row['PROGRAMME TITLE']
            TrainingProgramme.objects.create(title=title)
            self.stdout.write(self.style.SUCCESS(f'Successfully added: {title}'))

        self.stdout.write(self.style.SUCCESS('All training names have been uploaded successfully'))
