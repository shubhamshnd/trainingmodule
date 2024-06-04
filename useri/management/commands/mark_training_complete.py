# myapp/management/commands/mark_trainings_complete.py
from django.core.management.base import BaseCommand
from useri.models import TrainingSession, AttendanceMaster

class Command(BaseCommand):
    help = 'Mark training sessions as complete and add attendees to the selected participants'

    def handle(self, *args, **kwargs):
        training_sessions = TrainingSession.objects.all()

        for training in training_sessions:
            attendees = AttendanceMaster.objects.filter(training_session=training).values_list('custom_user', flat=True)
            if attendees.exists():
                training.selected_participants.set(attendees)
                training.save()
                self.stdout.write(f'Marked training {training.id} as completed with {attendees.count()} attendees.')

        self.stdout.write(self.style.SUCCESS('Successfully marked trainings as completed.'))