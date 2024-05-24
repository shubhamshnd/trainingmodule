# In useri/management/commands/create_default_role.py

from django.core.management.base import BaseCommand
from useri.models import Role

class Command(BaseCommand):
    help = 'Create a default role if not exists'

    def handle(self, *args, **kwargs):
        # Check if the default role already exists
        default_role, created = Role.objects.get_or_create(name='User')
        
        if created:
            self.stdout.write(self.style.SUCCESS('Default role created successfully'))
        else:
            self.stdout.write(self.style.WARNING('Default role already exists'))
