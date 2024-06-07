from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CustomUser, RequestTraining, Status, HODTrainingAssignment ,  VenueMaster, TrainerMaster , TrainingSession , AttendanceMaster , Approval ,SuperiorAssignedTraining , Department
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse
from .forms import RequestTrainingForm, TrainingRequestApprovalForm, CheckerApprovalForm ,  TrainingCreationForm, ExternalTrainerForm ,  TrainingRequestForm , SuperiorAssignmentForm
import logging
from django.utils import timezone
from itertools import chain
from collections import defaultdict
from django.db.models import Count
logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler()])
from django.db.models import Q
from datetime import timedelta
from django.db.models import F
def easter_egg_page(request):
    context = {
        'range_170': range(170),
        'range_10': range(10),
    }
    return render(request, 'easter_egg.html', context)
logger = logging.getLogger(__name__)

@csrf_protect
@login_required
def home(request):
    user = request.user

    # Determine if the user is a superior (head of a department or sub-department)
    user_is_superior = user.headed_departments.exists()
    is_maker = user.is_maker
    is_checker = user.is_checker

    # Determine the highest priority role
    if is_checker:
        role = 'checker'
    elif is_maker:
        role = 'maker'
    elif user_is_superior:
        role = 'superior'
    else:
        role = 'member'

    context = {
        'role': role,
    }

    response = render(request, 'home.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password')
    else:
        storage = messages.get_messages(request)
        for _ in storage:
            pass

    return render(request, 'login.html', {'username': request.POST.get('username', '')})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def request_training(request):
    user = request.user
    if request.method == 'POST':
        form = RequestTrainingForm(request.POST)
        if form.is_valid():
            training_request = form.save(commit=False)
            training_request.custom_user = user
            training_request.status_id = 1  # Assuming 1 is the ID for the initial status
            training_request.save()

            logger.info(f"Training request {training_request.id} saved successfully.")

            # Get the superiors for the user's departments
            user_departments = user.departments.all()
            if not user_departments:
                messages.error(request, "You are not associated with any departments.")
                return redirect('request_training')

            logger.info(f"User {user.username} is in departments: {[dept.name for dept in user_departments]}")

            superiors = CustomUser.objects.filter(
                headed_departments__in=user_departments
            ).distinct()
            logger.info(f"Found superiors: {[sup.username for sup in superiors]}")

            if superiors.count() == 1:
                # If there's only one superior, directly assign the request
                superior = superiors.first()
                Approval.objects.create(
                    request_training=training_request,
                    approver=superior,
                    comment="Auto-assigned to superior",
                    approval_timestamp=timezone.now()
                )
                messages.success(request, "Your training request has been submitted successfully.")
                return redirect('request_training')
            elif superiors.count() > 1:
                # If there are multiple superiors, render the selection in the same template
                request.session['training_request_id'] = training_request.id
                return render(request, 'request_training.html', {
                    'form': form,
                    'user_requests': RequestTraining.objects.filter(custom_user=user).order_by('-request_date'),
                    'superiors': superiors,
                    'select_superior': True  # Indicate that we need to select a superior
                })
            else:
                messages.error(request, "No superior found for your departments.")
                training_request.delete()
                return redirect('request_training')
        else:
            logger.error(f"Form is not valid: {form.errors}")
    else:
        form = RequestTrainingForm()

    user_requests = RequestTraining.objects.filter(custom_user=user).order_by('-request_date')

    return render(request, 'request_training.html', {
        'form': form,
        'user_requests': user_requests,
    })

@login_required
def assign_superior(request):
    if request.method == 'POST':
        superior_id = request.POST.get('superior_id')
        training_request_id = request.session.get('training_request_id')

        if not superior_id or not training_request_id:
            messages.error(request, "Invalid superior or training request.")
            return redirect('request_training')

        try:
            superior = CustomUser.objects.get(id=superior_id)
            training_request = RequestTraining.objects.get(id=training_request_id)
            Approval.objects.create(
                request_training=training_request,
                approver=superior,
                comment="Assigned to superior by user",
                approval_timestamp=timezone.now()
            )
            messages.success(request, "Your training request has been submitted to the selected superior successfully.")
            return redirect('request_training')
        except (CustomUser.DoesNotExist, RequestTraining.DoesNotExist):
            messages.error(request, "Superior or training request not found.")
            return redirect('request_training')
    else:
        return redirect('request_training')
    
