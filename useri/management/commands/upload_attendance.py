import pandas as pd
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.db import IntegrityError
import logging
from useri.models import CustomUser, TrainingProgramme, VenueMaster, TrainerMaster, TrainingSession, AttendanceMaster

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Command(BaseCommand):
    help = 'Uploads attendance data from an Excel file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='The path to the Excel file containing attendance data')

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

        # Fetch all CustomUser usernames
        existing_users = CustomUser.objects.values_list('username', flat=True)
        existing_usernames = set(existing_users)  # For quick lookup

        # Log the start of the process
        logging.info("Starting attendance data upload process...")

        # Function to convert time format
        def convert_time(time_str):
            for fmt in ('%I:%M %p', '%H:%M:%S', '%I:%M%p'):
                try:
                    return pd.to_datetime(time_str, format=fmt).time()
                except ValueError:
                    continue
            raise ValueError(f"time data '{time_str}' does not match any format")

        # Loop through each row in the dataframe
        for index, row in attendance_df.iterrows():
            empl_no = str(row['EMPL NO']).strip()
            
            # Check if the user exists
            if empl_no not in existing_usernames:
                logging.warning(f"User with EMPL NO {empl_no} not found. Skipping row {index + 1}.")
                continue  # Skip this row if user does not exist
            
            # Fetch or create the TrainingProgramme
            programme_title = row['PROGRAMME TITLE'].strip()
            training_programme, created = TrainingProgramme.objects.get_or_create(title=programme_title)
            if created:
                logging.info(f"Created new TrainingProgramme: {programme_title}")
            
            # Fetch or create the VenueMaster
            venue_name = row['VENUE']
            if isinstance(venue_name, str):
                venue_name = venue_name.strip()
            else:
                logging.warning(f"Invalid venue name in row {index + 1}. Skipping row.")
                continue
            
            venue, created = VenueMaster.objects.get_or_create(name=venue_name, defaults={'venue_type': 'Classroom'})  # Default to Classroom
            if created:
                logging.info(f"Created new VenueMaster: {venue_name}")
            
            # Determine if the trainer is internal or external
            faculty_name = row['FACULTY'].strip()
            trainer_type = 'Internal' if faculty_name in existing_usernames else 'External'
            custom_user = CustomUser.objects.filter(username=faculty_name).first() if trainer_type == 'Internal' else None
            
            # Fetch or create the TrainerMaster
            trainer, created = TrainerMaster.objects.get_or_create(
                name=faculty_name, 
                defaults={'trainer_type': trainer_type, 'custom_user': custom_user}
            )
            if created:
                logging.info(f"Created new TrainerMaster: {faculty_name} as {trainer_type}")
            
            # Fetch or create the TrainingSession
            try:
                from_time = convert_time(row['FROM'])
                to_time = convert_time(row['TO'])
            except ValueError as e:
                logging.error(f"Error parsing time in row {index + 1}: {e}")
                continue

            session_date = parse_date(str(row['DATE']).split(' ')[0])
            
            training_session, created = TrainingSession.objects.get_or_create(
                training_programme=training_programme,
                venue=venue,
                trainer=trainer,
                date=session_date,
                from_time=from_time,
                to_time=to_time,
                defaults={
                    'created_by': CustomUser.objects.first(),  # Assuming the first user created this session
                    'created_at': timezone.now()
                }
            )
            if created:
                logging.info(f"Created new TrainingSession on {session_date} from {from_time} to {to_time}")
            
            # Check for existing attendance record
            attendance_exists = AttendanceMaster.objects.filter(
                custom_user=CustomUser.objects.get(username=empl_no),
                training_session=training_session,
                attendance_date=session_date
            ).exists()

            if not attendance_exists:
                # Create the AttendanceMaster entry
                try:
                    AttendanceMaster.objects.create(
                        custom_user=CustomUser.objects.get(username=empl_no),
                        training_session=training_session,
                        attendance_date=session_date
                    )
                    logging.info(f"Created attendance record for user {empl_no} in session on {session_date}")
                except IntegrityError:
                    logging.warning(f"Duplicate attendance record for user {empl_no} in session on {session_date}. Skipping entry.")
                    continue

            # Add the user to selected participants if not already added
            training_session.selected_participants.add(CustomUser.objects.get(username=empl_no))

            # Set the attendance_frozen field to True
            training_session.attendance_frozen = True
            training_session.save()

        # Log the end of the process
        logging.info("Attendance data upload process completed successfully.")
