from decimal import Decimal, InvalidOperation

from django.db import migrations


def migrate_partner_discounts(apps, schema_editor):
    ApplicationAnswer = apps.get_model(
        "underwriting",
        "ApplicationAnswer",
    )

    ApplicationDiscount = apps.get_model(
        "underwriting",
        "ApplicationDiscount",
    )

    ProgramDiscountConfig = apps.get_model(
        "underwriting",
        "ProgramDiscountConfig",
    )

    discount_answers = ApplicationAnswer.objects.filter(
        application__program_version__isnull=False,
        question__isnull=False,
        question__is_pricing_modifier=True,
        program_question__isnull=True,
    ).select_related(
        "application",
        "question",
    )

    for answer in discount_answers:
        key = answer.question.rating_engine_question_key

        configs = ProgramDiscountConfig.objects.filter(
            program_version_id=(
                answer.application.program_version_id
            )
        )

        discount_config = configs.filter(
            rating_engine_key=key,
        ).first()

        if discount_config is None:
            discount_config = configs.filter(
                code=key,
            ).first()

        if discount_config is None:
            raise RuntimeError(
                f"No program discount config found for {key}."
            )

        try:
            discount_value = Decimal(answer.answer_text)
        except InvalidOperation as exc:
            raise RuntimeError(
                f"Invalid discount value: {answer.answer_text}"
            ) from exc

        ApplicationDiscount.objects.update_or_create(
            application_id=answer.application_id,
            discount_config_id=discount_config.id,
            defaults={
                "discount_value": discount_value,
                "notes": "Migrated from legacy answer.",
            },
        )

        answer.delete()


def reverse_partner_discounts(apps, schema_editor):
    ApplicationAnswer = apps.get_model(
        "underwriting",
        "ApplicationAnswer",
    )

    ApplicationDiscount = apps.get_model(
        "underwriting",
        "ApplicationDiscount",
    )

    ApplicationQuestion = apps.get_model(
        "underwriting",
        "ApplicationQuestion",
    )

    discounts = ApplicationDiscount.objects.select_related(
        "application",
        "discount_config",
    )

    for application_discount in discounts:
        application = application_discount.application
        discount_config = application_discount.discount_config

        key = (
            discount_config.rating_engine_key
            or discount_config.code
        )

        application_question = ApplicationQuestion.objects.get(
            rating_engine_version_id=(
                application.rating_engine_version_id
            ),
            rating_engine_question_key=key,
            is_pricing_modifier=True,
        )

        ApplicationAnswer.objects.update_or_create(
            application_id=application.id,
            question_id=application_question.id,
            defaults={
                "program_question_id": None,
                "answer_text": str(
                    application_discount.discount_value
                ),
            },
        )

        application_discount.delete()


class Migration(migrations.Migration):

    dependencies = [
            ("underwriting", "0009_applicationdiscount"),
        ]

    operations = [
        migrations.RunPython(
            migrate_partner_discounts,
            reverse_partner_discounts,
        ),
    ]