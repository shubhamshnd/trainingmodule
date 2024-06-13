from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CustomUser, RequestTraining, Status, HODTrainingAssignment ,  VenueMaster, TrainerMaster , TrainingSession , AttendanceMaster , Approval ,SuperiorAssignedTraining , Department , TrainingProgramme
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse
from .forms import RequestTrainingForm, TrainingRequestApprovalForm, CheckerApprovalForm ,  TrainingCreationForm, ExternalTrainerForm ,  TrainingRequestForm , SuperiorAssignmentForm
import logging
from django.utils import timezone
from itertools import chain
from collections import defaultdict
from django.db.models import Count
logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler()])
from django.db.models import Q , F , Max
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

    context = {
        'is_checker': is_checker,
        'is_maker': is_maker,
        'is_superior': user_is_superior,
        'role': 'checker' if is_checker else ('maker' if is_maker else ('superior' if user_is_superior else 'member')),
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

    member_departments = Department.objects.filter(members=user)
    if member_departments.exists():
        logger.info(f"User {user.username} is a member of departments: {list(member_departments)}")

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
            training_request_data = {
                'training_programme': form.cleaned_data['training_programme'].id if form.cleaned_data['training_programme'] else None,
                'other_training': form.cleaned_data['other_training'],
                'user_comment': form.cleaned_data['user_comment']
            }
            request.session['training_request_data'] = training_request_data

            superiors = CustomUser.objects.filter(
                Q(headed_departments__in=member_departments) |
                Q(headed_departments__in=member_departments.values_list('sub_departments', flat=True))
            ).distinct()

            if superiors.count() == 1:
                # If there's only one superior, assign and submit directly
                training_programme = TrainingProgramme.objects.get(id=training_request_data['training_programme']) if training_request_data['training_programme'] else None
                training_request = RequestTraining.objects.create(
                    custom_user=user,
                    current_approver=superiors.first(),
                    training_programme=training_programme,
                    other_training=training_request_data['other_training'],
                    user_comment=training_request_data['user_comment']
                )
                Approval.objects.create(
                    request_training=training_request,
                    approver=superiors.first(),
                    comment="Auto-assigned to superior",
                    approval_timestamp=timezone.now(),
                    action='pending'
                )
                messages.success(request, "Your training request has been submitted successfully.")
                return redirect('request_training')
            elif superiors.count() > 1:
                # Render the page with the modal for selecting a superior
                return render(request, 'request_training.html', {
                    'form': form,
                    'user_requests': RequestTraining.objects.filter(custom_user=user).order_by('-request_date'),
                    'superiors': superiors,
                    'select_superior': True
                })
            else:
                messages.error(request, "No superior found for your departments.")
                return redirect('request_training')
        else:
            # Handle form errors
            return render(request, 'request_training.html', {
                'form': form,
                'user_requests': RequestTraining.objects.filter(custom_user=user).order_by('-request_date'),
                'superiors': None,
                'select_superior': False
            })
    else:
        form = RequestTrainingForm()
        return render(request, 'request_training.html', {
            'form': form,
            'user_requests': RequestTraining.objects.filter(custom_user=user).order_by('-request_date'),
            'superiors': None,
            'select_superior': False
        })
@login_required
def assign_superior(request):
    if request.method == 'POST':
        superior_id = request.POST.get('superior_id')
        training_request_data = request.session.get('training_request_data')
        user = request.user

        logger.info(f"POST data: {request.POST}")
        logger.info(f"Training request data from session: {training_request_data}")

        if not superior_id or not training_request_data:
            messages.error(request, "Invalid superior or training request.")
            logger.error("Invalid superior or training request. superior_id: %s, training_request_data: %s", superior_id, training_request_data)
            return redirect('request_training')

        try:
            superior = CustomUser.objects.get(id=superior_id)
            training_programme = TrainingProgramme.objects.get(id=training_request_data['training_programme']) if training_request_data['training_programme'] else None
            training_request = RequestTraining.objects.create(
                custom_user=user,
                current_approver=superior,
                training_programme=training_programme,
                other_training=training_request_data['other_training'],
                user_comment=training_request_data['user_comment']
            )
            Approval.objects.create(
                request_training=training_request,
                approver=superior,
                comment="Assigned to superior by user",
                approval_timestamp=timezone.now(),
                action='pending'
            )
            logger.info(f"Approval object created with approver {superior.username} for training request ID {training_request.id}")
            messages.success(request, "Your training request has been submitted to the selected superior successfully.")
            return redirect('request_training')
        except CustomUser.DoesNotExist:
            messages.error(request, "Selected superior not found.")
            logger.error(f"Superior with ID {superior_id} not found.")
            return redirect('request_training')
        except TrainingProgramme.DoesNotExist:
            messages.error(request, "Selected training programme not found.")
            logger.error(f"Training programme with ID {training_request_data['training_programme']} not found.")
            return redirect('request_training')
    else:
        return redirect('request_training')
#------------------------------------------------------------------------------------------------------------------------------------@login_required
@login_required
def superior_check_requests(request):
    user = request.user

    headed_departments = Department.objects.filter(head=user)
    if not headed_departments.exists():
        messages.error(request, "You are not assigned as a head of any departments.")
        logger.info(f"User {user.username} is not assigned as head of any departments.")
        return redirect('home')

    # Log the hierarchy of the departments the user heads
    logger.info(f"Logging hierarchy for user {user.username}")
    for department in headed_departments:
        log_department_hierarchy(department)

    # Log the headed departments of the current user
    logger.info(f"Headed departments for current user {user.username}: {[dept.name for dept in user.headed_departments.all()]}")

    # Fetch the requests where the current approver is the user
    user_requests = RequestTraining.objects.filter(
        current_approver=user,
    ).annotate(timestamp=F('request_date')).order_by('-timestamp')

    superior_assignments = SuperiorAssignedTraining.objects.filter(
        current_approver=user,
    ).annotate(timestamp=F('created_at')).order_by('-timestamp')

    # Combine the requests for display
    combined_requests = sorted(
        chain(user_requests, superior_assignments),
        key=lambda x: x.timestamp,
        reverse=True
    )

    logger.info(f"User {user.username} visited superior check requests page.")
    for request_item in combined_requests:
        if isinstance(request_item, RequestTraining):
            logger.info(f"RequestTraining ID: {request_item.id}, User: {request_item.custom_user.username}, Current Approver: {request_item.current_approver.username if request_item.current_approver else 'None'}")
            next_approver, parent_dept_name = find_next_approver(request_item.current_approver)
            if next_approver:
                logger.info(f"Next Approver: {next_approver.username}, Department: {parent_dept_name}")
            else:
                logger.info("No further approvers.")
        elif isinstance(request_item, SuperiorAssignedTraining):
            logger.info(f"SuperiorAssignedTraining ID: {request_item.id}, Assigned By: {request_item.assigned_by.username}, Current Approver: {request_item.current_approver.username if request_item.current_approver else 'None'}")
            next_approver, parent_dept_name = find_next_approver(request_item.current_approver)
            if next_approver:
                logger.info(f"Next Approver: {next_approver.username}, Department: {parent_dept_name}")
            else:
                logger.info("No further approvers.")

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
                training_request.hod_comment = hod_comment
                approval_timestamp = timezone.now()

                next_approver, parent_dept_name = find_next_approver(training_request.current_approver)

                if action == 'approve':
                    if next_approver:
                        training_request.current_approver = next_approver
                        Approval.objects.create(
                            request_training=training_request,
                            approver=request.user,
                            comment=hod_comment,
                            approval_timestamp=approval_timestamp,
                            action='approve'
                        )
                        logger.info(f"Training request {training_request.id} approved by {request.user.username}. Next approver: {next_approver.username}, Department: {parent_dept_name}")
                    else:
                        training_request.is_approved = True
                        training_request.final_approval_timestamp = approval_timestamp
                        training_request.current_approver = None
                        logger.info(f"Training request {training_request.id} fully approved by {request.user.username}. No further approvers.")
                    training_request.save()
                elif action == 'reject':
                    training_request.is_rejected = True
                    training_request.current_approver = None
                    training_request.final_approval_timestamp = approval_timestamp
                    logger.info(f"Training request {training_request.id} rejected by {request.user.username}.")
                    training_request.save()

            if assignment_id:
                superior_assignment = get_object_or_404(SuperiorAssignedTraining, id=assignment_id)
                superior_assignment.hod_comment = hod_comment
                approval_timestamp = timezone.now()

                next_approver, parent_dept_name = find_next_approver(superior_assignment.current_approver)

                if action == 'approve':
                    if next_approver:
                        superior_assignment.current_approver = next_approver
                        Approval.objects.create(
                            superior_assignment=superior_assignment,
                            approver=request.user,
                            comment=hod_comment,
                            approval_timestamp=approval_timestamp,
                            action='approve'
                        )
                        logger.info(f"Superior assignment {superior_assignment.id} approved by {request.user.username}. Next approver: {next_approver.username}, Department: {parent_dept_name}")
                    else:
                        superior_assignment.is_approved = True
                        superior_assignment.final_approval_timestamp = approval_timestamp  # Set the final approval timestamp
                        superior_assignment.current_approver = None
                        logger.info(f"Superior assignment {superior_assignment.id} fully approved by {request.user.username}. No further approvers.")
                    superior_assignment.save()
                elif action == 'reject':
                    superior_assignment.is_rejected = True
                    superior_assignment.current_approver = None
                    superior_assignment.final_approval_timestamp = approval_timestamp
                    logger.info(f"Superior assignment {superior_assignment.id} rejected by {request.user.username}.")
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
                department=headed_departments.first(),
                training_programme=training_programme,
                other_training=other_training,
                hod_comment=hod_comment,
            )
            superior_assignment.save()
            superior_assignment.assigned_users.set(assigned_users)

            # Set current approver to the immediate superior of the assigner
            next_approver, parent_dept_name = find_next_approver(user)
            if next_approver:
                superior_assignment.current_approver = next_approver
                logger.info(f"Superior assignment {superior_assignment.id} assigned by {user.username}. Next approver: {next_approver.username}, Department: {parent_dept_name}")
            else:
                logger.info(f"Superior assignment {superior_assignment.id} assigned by {user.username}. No further approvers.")
            superior_assignment.save()

            for assigned_user in assigned_users:
                Approval.objects.create(
                    superior_assignment=superior_assignment,
                    approver=user,
                    comment=hod_comment,
                    approval_timestamp=timezone.now(),
                    action='assign'
                )

            messages.success(request, "Training has been assigned successfully.")
            logger.info(f"Training assigned by {user.username} to {', '.join([u.username for u in assigned_users])}.")
            return redirect('superior_check_requests')
        else:
            messages.error(request, "Invalid form submission. Please try again.")
    else:
        form = TrainingRequestApprovalForm()
        assignment_form = SuperiorAssignmentForm(superior_user=user)

    higher_superiors = [dept.parent.head for dept in headed_departments if dept.parent and dept.parent.head]

    is_final_approver = not higher_superiors

    return render(request, 'superiorcheck.html', {
        'combined_requests': combined_requests,
        'form': form,
        'assignment_form': assignment_form,
        'higher_superiors': higher_superiors,
        'select_higher_superior': bool(higher_superiors),
        'is_final_approver': is_final_approver
    })

