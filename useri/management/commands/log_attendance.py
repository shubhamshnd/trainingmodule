from django.core.management.base import BaseCommand
from django.utils import timezone
from useri.models import TrainingSession, AttendanceMaster, TrainingApproval, CustomUser

class Command(BaseCommand):
    help = 'Move AttendanceMaster participants to the approved training for each department head'

    def handle(self, *args, **kwargs):
        training_sessions = TrainingSession.objects.filter(finalized=True, date__lt=timezone.now().date())
        
        for training in training_sessions:
            attendees = AttendanceMaster.objects.filter(training_session=training).values_list('custom_user', flat=True)
            if attendees.exists():
                training.selected_participants.set(attendees)
                training.save()

                # Ensure TrainingApproval exists
                if not TrainingApproval.objects.filter(training_session=training).exists():
                    approval = TrainingApproval.objects.create(
                        training_session=training,
                        head=training.created_by,
                        department=training.created_by.department_set.first(),  # Assuming the user is head of the department
                        approved=True,
                        approval_timestamp=timezone.now(),
                    )
                    approval.selected_participants.set(training.selected_participants.all())
                    approval.save()
        
        self.stdout.write(self.style.SUCCESS('Successfully moved attendance participants to approved training'))
