from django.shortcuts import render
import numpy as np
import pandas as pd
from django.core.mail import send_mail
from django.conf import settings
from .models import Projects

data = pd.read_csv('Data.csv')
data = data.replace({np.nan: None})


def mail(subject, name, email, message):
    send_mail(
    subject=f'Portfolio Contact: {subject}',
    message=f'''You have a Message from {name} whose Email is {email} and the Message is :-\n{message}''', 
    from_email=settings.EMAIL_HOST_USER, 
    recipient_list=['srinetabhaysingh14@gmail.com'], 
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
        context ={
            'count_project': Projects.objects.count()
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
        context ={
            'projects': Projects.objects.all(),
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
        context ={}
        return render(request, 'contact.html', context)
    except Exception as e:
        return render(request, 'error.html', {'error':e})
    
def projectdetail(request, project_name):
    try:
        project = Projects.objects.filter(Name = project_name).first()
        if project is None:
            return render(request, 'error.html', {'error': 'Project Not Found'})
        context ={
            'project': project,
        }
        return render(request, 'projectdetail.html', context)
    except Exception as e:
        return render(request, 'error.html', {'error':e})
    

def project_database(request):
    try:
        message = None
        data = pd.read_csv('Data.csv')
        data = data.replace({np.nan: ''})
        if request.method == 'POST':
            count = 0

            for _, row in data.iterrows():
                Projects.objects.update_or_create(
                    Name=row['Name'],
                    defaults={
                        'Category': row.get('Category', ''),
                        'Description': row.get('Description', ''),
                        'Detail': row.get('Detail', ''),
                        'Github': row.get('Github', ''),
                        'Project': row.get('Project', ''),
                    }
                )
                count += 1

            message = f'{count} records added/updated successfully.'

        context = {
            'db_count': Projects.objects.count(),
            'csv_count': len(data),
            'message': message
        }

        return render(request, 'project_database.html', context)

    except Exception as e:
        return render(request, 'error.html', {'error': e})