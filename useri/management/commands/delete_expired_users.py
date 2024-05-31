from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from useri.models import CustomUser  # Adjust the import based on your app name

class Command(BaseCommand):
    help = 'Deletes all users with work order expiry date before today'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        expired_users = CustomUser.objects.filter(work_order_expiry_date__lt=today)
        num_expired_users = expired_users.count()

        if num_expired_users == 0:
            self.stdout.write(self.style.SUCCESS('No users found with expired work orders.'))
            return

        self.stdout.write(f'Number of users with expired work orders: {num_expired_users}')
        self.stdout.write('Do you want to delete these users? (yes/no)')
        confirm = input()

        if confirm.lower() == 'yes':
            expired_users.delete()
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted {num_expired_users} users.'))
        else:
            self.stdout.write(self.style.WARNING('Operation cancelled.'))
