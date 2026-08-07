from django.contrib import admin

from .models import (
    Application,
    ApplicationAnswer,
    ApplicationCoverage,
    ApplicationDiscount,
    ApplicationQuestion,
    Company,
    Coverage,
    DistributionPartner,
    Program,
    ProgramCoverageConfig,
    ProgramDiscountConfig,
    ProgramQuestion,
    ProgramRatingConfig,
    ProgramVersion,
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
        "program_version",
        "rating_engine_version",
        "created_at",
    )

    list_filter = (
        "status",
        "program_version",
        "rating_engine_version",
    )


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
        "program_question",
        "answer_text",
    )

    list_filter = ("application__program_version",)


@admin.register(ApplicationCoverage)
class ApplicationCoverageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "application",
        "coverage",
        "limit",
        "deductible",
        "computed_premium",
        "coverage_denied",
    )

@admin.register(Coverage)
class CoverageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "code",
        "name",
        "is_active",
    )

    search_fields = (
        "code",
        "name",
    )

    list_filter = (
        "is_active",
    )

@admin.register(DistributionPartner)
class DistributionPartnerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "code",
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "code",
    )

    list_filter = (
        "is_active",
    )

@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "code",
        "distribution_partner",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
        "distribution_partner__name",
    )

    list_filter = (
        "distribution_partner",
        "is_active",
    )


@admin.register(ProgramVersion)
class ProgramVersionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "program",
        "version",
        "rating_engine_version",
        "status",
        "effective_date",
        "expiration_date",
    )

    list_filter = (
        "status",
        "rating_engine_version",
        "program__distribution_partner",
    )

@admin.register(ProgramQuestion)
class ProgramQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "question_key",
        "question_text",
        "program_version",
        "question_type",
        "is_required",
        "display_order",
        "is_active",
    )

    search_fields = (
        "question_key",
        "question_text",
    )

    list_filter = (
        "program_version",
        "question_type",
        "is_required",
        "is_active",
    )

@admin.register(ProgramRatingConfig)
class ProgramRatingConfigAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "program_version",
        "rating_engine_key",
        "value_source",
        "source_question",
        "is_required",
    )

    list_filter = (
        "program_version",
        "value_source",
        "is_required",
    )

@admin.register(ProgramDiscountConfig)
class ProgramDiscountConfigAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "program_version",
        "code",
        "name",
        "discount_type",
        "application_type",
        "maximum_value",
        "requires_approval",
        "is_active",
    )

    list_filter = (
        "program_version",
        "discount_type",
        "application_type",
        "requires_approval",
        "is_active",
    )

@admin.register(ProgramCoverageConfig)
class ProgramCoverageConfigAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "program_version",
        "coverage",
        "is_available",
        "is_required",
        "default_limit",
        "default_deductible",
    )

    list_filter = (
        "program_version",
        "coverage",
        "is_available",
        "is_required",
    )


@admin.register(ApplicationDiscount)
class ApplicationDiscountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "application",
        "discount_config",
        "discount_value",
        "created_at",
    )

    list_filter = (
        "discount_config__program_version",
        "discount_config",
    )

    search_fields = (
        "application__company__legal_name",
        "discount_config__name",
        "discount_config__code",
    )