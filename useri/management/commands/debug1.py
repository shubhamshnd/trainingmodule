import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from useri.models import TrainingSession, TrainingApproval, CustomUser
from django.db.models import Q , F , Max
from datetime import timedelta, datetime

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'List all trainings for the head and their departments\' members and associates'

    def add_arguments(self, parser):
        parser.add_argument('head_id', type=int, help='The ID of the head to list trainings for')

    def handle(self, *args, **kwargs):
        head_id = kwargs['head_id']
        try:
            head = CustomUser.objects.get(id=head_id)
        except CustomUser.DoesNotExist:
            self.stdout.write(self.style.ERROR('Head with ID {} does not exist'.format(head_id)))
            return

        departments = head.headed_departments.all()
        if not departments.exists():
            self.stdout.write(self.style.WARNING('User {} is not head of any departments.'.format(head.username)))
            return

        self.stdout.write(self.style.SUCCESS('User {} is head of the following departments: {}'.format(
            head.username, [dept.name for dept in departments]
        )))

        current_time = timezone.now()
        training_sessions = TrainingSession.objects.filter(
            Q(selected_participants__user_departments__in=departments) |
            Q(trainingapproval__head=head)
        ).distinct().order_by('-date', '-from_time')

        if not training_sessions.exists():
            self.stdout.write(self.style.WARNING('No training sessions found for the head and their departments.'))
            return

        self.stdout.write(self.style.SUCCESS('Listing training sessions:'))
        for training in training_sessions:
            approval = TrainingApproval.objects.filter(training_session=training, head=head).first()
            if approval:
                selected_participants = approval.selected_participants.all()
                removed_participants = approval.removed_participants.all()
            else:
                selected_participants = CustomUser.objects.none()
                removed_participants = CustomUser.objects.none()

            original_participants = training.selected_participants.filter(
                Q(user_departments__in=departments) | Q(associated_departments__in=departments)
            )

            training_datetime = datetime.combine(training.date, training.from_time)
            if training_datetime.tzinfo is None:
                training_datetime = timezone.make_aware(training_datetime, timezone.get_current_timezone())

            is_past_training = training_datetime < current_time
            is_within_threshold = training_datetime - timedelta(hours=48) < current_time
            approved_by_head = approval and approval.approved
            status = "Approved" if approved_by_head else ("Pending" if not is_past_training else "Not Approved")

            self.stdout.write('Training ID: {}'.format(training.id))
            self.stdout.write('Title: {}'.format(training.training_programme.title if training.training_programme else training.custom_training_programme))
            self.stdout.write('Date: {}'.format(training.date))
            self.stdout.write('From Time: {}'.format(training.from_time))
            self.stdout.write('To Time: {}'.format(training.to_time))
            self.stdout.write('Finalized: {}'.format(training.finalized))
            self.stdout.write('Status: {}'.format(status))
            self.stdout.write('Approved by Head: {}'.format(approved_by_head))

            self.stdout.write('Original Participants: {}'.format(', '.join([str(user.username) for user in original_participants])))
            self.stdout.write('Selected Participants in Approval: {}'.format(', '.join([str(user.username) for user in selected_participants])))
            self.stdout.write('Removed Participants in Approval: {}'.format(', '.join([str(user.username) for user in removed_participants])))
            self.stdout.write('---')

        logger.info("Listed trainings for head ID {}".format(head_id))