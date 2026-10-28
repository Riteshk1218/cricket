from django.contrib import admin

from .models import Delivery, Innings, Match, MatchResult, MatchSquad, ScorerAssignment, ScoringCorrection, Wicket


class InningsInline(admin.TabularInline):
    model = Innings
    extra = 0
    fields = ("number", "batting_team", "status", "total_runs", "wickets", "legal_balls")
    readonly_fields = fields
    can_delete = False


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("__str__", "tournament", "stage", "status", "scheduled_at", "ground")
    list_filter = ("status", "stage", "tournament")
    inlines = [InningsInline]


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("innings", "sequence", "over_number", "ball_in_over", "striker", "bowler", "runs_bat",
                    "wides", "noballs", "byes", "legbyes", "is_wicket", "voided")
    list_filter = ("voided", "is_wicket")

    def has_change_permission(self, request, obj=None):
        # Corrections must go through the scoring API so they are replayed and audited.
        return False


admin.site.register([Innings, MatchSquad, ScorerAssignment, ScoringCorrection, MatchResult, Wicket])
