from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CustomUser, RequestTraining, Status, HODTrainingAssignment
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse
from .forms import RequestTrainingForm, TrainingRequestApprovalForm, CheckerApprovalForm, HODTrainingAssignmentForm
import logging
from django.utils import timezone
from itertools import chain

logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler()])

def easter_egg_page(request):
    context = {
        'range_170': range(170),
        'range_10': range(10),
    }
    return render(request, 'easter_egg.html', context)


@csrf_protect
@login_required
def home(request):
    user_role = None
    if request.user.is_authenticated:
        try:
            user_role = request.user.role.name
        except AttributeError:
            pass
    
    base_template = {
        'HOD': 'hodbase.html',
        'Checker': 'checkerbase.html',
        'Maker': 'makerbase.html'
    }.get(user_role, 'userbase.html')
    
    response = render(request, 'home.html', {'user_role': user_role, 'base_template': base_template})
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
            training_request.status_id = 1
            training_request.save()
            messages.success(request, "Your training request has been submitted successfully.")
            return redirect('request_training')
    else:
        form = RequestTrainingForm()

    user_requests = RequestTraining.objects.filter(custom_user=user).order_by('-request_date')

    return render(request, 'request_training.html', {
        'form': form,
        'user_requests': user_requests,
    })


@login_required
def hod_check_requests(request):
    hod_department = request.user.department
    user_requests = RequestTraining.objects.filter(
        custom_user__role__name='User', custom_user__department=hod_department
    ).order_by('-request_date')

    hod_assignments = HODTrainingAssignment.objects.filter(hod_user=request.user).order_by('-assignment_date')

    if request.method == 'POST':
        form = TrainingRequestApprovalForm(request.POST)
        hod_assignment_form = HODTrainingAssignmentForm(request.POST, hod_user=request.user)
        if form.is_valid():
            request_id = form.cleaned_data['request_id']
            status_id = form.cleaned_data['status_id']
            hod_comment = form.cleaned_data['hod_comment']

            training_request = get_object_or_404(RequestTraining, id=request_id)
            status = get_object_or_404(Status, id=status_id)

            training_request.status = status
            training_request.hod_comment = hod_comment
            training_request.hod_approval_timestamp = timezone.now()
            training_request.save()

            messages.success(request, f"Training request #{request_id} has been updated successfully.")
            return redirect('hod_check_requests')

        elif hod_assignment_form.is_valid():
            assigned_users = hod_assignment_form.cleaned_data['assigned_users']
            for user in assigned_users:
                hod_assignment = HODTrainingAssignment(
                    hod_user=request.user,
                    assigned_user=user,
                    training_programme=hod_assignment_form.cleaned_data['training_programme'],
                    other_training=hod_assignment_form.cleaned_data['other_training'],
                    hod_comment=hod_assignment_form.cleaned_data['hod_comment'],
                    status=Status.objects.get(name='HODapproved')
                )
                hod_assignment.save()
            messages.success(request, "Training has been assigned successfully.")
            return redirect('hod_check_requests')

        else:
            messages.error(request, "Invalid form submission. Please try again.")

    else:
        form = TrainingRequestApprovalForm()
        hod_assignment_form = HODTrainingAssignmentForm(hod_user=request.user)

    combined_requests = sorted(
        list(user_requests) + list(hod_assignments),
        key=lambda x: x.request_date if isinstance(x, RequestTraining) else x.assignment_date,
        reverse=True
    )

    return render(request, 'hodcheck.html', {
        'combined_requests': combined_requests,
        'form': form,
        'hod_assignment_form': hod_assignment_form,
    })


@login_required
def hod_approve_request(request):
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
            training_request.save()
            
            messages.success(request, f"Training request #{request_id} has been approved successfully.")
            return redirect('hod_check_requests')
        else:
            messages.error(request, "Invalid form submission. Please try again.")
            logging.error(f"Form errors: {form.errors}")
    else:
        messages.error(request, "Invalid request method.")
    
    return redirect('hod_check_requests')


@login_required
def hod_reject_request(request):
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
            training_request.save()
            
            messages.success(request, f"Training request #{request_id} has been rejected successfully.")
            return redirect('hod_check_requests')
        else:
            messages.error(request, "Invalid form submission. Please try again.")
            logging.error(f"Form errors: {form.errors}")
    else:
        messages.error(request, "Invalid request method.")
        logging.error(f"Invalid request method: {request.method}")
    
    return redirect('hod_check_requests')


@login_required
def checker_check_requests(request):
    user_requests = RequestTraining.objects.all().order_by('-request_date')
    hod_assignments = HODTrainingAssignment.objects.all().order_by('-assignment_date')

    if request.method == 'POST':
        form = TrainingRequestApprovalForm(request.POST)
        if form.is_valid():
            request_id = form.cleaned_data.get('request_id')
            assignment_id = form.cleaned_data.get('assignment_id')
            status_id = form.cleaned_data['status_id']
            checker_comment = form.cleaned_data['checker_comment']

            if assignment_id:
                assignment = get_object_or_404(HODTrainingAssignment, id=assignment_id)
                status = get_object_or_404(Status, id=status_id)
                assignment.status = status
                assignment.checker_comment = checker_comment
                assignment.checker_approval_timestamp = timezone.now()
                assignment.save()
                messages.success(request, f"Training assignment #{assignment.id} has been updated successfully.")
            else:
                training_request = get_object_or_404(RequestTraining, id=request_id)
                status = get_object_or_404(Status, id=status_id)
                training_request.status = status
                training_request.checker_comment = checker_comment
                training_request.checker_approval_timestamp = timezone.now()
                training_request.save()
                messages.success(request, f"Training request #{request_id} has been updated successfully.")

            return redirect('checker_check_requests')
        else:
            messages.error(request, "Invalid form submission. Please try again.")
            logging.error(f"Invalid form data: {form.errors}")
    else:
        form = TrainingRequestApprovalForm()

    combined_requests = sorted(
        list(user_requests) + list(hod_assignments),
        key=lambda x: x.request_date if isinstance(x, RequestTraining) else x.assignment_date,
        reverse=True
    )

    return render(request, 'checkercheck.html', {
        'combined_requests': combined_requests,
        'form': form,
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
    user_requests = RequestTraining.objects.filter(status__name='CKRapproved').order_by('-request_date')
    hod_assignments = HODTrainingAssignment.objects.filter(status__name='CKRapproved').order_by('-assignment_date')
    
    combined_requests = sorted(
        list(user_requests) + list(hod_assignments),
        key=lambda x: x.request_date if isinstance(x, RequestTraining) else x.assignment_date,
        reverse=True
    )

    logging.debug(f"Fetched {len(combined_requests)} CKRapproved requests for the maker view.")
    return render(request, 'makercheck.html', {'combined_requests': combined_requests})
