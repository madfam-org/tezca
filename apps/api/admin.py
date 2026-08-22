"""Django admin for the fiscal-value feed.

Operator-entry surface for the values Tezca serves. Registered on the
default admin site, which `apps/indigo/urls.py` mounts at ``/admin/`` and
which Django gates to ``is_staff`` users — so this is staff-only CRUD.

Deliberately read-mostly: the feed is append-only by design (a correction
is a new row with a later ``vigencia_from``, never an edit of a published
one), so ``created_at`` is read-only everywhere and delete is disabled for
DOF-published rows. An operator who needs to retract a published value
closes its ``vigencia_to`` instead of erasing history.
"""

from django.contrib import admin

from .fiscal_models import FiscalTable, MinimumWage, Provenance, UMAValue


class _AppendOnlyAdmin(admin.ModelAdmin):
    """Shared policy: history is not erased, only superseded."""

    readonly_fields = ["created_at"]

    def has_delete_permission(self, request, obj=None):
        """Published rows are part of the citation record — never deleted."""
        if obj is not None and obj.provenance == Provenance.PUBLISHED:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(UMAValue)
class UMAValueAdmin(_AppendOnlyAdmin):
    list_display = [
        "year",
        "value",
        "monthly_value",
        "annual_value",
        "vigencia_from",
        "vigencia_to",
        "provenance",
        "dof_date",
    ]
    list_filter = ["provenance", "year"]
    search_fields = ["year", "source_citation", "notes"]
    ordering = ["-vigencia_from"]


@admin.register(MinimumWage)
class MinimumWageAdmin(_AppendOnlyAdmin):
    list_display = [
        "year",
        "zone",
        "value",
        "vigencia_from",
        "vigencia_to",
        "provenance",
        "dof_date",
    ]
    list_filter = ["provenance", "zone", "year"]
    search_fields = ["year", "source_citation", "notes"]
    ordering = ["-vigencia_from", "zone"]


@admin.register(FiscalTable)
class FiscalTableAdmin(_AppendOnlyAdmin):
    list_display = [
        "kind",
        "year",
        "period",
        "row_count",
        "vigencia_from",
        "provenance",
        "dof_date",
    ]
    list_filter = ["provenance", "kind", "year"]
    search_fields = ["year", "kind", "legal_basis", "source_citation", "notes"]
    ordering = ["-year", "kind"]

    @admin.display(description="Rows")
    def row_count(self, obj):
        return len(obj.rows) if isinstance(obj.rows, list) else 0
