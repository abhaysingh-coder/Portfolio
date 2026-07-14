from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import *

admin.site.site_header = "Abhay Singh Portfolio Admin"
admin.site.site_title = "Portfolio Admin"
admin.site.index_title = "Welcome to Portfolio Dashboard"

admin.site.register(Request)


class CSVAdmin(admin.ModelAdmin):

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['csv_link'] = reverse('CSV_Admin_Projects')
        return super().changelist_view(request, extra_context)
