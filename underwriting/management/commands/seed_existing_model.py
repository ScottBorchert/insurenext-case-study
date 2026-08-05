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
    RatingEngineVersion,
)


class Command(BaseCommand):
    help = "Seed the existing InsureNext core model."

    @transaction.atomic
    def handle(self, *args, **options):
        rating_engine, _ = RatingEngineVersion.objects.update_or_create(
            version=100,
            defaults={
                "effective_date": date(2026, 1, 1),
                "endpoint_url": "https://fake-rater.local/v100",
            },
        )

        company, _ = Company.objects.update_or_create(
            legal_name="Bug Away Pest Control LLC",
            defaults={
                "dba_name": "Bug Away",
                "url": "https://example.com",
                "address1": "100 Main Street",
                "city": "Minneapolis",
                "state": "MN",
                "zip": "55401",
            },
        )

        question_data = [
            {
                "key": "industry",
                "text": "What industry is the business in?",
                "is_pricing_modifier": False,
            },
            {
                "key": "industry_other",
                "text": "Please describe the industry.",
                "is_pricing_modifier": False,
            },
            {
                "key": "annual_revenue",
                "text": "What is the company's annual revenue?",
                "is_pricing_modifier": False,
            },
            {
                "key": "employee_count",
                "text": "How many employees does the company have?",
                "is_pricing_modifier": False,
            },
            {
                "key": "discount_1",
                "text": "Underwriter discount 1",
                "is_pricing_modifier": True,
            },
            {
                "key": "discount_2",
                "text": "Underwriter discount 2",
                "is_pricing_modifier": True,
            },
        ]

        questions = {}

        for item in question_data:
            question, _ = ApplicationQuestion.objects.update_or_create(
                rating_engine_version=rating_engine,
                rating_engine_question_key=item["key"],
                defaults={
                    "question_text": item["text"],
                    "is_pricing_modifier": item[
                        "is_pricing_modifier"
                    ],
                },
            )

            questions[item["key"]] = question

        application, _ = Application.objects.get_or_create(
            company=company,
            rating_engine_version=rating_engine,
            defaults={
                "status": Application.Status.SUBMITTED,
            },
        )

        answer_data = {
            "industry": "Pest Control",
            "industry_other": "",
            "annual_revenue": "1500000",
            "employee_count": "35",
            "discount_1": "0.25",
            "discount_2": "0.10",
        }

        for key, value in answer_data.items():
            ApplicationAnswer.objects.update_or_create(
                application=application,
                question=questions[key],
                defaults={
                    "answer_text": value,
                },
            )

        ApplicationCoverage.objects.update_or_create(
            application=application,
            coverage_id="epl",
            defaults={
                "limit": Decimal("5000000.00"),
                "deductible": Decimal("25000.00"),
                "computed_premium": None,
                "coverage_denied": False,
                "additional_details": {},
                "rating_engine_response": {},
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded application {application.id}."
            )
        )