import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from useri.models import TrainingSession, TrainingApproval, CustomUser, Department
from datetime import timedelta, datetime
from django.db.models import Q , F , Max

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Log training sessions and their statuses'

    def add_arguments(self, parser):
        parser.add_argument('--head_id', type=int, help='ID of the head user')

    def handle(self, *args, **kwargs):
        head_id = kwargs.get('head_id')
        if not head_id:
            self.stderr.write(self.style.ERROR('Head ID is required'))
            return

        try:
            head_user = CustomUser.objects.get(pk=head_id)
        except CustomUser.DoesNotExist:
            self.stderr.write(self.style.ERROR('Head user does not exist'))
            return

        departments = Department.objects.filter(head=head_user)
        if not departments.exists():
            logger.info(f"User {head_user.username} is not head of any departments.")
            self.stdout.write(self.style.WARNING(f"User {head_user.username} is not head of any departments."))
            return

        logger.info(f"User {head_user.username} is head of the following departments: {[dept.name for dept in departments]}")

        training_sessions = TrainingSession.objects.filter(
            selected_participants__user_departments__in=departments
        ).distinct().order_by('-date', '-from_time')

        current_time = timezone.now()
        logger.info(f"Current time: {current_time}")
        
        for training in training_sessions:
            training_datetime = datetime.combine(training.date, training.from_time)
            if training_datetime.tzinfo is None:
                training_datetime = timezone.make_aware(training_datetime, timezone.get_current_timezone())

            is_past_training = training_datetime < current_time
            is_within_threshold = training_datetime - timedelta(hours=48) < current_time

            approved_by_head = TrainingApproval.objects.filter(training_session=training, head=head_user, approved=True).exists()

            status = "Approved" if approved_by_head else ("Pending" if not is_past_training else "Not Approved")

            logger.info(
                f"Training: {training.training_programme.title if training.training_programme else training.custom_training_programme}, "
                f"Date: {training.date}, From Time: {training.from_time}, To Time: {training.to_time}, "
                f"Finalized: {training.finalized}, Is Past Training: {is_past_training}, "
                f"Is Within Threshold: {is_within_threshold}, Status: {status}, Approved by Head: {approved_by_head}"
            )

            self.stdout.write(self.style.SUCCESS(
                f"Training: {training.training_programme.title if training.training_programme else training.custom_training_programme}, "
                f"Date: {training.date}, From Time: {training.from_time}, To Time: {training.to_time}, "
                f"Finalized: {training.finalized}, Is Past Training: {is_past_training}, "
                f"Is Within Threshold: {is_within_threshold}, Status: {status}, Approved by Head: {approved_by_head}"
            ))

            available_employees = CustomUser.objects.filter(user_departments__in=departments).distinct().exclude(id__in=training.selected_participants.values_list('id', flat=True))
            available_associates = CustomUser.objects.filter(associated_departments__in=departments).distinct().exclude(id__in=training.selected_participants.values_list('id', flat=True))
            nominated_employees = CustomUser.objects.filter(id__in=training.selected_participants.values_list('id', flat=True), user_departments__in=departments).distinct()
            nominated_associates = CustomUser.objects.filter(id__in=training.selected_participants.values_list('id', flat=True), associated_departments__in=departments).distinct()

            logger.info(f"Available Employees for training {training.id}: {[user.id for user in available_employees]}")
            logger.info(f"Nominated Employees for training {training.id}: {[user.id for user in nominated_employees]}")
            logger.info(f"Available Associates for training {training.id}: {[user.id for user in available_associates]}")
            logger.info(f"Nominated Associates for training {training.id}: {[user.id for user in nominated_associates]}")

            self.stdout.write(self.style.SUCCESS(f"Available Employees for training {training.id}: {[user.id for user in available_employees]}"))
            self.stdout.write(self.style.SUCCESS(f"Nominated Employees for training {training.id}: {[user.id for user in nominated_employees]}"))
            self.stdout.write(self.style.SUCCESS(f"Available Associates for training {training.id}: {[user.id for user in available_associates]}"))
            self.stdout.write(self.style.SUCCESS(f"Nominated Associates for training {training.id}: {[user.id for user in nominated_associates]}"))