def find_next_approver(current_approver):
    if not current_approver:
        logger.info("No current approver provided.")
        return None, None

    logger.info(f"Finding next approver for current approver: {current_approver.username}")

    # Check departments where the user is the head
    headed_departments = current_approver.headed_departments.all()
    logger.info(f"Headed departments for current approver {current_approver.username}: {[dept.name for dept in headed_departments]}")

    if not headed_departments:
        logger.info(f"Current approver {current_approver.username} does not head any departments.")
        return None, None

    for department in headed_departments:
        logger.info(f"Checking headed department: {department.name}")
        parent_department = department.parent
        if parent_department:
            logger.info(f"Parent department: {parent_department.name}")
            if parent_department.head:
                logger.info(f"Parent department head: {parent_department.head.username}")
                return parent_department.head, parent_department.name
            else:
                logger.info("Parent department has no head.")
        else:
            logger.info("No parent department.")

    logger.info("No further approver found.")
    return None, None

def log_department_hierarchy(department, level=0):
    indent = " " * (level * 4)
    logger.info(f"{indent}Department: {department.name}")
    logger.info(f"{indent}Head: {department.head.username if department.head else 'No head'}")
    
    if department.parent:
        logger.info(f"{indent}Is a sub-department of: {department.parent.name}")
        logger.info(f"{indent}Parent Department Head: {department.parent.head.username if department.parent.head else 'No head'}")
    
    for member in department.members.all():
        logger.info(f"{indent}Member: {member.username}")

    sub_departments = department.sub_departments.all()
    if sub_departments.exists():
        logger.info(f"{indent}Sub-departments of {department.name}:")
        for sub_department in sub_departments:
            log_department_hierarchy(sub_department, level + 1)
            
            
