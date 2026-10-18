"""
URL configuration for Portfolio project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from mainapp import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='Index'),
    path('Error', views.error, name='Error'),
    path('About', views.about, name='About'),
    path('Skills', views.skills, name='Skills'),
    path('Projects', views.projects, name='Projects'),
    path('Projects/<str:project_name>/', views.projectdetail, name='Project_Detail'),
    path('Contact', views.contact, name='Contact'),
    path('admins',views.login_page, name='Login'),
    path('admins/logout/', views.logout_page, name='Logout'),
    path('cv/download/', views.download_cv, name='Download_CV'),
    path('csv-projects/', views.csv_admin_projects, name='CSV_Admin_Projects'),
    path('csv-projects/add/', views.add_csv_project, name='CSV_Add_Project'),
    path('csv-projects/edit/<str:project_name>/', views.edit_csv_project, name='CSV_Edit_Project'),
    path('csv-projects/delete/<str:project_name>/', views.delete_csv_project, name='CSV_Delete_Project'),
    path('csv-projects/cv/', views.update_cv, name='CSV_Update_CV'),
]

handler400 = 'mainapp.views.bad_request'
handler403 = 'mainapp.views.permission_denied'
handler404 = 'mainapp.views.page_not_found'
handler500 = 'mainapp.views.server_error'
