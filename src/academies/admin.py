"""Django admin registrations for the academies app."""

from django.contrib import admin

from academies.models import Academy, Membership

admin.site.register(Academy)
admin.site.register(Membership)