#------------------------------------------------------------------------------------------------------------------------------------


@login_required
def superior_check_requests(request):
    user = request.user

    # Check if the user is the head of any departments
    headed_departments = Department.objects.filter(head=user)
    logging.info(f"User {user.username} is a head of departments: {headed_departments}")

    if headed_departments.exists():
        # Find subordinate users
        subordinate_users = CustomUser.objects.filter(user_departments__in=headed_departments).distinct()
        logging.info(f"Subordinate users: {subordinate_users}")

        # Get user training requests
        user_requests = RequestTraining.objects.filter(custom_user__in=subordinate_users).annotate(timestamp=F('request_date')).order_by('-timestamp')
        logging.info(f"User requests: {user_requests}")

        # Get superior assigned trainings
        superior_assignments = SuperiorAssignedTraining.objects.filter(
            assigned_by=user,
            department__in=headed_departments
        ).annotate(timestamp=F('assigned_by__date_joined')).order_by('-timestamp')
        logging.info(f"Superior assignments: {superior_assignments}")

        # Combine requests and sort by datetime
        combined_requests = sorted(
            chain(user_requests, superior_assignments),
            key=lambda x: x.timestamp,
            reverse=True
        )
        logging.info(f"Combined requests: {combined_requests}")

        if request.method == 'POST':
            form = TrainingRequestApprovalForm(request.POST)
            assignment_form = SuperiorAssignmentForm(request.POST, superior_user=user)

            if form.is_valid():
                request_id = form.cleaned_data.get('request_id')
                status_id = form.cleaned_data.get('status_id')
                hod_comment = form.cleaned_data.get('hod_comment')
                checker_comment = form.cleaned_data.get('checker_comment')
                next_superior_id = request.POST.get('higher_superior_id')

                training_request = RequestTraining.objects.get(id=request_id)
                status = Status.objects.get(id=status_id)
                training_request.status = status
                training_request.hod_comment = hod_comment
                training_request.checker_comment = checker_comment
                training_request.hod_approval_timestamp = timezone.now()
                training_request.save()

                if next_superior_id:
                    # Assign to next superior
                    next_superior = CustomUser.objects.get(id=next_superior_id)
                    training_request.hod_user = next_superior
                    training_request.save()

                messages.success(request, "Training request has been processed successfully.")
                return redirect('superior_check_requests')

            elif assignment_form.is_valid():
                assigned_users = assignment_form.cleaned_data.get('assigned_users')
                training_programme = assignment_form.cleaned_data.get('training_programme')
                other_training = assignment_form.cleaned_data.get('other_training')
                hod_comment = assignment_form.cleaned_data.get('hod_comment')

                for assigned_user in assigned_users:
                    superior_assignment = SuperiorAssignedTraining(
                        assigned_by=user,
                        department=headed_departments.first(),  # Assuming one department for simplicity
                        training_programme=training_programme,
                        other_training=other_training,
                        hod_comment=hod_comment
                    )
                    superior_assignment.save()

                messages.success(request, "Training has been assigned successfully.")
                return redirect('superior_check_requests')
            else:
                messages.error(request, "Invalid form submission. Please try again.")

        else:
            form = TrainingRequestApprovalForm()
            assignment_form = SuperiorAssignmentForm(superior_user=user)

        higher_superiors = CustomUser.objects.filter(
            user_departments__in=Department.objects.filter(sub_departments__head=user)
        ).distinct()
        logging.info(f"Higher superiors: {higher_superiors}")

        return render(request, 'superiorcheck.html', {
            'combined_requests': combined_requests,
            'form': form,
            'assignment_form': assignment_form,
            'higher_superiors': higher_superiors,
            'select_higher_superior': bool(higher_superiors),
        })
    else:
        messages.error(request, "You are not assigned as a head of any departments.")
        return redirect('home')