@login_required
def superior_approve_request(request):
    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        hod_comment = request.POST.get('hod_comment')
        action = request.POST.get('action')

        # Determine the type of request (RequestTraining or SuperiorAssignedTraining)
        if action == 'approve':
            try:
                training_request = RequestTraining.objects.get(id=request_id)
                training_request.hod_comment = hod_comment

                approval_timestamp = timezone.now()

                next_approver, parent_dept_name = find_next_approver(training_request.current_approver)

                Approval.objects.create(
                    request_training=training_request,
                    approver=request.user,
                    comment=hod_comment,
                    approval_timestamp=approval_timestamp,
                    action='approve'
                )

                if next_approver:
                    training_request.current_approver = next_approver
                    logger.info(f"Training request {training_request.id} approved by {request.user.username}. Next approver: {next_approver.username}, Department: {parent_dept_name}")
                else:
                    training_request.is_approved = True
                    training_request.final_approval_timestamp = approval_timestamp
                    training_request.current_approver = None
                    logger.info(f"Training request {training_request.id} fully approved by {request.user.username}. No further approvers.")

                training_request.save()
                messages.success(request, f"Training request #{request_id} has been approved successfully.")
            except RequestTraining.DoesNotExist:
                try:
                    superior_assignment = SuperiorAssignedTraining.objects.get(id=request_id)
                    superior_assignment.hod_comment = hod_comment

                    approval_timestamp = timezone.now()

                    next_approver, parent_dept_name = find_next_approver(superior_assignment.current_approver)

                    Approval.objects.create(
                        superior_assignment=superior_assignment,
                        approver=request.user,
                        comment=hod_comment,
                        approval_timestamp=approval_timestamp,
                        action='approve'
                    )

                    if next_approver:
                        superior_assignment.current_approver = next_approver
                        logger.info(f"Superior assignment {superior_assignment.id} approved by {request.user.username}. Next approver: {next_approver.username}, Department: {parent_dept_name}")
                    else:
                        superior_assignment.is_approved = True
                        superior_assignment.final_approval_timestamp = approval_timestamp  # Set the final approval timestamp
                        superior_assignment.current_approver = None
                        logger.info(f"Superior assignment {superior_assignment.id} fully approved by {request.user.username}. No further approvers.")

                    superior_assignment.save()
                    messages.success(request, f"Superior assignment #{request_id} has been approved successfully.")
                except SuperiorAssignedTraining.DoesNotExist:
                    messages.error(request, "No matching training request found.")
                    logger.error(f"No matching training request found for ID {request_id}.")
                    return redirect('superior_check_requests')

        return redirect('superior_check_requests')

    return redirect('superior_check_requests')

