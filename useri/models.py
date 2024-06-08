from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Role(models.Model):
    ROLE_CHOICES = (
        ('User', 'User'),
        ('Maker', 'Maker'),
        ('Checker', 'Checker'),
        ('HOD', 'HOD'),
    )

    name = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    # Field to use as username
    username = models.CharField(max_length=20, unique=True)  # Assuming EMPLOYEE ID is unique

    # Fields from MSSQL attendance database
    employee_id = models.CharField(max_length=20)
    employee_name = models.CharField(max_length=255)
    gender = models.CharField(max_length=10)
    date_of_birth = models.DateField(null=True, blank=True)
    blood_group = models.CharField(max_length=10, blank=True)
    marital_status = models.CharField(max_length=20, blank=True)
    weight = models.FloatField(default=0)
    height = models.FloatField(default=0)
    date_of_joining = models.DateField(null=True, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    grade = models.CharField(max_length=20, blank=True)
    work_order_no = models.CharField(max_length=20, blank=True)
    work_order_expiry_date = models.DateField(null=True, blank=True)
    item_code = models.CharField(max_length=20, blank=True)
    contractor_name = models.CharField(max_length=100, blank=True)
    sub_contractor_name = models.CharField(max_length=100, blank=True)
    under_sub_contractor_name = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=50, blank=True)
    pf_code = models.CharField(max_length=20, blank=True)
    uan_no_pf = models.CharField(max_length=20, blank=True)
    pf_no = models.CharField(max_length=20, blank=True)
    pan_no = models.CharField(max_length=20, blank=True)
    lic_policy_no = models.CharField(max_length=20, blank=True)
    passport_no = models.CharField(max_length=20, blank=True)
    esi_no = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    pin_code = models.CharField(max_length=10, blank=True)
    taluka = models.CharField(max_length=50, blank=True)
    district = models.CharField(max_length=50, blank=True)
    state = models.CharField(max_length=50, blank=True)
    per_address = models.TextField(blank=True)
    per_pin_code = models.CharField(max_length=10, blank=True)
    per_taluka = models.CharField(max_length=50, blank=True)
    per_district = models.CharField(max_length=50, blank=True)
    per_state = models.CharField(max_length=50, blank=True)
    poi = models.CharField(max_length=50, blank=True)
    poino = models.CharField(max_length=50, blank=True)
    poa = models.CharField(max_length=50, blank=True)
    poano = models.CharField(max_length=50, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    branch_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    selected = models.BooleanField(default=False)
    
    can_assign_trainings = models.BooleanField(default=False)
    is_maker = models.BooleanField(default=False)
    is_checker = models.BooleanField(default=False)

    # Foreign key to Role model
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    # Many-to-many relationship with Department
    departments = models.ManyToManyField('Department', related_name='department_members', blank=True)

    # Specify unique related_name for groups and user_permissions
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        related_name='customuser_set',
        related_query_name='customuser',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        related_name='customuser_set',
        related_query_name='customuser',
    )

    def __str__(self):
        return f"{self.employee_name} - {self.username}"


class Department(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='sub_departments')
    head = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL, related_name='headed_departments')
    members = models.ManyToManyField(CustomUser, related_name='user_departments', blank=True)

    def __str__(self):
        return self.name


class TrainingProgramme(models.Model):
    title = models.CharField(max_length=255)
    validity = models.IntegerField(default=2)  # Validity in years

    def __str__(self):
        return self.title


class VenueMaster(models.Model):
    VENUE_TYPE_CHOICES = (
        ('Classroom', 'Classroom'),
        ('On Job', 'On Job'),
        ('External', 'External'),
        ('Online', 'Online'),
    )

    name = models.CharField(max_length=255)
    venue_type = models.CharField(max_length=20, choices=VENUE_TYPE_CHOICES, default='Classroom')

    def __str__(self):
        return self.name


class Status(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class RequestTraining(models.Model):
    custom_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    training_programme = models.ForeignKey(TrainingProgramme, null=True, blank=True, on_delete=models.SET_NULL)
    other_training = models.CharField(max_length=255, blank=True)
    user_comment = models.TextField(blank=True)
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True)
    request_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    final_approval_timestamp = models.DateTimeField(null=True, blank=True)  # Track the final approval

    def __str__(self):
        return f"Request by {self.custom_user.username} for {self.training_programme if self.training_programme else self.other_training}"