@login_required
def assign_higher_superior(request):
    if request.method == 'POST':
        higher_superior_id = request.POST.get('higher_superior_id')
        training_request_id = request.session.get('training_request_id')
        hod_comment = request.session.get('hod_comment')

        if not higher_superior_id or not training_request_id:
            messages.error(request, "Invalid superior or training request.")
            return redirect('superior_check_requests')

        try:
            higher_superior = CustomUser.objects.get(id=higher_superior_id)
            training_request = RequestTraining.objects.get(id=training_request_id)
            Approval.objects.create(
                request_training=training_request,
                approver=higher_superior,
                comment=hod_comment,
                approval_timestamp=timezone.now()
            )
            messages.success(request, "Your training request has been submitted to the selected higher superior successfully.")
            return redirect('superior_check_requests')
        except (CustomUser.DoesNotExist, RequestTraining.DoesNotExist):
            messages.error(request, "Superior or training request not found.")
            return redirect('superior_check_requests')
    else:
        return redirect('superior_check_requests')


@login_required
def superior_approve_request(request):
    if request.method == 'POST':
        form = TrainingRequestApprovalForm(request.POST)
        if form.is_valid():
            request_id = form.cleaned_data['request_id']
            status_id = form.cleaned_data['status_id']
            hod_comment = form.cleaned_data['hod_comment']

            logging.info(f"Received form data for approval: Request ID: {request_id}, Status ID: {status_id}, HOD Comment: {hod_comment}")

            training_request = get_object_or_404(RequestTraining, id=request_id)
            status = get_object_or_404(Status, id=status_id)
            training_request.status = status
            training_request.hod_comment = hod_comment
            training_request.hod_approval_timestamp = timezone.now()
            training_request.hod_user = request.user  # Set the HOD user
            training_request.save()

            # Check if there's a higher level superior
            higher_superiors = CustomUser.objects.filter(headed_departments__in=training_request.custom_user.departments.all()).exclude(id=request.user.id)
            if higher_superiors.exists():
                higher_superior = higher_superiors.first()  # Take the first higher superior
                Approval.objects.create(
                    request_training=training_request,
                    approver=higher_superior,
                    comment=hod_comment,
                    approval_timestamp=timezone.now()
                )
                messages.success(request, f"Training request #{request_id} has been approved and forwarded to higher superior.")
            else:
                # Final approval
                Approval.objects.create(
                    request_training=training_request,
                    approver=request.user,
                    comment=hod_comment,
                    approval_timestamp=timezone.now()
                )
                training_request.final_approval_timestamp = timezone.now()
                training_request.save()
                messages.success(request, f"Training request #{request_id} has been finally approved.")

            return redirect('superior_check_requests')
        else:
            messages.error(request, "Invalid form submission. Please try again.")
            logging.error(f"Form errors: {form.errors}")
    else:
        messages.error(request, "Invalid request method.")

    return redirect('superior_check_requests')

@login_required
def superior_reject_request(request):
    if request.method == 'POST':
        form = TrainingRequestApprovalForm(request.POST)
        if form.is_valid():
            request_id = form.cleaned_data['request_id']
            status_id = form.cleaned_data['status_id']
            hod_comment = form.cleaned_data['hod_comment']

            logging.info(f"Received form data for rejection: Request ID: {request_id}, Status ID: {status_id}, HOD Comment: {hod_comment}")

            training_request = get_object_or_404(RequestTraining, id=request_id)
            status = get_object_or_404(Status, id=status_id)
            training_request.status = status
            training_request.hod_comment = hod_comment
            training_request.hod_approval_timestamp = timezone.now()
            training_request.hod_user = request.user  # Set the HOD user
            training_request.save()

            # Add rejection logic here
            messages.success(request, f"Training request #{request_id} has been rejected successfully.")
            return redirect('superior_check_requests')
        else:
            messages.error(request, "Invalid form submission. Please try again.")
            logging.error(f"Form errors: {form.errors}")
    else:
        messages.error(request, "Invalid request method.")
        logging.error(f"Invalid request method: {request.method}")

    return redirect('superior_check_requests')



#-----------------------------------------------------------------------------------------------------------------------------------------------------------------
@login_required
def checker_check_requests(request):
    # Get counts for each training programme and their statuses, including fully processed ones
    user_requests = RequestTraining.objects.filter(status__id__in=[2, 3, 5]).values('training_programme__title', 'status__name').annotate(count=Count('id'))
    hod_assignments = HODTrainingAssignment.objects.filter(status__id__in=[2, 3, 5]).values('training_programme__title', 'status__name').annotate(count=Count('id'))

    combined_counts = defaultdict(lambda: {'total': 0, 'HODapproved': 0, 'CKRapproved': 0, 'CKRrejected': 0})
    
    for req in user_requests:
        combined_counts[req['training_programme__title']]['total'] += req['count']
        combined_counts[req['training_programme__title']][req['status__name']] += req['count']
    
    for assignment in hod_assignments:
        combined_counts[assignment['training_programme__title']]['total'] += assignment['count']
        combined_counts[assignment['training_programme__title']][assignment['status__name']] += assignment['count']
    
    # Convert to list and sort by total count
    combined_requests = sorted(combined_counts.items(), key=lambda x: x[1]['total'], reverse=True)
    
    return render(request, 'checkercheck.html', {
        'combined_requests': combined_requests,
    })

