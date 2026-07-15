from django.shortcuts import render, redirect
import numpy as np
import pandas as pd
from django.core.mail import send_mail
from django.conf import settings
from .models import *
import os
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required

CSV_PATH = os.path.join(settings.BASE_DIR, 'Data.csv')

def read_projects_csv():
    data = pd.read_csv(CSV_PATH)
    data = data.replace({np.nan: None})
    return data

def mail(subject, name, email, message):
    send_mail(
    subject=f'Portfolio Contact: {subject}',
    message=f'''You have a Message from {name} whose Email is {email} and the Message is :-\n{message}''', 
    from_email=settings.EMAIL_CONFIGS['portfolio']['host_user'], 
    recipient_list=['srinetabhaysingh14@gmail.com'], 
    fail_silently=False
    )


def confirmationmail(subject, name, email, message):
    send_mail(
        subject=f'Thank You for Contacting Me',
        message=f'''Dear { name },\nThank you for reaching out through my portfolio website.\n\nI have successfully received your message and will review it shortly. I appreciate your interest and will get back to you as soon as possible.\n\nHere is a copy of your submission:\n\nName: { name }\nEmail: { email }\nSubject: { subject }\n\nMessage:\n{ message }\n\nThank you for your time.\n\nBest Regards,\n\nAbhay Singh\nData Analyst | Data Science Enthusiast | Django Developer\nPortfolio: https://portfolio-m1il.onrender.com''',
        from_email=settings.EMAIL_CONFIGS['personal']['host_user'],
        recipient_list=[email],
        fail_silently=False
    )

# Create your views here.
def index(request):
    try:
        return render(request, 'index.html')
    except Exception as e:
        return render(request, 'error.html', {'error':e})

def about(request):
    try:
        data = read_projects_csv()
        context ={
            'count_project': data['S.No'].count()
        }
        return render(request, 'about.html', context)
    except Exception as e:
        return render(request, 'error.html', {'error':e})

def skills(request):
    try:
        return render(request, 'skills.html')
    except Exception as e:
        return render(request, 'error.html', {'error':e})
    
def projects(request):
    try:
        data = read_projects_csv()
        context ={
            'projects': data.to_dict('records'),
        }
        return render(request, 'projects.html', context)
    except Exception as e:
        return render(request, 'error.html', {'error':e})
        
def error(request):
        return render(request, 'error.html')

def contact(request):
    try:
        if request.method == 'POST':
            name = request.POST.get('name')
            email = request.POST.get('email')
            subject = request.POST.get('subject')
            message = request.POST.get('message')
            mail(subject, name, email, message)
            confirmationmail(subject, name, email, message)
            Request.objects.create(Name=name, Email=email, Subject=subject, Message=message)

        context ={}
        return render(request, 'contact.html', context)
    except Exception as e:
        return render(request, 'error.html', {'error':e})
    
def projectdetail(request, project_name):
    try:
        data = read_projects_csv()
        project = data[data['Name'] == project_name]
        if project.empty:
            return render(request, 'error.html', {'error': 'Project Not Found'})
        context ={
            'project': project.to_dict('records'),
        }
        return render(request, 'projectdetail.html', context)
    except Exception as e:
        return render(request, 'error.html', {'error':e})
 
def save_projects_csv(data):
    data.to_csv(CSV_PATH, index=False)

@login_required(login_url='login')
def csv_admin_projects(request):
    try:
        data = read_projects_csv()
        context = {
            'projects': data.to_dict('records'),
            'total_projects': len(data),
        }
        return render(request, 'csv_admin_projects.html', context)
    except Exception as e:
        return render(request, 'error.html', {'error': e})

@login_required(login_url='login')
def add_csv_project(request):
    try:
        if request.method == 'POST':
            data = read_projects_csv()
            new_project = {
                'Name': request.POST.get('Name'),
                'Category': request.POST.get('Category'),
                'Description': request.POST.get('Description'),
                'Detail': request.POST.get('Detail'),
                'Github': request.POST.get('Github'),
                'Project': request.POST.get('Project'),
            }
            data.loc[len(data)] = new_project
            save_projects_csv(data)
            return redirect('CSV_Admin_Projects')
        return render(request, 'add_csv_project.html')
    except Exception as e:
        return render(request, 'error.html', {'error': e})

@login_required(login_url='login')
def edit_csv_project(request, project_name):
    try:
        data = read_projects_csv()
        project = data[data['Name'] == project_name]
        if project.empty:
            return render(request, 'error.html', {'error': 'Project not found'})
        index = project.index[0]
        if request.method == 'POST':
            data.loc[index, 'Name'] = request.POST.get('Name')
            data.loc[index, 'Category'] = request.POST.get('Category')
            data.loc[index, 'Description'] = request.POST.get('Description')
            data.loc[index, 'Detail'] = request.POST.get('Detail')
            data.loc[index, 'Github'] = request.POST.get('Github')
            data.loc[index, 'Project'] = request.POST.get('Project')
            save_projects_csv(data)
            return redirect('CSV_Admin_Projects')
        context = {
            'project': project.iloc[0].to_dict()
        }
        return render(request, 'edit_csv_project.html', context)
    except Exception as e:
        return render(request, 'error.html', {'error': e})

@login_required(login_url='login')
def delete_csv_project(request, project_name):
    try:
        data = read_projects_csv()
        data = data[data['Name'] != project_name]
        save_projects_csv(data)
        return redirect('CSV_Admin_Projects')
    except Exception as e:
        return render(request, 'error.html', {'error': e})
    
def login_page(request):
    try:
        if request.method == "POST":
            username = request.POST.get("username")
            password = request.POST.get("password")

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('CSV_Admin_Projects')
            else:
                raise Exception("Invalid username or password")
        return render(request, 'login.html')
    except Exception as e:
        return render(request, 'error.html', {'error': e})