from django.contrib import admin
from . models import Community, Pioneer

# Register your models here.
admin.site.register(Community)

@admin.register(Pioneer)
class PioneerAdmin(admin.ModelAdmin):
    list_display = ('pioneer_name', 'position', 'pioneer_social_link', 'has_image')
    list_filter = ('position',)
    search_fields = ('pioneer_name', 'position', 'bio')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('pioneer_name', 'position')
        }),
        ('Profile', {
            'fields': ('bio', 'profile_image')
        }),
        ('Social Media', {
            'fields': ('pioneer_social_link',)
        }),
    )
    
    def has_image(self, obj):
        return "✅" if obj.profile_image else "❌"
    has_image.short_description = "Image"