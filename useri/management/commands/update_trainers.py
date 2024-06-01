import pandas as pd
from django.core.management.base import BaseCommand
import logging
from useri.models import CustomUser, TrainerMaster

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Command(BaseCommand):
    help = 'Updates trainer information by marking them as internal or external'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='The path to the Excel file containing trainer data')

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']
        
        # Load the uploaded Excel file
        try:
            attendance_df = pd.read_excel(file_path)
        except Exception as e:
            logging.error(f"Error reading Excel file: {e}")
            return

        # Print the column names to verify
        logging.info(f"Excel Columns: {attendance_df.columns.tolist()}")

        # Log the start of the process
        logging.info("Starting trainer information update process...")

        # Loop through each row in the dataframe
        for index, row in attendance_df.iterrows():
            # Determine if the trainer is internal or external
            faculty_name = row['FACULTY'].strip()
            custom_user = CustomUser.objects.filter(employee_name=faculty_name).first()
            trainer_type = 'Internal' if custom_user else 'External'

            # Fetch or update the TrainerMaster
            try:
                trainer = TrainerMaster.objects.get(name=faculty_name)
                trainer.trainer_type = trainer_type
                trainer.custom_user = custom_user
                trainer.save()
                logging.info(f"Updated TrainerMaster: {faculty_name} to {trainer_type}")
            except TrainerMaster.DoesNotExist:
                TrainerMaster.objects.create(
                    name=faculty_name,
                    trainer_type=trainer_type,
                    custom_user=custom_user
                )
                logging.info(f"Created new TrainerMaster: {faculty_name} as {trainer_type}")

        # Log the end of the process
        logging.info("Trainer information update process completed successfully.")
