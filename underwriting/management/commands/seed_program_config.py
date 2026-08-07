from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from underwriting.models import (
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


class Command(BaseCommand):
    help = "Seed the partner program configuration."

    @transaction.atomic
    def handle(self, *args, **options):
        # Existing rating engine used by this program version.
        rating_engine, _ = (
            RatingEngineVersion.objects.update_or_create(
                version=100,
                defaults={
                    "effective_date": date(2026, 1, 1),
                    "endpoint_url": (
                        "https://fake-rater.local/v100"
                    ),
                },
            )
        )

        # Existing coverage used by the program.
        epl_coverage, _ = Coverage.objects.update_or_create(
            code="epl",
            defaults={
                "name": "Employment Practices Liability",
                "description": (
                    "Coverage for employment-related claims."
                ),
                "is_active": True,
            },
        )

        # Who is distributing the program?
        partner, _ = (
            DistributionPartner.objects.update_or_create(
                code="acme",
                defaults={
                    "name": "Acme Insurance Partners",
                    "is_active": True,
                },
            )
        )

        # Which program is the partner offering?
        program, _ = Program.objects.update_or_create(
            distribution_partner=partner,
            code="pest_control",
            defaults={
                "name": "Pest Control Insurance Program",
                "description": (
                    "Insurance program for pest control "
                    "businesses."
                ),
                "is_active": True,
            },
        )

        # Exact version of the program configuration.
        program_version, _ = (
            ProgramVersion.objects.update_or_create(
                program=program,
                version=1,
                defaults={
                    "rating_engine_version": rating_engine,
                    "status": ProgramVersion.Status.PUBLISHED,
                    "effective_date": date(2026, 8, 1),
                    "expiration_date": None,
                },
            )
        )

        question_data = [
            {
                "key": "industry",
                "text": "What industry is the business in?",
                "type": ProgramQuestion.QuestionType.TEXT,
                "required": True,
                "order": 1,
                "help_text": "",
            },
            {
                "key": "industry_other",
                "text": "Please describe the industry.",
                "type": ProgramQuestion.QuestionType.TEXT,
                "required": False,
                "order": 2,
                "help_text": (
                    "Provide additional details when needed."
                ),
            },
            {
                "key": "annual_revenue",
                "text": (
                    "What is the company's annual revenue?"
                ),
                "type": ProgramQuestion.QuestionType.NUMBER,
                "required": True,
                "order": 3,
                "help_text": (
                    "Enter gross annual revenue in dollars."
                ),
            },
            {
                "key": "employee_count",
                "text": (
                    "How many employees does the company have?"
                ),
                "type": ProgramQuestion.QuestionType.NUMBER,
                "required": True,
                "order": 4,
                "help_text": "",
            },
        ]

        questions = {}

        for item in question_data:
            question, _ = ProgramQuestion.objects.update_or_create(
                program_version=program_version,
                question_key=item["key"],
                defaults={
                    "question_text": item["text"],
                    "question_type": item["type"],
                    "is_required": item["required"],
                    "display_order": item["order"],
                    "help_text": item["help_text"],
                    "default_value": None,
                    "is_active": True,
                },
            )

            questions[item["key"]] = question

        # Map applicant answers to rating engine keys.
        for question_key in [
            "industry",
            "industry_other",
            "annual_revenue",
            "employee_count",
        ]:
            ProgramRatingConfig.objects.update_or_create(
                program_version=program_version,
                rating_engine_key=question_key,
                defaults={
                    "value_source": (
                        ProgramRatingConfig
                        .ValueSource
                        .DIRECT_ANSWER
                    ),
                    "source_question": questions[question_key],
                    "static_value": None,
                    "is_required": (
                        question_key != "industry_other"
                    ),
                    "description": (
                        f"Send the {question_key} answer "
                        "directly to the rating engine."
                    ),
                },
            )

        # Example static input that is not asked as a question.
        ProgramRatingConfig.objects.update_or_create(
            program_version=program_version,
            rating_engine_key="partner_program_code",
            defaults={
                "value_source": (
                    ProgramRatingConfig
                    .ValueSource
                    .STATIC_VALUE
                ),
                "source_question": None,
                "static_value": "ACME_PEST",
                "is_required": True,
                "description": (
                    "Identifies the partner program to the "
                    "rating engine."
                ),
            },
        )

        # Discounts allowed by this program version.
        ProgramDiscountConfig.objects.update_or_create(
            program_version=program_version,
            code="discount_1",
            defaults={
                "name": "Underwriter Discount 1",
                "description": (
                    "Primary discretionary underwriter discount."
                ),
                "rating_engine_key": "discount_1",
                "discount_type": (
                    ProgramDiscountConfig
                    .DiscountType
                    .PERCENTAGE
                ),
                "application_type": (
                    ProgramDiscountConfig
                    .ApplicationType
                    .MANUAL
                ),
                "default_value": Decimal("0.0000"),
                "minimum_value": Decimal("0.0000"),
                "maximum_value": Decimal("0.2500"),
                "requires_approval": False,
                "display_order": 1,
                "is_active": True,
            },
        )

        ProgramDiscountConfig.objects.update_or_create(
            program_version=program_version,
            code="discount_2",
            defaults={
                "name": "Underwriter Discount 2",
                "description": (
                    "Secondary discretionary underwriter "
                    "discount."
                ),
                "rating_engine_key": "discount_2",
                "discount_type": (
                    ProgramDiscountConfig
                    .DiscountType
                    .PERCENTAGE
                ),
                "application_type": (
                    ProgramDiscountConfig
                    .ApplicationType
                    .MANUAL
                ),
                "default_value": Decimal("0.0000"),
                "minimum_value": Decimal("0.0000"),
                "maximum_value": Decimal("0.1000"),
                "requires_approval": False,
                "display_order": 2,
                "is_active": True,
            },
        )

        # Coverage offered by this program version.
        ProgramCoverageConfig.objects.update_or_create(
            program_version=program_version,
            coverage=epl_coverage,
            defaults={
                "is_available": True,
                "is_required": True,
                "default_limit": Decimal("5000000.00"),
                "default_deductible": Decimal("25000.00"),
                "minimum_limit": Decimal("1000000.00"),
                "maximum_limit": Decimal("5000000.00"),
                "display_order": 1,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded Acme Pest Control Program v1."
            )
        )