@login_required
def checker_approve_request(request):
    if request.method == 'POST':
        form = TrainingRequestApprovalForm(request.POST)
        if form.is_valid():
            request_id = form.cleaned_data.get('request_id')
            assignment_id = form.cleaned_data.get('assignment_id')
            status_id = form.cleaned_data['status_id']
            checker_comment = form.cleaned_data['checker_comment']
            
            logging.info(f"Received form data for approval: Request ID: {request_id}, Assignment ID: {assignment_id}, Status ID: {status_id}, Checker Comment: {checker_comment}")
            
            if assignment_id:
                assignment = get_object_or_404(HODTrainingAssignment, id=assignment_id)
                status = get_object_or_404(Status, id=status_id)
                assignment.status = status
                assignment.checker_comment = checker_comment
                assignment.checker_approval_timestamp = timezone.now()
                assignment.save()
                messages.success(request, f"Training assignment #{assignment.id} has been approved successfully.")
            else:
                training_request = get_object_or_404(RequestTraining, id=request_id)
                status = get_object_or_404(Status, id=status_id)
                training_request.status = status
                training_request.checker_comment = checker_comment
                training_request.checker_approval_timestamp = timezone.now()
                training_request.save()
                messages.success(request, f"Training request #{request_id} has been approved successfully.")
            
            return redirect('checker_check_requests')
        else:
            messages.error(request, "Invalid form submission. Please try again.")
            logging.error(f"Form errors: {form.errors}")
    else:
        messages.error(request, "Invalid request method.")
    
    return redirect('checker_check_requests')


@login_required
def checker_reject_request(request):
    if request.method == 'POST':
        form = TrainingRequestApprovalForm(request.POST)
        if form.is_valid():
            request_id = form.cleaned_data.get('request_id')
            assignment_id = form.cleaned_data.get('assignment_id')
            status_id = form.cleaned_data['status_id']
            checker_comment = form.cleaned_data['checker_comment']
            
            logging.info(f"Received form data for rejection: Request ID: {request_id}, Assignment ID: {assignment_id}, Status ID: {status_id}, Checker Comment: {checker_comment}")
            
            if assignment_id:
                assignment = get_object_or_404(HODTrainingAssignment, id=assignment_id)
                status = get_object_or_404(Status, id=status_id)
                assignment.status = status
                assignment.checker_comment = checker_comment
                assignment.checker_approval_timestamp = timezone.now()
                assignment.save()
                messages.success(request, f"Training assignment #{assignment.id} has been rejected successfully.")
            else:
                training_request = get_object_or_404(RequestTraining, id=request_id)
                status = get_object_or_404(Status, id=status_id)
                training_request.status = status
                training_request.checker_comment = checker_comment
                training_request.checker_approval_timestamp = timezone.now()
                training_request.save()
                messages.success(request, f"Training request #{request_id} has been rejected successfully.")
            
            return redirect('checker_check_requests')
        else:
            messages.error(request, "Invalid form submission. Please try again.")
            logging.error(f"Form errors: {form.errors}")
    else:
        messages.error(request, "Invalid request method.")
        logging.error(f"Invalid request method: {request.method}")
    
    return redirect('checker_check_requests')


