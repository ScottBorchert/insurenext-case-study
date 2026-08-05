from django.contrib import admin

from .models import (
    Application,
    ApplicationAnswer,
    ApplicationCoverage,
    ApplicationQuestion,
    Company,
    RatingEngineVersion,
)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "legal_name",
        "dba_name",
        "state",
        "created_at",
    )
    search_fields = ("legal_name", "dba_name")


@admin.register(RatingEngineVersion)
class RatingEngineVersionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "version",
        "effective_date",
        "endpoint_url",
    )


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "company",
        "status",
        "rating_engine_version",
        "created_at",
    )
    list_filter = ("status", "rating_engine_version")


@admin.register(ApplicationQuestion)
class ApplicationQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "rating_engine_question_key",
        "question_text",
        "rating_engine_version",
        "is_pricing_modifier",
    )
    list_filter = (
        "rating_engine_version",
        "is_pricing_modifier",
    )


@admin.register(ApplicationAnswer)
class ApplicationAnswerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "application",
        "question",
        "answer_text",
    )


@admin.register(ApplicationCoverage)
class ApplicationCoverageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "application",
        "coverage_id",
        "limit",
        "deductible",
        "computed_premium",
        "coverage_denied",
    )