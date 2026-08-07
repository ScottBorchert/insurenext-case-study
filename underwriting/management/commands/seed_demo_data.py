from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from underwriting.models import (
    Application,
    ApplicationAnswer,
    ApplicationCoverage,
    ApplicationQuestion,
    Company,
    Coverage,
    DistributionPartner,
    Program,
    ProgramDiscountConfig,
    ProgramQuestionConfig,
    ProgramRatingConfig,
    ProgramVersion,
    RatingEngineVersion,
)


class Command(BaseCommand):
    help = "Seed InsureNext demo data for the partner program case study."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Seeding InsureNext demo data...")

        # ---------------------------------------------------------
        # Rating Engine
        # ---------------------------------------------------------

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

        # ---------------------------------------------------------
        # Coverages
        # ---------------------------------------------------------

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

        cyber_coverage, _ = Coverage.objects.update_or_create(
            code="cyber",
            defaults={
                "name": "Cyber Liability",
                "description": (
                    "Coverage for cyber incidents and "
                    "data breaches."
                ),
                "is_active": True,
            },
        )

        # ---------------------------------------------------------
        # Core Application Questions
        #
        # These remain authoritative for BOTH standard and
        # partner applications.
        # ---------------------------------------------------------

        question_data = [
            {
                "key": "industry",
                "text": "What industry is the business in?",
                "pricing_modifier": False,
            },
            {
                "key": "industry_other",
                "text": "Please describe the industry.",
                "pricing_modifier": False,
            },
            {
                "key": "annual_revenue",
                "text": (
                    "What is the company's annual revenue?"
                ),
                "pricing_modifier": False,
            },
            {
                "key": "employee_count",
                "text": (
                    "How many employees does the company have?"
                ),
                "pricing_modifier": False,
            },
            {
                "key": "business_state",
                "text": (
                    "In what state is the business located?"
                ),
                "pricing_modifier": False,
            },
            {
                "key": "prior_claims",
                "text": (
                    "Has the company had any claims "
                    "in the last five years?"
                ),
                "pricing_modifier": False,
            },
            {
                "key": "discount_1",
                "text": "Primary underwriter discount",
                "pricing_modifier": True,
            },
            {
                "key": "discount_2",
                "text": "Secondary underwriter discount",
                "pricing_modifier": True,
            },
        ]

        questions = {}

        for item in question_data:
            question, _ = (
                ApplicationQuestion.objects.update_or_create(
                    rating_engine_version=rating_engine,
                    rating_engine_question_key=item["key"],
                    defaults={
                        "question_text": item["text"],
                        "is_pricing_modifier": (
                            item["pricing_modifier"]
                        ),
                    },
                )
            )

            questions[item["key"]] = question

        # =========================================================
        # STANDARD / LEGACY APPLICATION
        # =========================================================

        standard_company, _ = Company.objects.update_or_create(
            legal_name="North Star Landscaping LLC",
            defaults={
                "dba_name": "North Star Landscaping",
                "url": "https://northstar.example.com",
                "address1": "1250 Lake Street",
                "address2": "",
                "city": "Minneapolis",
                "state": "MN",
                "zip": "55408",
            },
        )

        standard_application, _ = (
            Application.objects.get_or_create(
                company=standard_company,
                rating_engine_version=rating_engine,
                program_version=None,
                defaults={
                    "status": Application.Status.SUBMITTED,
                },
            )
        )

        standard_answers = {
            "industry": "Landscaping",
            "industry_other": "",
            "annual_revenue": "2200000",
            "employee_count": "28",
            "business_state": "MN",
            "prior_claims": "false",

            # Discounts still live in ApplicationAnswer.
            "discount_1": "0.05",
            "discount_2": "0.02",
        }

        self._seed_answers(
            standard_application,
            questions,
            standard_answers,
        )

        ApplicationCoverage.objects.update_or_create(
            application=standard_application,
            coverage=epl_coverage,
            defaults={
                "limit": Decimal("2000000.00"),
                "deductible": Decimal("10000.00"),
                "computed_premium": None,
                "coverage_denied": False,
                "additional_details": {},
                "rating_engine_response": {},
            },
        )

        # =========================================================
        # PARTNER MODEL
        # =========================================================

        partner, _ = (
            DistributionPartner.objects.update_or_create(
                code="acme",
                defaults={
                    "name": "Acme Insurance Partners",
                    "is_active": True,
                },
            )
        )

        program, _ = Program.objects.update_or_create(
            distribution_partner=partner,
            code="pest_control",
            defaults={
                "name": "Pest Control Insurance Program",
                "description": (
                    "Partner-distributed insurance program "
                    "for pest control businesses."
                ),
                "is_active": True,
            },
        )

        program_version, _ = (
            ProgramVersion.objects.update_or_create(
                program=program,
                version=1,
                defaults={
                    "rating_engine_version": rating_engine,
                    "status": (
                        ProgramVersion.Status.PUBLISHED
                    ),
                    "effective_date": date(2026, 8, 1),
                    "expiration_date": None,
                },
            )
        )

        # ---------------------------------------------------------
        # Program Question Configuration
        #
        # IMPORTANT:
        # These reference existing ApplicationQuestion rows.
        # No questions or rating keys are duplicated.
        # ---------------------------------------------------------

        ProgramQuestionConfig.objects.update_or_create(
            program_version=program_version,
            question=questions["industry"],
            defaults={
                "question_text_override": (
                    "What type of pest control services "
                    "does your business provide?"
                ),
                "default_answer_text": "Pest Control",
                "is_answer_locked": True,
                "display_order": 1,
                "is_active": True,
            },
        )

        ProgramQuestionConfig.objects.update_or_create(
            program_version=program_version,
            question=questions["annual_revenue"],
            defaults={
                "question_text_override": (
                    "What was your pest control business's "
                    "gross revenue during the last 12 months?"
                ),
                "default_answer_text": None,
                "is_answer_locked": False,
                "display_order": 2,
                "is_active": True,
            },
        )

        ProgramQuestionConfig.objects.update_or_create(
            program_version=program_version,
            question=questions["business_state"],
            defaults={
                "question_text_override": (
                    "In which state is your primary "
                    "pest control operation located?"
                ),
                "default_answer_text": "MN",
                "is_answer_locked": True,
                "display_order": 3,
                "is_active": True,
            },
        )

        ProgramQuestionConfig.objects.update_or_create(
            program_version=program_version,
            question=questions["prior_claims"],
            defaults={
                "question_text_override": (
                    "Has your pest control business had "
                    "any insurance claims in the last "
                    "five years?"
                ),
                "default_answer_text": "false",
                "is_answer_locked": False,
                "display_order": 4,
                "is_active": True,
            },
        )

        # ---------------------------------------------------------
        # Program Rating Configuration
        #
        # These are the new values that Django will resolve
        # into the optional rating_config JSON object.
        # ---------------------------------------------------------

        rating_configs = {
            "partner_program_code": {
                "value": "ACME_PEST",
                "description": (
                    "Identifies the Acme Pest Control "
                    "program to the rating engine."
                ),
            },
            "territory_factor": {
                "value": 1.15,
                "description": (
                    "Program-specific territory rating "
                    "factor."
                ),
            },
            "program_tier": {
                "value": "preferred",
                "description": (
                    "Partner-specific underwriting tier."
                ),
            },
        }

        for key, config in rating_configs.items():
            ProgramRatingConfig.objects.update_or_create(
                program_version=program_version,
                config_key=key,
                defaults={
                    "config_value": config["value"],
                    "description": config["description"],
                    "is_active": True,
                },
            )

        # ---------------------------------------------------------
        # Program Discount Configuration
        #
        # These reference the existing pricing-modifier
        # ApplicationQuestions.
        #
        # Actual applied values still live in
        # ApplicationAnswer.
        # ---------------------------------------------------------

        ProgramDiscountConfig.objects.update_or_create(
            program_version=program_version,
            question=questions["discount_1"],
            defaults={
                "name": "Preferred Program Discount",
                "description": (
                    "Primary discretionary discount "
                    "available through the Acme program."
                ),
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
                "maximum_value": Decimal("0.1500"),
                "requires_approval": False,
                "display_order": 1,
                "is_active": True,
            },
        )

        ProgramDiscountConfig.objects.update_or_create(
            program_version=program_version,
            question=questions["discount_2"],
            defaults={
                "name": "Manager Approval Discount",
                "description": (
                    "Additional discretionary discount "
                    "requiring approval."
                ),
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
                "requires_approval": True,
                "display_order": 2,
                "is_active": True,
            },
        )

        # =========================================================
        # PARTNER APPLICATION
        # =========================================================

        partner_company, _ = Company.objects.update_or_create(
            legal_name="Bug Away Pest Control LLC",
            defaults={
                "dba_name": "Bug Away",
                "url": "https://bugaway.example.com",
                "address1": "100 Main Street",
                "address2": "",
                "city": "Minneapolis",
                "state": "MN",
                "zip": "55401",
            },
        )

        partner_application, _ = (
            Application.objects.get_or_create(
                company=partner_company,
                rating_engine_version=rating_engine,
                program_version=program_version,
                defaults={
                    "status": Application.Status.SUBMITTED,
                },
            )
        )

        # Notice that these are STILL ApplicationAnswer rows
        # pointing to the canonical ApplicationQuestion.
        #
        # The values for industry, business_state, and
        # prior_claims demonstrate answers that could have
        # originated from ProgramQuestionConfig defaults.

        partner_answers = {
            "industry": "Pest Control",
            "industry_other": (
                "Residential and commercial pest management"
            ),
            "annual_revenue": "1500000",
            "employee_count": "35",
            "business_state": "MN",
            "prior_claims": "false",

            # Applied program discounts are STILL answers.
            "discount_1": "0.10",
            "discount_2": "0.05",
        }

        self._seed_answers(
            partner_application,
            questions,
            partner_answers,
        )

        ApplicationCoverage.objects.update_or_create(
            application=partner_application,
            coverage=epl_coverage,
            defaults={
                "limit": Decimal("5000000.00"),
                "deductible": Decimal("25000.00"),
                "computed_premium": None,
                "coverage_denied": False,
                "additional_details": {},
                "rating_engine_response": {},
            },
        )

        ApplicationCoverage.objects.update_or_create(
            application=partner_application,
            coverage=cyber_coverage,
            defaults={
                "limit": Decimal("1000000.00"),
                "deductible": Decimal("10000.00"),
                "computed_premium": None,
                "coverage_denied": False,
                "additional_details": {},
                "rating_engine_response": {},
            },
        )

        # ---------------------------------------------------------
        # Summary
        # ---------------------------------------------------------

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "InsureNext demo data seeded successfully."
            )
        )

        self.stdout.write(
            f"  Rating Engine: v{rating_engine.version}"
        )

        self.stdout.write(
            f"  Questions: {len(questions)}"
        )

        self.stdout.write(
            f"  Standard Application: "
            f"{standard_application.id}"
        )

        self.stdout.write(
            f"  Partner: {partner.name}"
        )

        self.stdout.write(
            f"  Program: {program.name}"
        )

        self.stdout.write(
            f"  Program Version: v{program_version.version}"
        )

        self.stdout.write(
            f"  Partner Application: "
            f"{partner_application.id}"
        )

    def _seed_answers(
        self,
        application,
        questions,
        answer_data,
    ):
        for key, value in answer_data.items():
            ApplicationAnswer.objects.update_or_create(
                application=application,
                question=questions[key],
                defaults={
                    "answer_text": value,
                },
            )