@login_required
def maker_check_requests(request):
    # Get counts for each training programme and their statuses
    user_requests = RequestTraining.objects.filter(status__name='CKRapproved').values('training_programme__title', 'status__name').annotate(count=Count('id'))
    hod_assignments = HODTrainingAssignment.objects.filter(status__name='CKRapproved').values('training_programme__title', 'status__name').annotate(count=Count('id'))

    combined_counts = defaultdict(lambda: {'total': 0, 'CKRapproved': 0})
    
    for req in user_requests:
        combined_counts[req['training_programme__title']]['total'] += req['count']
        combined_counts[req['training_programme__title']][req['status__name']] += req['count']
    
    for assignment in hod_assignments:
        combined_counts[assignment['training_programme__title']]['total'] += assignment['count']
        combined_counts[assignment['training_programme__title']][assignment['status__name']] += assignment['count']
    
    # Convert to list and sort by total count
    combined_requests = sorted(combined_counts.items(), key=lambda x: x[1]['total'], reverse=True)
    
    return render(request, 'makercheck.html', {
        'combined_requests': combined_requests,
    })



@login_required
def checker_training_detail(request, training_programme_title):
    user_requests = RequestTraining.objects.filter(training_programme__title=training_programme_title, status__id__in=[2, 3, 5])
    hod_assignments = HODTrainingAssignment.objects.filter(training_programme__title=training_programme_title, status__id__in=[2, 3, 5])

    combined_requests = sorted(
        list(user_requests) + list(hod_assignments),
        key=lambda x: x.request_date if isinstance(x, RequestTraining) else x.assignment_date,
        reverse=True
    )

    if request.method == 'POST':
        request_ids = request.POST.getlist('selected_requests')
        action = request.POST.get('action')
        checker_comment = request.POST.get('checker_comment')
        status_id = 3 if action == 'approve' else 5

        for request_id in request_ids:
            req = RequestTraining.objects.filter(id=request_id).first() or HODTrainingAssignment.objects.filter(id=request_id).first()
            if req:
                req.status_id = status_id
                req.checker_comment = checker_comment
                req.checker_approval_timestamp = timezone.now()
                req.save()

        messages.success(request, "Selected training requests have been updated successfully.")
        return redirect('checker_check_requests')

    pending_approval = any(req.status.name not in ['CKRapproved', 'CKRrejected'] for req in combined_requests)

    return render(request, 'checker_training_detail.html', {
        'training_programme_title': training_programme_title,
        'combined_requests': combined_requests,
        'pending_approval': pending_approval
    })


@login_required
def maker_training_detail(request, training_programme_title):
    user_requests = RequestTraining.objects.filter(training_programme__title=training_programme_title, status__name='CKRapproved')
    hod_assignments = HODTrainingAssignment.objects.filter(training_programme__title=training_programme_title, status__name='CKRapproved')

    combined_requests = sorted(
        list(user_requests) + list(hod_assignments),
        key=lambda x: x.request_date if isinstance(x, RequestTraining) else x.assignment_date,
        reverse=True
    )

    return render(request, 'maker_training_detail.html', {
        'training_programme_title': training_programme_title,
        'combined_requests': combined_requests,
    })
    
    

@login_required
def create_training(request):
    if request.method == 'POST':
        form = TrainingCreationForm(request.POST, request.FILES)
        external_trainer_form = ExternalTrainerForm(request.POST)

        if form.is_valid() and (form.cleaned_data['trainer_type'] == 'Internal' or external_trainer_form.is_valid() or form.cleaned_data['venue_type'] == 'Online'):
            training_session = form.save(commit=False)
            trainer_type = form.cleaned_data['trainer_type']

            if form.cleaned_data['venue_type'] == 'Online':
                training_session.trainer = None  # No trainer required for online training
            elif trainer_type == 'External':
                external_trainer = external_trainer_form.cleaned_data.get('existing_trainer')
                if external_trainer:
                    training_session.trainer = external_trainer
                else:
                    external_trainer = external_trainer_form.save(commit=False)
                    external_trainer.trainer_type = 'External'
                    external_trainer.save()
                    training_session.trainer = external_trainer
            else:
                internal_trainer = form.cleaned_data['internal_trainer']
                if internal_trainer:
                    training_session.trainer, created = TrainerMaster.objects.get_or_create(
                        custom_user=internal_trainer,
                        defaults={
                            'trainer_type': 'Internal',
                            'name': internal_trainer.employee_name,
                            'email': internal_trainer.email,
                            'phone_number': internal_trainer.contact_no,
                        }
                    )

            training_session.created_by = request.user
            training_session.save()
            messages.success(request, "Training session has been created successfully.")
            return redirect('create_training')
        else:
            messages.error(request, "There was an error creating the training session. Please check the form for errors.")
    else:
        form = TrainingCreationForm()
        external_trainer_form = ExternalTrainerForm()

    trainings = TrainingSession.objects.all().order_by('-created_at')
    venues = list(VenueMaster.objects.values('id', 'name', 'venue_type'))
    trainers = list(TrainerMaster.objects.filter(trainer_type='External').values('id', 'name', 'email', 'phone_number', 'city'))

    return render(request, 'create_training.html', {
        'form': form,
        'external_trainer_form': external_trainer_form,
        'trainings': trainings,
        'venues': venues,
        'trainers': trainers,
    })
