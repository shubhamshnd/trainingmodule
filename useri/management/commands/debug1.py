from django.core.management.base import BaseCommand
from django.utils import timezone
from useri.models import TrainingSession, CustomUser, Department
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetch training sessions for department heads'

    def handle(self, *args, **kwargs):
        current_time = timezone.now()
        heads = CustomUser.objects.filter(departments__head__isnull=False).distinct()

        if not heads.exists():
            self.stdout.write("No department heads found.")
            logger.info("No department heads found.")
            return
        
        for head in heads:
            self.stdout.write(f"\nFetching training sessions for head: {head.username}")
            logger.info(f"Fetching training sessions for head: {head.username}")
            
            departments = Department.objects.filter(head=head)
            if not departments.exists():
                self.stdout.write(f"No departments found for head: {head.username}")
                logger.info(f"No departments found for head: {head.username}")
                continue

            members = CustomUser.objects.filter(user_departments__in=departments).distinct()
            associates = CustomUser.objects.filter(associated_departments__in=departments).distinct()

            training_sessions = TrainingSession.objects.filter(
                selected_participants__in=members | associates,
                date__gte=current_time.date()
            ).distinct()

            if training_sessions.exists():
                for session in training_sessions:
                    self.stdout.write(f"Training: {session.training_programme.title if session.training_programme else session.custom_training_programme}, Date: {session.date}, Venue: {session.venue.name if session.venue else 'Online'}")
                    logger.info(f"Training: {session.training_programme.title if session.training_programme else session.custom_training_programme}, Date: {session.date}, Venue: {session.venue.name if session.venue else 'Online'}")
            else:
                self.stdout.write(f"No upcoming training sessions found for head: {head.username}")
                logger.info(f"No upcoming training sessions found for head: {head.username}")
