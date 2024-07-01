from django.core.management.base import BaseCommand
from useri.models import TrainingSession, TrainingApproval, DepartmentCount
import logging

# Configure logger
logger = logging.getLogger(__name__)



class Command(BaseCommand):
    help = 'Logs all created trainings, their types, selected participants, or department counts and the heads associated with them'

    def handle(self, *args, **kwargs):
        trainings = TrainingSession.objects.all()
        if not trainings.exists():
            self.stdout.write("No training sessions found.")
            return

        for training in trainings:
            training_type = "Needs Nomination" if training.needs_hod_nomination else "Pre-assigned"
            self.stdout.write(f"Training: {training}")
            self.stdout.write(f"Type: {training_type}")

            if training_type == "Pre-assigned":
                selected_participants = training.selected_participants.all()
                self.stdout.write("Selected Participants:")
                for participant in selected_participants:
                    self.stdout.write(f" - {participant.employee_name} - {participant.username}")
            else:
                department_counts = DepartmentCount.objects.filter(training_session=training)
                self.stdout.write("Department Counts:")
                for dept_count in department_counts:
                    head_name = dept_count.head.employee_name if dept_count.head else "N/A"
                    self.stdout.write(f" - Department: {dept_count.department.name}, Head: {head_name}")
                    self.stdout.write(f"   Required Employees: {dept_count.required_employees}")
                    self.stdout.write(f"   Required Associates: {dept_count.required_associates}")

            approvals = TrainingApproval.objects.filter(training_session=training)
            self.stdout.write("Heads Associated with Approvals:")
            for approval in approvals:
                self.stdout.write(f" - Head: {approval.head.employee_name}")

            self.stdout.write("\n")

        self.stdout.write(self.style.SUCCESS('Successfully logged all trainings.'))