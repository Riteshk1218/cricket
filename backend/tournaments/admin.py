from django.contrib import admin

from .models import Ground, Player, PointsTableEntry, Team, Tournament, TournamentRegistration


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("name", "match_format", "ball_type", "kind", "start_date", "status")
    list_filter = ("status", "match_format", "ball_type")
    filter_horizontal = ("admins", "grounds")


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "team", "role")
    list_filter = ("role", "team")
    search_fields = ("full_name",)


admin.site.register([Ground, Team, TournamentRegistration, PointsTableEntry])
