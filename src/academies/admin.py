"""Django admin registrations for the academies app."""

from django.contrib import admin

from academies.models import Academy, Membership, Sport


@admin.register(Academy)
class AcademyAdmin(admin.ModelAdmin):
    """Admin for :class:`academies.models.Academy`."""

    filter_horizontal = ("sports",)


admin.site.register(Sport)
admin.site.register(Membership)
