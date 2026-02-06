from django.contrib import admin

from .models import AcquisitionLog, DataSource, GapRecord


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "source_type",
        "level",
        "state",
        "status",
        "last_check",
        "response_time_ms",
    ]
    list_filter = ["source_type", "level", "status"]
    search_fields = ["name", "state", "municipality", "base_url"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(GapRecord)
class GapRecordAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "level",
        "state",
        "gap_type",
        "status",
        "current_tier",
        "priority",
        "next_action_date",
    ]
    list_filter = ["status", "current_tier", "level", "gap_type", "state"]
    search_fields = ["law_name", "state", "municipality", "description"]
    readonly_fields = ["created_at", "updated_at"]
    actions = ["bulk_escalate"]

    @admin.action(description="Escalate selected gaps to next tier")
    def bulk_escalate(self, request, queryset):
        count = 0
        for gap in queryset.filter(status__in=["open", "in_progress"]):
            gap.escalate(
                action_taken="Bulk escalation via admin",
                result="Escalated to next tier",
            )
            count += 1
        self.message_user(request, f"Escalated {count} gap(s).")


@admin.register(AcquisitionLog)
class AcquisitionLogAdmin(admin.ModelAdmin):
    list_display = [
        "operation",
        "source",
        "started_at",
        "finished_at",
        "found",
        "downloaded",
        "failed",
        "ingested",
    ]
    list_filter = ["operation"]
    search_fields = ["operation", "error_summary"]
    readonly_fields = ["started_at"]
