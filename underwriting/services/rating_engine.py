from decimal import Decimal, InvalidOperation

from django.db import transaction

from underwriting.models import Application

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
    if application.program_version_id is not None:
        return (
            application
            .program_version
            .rating_engine_version
        )

    return application.rating_engine_version


def get_rating_engine_version(application: Application):
    if application.program_version_id is not None:
        return (
            application
            .program_version
            .rating_engine_version
        )

    return application.rating_engine_version


def build_rating_request(application: Application) -> dict:

    answers = {}
    underwriter_discounts = {}

    rating_engine_version = get_rating_engine_version(application)

    application_answers = application.answers.select_related(
        "question",
        "program_question",
    )

    for application_answer in application_answers:
        if application_answer.program_question_id is not None:
            key = application_answer.program_question.question_key

            answers[key] = parse_answer(
                application_answer.answer_text
            )

            continue

        question = application_answer.question
        key = question.rating_engine_question_key

        if question.is_pricing_modifier:
            # Legacy discounts remain supported for standard,
            # non-program applications.
            if application.program_version_id is None:
                underwriter_discounts[key] = float(
                    application_answer.answer_text
                )

            continue

        answers[key] = parse_answer(
            application_answer.answer_text
        )

    application_discounts = application.discounts.select_related(
        "discount_config"
    )

    for application_discount in application_discounts:
        discount_config = application_discount.discount_config

        key = (
            discount_config.rating_engine_key
            or discount_config.code
        )

        underwriter_discounts[key] = float(
            application_discount.discount_value
        )
        
    coverages = []

    for application_coverage in application.coverages.select_related(
        "coverage"
    ):
        coverages.append(
            {
                "code": application_coverage.coverage.code,
                "limit": float(application_coverage.limit),
                "deductible": float(application_coverage.deductible),
                "underwriter_discounts": (
                    underwriter_discounts.copy()
                ),
            }
        )

    return {
        "version": rating_engine_version.version,
        "answers": answers,
        "coverages": coverages,
    }


def create_fake_rating_response(request_payload: dict) -> dict:
    coverage_results = []

    for coverage in request_payload["coverages"]:
        premium_before_discount = Decimal("9123.00")

        discount_rate = sum(
            Decimal(str(value))
            for value in coverage[
                "underwriter_discounts"
            ].values()
        )

        discount_amount = (
            premium_before_discount * discount_rate
        ).quantize(Decimal("0.01"))

        final_premium = (
            premium_before_discount - discount_amount
        )

        coverage_results.append(
            {
                "code": coverage["code"],
                "response": {
                    "premium_no_discount": float(
                        premium_before_discount
                    ),
                    "discounted_amount": float(
                        discount_amount
                    ),
                    "premium": float(final_premium),
                },
            }
        )

    return {
        "coverages": coverage_results,
    }


@transaction.atomic
def rate_application(application: Application) -> dict:
    request_payload = build_rating_request(application)
    response_payload = create_fake_rating_response(
        request_payload
    )

    responses_by_code = {
        result["code"]: result["response"]
        for result in response_payload["coverages"]
    }

    for application_coverage in application.coverages.select_related("coverage"):
        response = responses_by_code[application_coverage.coverage.code]

        application_coverage.computed_premium = Decimal(str(response["premium"]))
        application_coverage.rating_engine_response = response
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