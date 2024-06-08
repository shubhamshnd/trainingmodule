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
from django.db.models import Q , F
from datetime import timedelta

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

    # Fetch departments where the user is a member
    member_departments = Department.objects.filter(members=user)
    if member_departments.exists():
        logger.info(f"User {user.username} is a member of departments: {list(member_departments)}")

        # Log user departments and their heads
        for dept in member_departments:
            logger.info(f"Department: {dept.name}")
            if dept.head:
                logger.info(f"Head: {dept.head.username} - {dept.head.employee_name}")
            else:
                logger.info(f"Head: None")
            members = dept.members.all()
            for member in members:
                logger.info(f"Member: {member.username} - {member.employee_name}")
    else:
        logger.info(f"User {user.username} is not associated with any departments.")

    if request.method == 'POST':
        form = RequestTrainingForm(request.POST)
        if form.is_valid():
            training_request = form.save(commit=False)
            training_request.custom_user = user
            training_request.save()

            logger.info(f"Training request {training_request.id} saved successfully.")

            # Find superiors in these departments
            superiors = CustomUser.objects.filter(
                Q(headed_departments__in=member_departments) |
                Q(headed_departments__in=member_departments.values_list('sub_departments', flat=True))
            ).distinct()
            logger.info(f"Found superiors: {list(superiors)}")

            if superiors.count() == 1:
                # If there's only one superior, directly assign the request
                superior = superiors.first()
                Approval.objects.create(
                    request_training=training_request,
                    approver=superior,
                    comment="Auto-assigned to superior",
                    approval_timestamp=timezone.now(),
                    action='pending'  # Ensure action is set to pending
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
                approval_timestamp=timezone.now(),
                action='pending'  # Ensure action is set to pending
            )
            messages.success(request, "Your training request has been submitted to the selected superior successfully.")
            logger.info(f"Training request {training_request.id} assigned to superior {superior.username}.")
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
    logger.info(f"User {user.username} is a head of departments: {list(headed_departments)}")

    if headed_departments.exists():
        # Find all subordinate users including those in sub-departments
        subordinate_users = CustomUser.objects.filter(
            Q(user_departments__in=headed_departments) |
            Q(user_departments__parent__in=headed_departments)
        ).distinct()
        logger.info(f"Subordinate users: {list(subordinate_users)}")

        # Get user training requests that are pending approval from the current user
        user_requests = RequestTraining.objects.filter(
            custom_user__in=subordinate_users,
            is_rejected=False
        ).exclude(
            approvals__approver=user, approvals__action='approve'
        ).annotate(timestamp=F('request_date')).order_by('-timestamp')
        logger.info(f"User requests count (with corrected exclusion filter): {user_requests.count()}")
        for req in user_requests:
            logger.info(f"Request ID: {req.id}, Custom User: {req.custom_user.username}, Is Approved: {req.is_approved}, Is Rejected: {req.is_rejected}, Request Date: {req.request_date}")

        # Get superior assigned trainings that are pending approval from the current user
        superior_assignments = SuperiorAssignedTraining.objects.filter(
            Q(assigned_by=user) |
            Q(department__in=headed_departments),
            is_rejected=False
        ).exclude(
            approvals__approver=user, approvals__action='approve'
        ).annotate(timestamp=F('created_at')).order_by('-timestamp')
        logger.info(f"Superior assignments count: {superior_assignments.count()}")
        for assignment in superior_assignments:
            logger.info(f"Assignment ID: {assignment.id}, Department: {assignment.department.name}, Is Approved: {assignment.is_approved}, Is Rejected: {assignment.is_rejected}")

        # Combine requests and sort by datetime
        combined_requests = sorted(
            chain(user_requests, superior_assignments),
            key=lambda x: x.timestamp,
            reverse=True
        )
        logger.info(f"Combined requests count: {len(combined_requests)}")

        if request.method == 'POST':
            form = TrainingRequestApprovalForm(request.POST)
            assignment_form = SuperiorAssignmentForm(request.POST, superior_user=user)

            if form.is_valid():
                request_id = form.cleaned_data.get('request_id')
                assignment_id = form.cleaned_data.get('assignment_id')
                hod_comment = form.cleaned_data.get('hod_comment')
                action = form.cleaned_data.get('action')

                if request_id:
                    training_request = get_object_or_404(RequestTraining, id=request_id)
                    comment = hod_comment
                    approval_timestamp = timezone.now()

                    # Add approval to Approval table
                    Approval.objects.create(
                        request_training=training_request,
                        approver=request.user,
                        comment=comment,
                        approval_timestamp=approval_timestamp,
                        action=action
                    )

                    if action == 'approve':
                        next_approver = training_request.custom_user.departments.first().parent.head
                        if next_approver:
                            logger.info(f"Next approver for request {training_request.id}: {next_approver.username} - {next_approver.employee_name}")
                            Approval.objects.create(
                                request_training=training_request,
                                approver=next_approver,
                                comment="Pending approval by higher superior",
                                approval_timestamp=timezone.now(),
                                action='pending'
                            )
                        else:
                            training_request.is_approved = True
                            training_request.is_rejected = False
                            training_request.final_approval_timestamp = timezone.now()
                            training_request.save()
                    elif action == 'reject':
                        training_request.is_approved = False
                        training_request.is_rejected = True
                        training_request.final_approval_timestamp = timezone.now()
                        training_request.save()

                if assignment_id:
                    superior_assignment = get_object_or_404(SuperiorAssignedTraining, id=assignment_id)
                    comment = hod_comment
                    approval_timestamp = timezone.now()

                    # Add approval to Approval table
                    Approval.objects.create(
                        superior_assignment=superior_assignment,
                        approver=request.user,
                        comment=comment,
                        approval_timestamp=approval_timestamp,
                        action=action
                    )

                    if action == 'approve':
                        next_approver = superior_assignment.department.parent.head
                        if next_approver:
                            logger.info(f"Next approver for assignment {superior_assignment.id}: {next_approver.username} - {next_approver.employee_name}")
                            Approval.objects.create(
                                superior_assignment=superior_assignment,
                                approver=next_approver,
                                comment="Pending approval by higher superior",
                                approval_timestamp=timezone.now(),
                                action='pending'
                            )
                        else:
                            superior_assignment.is_approved = True
                            superior_assignment.is_rejected = False
                            superior_assignment.save()
                    elif action == 'reject':
                        superior_assignment.is_approved = False
                        superior_assignment.is_rejected = True
                        superior_assignment.save()

                messages.success(request, "Training request has been processed successfully.")
                return redirect('superior_check_requests')

            elif assignment_form.is_valid():
                assigned_users = assignment_form.cleaned_data.get('assigned_users')
                training_programme = assignment_form.cleaned_data.get('training_programme')
                other_training = assignment_form.cleaned_data.get('other_training')
                hod_comment = assignment_form.cleaned_data.get('hod_comment')

                superior_assignment = SuperiorAssignedTraining(
                    assigned_by=user,
                    department=headed_departments.first(),  # Assuming one department for simplicity
                    training_programme=training_programme,
                    other_training=other_training,
                    hod_comment=hod_comment
                )
                superior_assignment.save()
                superior_assignment.assigned_users.set(assigned_users)

                # Automatically create approval records
                for assigned_user in assigned_users:
                    Approval.objects.create(
                        request_training=None,
                        approver=user,
                        comment=hod_comment,
                        approval_timestamp=timezone.now(),
                        superior_assignment=superior_assignment,
                        action='assign'
                    )

                messages.success(request, "Training has been assigned successfully.")
                return redirect('superior_check_requests')
            else:
                messages.error(request, "Invalid form submission. Please try again.")

        else:
            form = TrainingRequestApprovalForm()
            assignment_form = SuperiorAssignmentForm(superior_user=user)

        higher_superiors = []
        for dept in headed_departments:
            if dept.parent and dept.parent.head:
                higher_superiors.append(dept.parent.head)

        logger.info(f"Higher superiors: {higher_superiors}")

        # Check if the current user is the final approver
        is_final_approver = not higher_superiors

        return render(request, 'superiorcheck.html', {
            'combined_requests': combined_requests,
            'form': form,
            'assignment_form': assignment_form,
            'higher_superiors': higher_superiors,
            'select_higher_superior': bool(higher_superiors),
            'is_final_approver': is_final_approver
        })
    else:
        messages.error(request, "You are not assigned as a head of any departments.")
        return redirect('home')



