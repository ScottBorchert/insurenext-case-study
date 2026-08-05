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


def build_rating_request(application: Application) -> dict:
    answers = {}
    underwriter_discounts = {}

    application_answers = application.answers.select_related(
        "question"
    )

    for application_answer in application_answers:
        question = application_answer.question
        key = question.rating_engine_question_key

        if question.is_pricing_modifier:
            underwriter_discounts[key] = float(
                application_answer.answer_text
            )
        else:
            answers[key] = parse_answer(
                application_answer.answer_text
            )

    coverages = []

    for coverage in application.coverages.all():
        coverages.append(
            {
                "code": coverage.coverage_id,
                "limit": float(coverage.limit),
                "deductible": float(coverage.deductible),
                "underwriter_discounts": (
                    underwriter_discounts.copy()
                ),
            }
        )

    return {
        "version": application.rating_engine_version.version,
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

    for coverage in application.coverages.all():
        response = responses_by_code[coverage.coverage_id]

        coverage.computed_premium = Decimal(
            str(response["premium"])
        )

        coverage.rating_engine_response = response

        coverage.save(
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