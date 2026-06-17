from django.contrib import admin
from .models import Projects

admin.site.site_header = "Abhay Singh Portfolio Admin"
admin.site.site_title = "Portfolio Admin"
admin.site.index_title = "Welcome to Portfolio Dashboard"

admin.site.register(Projects)