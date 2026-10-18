import os
import csv
import logging
import tempfile
import threading
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from smtplib import SMTPException

import pandas as pd
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ImproperlyConfigured, PermissionDenied, ValidationError
from django.core.mail import get_connection, send_mail
from django.core.validators import URLValidator
from django.http import FileResponse, Http404, HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_POST

from .forms import ContactForm
from .models import Request

logger = logging.getLogger(__name__)
_PROJECT_CSV_THREAD_LOCK = threading.RLock()
CSV_PATH = Path(os.getenv('PROJECTS_CSV_PATH', settings.BASE_DIR / 'Data.csv'))
CV_PATH = Path(os.getenv(
    'PORTFOLIO_CV_PATH',
    settings.BASE_DIR / 'mainapp' / 'static' / 'CV' / 'Abhay_Singh_CV.pdf',
))
MAX_CV_SIZE = 5 * 1024 * 1024
PROJECT_COLUMNS = ('S.No', 'Name', 'Category', 'Description', 'Detail', 'Github', 'Project')


def login_required_custom(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('Login')
        if not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


def read_projects_csv():
    try:
        with CSV_PATH.open(encoding='utf-8-sig', newline='') as csv_file:
            reader = csv.reader(csv_file, strict=True)
            headers = next(reader)
            if any(len(row) != len(headers) for row in reader):
                raise ProjectDataError('The project CSV contains rows with inconsistent columns.')
        if len(headers) != len(set(headers)) or not set(PROJECT_COLUMNS).issubset(headers):
            raise ProjectDataError('The project CSV has missing or duplicate column headers.')
        return pd.read_csv(CSV_PATH, dtype=str, keep_default_na=False, encoding='utf-8-sig')
    except ProjectDataError:
        raise
    except (OSError, UnicodeError, csv.Error, StopIteration, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        raise ProjectDataError('The project CSV is missing, empty, unreadable, or malformed.') from exc


class ProjectDataError(Exception):
    pass


def project_data_error(request, exc):
    logger.exception('Portfolio project CSV could not be read.', exc_info=exc)
    return render(
        request,
        'error.html',
        {'error': 'Project data is temporarily unavailable. Please check the project CSV file.'},
        status=503,
    )


def render_http_error(request, status_code, title, message):
    return render(
        request,
        'http_error.html',
        {
            'status_code': status_code,
            'title': title,
            'message': message,
        },
        status=status_code,
    )


def bad_request(request, exception=None):
    return render_http_error(
        request,
        400,
        'Bad request',
        'The request could not be understood. Check the address or try again.',
    )


def permission_denied(request, exception=None):
    return render_http_error(
        request,
        403,
        'Access denied',
        'You do not have permission to view this page.',
    )


def csrf_failure(request, reason=''):
    return permission_denied(request)


def page_not_found(request, exception=None):
    return render_http_error(
        request,
        404,
        'Page not found',
        'The page may have moved, the address may be incorrect, or the content may no longer be available.',
    )


def server_error(request):
    return render_http_error(
        request,
        500,
        'Something went wrong',
        'An unexpected error occurred. Please try again later.',
    )


def safe_project_links(project):
    safe_project = project.copy()
    validate_url = URLValidator(schemes=('http', 'https'))
    for field in ('Github', 'Project'):
        try:
            if safe_project[field]:
                validate_url(safe_project[field])
        except ValidationError:
            safe_project[field] = ''
    return safe_project


def mail(subject, name, email, message):
    send_account_mail(
        'portfolio',
        subject=f'Portfolio Contact: {subject}',
        message=f'You have a Message from {name} whose Email is {email} and the Message is :-\n{message}',
        recipient_list=['srinetabhaysingh14@gmail.com'],
    )


def confirmationmail(subject, name, email, message):
    send_account_mail(
        'personal',
        subject='Thank You for Contacting Me',
        message=(
            f'Dear {name},\nThank you for reaching out through my portfolio website.\n\n'
            'I have successfully received your message and will review it shortly. '
            'I appreciate your interest and will get back to you as soon as possible.\n\n'
            f'Here is a copy of your submission:\n\nName: {name}\nEmail: {email}\n'
            f'Subject: {subject}\n\nMessage:\n{message}\n\nThank you for your time.\n\n'
            'Best Regards,\n\nAbhay Singh\nData Analyst | Data Science Enthusiast | Django Developer\n'
            'Portfolio: https://portfolio-m1il.onrender.com'
        ),
        recipient_list=[email],
    )


def send_account_mail(account, subject, message, recipient_list):
    email_config = settings.EMAIL_CONFIGS[account]
    username = email_config['host_user']
    password = email_config['host_password']
    if not username or not password:
        raise ImproperlyConfigured(f'Email credentials for the {account} account are not configured.')
    connection = get_connection(username=username, password=password)
    send_mail(
        subject=subject,
        message=message,
        from_email=username,
        recipient_list=recipient_list,
        fail_silently=False,
        connection=connection,
    )


def index(request):
    return render(request, 'index.html')


def about(request):
    try:
        data = read_projects_csv()
    except ProjectDataError as exc:
        return project_data_error(request, exc)
    return render(request, 'about.html', {'count_project': data['S.No'].count()})


def skills(request):
    return render(request, 'skills.html')


def projects(request):
    try:
        data = read_projects_csv()
    except ProjectDataError as exc:
        return project_data_error(request, exc)
    project_records = [safe_project_links(row) for row in data.to_dict('records')]
    return render(request, 'projects.html', {'projects': project_records})


def error(request):
    return render(request, 'error.html')


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            Request.objects.create(Name=name, Email=email, Subject=subject, Message=message)
            delivery_failed = False
            for send_message in (mail, confirmationmail):
                try:
                    send_message(subject, name, email, message)
                except (ImproperlyConfigured, OSError, SMTPException):
                    delivery_failed = True
                    logger.exception('A portfolio contact email could not be sent.')
            if delivery_failed:
                messages.warning(
                    request,
                    'Your message was saved, but an email notification could not be sent.',
                )
            else:
                messages.success(request, 'Your message has been sent successfully.')
            return redirect('Contact')
    return render(request, 'contact.html', {'form': form})


def projectdetail(request, project_name):
    try:
        data = read_projects_csv()
    except ProjectDataError as exc:
        return project_data_error(request, exc)
    project = data[data['Name'].astype(str) == project_name]
    if project.empty:
        raise Http404('Project not found.')
    project_record = safe_project_links(project.iloc[0].to_dict())
    return render(request, 'projectdetail.html', {'project': project_record})


def save_projects_csv(data):
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            newline='',
            dir=CSV_PATH.parent,
            delete=False,
        ) as temp_file:
            temp_path = temp_file.name
            data.to_csv(temp_file, index=False)
        os.replace(temp_path, CSV_PATH)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@contextmanager
def lock_projects_csv():
    lock_path = CSV_PATH.with_suffix(CSV_PATH.suffix + '.lock')
    with _PROJECT_CSV_THREAD_LOCK:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open('a+b') as lock_file:
            if os.name == 'nt':
                import msvcrt

                if os.fstat(lock_file.fileno()).st_size == 0:
                    lock_file.write(b'\0')
                    lock_file.flush()
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


@cache_control(no_store=True, no_cache=True, must_revalidate=True)
@login_required_custom
def csv_admin_projects(request):
    try:
        data = read_projects_csv()
    except ProjectDataError as exc:
        return project_data_error(request, exc)
    return render(request, 'csv_admin_projects.html', {
        'projects': [safe_project_links(row) for row in data.to_dict('records')],
        'total_projects': len(data),
        'cv_available': CV_PATH.is_file(),
    })


@cache_control(no_store=True, no_cache=True, must_revalidate=True)
@login_required_custom
def add_csv_project(request):
    if request.method == 'POST':
        try:
            with lock_projects_csv():
                data = read_projects_csv()
                new_project = {
                    'Name': request.POST.get('Name', '').strip(),
                    'Category': request.POST.get('Category', '').strip(),
                    'Description': request.POST.get('Description', '').strip(),
                    'Detail': request.POST.get('Detail', '').strip(),
                    'Github': request.POST.get('Github', '').strip(),
                    'Project': request.POST.get('Project', '').strip(),
                }
                if not all(new_project[key] for key in ('Name', 'Category', 'Description')):
                    messages.error(request, 'Project name, category, and description are required.')
                    return render(request, 'add_csv_project.html', {'project': new_project})
                if (
                    any(len(new_project[key]) > 100 for key in ('Name', 'Category'))
                    or len(new_project['Github']) > 200
                    or len(new_project['Project']) > 200
                ):
                    messages.error(request, 'Project name and category must be no longer than 100 characters; links must be no longer than 200.')
                    return render(request, 'add_csv_project.html', {'project': new_project})
                if not valid_project_links(new_project):
                    messages.error(request, 'Project links must be valid HTTP or HTTPS URLs.')
                    return render(request, 'add_csv_project.html', {'project': new_project})
                if data['Name'].astype(str).str.casefold().eq(new_project['Name'].casefold()).any():
                    messages.error(request, 'A project with this name already exists.')
                    return render(request, 'add_csv_project.html', {'project': new_project})

                serial_numbers = pd.to_numeric(data['S.No'], errors='coerce')
                highest_serial = serial_numbers.max()
                new_project['S.No'] = str((highest_serial if pd.notna(highest_serial) else 0) + 1)
                new_project = {column: new_project.get(column, '') for column in data.columns}
                data.loc[len(data)] = new_project
                save_projects_csv(data)
        except ProjectDataError as exc:
            return project_data_error(request, exc)
        messages.success(request, 'Project added successfully.')
        return redirect('CSV_Admin_Projects')
    return render(request, 'add_csv_project.html')


@cache_control(no_store=True, no_cache=True, must_revalidate=True)
@login_required_custom
def edit_csv_project(request, project_name):
    if request.method == 'POST':
        try:
            with lock_projects_csv():
                data = read_projects_csv()
                project = data[data['Name'].astype(str) == project_name]
                if project.empty:
                    raise Http404('Project not found.')
                index = project.index[0]
                updated_project = {
                    'Name': request.POST.get('Name', '').strip(),
                    'Category': request.POST.get('Category', '').strip(),
                    'Description': request.POST.get('Description', '').strip(),
                    'Detail': request.POST.get('Detail', '').strip(),
                    'Github': request.POST.get('Github', '').strip(),
                    'Project': request.POST.get('Project', '').strip(),
                }
                other_names = data.drop(index)['Name'].astype(str).str.casefold()
                if not all(updated_project[key] for key in ('Name', 'Category', 'Description')):
                    messages.error(request, 'Project name, category, and description are required.')
                elif (
                    any(len(updated_project[key]) > 100 for key in ('Name', 'Category'))
                    or len(updated_project['Github']) > 200
                    or len(updated_project['Project']) > 200
                ):
                    messages.error(request, 'Project name and category must be no longer than 100 characters; links must be no longer than 200.')
                elif not valid_project_links(updated_project):
                    messages.error(request, 'Project links must be valid HTTP or HTTPS URLs.')
                elif other_names.eq(updated_project['Name'].casefold()).any():
                    messages.error(request, 'A project with this name already exists.')
                else:
                    for field, value in updated_project.items():
                        data.loc[index, field] = value
                    save_projects_csv(data)
                    messages.success(request, 'Project updated successfully.')
                    return redirect('CSV_Admin_Projects')
                updated_project['S.No'] = data.loc[index, 'S.No']
                return render(request, 'edit_csv_project.html', {'project': updated_project})
        except ProjectDataError as exc:
            return project_data_error(request, exc)
        return redirect('CSV_Admin_Projects')

    try:
        data = read_projects_csv()
    except ProjectDataError as exc:
        return project_data_error(request, exc)
    project = data[data['Name'].astype(str) == project_name]
    if project.empty:
        raise Http404('Project not found.')
    return render(request, 'edit_csv_project.html', {'project': project.iloc[0].to_dict()})


@cache_control(no_store=True, no_cache=True, must_revalidate=True)
@login_required_custom
@require_POST
def delete_csv_project(request, project_name):
    try:
        with lock_projects_csv():
            data = read_projects_csv()
            if not data['Name'].astype(str).eq(project_name).any():
                raise Http404('Project not found.')
            data = data[data['Name'].astype(str) != project_name]
            save_projects_csv(data)
    except ProjectDataError as exc:
        return project_data_error(request, exc)
    messages.success(request, 'Project deleted successfully.')
    return redirect('CSV_Admin_Projects')


def login_page(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('CSV_Admin_Projects')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('CSV_Admin_Projects')
        messages.error(request, 'Invalid username or password, or this account is not an admin.')
    return render(request, 'login.html')


def valid_project_links(project):
    validate_url = URLValidator(schemes=('http', 'https'))
    try:
        for field in ('Github', 'Project'):
            if project[field]:
                validate_url(project[field])
    except ValidationError:
        return False
    return True


@login_required_custom
@require_POST
def logout_page(request):
    logout(request)
    return redirect('Index')


@cache_control(no_store=True, no_cache=True, must_revalidate=True)
@login_required_custom
@require_POST
def update_cv(request):
    uploaded_file = request.FILES.get('cv')
    if uploaded_file is None:
        messages.error(request, 'Choose a PDF file to upload.')
        return redirect('CSV_Admin_Projects')
    if Path(uploaded_file.name).suffix.lower() != '.pdf' or uploaded_file.size > MAX_CV_SIZE:
        messages.error(request, 'The CV must be a PDF no larger than 5 MB.')
        return redirect('CSV_Admin_Projects')
    temp_path = None
    try:
        CV_PATH.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=CV_PATH.parent, delete=False) as temp_file:
            temp_path = temp_file.name
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
        try:
            reader = PdfReader(temp_path, strict=True)
            if reader.is_encrypted or not reader.pages:
                messages.error(request, 'Upload a readable, unencrypted PDF containing at least one page.')
                return redirect('CSV_Admin_Projects')
        except (PdfReadError, ValueError):
            messages.error(request, 'The uploaded file is not a valid PDF.')
            return redirect('CSV_Admin_Projects')
        os.replace(temp_path, CV_PATH)
    except OSError:
        logger.exception('Unable to save the uploaded portfolio CV.')
        messages.error(request, 'The CV could not be saved. Your existing CV has not been changed.')
        return redirect('CSV_Admin_Projects')
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

    messages.success(request, 'Your CV has been updated.')
    return redirect('CSV_Admin_Projects')


def download_cv(request):
    if request.method not in ('GET', 'HEAD'):
        return HttpResponseNotAllowed(['GET', 'HEAD'])
    if not CV_PATH.is_file():
        raise Http404('CV not found.')
    return FileResponse(CV_PATH.open('rb'), as_attachment=True, filename=CV_PATH.name)
