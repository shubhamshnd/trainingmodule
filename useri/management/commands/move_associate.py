from django.core.management.base import BaseCommand
from useri.models import CustomUser, Department

# Define department variance mappings
DEPARTMENT_VARIANCE = {
    'SAFETY': 'EHS',
    'HORTICULTURE': 'EHS',
    'CIVIL': 'PROJECTS-CIVIL',
    'DREDGING' : 'PROJECTS-CIVIL',
    'ELECTRICAL' : 'ELECTRICAL',
    'ADMINISTRATION' : 'HR & ADMIN',
    'FINANCE & ACCOUNTS' : 'FINANCE',
    'INFORMATION TECHNOLOGY' : 'INFORMATION TECHNOLOGY',
    'MECHANICAL' : 'MECHANICAL',
    'OPERATIONS' : 'OPERATIONS',
    'SECURITY' : 'SECURITY',
    # Add more mappings as required
}

class Command(BaseCommand):
    help = 'Update associates in the Department model based on work order numbers and department mappings'

    def handle(self, *args, **kwargs):
        # Query users with work order numbers
        users_with_work_order = CustomUser.objects.exclude(work_order_no='')

        for user in users_with_work_order:
            user_department = user.department.strip().upper()  # Normalize department name
            mapped_department = DEPARTMENT_VARIANCE.get(user_department, user_department)

            try:
                # Find the corresponding department
                department = Department.objects.get(name=mapped_department)
                department.associates.add(user)  # Add user to associates
                department.save()  # Save changes
                self.stdout.write(self.style.SUCCESS(f"Added {user.username} to {mapped_department} department."))
            except Department.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Department {mapped_department} does not exist for user {user.username}."))

        self.stdout.write(self.style.SUCCESS('Update associates process completed.'))