@login_required
def send_training_request(request, pk):
    training = get_object_or_404(TrainingSession, pk=pk)
    venue_type = training.venue.venue_type if training.venue else 'Online'

    if request.method == 'POST':
        form = TrainingRequestForm(request.POST, instance=training)
        if form.is_valid():
            training = form.save(commit=False)
            selected_users_ids = request.POST.getlist('selected_users')
            selected_users = CustomUser.objects.filter(id__in=selected_users_ids)
            training.selected_participants.set(selected_users)
            training.save()
            messages.success(request, "Training session details updated successfully.")
            return redirect('create_training')
        else:
            messages.error(request, "There was an error updating the training session. Please check the form for errors.")
    else:
        form = TrainingRequestForm(instance=training)

    departments = CustomUser.objects.values_list('department', flat=True).distinct()
    hods = CustomUser.objects.filter(Q(role__name='HOD') | Q(role__name='Checker')).distinct()
    associates = CustomUser.objects.filter(work_order_no__isnull=False).exclude(work_order_no='')
    employees = CustomUser.objects.filter(Q(work_order_no__isnull=True) | Q(work_order_no=''))

    if training.training_programme:
        validity_period = training.training_programme.validity
        valid_date = timezone.now().date() - timedelta(days=365 * validity_period)
        attendances = AttendanceMaster.objects.filter(
            training_session__training_programme=training.training_programme,
            attendance_date__gte=valid_date
        ).values_list('custom_user_id', flat=True)
    else:
        attendances = []

    return render(request, 'send_training_request.html', {
        'form': form,
        'training': training,
        'venue_type': venue_type,
        'departments': departments,
        'hods': hods,
        'associates': associates,
        'employees': employees,
        'attendances': list(attendances),
    })

@login_required
def edit_training(request, pk):
    training = get_object_or_404(TrainingSession, pk=pk)
    if request.method == 'POST':
        form = TrainingCreationForm(request.POST, instance=training)
        external_trainer_form = ExternalTrainerForm(request.POST, instance=training.trainer)

        if form.is_valid() and (form.cleaned_data['trainer_type'] == 'Internal' or external_trainer_form.is_valid()):
            training_session = form.save(commit=False)
            trainer_type = form.cleaned_data['trainer_type']
            
            if trainer_type == 'External':
                external_trainer = external_trainer_form.cleaned_data['existing_trainer']
                if external_trainer:
                    training_session.trainer = external_trainer
                else:
                    external_trainer = external_trainer_form.save(commit=False)
                    external_trainer.trainer_type = 'External'
                    external_trainer.save()
                    training_session.trainer = external_trainer
            else:
                internal_trainer = form.cleaned_data['internal_trainer']
                if internal_trainer:
                    training_session.trainer, created = TrainerMaster.objects.get_or_create(
                        custom_user=internal_trainer,
                        defaults={
                            'trainer_type': 'Internal',
                            'name': internal_trainer.employee_name,
                            'email': internal_trainer.email,
                            'phone_number': internal_trainer.contact_no,
                        }
                    )
            
            training_session.created_by = request.user
            training_session.save()
            messages.success(request, "Training session has been updated successfully.")
            return redirect('create_training')
        else:
            messages.error(request, "There was an error updating the training session. Please check the form for errors.")
    else:
        form = TrainingCreationForm(instance=training)
        external_trainer_form = ExternalTrainerForm(instance=training.trainer)

    return render(request, 'edit_training.html', {
        'form': form,
        'external_trainer_form': external_trainer_form,
        'training': training,
    })

@login_required
def delete_training(request, pk):
    training = get_object_or_404(TrainingSession, pk=pk)
    if request.method == 'POST':
        training.delete()
        messages.success(request, "Training session has been deleted successfully.")
        return redirect('create_training')

    return render(request, 'delete_training.html', {'training': training})