@login_required
def superior_reject_request(request):
    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        hod_comment = request.POST.get('hod_comment')
        action = request.POST.get('action')

        # Determine the type of request (RequestTraining or SuperiorAssignedTraining)
        if action == 'reject':
            try:
                training_request = RequestTraining.objects.get(id=request_id)
                training_request.hod_comment = hod_comment
                training_request.is_rejected = True
                training_request.is_approved = False
                training_request.final_approval_timestamp = timezone.now()
                training_request.current_approver = None

                training_request.save()

                # Log the rejection
                Approval.objects.create(
                    request_training=training_request,
                    approver=request.user,
                    comment=hod_comment,
                    approval_timestamp=timezone.now(),
                    action='reject'
                )

                logger.info(f"Training request {training_request.id} rejected by {request.user.username}.")
                messages.success(request, f"Training request #{request_id} has been rejected successfully.")
            except RequestTraining.DoesNotExist:
                try:
                    superior_assignment = SuperiorAssignedTraining.objects.get(id=request_id)
                    superior_assignment.hod_comment = hod_comment
                    superior_assignment.is_rejected = True
                    superior_assignment.is_approved = False
                    superior_assignment.final_approval_timestamp = timezone.now()  # Set the final approval timestamp
                    superior_assignment.current_approver = None

                    superior_assignment.save()

                    # Log the rejection
                    Approval.objects.create(
                        superior_assignment=superior_assignment,
                        approver=request.user,
                        comment=hod_comment,
                        approval_timestamp=timezone.now(),
                        action='reject'
                    )

                    logger.info(f"Superior assignment {superior_assignment.id} rejected by {request.user.username}.")
                    messages.success(request, f"Superior assignment #{request_id} has been rejected successfully.")
                except SuperiorAssignedTraining.DoesNotExist:
                    messages.error(request, "No matching training request found.")
                    logger.error(f"No matching training request found for ID {request_id}.")
                    return redirect('superior_check_requests')

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
    # Get user requests and HOD assignments where the final approval timestamp exists
    user_requests = RequestTraining.objects.filter(final_approval_timestamp__isnull=False).values('training_programme__title').annotate(count=Count('id'))
    superior_assignments =SuperiorAssignedTraining.objects.filter(final_approval_timestamp__isnull=False).values('training_programme__title' ).annotate(count=Count('id'))

    # Combine counts and sort
    combined_requests = list(user_requests) + list(superior_assignments)
    combined_requests.sort(key=lambda x: x['count'], reverse=True)

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

