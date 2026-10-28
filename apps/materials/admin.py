from django.contrib import admin

from .models import Material


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'kind', 'size', 'created_at')
    search_fields = ('title', 'original_name')
