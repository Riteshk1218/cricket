from django.contrib import admin

from .models import LiveConnection, PageView

admin.site.register(PageView)
admin.site.register(LiveConnection)
