from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Feedback, DepartmentCount ,CustomUser, RequestTraining, Status, HODTrainingAssignment ,  VenueMaster, TrainerMaster , TrainingSession , AttendanceMaster , Approval ,SuperiorAssignedTraining , Department , TrainingProgramme , TrainingApproval
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse
from .forms import  FeedbackForm ,DepartmentCountForm, RequestTrainingForm, TrainingRequestApprovalForm, CheckerApprovalForm ,  TrainingCreationForm, ExternalTrainerForm ,  TrainingRequestForm , SuperiorAssignmentForm , TrainingApprovalForm, ReasonForm , ParticipantsForm
import logging
from django.utils import timezone
from itertools import chain
from collections import defaultdict
from django.db.models import Count
logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler()])
from django.db.models import Q , F , Max
from django.utils import timezone
from datetime import timedelta, datetime
from django.http import JsonResponse
from django.forms import formset_factory
import pytz
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

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
    attended_sessions = AttendanceMaster.objects.filter(custom_user=user).select_related('training_session').order_by('-training_session__date')
    feedback_sessions = Feedback.objects.filter(attendance__custom_user=user)
    feedback_sessions_ids = feedback_sessions.values_list('attendance_id', flat=True)
    context = {
        'is_checker': is_checker,
        'is_maker': is_maker,
        'is_superior': user_is_superior,
        'role': 'checker' if is_checker else ('maker' if is_maker else ('superior' if user_is_superior else 'member')),
        'attended_sessions': attended_sessions,
        'feedback_sessions_ids': feedback_sessions_ids,
    }
    
    response = render(request, 'home.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@login_required
def user_trainings(request):
    user = request.user
    current_date = datetime.now().date()
    
    # Fetch training sessions where checker_finalized is True and needs_hod_nomination is False
    sessions_direct = TrainingSession.objects.filter(
        selected_participants=user,
        checker_finalized=True,
        needs_hod_nomination=False
    )
    
    # Fetch training sessions where checker_finalized is True and needs_hod_nomination is True
    approvals = TrainingApproval.objects.filter(
        selected_participants=user,
        training_session__checker_finalized=True,
        training_session__needs_hod_nomination=True
    ).select_related('training_session')
    
    sessions_hod = [approval.training_session for approval in approvals]
    
    # Combine all sessions
    all_sessions = list(sessions_direct) + sessions_hod
    
    # Format data for the frontend
    events = [
        {
            'date': session.date.strftime('%Y-%m-%d'),
            'startTime': session.from_time.strftime('%I:%M %p'),
            'endTime': session.to_time.strftime('%I:%M %p'),
            'title': session.training_programme.title if session.training_programme else session.custom_training_programme,
            'venue': session.venue.name if session.venue else 'Online',
            'trainer': session.trainer.name if session.trainer else 'N/A'
        }
        for session in all_sessions
    ]
    
    logger.debug(f"User: {user.username}, Events: {events}")
    
    return JsonResponse(events, safe=False)

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
def get_approvals(request, request_id):
    approvals = Approval.objects.filter(request_training_id=request_id).values(
        'approver__username', 'comment', 'approval_timestamp'
    )
    training_request = RequestTraining.objects.get(id=request_id)
    approval_list = list(approvals)
    response_data = {
        'approvals': approval_list,
        'checker_approval_timestamp': training_request.final_approval_timestamp
    }
    return JsonResponse(response_data)

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
#------------------------------------------------------------------------------------------------------------------------------------@login_required@login_required
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
                        superior_assignment.final_approval_timestamp = approval_timestamp
                        superior_assignment.current_approver = None
                        Approval.objects.create(
                            superior_assignment=superior_assignment,
                            approver=request.user,
                            comment=hod_comment,
                            approval_timestamp=approval_timestamp,
                            action='approve'
                        )
                        logger.info(f"Superior assignment {superior_assignment.id} fully approved by {request.user.username}. No further approvers.")
                    superior_assignment.save()
                elif action == 'reject':
                    superior_assignment.is_rejected = True
                    superior_assignment.current_approver = None
                    superior_assignment.final_approval_timestamp = approval_timestamp
                    Approval.objects.create(
                        superior_assignment=superior_assignment,
                        approver=request.user,
                        comment=hod_comment,
                        approval_timestamp=approval_timestamp,
                        action='reject'
                    )
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
                superior_assignment.current_approver = None
                superior_assignment.is_approved = True
                superior_assignment.final_approval_timestamp = timezone.now()
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

    parent_department_heads = find_parent_department_heads(user)

    higher_superiors = [dept.parent.head for dept in headed_departments if dept.parent and dept.parent.head]

    is_final_approver = not higher_superiors

    return render(request, 'superiorcheck.html', {
        'combined_requests': combined_requests,
        'form': form,
        'assignment_form': assignment_form,
        'higher_superiors': higher_superiors,
        'select_higher_superior': bool(higher_superiors),
        'is_final_approver': is_final_approver,
        'parent_department_heads': parent_department_heads,
    })


def find_next_approver(current_approver):
    if not current_approver:
        logger.info("No current approver provided.")
        return None, None

    logger.info(f"Finding next approver for current approver: {current_approver.username}")

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
        approve_type = request.POST.get('approve_type')
        parent_department_head_id = request.POST.get('parent_department_head_id')

        if action == 'approve':
            try:
                training_request = RequestTraining.objects.get(id=request_id)
                training_request.hod_comment = hod_comment
                approval_timestamp = timezone.now()

                if approve_type == 'department':
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

                elif approve_type == 'parent_department':
                    parent_department_head = get_object_or_404(CustomUser, id=parent_department_head_id)
                    training_request.current_approver = parent_department_head
                    Approval.objects.create(
                        request_training=training_request,
                        approver=request.user,
                        comment=hod_comment,
                        approval_timestamp=approval_timestamp,
                        action='approve'
                    )
                    logger.info(f"Training request {training_request.id} approved by {request.user.username} for parent department. Next approver: {parent_department_head.username}")

                training_request.save()
                messages.success(request, f"Training request #{request_id} has been approved successfully.")
            except RequestTraining.DoesNotExist:
                try:
                    superior_assignment = SuperiorAssignedTraining.objects.get(id=request_id)
                    superior_assignment.hod_comment = hod_comment
                    approval_timestamp = timezone.now()

                    if approve_type == 'department':
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
                            superior_assignment.final_approval_timestamp = approval_timestamp
                            superior_assignment.current_approver = None
                            logger.info(f"Superior assignment {superior_assignment.id} fully approved by {request.user.username}. No further approvers.")

                    elif approve_type == 'parent_department':
                        parent_department_head = get_object_or_404(CustomUser, id=parent_department_head_id)
                        superior_assignment.current_approver = parent_department_head
                        Approval.objects.create(
                            superior_assignment=superior_assignment,
                            approver=request.user,
                            comment=hod_comment,
                            approval_timestamp=approval_timestamp,
                            action='approve'
                        )
                        logger.info(f"Superior assignment {superior_assignment.id} approved by {request.user.username} for parent department. Next approver: {parent_department_head.username}")

                    superior_assignment.save()
                    messages.success(request, f"Superior assignment #{request_id} has been approved successfully.")
                except SuperiorAssignedTraining.DoesNotExist:
                    messages.error(request, "No matching training request found.")
                    logger.error(f"No matching training request found for ID {request_id}.")
                    return redirect('superior_check_requests')

        return redirect('superior_check_requests')

    return redirect('superior_check_requests')


def find_parent_department_heads(current_approver):

    if not current_approver:
        logger.info("No current approver provided.")
        return []

    headed_departments = current_approver.headed_departments.all()
    parent_department_heads = []

    for department in headed_departments:
        parent_department = department.parent
        if parent_department and parent_department.head:
            parent_department_heads.append((parent_department.head, parent_department.name))

    return parent_department_heads


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
    user_requests = RequestTraining.objects.filter(final_approval_timestamp__isnull=False)
    superior_assignments = SuperiorAssignedTraining.objects.filter(final_approval_timestamp__isnull=False)

    # Group by training programme and status
    user_requests_agg = user_requests.values('training_programme__title', 'status__name').annotate(count=Count('id'))
    superior_assignments_agg = superior_assignments.values('training_programme__title', 'status__name').annotate(count=Count('id'))

    # Combine the counts and initialize counts for pending, approved, and rejected
    combined_counts = {}
    for req in list(user_requests_agg) + list(superior_assignments_agg):
        title = req['training_programme__title']
        status = req['status__name']
        if title not in combined_counts:
            combined_counts[title] = {'pending': 0, 'approved': 0, 'rejected': 0}

        if status is None:
            combined_counts[title]['pending'] += req['count']
        elif status == 'CKRapproved':
            combined_counts[title]['approved'] += req['count']
        elif status == 'CKRrejected':
            combined_counts[title]['rejected'] += req['count']

    return render(request, 'checkercheck.html', {
        'combined_requests': combined_counts,
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
def checker_training_detail(request, training_programme_title):
    user_requests = RequestTraining.objects.filter(training_programme__title=training_programme_title, final_approval_timestamp__isnull=False)
    superior_assignments = SuperiorAssignedTraining.objects.filter(training_programme__title=training_programme_title, final_approval_timestamp__isnull=False)

    combined_requests = sorted(
        list(user_requests) + list(superior_assignments),
        key=lambda x: x.final_approval_timestamp,
        reverse=True
    )

    if request.method == 'POST':
        request_ids = request.POST.getlist('selected_requests')
        action = request.POST.get('action')
        checker_comment = request.POST.get('checker_comment')
        status_id = 3 if action == 'approve' else 5

        for request_id in request_ids:
            req = RequestTraining.objects.filter(id=request_id).first() or SuperiorAssignedTraining.objects.filter(id=request_id).first()
            if req:
                req.status_id = status_id
                req.checker_comment = checker_comment
                req.checker_approval_timestamp = timezone.now()
                req.save()

        messages.success(request, "Selected training requests have been updated successfully.")
        return redirect('checker_check_requests')

    pending_approval = any(req.status is None or req.status.name not in ['CKRapproved', 'CKRrejected'] for req in combined_requests)

    return render(request, 'checker_training_detail.html', {
        'training_programme_title': training_programme_title,
        'combined_requests': combined_requests,
        'pending_approval': pending_approval
    })
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------

@login_required
def maker_check_requests(request):
    user_requests = RequestTraining.objects.filter(status__name='CKRapproved').values('training_programme__title', 'status__name').annotate(count=Count('id'))
    hod_assignments = HODTrainingAssignment.objects.filter(status__name='CKRapproved').values('training_programme__title', 'status__name').annotate(count=Count('id'))

    combined_counts = defaultdict(lambda: {'total': 0, 'CKRapproved': 0})

    for req in user_requests:
        combined_counts[req['training_programme__title']]['total'] += req['count']
        combined_counts[req['training_programme__title']][req['status__name']] += req['count']

    for assignment in hod_assignments:
        combined_counts[assignment['training_programme__title']]['total'] += assignment['count']
        combined_counts[assignment['training_programme__title']][assignment['status__name']] += assignment['count']

    combined_requests = sorted(combined_counts.items(), key=lambda x: x[1]['total'], reverse=True)

    return render(request, 'makercheck.html', {
        'combined_requests': combined_requests,
    })

@login_required
def maker_training_detail(request, training_programme_title):
    user_requests = RequestTraining.objects.filter(training_programme__title=training_programme_title, final_approval_timestamp__isnull=False)
    superior_assignments = SuperiorAssignedTraining.objects.filter(training_programme__title=training_programme_title, final_approval_timestamp__isnull=False)
    trainings = TrainingSession.objects.filter(finalized=False, needs_hod_nomination=False)

    combined_requests = sorted(
        list(user_requests) + list(superior_assignments),
        key=lambda x: x.final_approval_timestamp,
        reverse=True
    )

    selected_participants = set()
    for training in trainings:
        selected_participants.update(training.selected_participants.all())

    return render(request, 'maker_training_detail.html', {
        'training_programme_title': training_programme_title,
        'combined_requests': combined_requests,
        'trainings': trainings,
        'selected_participants': selected_participants,
    })

@login_required
def add_to_training(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        training_id = data.get('training_id')
        user_ids = data.get('user_ids', [])
        training = TrainingSession.objects.get(id=training_id)

        current_participants = set(training.selected_participants.all())
        new_participants = set(user_ids) - current_participants
        training.selected_participants.add(*new_participants)

        # Log the action
        training_log = f"Added users {', '.join(map(str, new_participants))} to training session {training}."
        print(training_log)  # Replace with actual logging

        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

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

    for training in trainings:
        if training.attendance_frozen:
            training.completion_date = training.date  # Use the training session date
        else:
            training.completion_date = None

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
def mark_attendance(request, training_id):
    training = get_object_or_404(TrainingSession, id=training_id)
    
    if request.method == 'POST':
        attendees = request.POST.getlist('attendees')
        action = request.POST.get('action')
        
        if action == 'save':
            # Clear existing attendance records
            AttendanceMaster.objects.filter(training_session=training).delete()
            
            for user_id in attendees:
                user = CustomUser.objects.get(id=user_id)
                AttendanceMaster.objects.create(
                    custom_user=user,
                    training_session=training,
                    attendance_date=training.date  # Use the training's date
                )
            
            messages.success(request, "Attendance has been marked successfully.")
        
        elif action == 'close':
            training.attendance_frozen = True
            training.save()
            messages.success(request, "Attendance has been frozen and can no longer be edited.")
        
        return redirect('mark_attendance', training_id=training.id)
    
    if training.needs_hod_nomination:
        participants = CustomUser.objects.filter(
            selected_participants__training_session=training,
            selected_participants__approved=True
        )
    else:
        participants = training.selected_participants.all()
    
    # Get existing attendance records
    existing_attendees = AttendanceMaster.objects.filter(training_session=training).values_list('custom_user_id', flat=True)
    
    return render(request, 'mark_attendance.html', {
        'training': training,
        'participants': participants,
        'existing_attendees': existing_attendees,
    })
@login_required
def send_training_request(request, pk):
    training = get_object_or_404(TrainingSession, pk=pk)
    departments = Department.objects.all()

    if request.method == 'POST':
        form = TrainingRequestForm(request.POST, instance=training)
        needs_hod_nomination = request.POST.get('needs_hod_nomination') == 'on'

        department_count_forms = []
        if needs_hod_nomination:
            for dept in departments:
                dept_form = DepartmentCountForm(
                    request.POST, 
                    prefix=str(dept.id), 
                    initial={
                        'department_id': dept.id,
                        'department_name': dept.name,
                        'head_name': dept.head.employee_name if dept.head else 'N/A',
                        'available_employees': dept.members.count(),
                        'available_associates': dept.associates.count(),
                        'required_employees': request.POST.get(f'{dept.id}-required_employees', 0),
                        'required_associates': request.POST.get(f'{dept.id}-required_associates', 0),
                    }
                )
                department_count_forms.append(dept_form)

        if form.is_valid() and (not needs_hod_nomination or all(dept_form.is_valid() for dept_form in department_count_forms)):
            training = form.save(commit=False)
            if needs_hod_nomination:
                DepartmentCount.objects.filter(training_session=training).delete()
                for dept_form in department_count_forms:
                    if dept_form.is_valid():
                        cleaned_data = dept_form.cleaned_data
                        department_id = cleaned_data['department_id']
                        department = Department.objects.get(id=department_id)
                        head = department.head
                        required_employees = cleaned_data.get('required_employees', 0)
                        required_associates = cleaned_data.get('required_associates', 0)
                        DepartmentCount.objects.create(
                            training_session=training,
                            department=department,
                            head=head,
                            required_employees=required_employees,
                            required_associates=required_associates
                        )
                training.selected_participants.clear()
            else:
                selected_users_ids = request.POST.getlist('selected_users')
                selected_users = CustomUser.objects.filter(id__in=selected_users_ids)
                training.selected_participants.set(selected_users)
                DepartmentCount.objects.filter(training_session=training).delete()

            if 'finalize' in request.POST:
                training.finalized = True

            training.save()
            training.mark_as_completed()
            return JsonResponse({'success': True, 'finalized': training.finalized})
        else:
            errors = form.errors.copy()
            for dept_form in department_count_forms:
                if not dept_form.is_valid():
                    errors.update({f"dept_{dept_form.initial['department_id']}": dept_form.errors})
            return JsonResponse({'success': False, 'errors': errors})
    else:
        form = TrainingRequestForm(instance=training)
        department_count_forms = [
            DepartmentCountForm(
                prefix=str(dept.id), 
                initial={
                    'department_id': dept.id,
                    'department_name': dept.name,
                    'head_name': dept.head.employee_name if dept.head else 'N/A',
                    'available_employees': dept.members.count(),
                    'available_associates': dept.associates.count(),
                    'required_employees': training.department_counts.filter(department=dept).first().required_employees if training.department_counts.filter(department=dept).exists() else 0,
                    'required_associates': training.department_counts.filter(department=dept).first().required_associates if training.department_counts.filter(department=dept).exists() else 0,
                }
            ) for dept in departments
        ]

    return render(request, 'send_training_request.html', {
        'form': form,
        'training': training,
        'departments': departments,
        'department_count_forms': department_count_forms,
    })
@login_required
@require_POST
@csrf_exempt
def store_department_counts(request):
    training_id = request.POST.get('training_id')
    training = get_object_or_404(TrainingSession, id=training_id)
    counts = request.POST.get('counts')

    if not counts:
        return JsonResponse({'success': False, 'message': 'No counts provided'}, status=400)

    counts = json.loads(counts)

    training.department_counts.clear()

    for dept_id, dept_counts in counts.items():
        department = get_object_or_404(Department, id=dept_id)
        head = department.head
        DepartmentCount.objects.create(
            training_session=training,
            department=department,
            head=head,
            required_employees=dept_counts.get('required_employees', 0),
            required_associates=dept_counts.get('required_associates', 0)
        )

    return JsonResponse({'success': True, 'message': 'Department counts saved successfully'})

@login_required
def get_department_counts(request):
    training_id = request.GET.get('training_id')
    training = get_object_or_404(TrainingSession, id=training_id)
    department_counts = training.department_counts.all()

    counts = {}
    for dept_count in department_counts:
        counts[dept_count.department.id] = {
            'required_employees': dept_count.required_employees,
            'required_associates': dept_count.required_associates,
        }

    return JsonResponse({'success': True, 'counts': counts})

@login_required
def get_department_details(request):
    department_id = request.GET.get('department_id')
    training_id = request.GET.get('training_id')
    department = get_object_or_404(Department, id=department_id)
    training = get_object_or_404(TrainingSession, id=training_id)
    associates = department.associates.all()
    employees = department.members.all()
    head = department.head

    current_date = timezone.now().date()

    def check_validity(user, programme):
        attendance = AttendanceMaster.objects.filter(custom_user=user, training_session__training_programme=programme).order_by('-attendance_date').first()
        if attendance:
            validity_end_date = attendance.attendance_date + timedelta(days=365 * programme.validity)
            days_left = (validity_end_date - current_date).days
            if days_left > 0:
                return days_left, validity_end_date
        return 0, current_date

    def get_user_data(user):
        days_left, validity_end_date = check_validity(user, training.training_programme) if training.training_programme else (0, current_date)
        status = 'success' if days_left > 30 else 'warning' if days_left > 0 else 'not_trained'
        show_checkbox = days_left <= 30
        return {
            'id': user.id,
            'employee_name': user.employee_name,
            'username': user.username,
            'contractor_name': user.contractor_name,
            'selected': user.id in training.selected_participants.all(),
            'status': status,
            'show_checkbox': show_checkbox,
            'validity_end_date': validity_end_date.strftime('%Y-%m-%d')
        }

    associates_data = [get_user_data(assoc) for assoc in associates]
    employees_data = [get_user_data(emp) for emp in employees]
    head_data = {'employee_name': head.employee_name, 'username': head.username} if head else {}

    return JsonResponse({
        'department': {
            'head': head_data,
            'associates': associates_data,
            'employees': employees_data,
        }
    })

@login_required
def get_training_selected_users(request, pk):
    training = get_object_or_404(TrainingSession, pk=pk)
    selected_users = training.selected_participants.all()

    selected_users_data = [
        {
            'id': user.id,
            'employee_name': user.employee_name,
            'username': user.username,
            'contractor_name': user.contractor_name,
            'type': 'associate' if Department.objects.filter(associates__id=user.id).exists() else 'member'
        }
        for user in selected_users
    ]

    return JsonResponse({
        'selected_users': selected_users_data
    })
    
#==================================================closed on 1-7-2024=================================================================================================
APPROVAL_THRESHOLD_HOURS = 48

@login_required
def list_and_finalize_trainings(request):
    user = request.user
    departments = user.headed_departments.all()

    logger.info(f"User {user.username} accessing list_and_finalize_trainings")

    if not departments.exists():
        logger.info(f"User {user.username} has no headed departments")
        return render(request, 'list_and_finalize_trainings.html', {'training_info': []})

    current_time = timezone.now()
    training_sessions = TrainingSession.objects.filter(
        Q(selected_participants__user_departments__in=departments) |
        Q(department_counts__head=user)
    ).distinct().order_by('-date', '-from_time')

    logger.info(f"Found {training_sessions.count()} training sessions for user {user.username}")

    training_info = []

    for training in training_sessions:
        training_type = "Needs Nomination" if training.needs_hod_nomination else "Pre-assigned"
        
        if training_type == "Pre-assigned":
            selected_participants = training.selected_participants.all()
            department_heads = CustomUser.objects.filter(
                Q(user_departments__in=departments) |
                Q(associated_departments__in=departments),
                id__in=selected_participants.values('user_departments__head')
            ).distinct()
            department_counts = []
        else:
            department_counts = DepartmentCount.objects.filter(training_session=training, head=user)
            department_counts = [
                count for count in department_counts
                if count.required_employees > 0 or count.required_associates > 0
            ]
            if not department_counts:
                continue  # Skip trainings with zero required employees and associates

            department_heads = CustomUser.objects.filter(
                id__in=[count.head.id for count in department_counts]
            ).distinct()

        approval = TrainingApproval.objects.filter(training_session=training, head=user).first()
        selected_participants = approval.selected_participants.all() if approval else training.selected_participants.all()

        training_datetime = None
        if training.date and training.from_time:
            training_datetime = datetime.combine(training.date, training.from_time)
            if training_datetime.tzinfo is None:
                training_datetime = timezone.make_aware(training_datetime, timezone.get_current_timezone())

        is_past_training = training_datetime and training_datetime < current_time
        is_within_threshold = training_datetime and training_datetime - timedelta(hours=APPROVAL_THRESHOLD_HOURS) < current_time

        approved_by_head = approval and approval.approved
        status = "Approved" if approved_by_head else ("Pending" if not is_past_training else "Not Approved")

        training_info.append({
            'training': training,
            'type': training_type,
            'show_confirm_button': not training.finalized and not is_past_training and not is_within_threshold and not approved_by_head,
            'allow_modification': not training.finalized and not is_past_training and not is_within_threshold,
            'status': status,
            'selected_participants': selected_participants,
            'department_counts': department_counts,
            'department_heads': department_heads,
        })

    logger.info(f"Prepared training_info for {len(training_info)} trainings")

    if request.method == 'POST':
        training_id = request.POST.get('training_id')
        action = request.POST.get('action')
        training = get_object_or_404(TrainingSession, pk=training_id)
        
        logger.info(f"Processing POST request - Training ID: {training_id}, Action: {action}")
        logger.info(f"Raw POST data: {request.POST}")

        form = ParticipantsForm(request.POST, user=user, training=training)

        if form.is_valid():
            nominated_members = form.cleaned_data['nominated_members']
            nominated_associates = form.cleaned_data['nominated_associates']
            comment = request.POST.get('comment', '')

            logger.info(f"Nominated Members: {[m.id for m in nominated_members]}")
            logger.info(f"Nominated Associates: {[a.id for a in nominated_associates]}")

            # Combine nominated members and associates
            updated_selected_participants = set(nominated_members) | set(nominated_associates)

            logger.info(f"Total updated participants: {len(updated_selected_participants)}")

            approval, created = TrainingApproval.objects.get_or_create(
                training_session=training,
                head=user,
                defaults={
                    'department': departments.first(),
                    'approved': action == 'confirm_training',
                    'pending_approval': action != 'confirm_training',
                    'comment': comment
                }
            )

            logger.info(f"TrainingApproval {'created' if created else 'updated'} - ID: {approval.id}")

            if not created:
                if action == 'confirm_training':
                    approval.approved = True
                    approval.pending_approval = False
                approval.comment = comment

                # Log the current participants before updating
                logger.info(f"Current participants before update: {[p.id for p in approval.selected_participants.all()]}")

                # Update the approval's selected participants only if not confirming
                if action != 'confirm_training':
                    approval.selected_participants.set(updated_selected_participants)
                approval.save()

                # Log the updated participants
                logger.info(f"Updated participants after save: {[p.id for p in approval.selected_participants.all()]}")

            # If confirming the training, update the main TrainingSession as well
            if action == 'confirm_training':
                logger.info("Confirming training and updating TrainingSession")
                training.finalized = True
                training.save()
                logger.info(f"TrainingSession finalized: {training.finalized}")

            return JsonResponse({'success': True})
        else:
            logger.error(f"Form validation failed. Errors: {form.errors}")
            logger.error(f"Form data: {form.data}")
            logger.error(f"Form cleaned data: {form.cleaned_data}")
            return JsonResponse({'success': False, 'error': str(form.errors)})

    else:
        form = ParticipantsForm(user=user, training=None)

    context = {
        'training_info': training_info,
        'form': form,
        'current_time': current_time,
        'approval_threshold_hours': APPROVAL_THRESHOLD_HOURS,
    }

    return render(request, 'list_and_finalize_trainings.html', context)
    
@login_required
def get_department_participants(request, training_id):
    user = request.user
    training = get_object_or_404(TrainingSession, id=training_id)
    approval = TrainingApproval.objects.filter(training_session=training, head=user).first()
    departments = user.headed_departments.all()

    def get_participant_data(user):
        return {
            "id": user.id,
            "employee_name": str(user),
            "username": user.username,
            "type": "associate" if user.work_order_no else "employee"
        }

    all_department_members = CustomUser.objects.filter(
        Q(user_departments__in=departments) | Q(associated_departments__in=departments)
    ).distinct()

    original_participants = training.selected_participants.all()
    selected_participants = approval.selected_participants.all() if approval else CustomUser.objects.none()

    def filter_by_department(users, departments):
        return users.filter(Q(user_departments__in=departments) | Q(associated_departments__in=departments)).distinct()

    department_selected_participants = filter_by_department(selected_participants, departments)
    department_original_participants = filter_by_department(original_participants, departments)

    def separate_participants(participants):
        members = participants.filter(work_order_no='')
        associates = participants.exclude(work_order_no='')
        return members, associates

    selected_members, selected_associates = separate_participants(department_selected_participants)
    all_members, all_associates = separate_participants(all_department_members)
    original_members, original_associates = separate_participants(department_original_participants)

    combined_nominated_members = list(set(original_members) - set(selected_members)) + list(selected_members)
    combined_nominated_associates = list(set(original_associates) - set(selected_associates)) + list(selected_associates)

    available_members = all_members.exclude(id__in=selected_members)
    available_associates = all_associates.exclude(id__in=selected_associates)

    participants_data = {
        "combined_nominated_participants": {
            "members": [get_participant_data(user) for user in combined_nominated_members],
            "associates": [get_participant_data(user) for user in combined_nominated_associates],
        },
        "all_participants": {
            "members": [get_participant_data(user) for user in available_members],
            "associates": [get_participant_data(user) for user in available_associates]
        }
    }

    return JsonResponse(participants_data)
#=====================================================================minor changes but closed 01-07-2024==========================================================================================
@login_required
def checker_finalize_trainings(request):
    user = request.user

    # Ensure the user is a checker
    if not user.is_checker:
        return JsonResponse({'error': 'Unauthorized access'}, status=403)

    current_date = timezone.now().date()
    training_sessions = TrainingSession.objects.all().order_by('-date', '-from_time')

    training_info = []

    for training in training_sessions:
        original_participants = training.selected_participants.all()
        heads = Department.objects.filter(members__in=original_participants).distinct()
        approval_status = []

        for head in heads:
            head_approval = TrainingApproval.objects.filter(training_session=training, head=head.head).first()
            if head_approval:
                approval_status.append({
                    'head': head.head,
                    'approved': head_approval.approved,
                    'selected_participants': head_approval.selected_participants.all(),
                    'comment': head_approval.comment,
                })
            else:
                approval_status.append({
                    'head': head.head,
                    'approved': False,
                    'selected_participants': original_participants.filter(user_departments=head),
                    'comment': '',
                })

        is_past_training = training.date and training.date < current_date
        training_type = "Pre-assigned" if not training.needs_hod_nomination else "Needs Nomination"

        training_info.append({
            'training': training,
            'original_participants': original_participants,
            'approval_status': approval_status,
            'checker_finalized': training.checker_finalized,
            'checker_finalized_timestamp': training.checker_finalized_timestamp,
            'is_past_training': is_past_training,
            'type': training_type,
        })

    if request.method == 'POST':
        training_id = request.POST.get('training_id')
        action = request.POST.get('action')

        training = get_object_or_404(TrainingSession, pk=training_id)

        if action == 'finalize_training':
            try:
                heads = Department.objects.filter(members__in=training.selected_participants.all()).distinct()
                for head in heads:
                    TrainingApproval.objects.update_or_create(
                        training_session=training,
                        head=head.head,
                        defaults={'approved': True}
                    )
                training.checker_finalized = True
                training.checker_finalized_timestamp = timezone.now()
                training.save()

                logger.info(f"Training session {training_id} finalized by checker {user.username}")
                return JsonResponse({'success': True})
            except Exception as e:
                logger.error(f"Error finalizing training session {training_id}: {str(e)}")
                return JsonResponse({'success': False, 'error': str(e)})

    return render(request, 'checker_finalize_trainings.html', {
        'training_info': training_info,
    })
@login_required
def get_checker_training_details(request, training_id):
    training = get_object_or_404(TrainingSession, id=training_id)

    def get_participant_data(user):
        return {
            "id": user.id,
            "employee_name": str(user),
            "username": user.username,
            "type": "associate" if user.work_order_no else "employee"
        }

    # Retrieve departments through DepartmentCount if needs_hod_nomination, else through selected participants
    if training.needs_hod_nomination:
        department_counts = DepartmentCount.objects.filter(training_session=training)
        departments = Department.objects.filter(id__in=department_counts.values('department_id')).distinct()
    else:
        departments = Department.objects.filter(members__in=training.selected_participants.all()).distinct()

    participants_data = []
    for department in departments:
        head = department.head
        approval = TrainingApproval.objects.filter(training_session=training, head=head).first()

        if approval:
            selected_participants = approval.selected_participants.all()
            added_participants = selected_participants.difference(training.selected_participants.all())
            reason = approval.comment if approval.comment else "-"
        else:
            added_participants = CustomUser.objects.none()
            reason = "-"

        department_count = DepartmentCount.objects.filter(training_session=training, department=department).first()

        participants_data.append({
            'head': get_participant_data(head),
            'department_name': department.name,
            'required_employees': department_count.required_employees if department_count else 0,
            'required_associates': department_count.required_associates if department_count else 0,
            'added_participants': [get_participant_data(user) for user in added_participants],
            'total_added': added_participants.count(),
            'approved': approval.approved if approval else False,
            'reason': reason,
            'type': 'Needs Nomination' if training.needs_hod_nomination else 'Pre-assigned',
            'original_participants': [get_participant_data(user) for user in training.selected_participants.filter(Q(user_departments=department) | Q(associated_departments=department)).distinct()],
            'checker_finalized': training.checker_finalized
        })

    return JsonResponse(participants_data, safe=False)



@login_required
def get_training_details(request, training_id):
    training = get_object_or_404(TrainingSession, id=training_id)
    original_participants = training.selected_participants.all()
    heads = Department.objects.filter(members__in=original_participants).distinct()
    approval_status = []

    for head in heads:
        head_approval = TrainingApproval.objects.filter(training_session=training, head=head.head).first()
        if head_approval:
            approval_status.append({
                'head': head.head.username,
                'approved': head_approval.approved,
            })
        else:
            approval_status.append({
                'head': head.head.username,
                'approved': False,
            })

    participants = [{'name': participant.username} for participant in original_participants]

    data = {
        'training_title': training.training_programme.title if training.training_programme else training.custom_training_programme,
        'training_date': training.date,
        'training_time': f"{training.from_time} - {training.to_time}",
        'training_venue': training.venue.name,
        'participants': participants,
        'approval_status': approval_status,
        'finalized': training.checker_finalized,
        'is_past_training': training.date < timezone.now().date(),
    }

    return JsonResponse(data)



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

@login_required
def get_attended_sessions(request):
    user = request.user
    attended_sessions = AttendanceMaster.objects.filter(custom_user=user).select_related('training_session')
    return attended_sessions



@login_required
@csrf_protect
def feedback_form(request, session_id):
    session = get_object_or_404(TrainingSession, id=session_id)
    attendance = get_object_or_404(AttendanceMaster, custom_user=request.user, training_session=session)
    
    # Calculate duration in hours
    duration = (datetime.combine(datetime.min, session.to_time) - datetime.combine(datetime.min, session.from_time)).total_seconds() / 3600

    initial_data = {
        'name': request.user.employee_name,
        'employee_number': request.user.username,
        'date': timezone.now().date(),
        'designation': request.user.designation,
        'department': request.user.department,  # Assuming department is a string
        'programme_title': session.training_programme.title,
        'faculty': session.trainer.name if hasattr(session.trainer, 'name') else session.trainer,
        'duration': duration,
    }

    if request.method == 'POST':
        form = FeedbackForm(request.POST, initial=initial_data)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.attendance = attendance
            feedback.save()
            return redirect('home')  # Redirect to the home page after submission
    else:
        form = FeedbackForm(initial=initial_data)

    return render(request, 'feedback_form.html', {'form': form, 'session': session})