@login_required
def superior_approve_request(request):
    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        hod_comment = request.POST.get('hod_comment')

        training_request = get_object_or_404(RequestTraining, id=request_id)
        training_request.hod_comment = hod_comment

        # Check if the current user is the final approver
        is_final_approver = not training_request.custom_user.departments.first().parent

        if is_final_approver:
            training_request.is_approved = True
            training_request.is_rejected = False
            training_request.final_approval_timestamp = timezone.now()
            training_request.save()

        # Log the approval
        Approval.objects.create(
            request_training=training_request,
            approver=request.user,
            comment=hod_comment,
            approval_timestamp=timezone.now(),
            action='approve'
        )

        messages.success(request, f"Training request #{request_id} has been approved successfully.")
        return redirect('superior_check_requests')

    return redirect('superior_check_requests')


@login_required
def superior_reject_request(request):
    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        hod_comment = request.POST.get('hod_comment')

        training_request = get_object_or_404(RequestTraining, id=request_id)
        training_request.hod_comment = hod_comment
        training_request.is_rejected = True
        training_request.is_approved = False

        # Check if the current approver is the last in the hierarchy
        current_approver_department = Department.objects.filter(head=request.user).first()
        if current_approver_department and not current_approver_department.parent:
            # Set the final approval timestamp if the approver is the last in the hierarchy
            training_request.final_approval_timestamp = timezone.now()

        training_request.save()

        # Log the rejection
        Approval.objects.create(
            request_training=training_request,
            approver=request.user,
            comment=hod_comment,
            approval_timestamp=timezone.now(),
            action='reject'
        )

        messages.success(request, f"Training request #{request_id} has been rejected successfully.")
        return redirect('superior_check_requests')

    return redirect('superior_check_requests')



@login_required
def assign_higher_superior(request):
    if request.method == 'POST':
        higher_superior_id = request.POST.get('higher_superior_id')
        higher_superior = get_object_or_404(CustomUser, id=higher_superior_id)

        # Find the training request or superior assignment based on the provided ID
        request_id = request.POST.get('request_id')
        training_request = RequestTraining.objects.filter(id=request_id).first()
        superior_assignment = SuperiorAssignedTraining.objects.filter(id=request_id).first()

        if training_request:
            training_request.assigned_to = higher_superior
            training_request.save()
        elif superior_assignment:
            superior_assignment.assigned_to = higher_superior
            superior_assignment.save()

        messages.success(request, "Request has been forwarded to the higher superior.")
        return redirect('superior_check_requests')

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
            training.mark_as_completed()
            messages.success(request, "Training session details and participants updated successfully.")
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

