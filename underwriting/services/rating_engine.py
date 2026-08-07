from decimal import Decimal, InvalidOperation

from django.db import transaction

from underwriting.models import Application
from underwriting.services.program_config import get_rating_config


def parse_answer(value: str):
    if value == "":
        return None

    lowered = value.lower()

    if lowered == "true":
        return True

    if lowered == "false":
        return False

    try:
        decimal_value = Decimal(value)

        if decimal_value == decimal_value.to_integral_value():
            return int(decimal_value)

        return float(decimal_value)

    except InvalidOperation:
        return value


def get_rating_engine_version(application: Application):
    """
    Partner applications use the RatingEngineVersion selected
    by ProgramVersion.

    Standard applications continue using the RatingEngineVersion
    directly on Application.
    """

    if application.program_version_id is not None:
        return application.program_version.rating_engine_version

    return application.rating_engine_version


def build_rating_request(application: Application) -> dict:
    answers = {}
    underwriter_discounts = {}

    rating_engine_version = get_rating_engine_version(
        application
    )

    # ---------------------------------------------------------
    # Existing ApplicationAnswer behavior
    # ---------------------------------------------------------

    application_answers = (
        application
        .answers
        .select_related("question")
    )

    for application_answer in application_answers:
        question = application_answer.question
        key = question.rating_engine_question_key

        if question.is_pricing_modifier:
            underwriter_discounts[key] = parse_answer(
                application_answer.answer_text
            )

            continue

        answers[key] = parse_answer(
            application_answer.answer_text
        )

    # ---------------------------------------------------------
    # Existing coverage behavior
    # ---------------------------------------------------------

    coverages = []

    for application_coverage in (
        application
        .coverages
        .select_related("coverage")
    ):
        coverages.append(
            {
                "code": application_coverage.coverage.code,
                "limit": float(
                    application_coverage.limit
                ),
                "deductible": float(
                    application_coverage.deductible
                ),
                "underwriter_discounts": (
                    underwriter_discounts.copy()
                ),
            }
        )

    request_payload = {
        "version": rating_engine_version.version,
        "answers": answers,
        "coverages": coverages,
    }

    # ---------------------------------------------------------
    # New optional partner configuration
    # ---------------------------------------------------------

    rating_config = get_rating_config(application)

    if rating_config:
        request_payload["rating_config"] = rating_config

    return request_payload


def create_fake_rating_response(
    request_payload: dict,
) -> dict:
    """
    Fake rating engine.

    Existing requests continue to work because rating_config
    is optional.

    Partner requests can supply additional rating factors.
    """

    rating_config = request_payload.get(
        "rating_config",
        {},
    )

    territory_factor = Decimal(
        str(
            rating_config.get(
                "territory_factor",
                1,
            )
        )
    )

    coverage_results = []

    for coverage in request_payload["coverages"]:
        base_premium = Decimal("9123.00")

        # New program-specific rating behavior.
        premium_before_discount = (
            base_premium * territory_factor
        ).quantize(
            Decimal("0.01")
        )

        discount_rate = sum(
            (
                Decimal(str(value))
                for value in coverage[
                    "underwriter_discounts"
                ].values()
                if value is not None
            ),
            Decimal("0"),
        )

        discount_amount = (
            premium_before_discount
            * discount_rate
        ).quantize(
            Decimal("0.01")
        )

        final_premium = (
            premium_before_discount
            - discount_amount
        ).quantize(
            Decimal("0.01")
        )

        coverage_results.append(
            {
                "code": coverage["code"],
                "response": {
                    "base_premium": float(
                        base_premium
                    ),
                    "territory_factor": float(
                        territory_factor
                    ),
                    "premium_no_discount": float(
                        premium_before_discount
                    ),
                    "discounted_amount": float(
                        discount_amount
                    ),
                    "premium": float(
                        final_premium
                    ),
                },
            }
        )

    return {
        "coverages": coverage_results,
    }


@transaction.atomic
def rate_application(application: Application) -> dict:
    request_payload = build_rating_request(
        application
    )

    response_payload = create_fake_rating_response(
        request_payload
    )

    responses_by_code = {
        result["code"]: result["response"]
        for result in response_payload["coverages"]
    }

    for application_coverage in (
        application
        .coverages
        .select_related("coverage")
    ):
        response = responses_by_code[
            application_coverage.coverage.code
        ]

        application_coverage.computed_premium = (
            Decimal(
                str(response["premium"])
            )
        )

        application_coverage.rating_engine_response = (
            response
        )

        application_coverage.save(
            update_fields=[
                "computed_premium",
                "rating_engine_response",
            ]
        )

    application.status = Application.Status.RATED

    application.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    return {
        "request": request_payload,
        "response": response_payload,
    }