class Approval(models.Model):
    request_training = models.ForeignKey(RequestTraining, on_delete=models.CASCADE, related_name='approvals')
    approver = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    comment = models.TextField(blank=True)
    approval_timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Approval by {self.approver.username} for request {self.request_training.id}"


class HODTrainingAssignment(models.Model):
    hod_user = models.ForeignKey(CustomUser, related_name='assignments_by_hod', on_delete=models.CASCADE)
    assigned_user = models.ForeignKey(CustomUser, related_name='assigned_trainings_hod', on_delete=models.CASCADE)
    training_programme = models.ForeignKey(TrainingProgramme, null=True, blank=True, on_delete=models.SET_NULL)
    other_training = models.CharField(max_length=255, blank=True)
    hod_comment = models.TextField(blank=True)
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True)
    assignment_date = models.DateTimeField(auto_now_add=True)
    checker_comment = models.TextField(blank=True)
    checker_approval_timestamp = models.DateTimeField(null=True, blank=True)
    hod_approval_timestamp = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.status = Status.objects.get(name='HODapproved')
            self.hod_approval_timestamp = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Assignment for {self.assigned_user.employee_name} by {self.hod_user.employee_name}"


class TrainerMaster(models.Model):
    TRAINER_TYPE_CHOICES = (
        ('Internal', 'Internal'),
        ('External', 'External'),
    )

    trainer_type = models.CharField(max_length=10, choices=TRAINER_TYPE_CHOICES)
    custom_user = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL, related_name='trainings_conducted')
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100, blank=True)
    training_programmes = models.ManyToManyField(TrainingProgramme, related_name='trainers')

    def __str__(self):
        return f"{self.name} ({self.get_trainer_type_display()})"


class TrainingSession(models.Model):
    training_programme = models.ForeignKey(TrainingProgramme, on_delete=models.CASCADE, null=True, blank=True)
    custom_training_programme = models.CharField(max_length=255, blank=True)
    venue = models.ForeignKey(VenueMaster, on_delete=models.CASCADE, null=True, blank=True)
    trainer = models.ForeignKey(TrainerMaster, on_delete=models.CASCADE, null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    date = models.DateField(null=True, blank=True)
    from_time = models.TimeField(null=True, blank=True)
    to_time = models.TimeField(null=True, blank=True)
    online_training_link = models.URLField(blank=True, null=True)
    online_training_file = models.FileField(upload_to='online_training_files/', blank=True, null=True)
    deadline_to_complete = models.DateField(null=True, blank=True)
    selected_participants = models.ManyToManyField(CustomUser, related_name='selected_trainings', blank=True)

    def mark_as_completed(self):
        attendees = AttendanceMaster.objects.filter(training_session=self).values_list('custom_user', flat=True)
        if attendees.exists():
            self.selected_participants.set(attendees)
            self.save()

    @property
    def is_completed(self):
        return AttendanceMaster.objects.filter(training_session=self, custom_user__in=self.selected_participants.all()).exists()

    def __str__(self):
        return f"{self.training_programme.title if self.training_programme else self.custom_training_programme} at {self.venue.name if self.venue else 'Online'} by {self.trainer.name if self.trainer else 'N/A'}"

class AttendanceMaster(models.Model):
    custom_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    training_session = models.ForeignKey(TrainingSession, on_delete=models.CASCADE)
    attendance_date = models.DateField()

    def __str__(self):
        return f"Attendance for {self.custom_user.username} in session {self.training_session}"


class SuperiorAssignedTraining(models.Model):
    assigned_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='superior_assigned_trainings')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='superior_assigned_trainings')
    training_programme = models.ForeignKey(TrainingProgramme, on_delete=models.CASCADE, related_name='superior_assigned_trainings')
    other_training = models.CharField(max_length=255, blank=True)  # Add this field if not already present
    hod_comment = models.TextField(blank=True)  # Add this field if not already present

    def __str__(self):
        return f"{self.assigned_by} - {self.department}"
