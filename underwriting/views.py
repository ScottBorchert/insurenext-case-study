import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from underwriting.models import (
    Application,
    ApplicationAnswer,
    ApplicationCoverage,
    ApplicationQuestion,
    Company,
    Coverage,
    ProgramVersion,
    RatingEngineVersion,
)

from underwriting.services.program_config import (
    get_application_questions,
)

from underwriting.services.rating_engine import (
    build_rating_request,
    get_rating_engine_version,
    rate_application,
)


# =========================================================
# Helpers
# =========================================================


def _parse_decimal(value: str, field_name: str) -> Decimal:
    value = (value or "").replace(",", "").strip()

    if not value:
        raise ValueError(f"{field_name} is required.")

    try:
        decimal_value = Decimal(value)
    except InvalidOperation:
        raise ValueError(
            f"{field_name} must be a valid number."
        )

    if decimal_value < 0:
        raise ValueError(
            f"{field_name} cannot be negative."
        )

    return decimal_value


def _get_coverage_rows(application: Application):
    existing = {
        item.coverage_id: item
        for item in application.coverages.all()
    }

    rows = []

    for coverage in (
        Coverage.objects
        .filter(is_active=True)
        .order_by("name")
    ):
        current = existing.get(coverage.id)

        rows.append(
            {
                "coverage": coverage,
                "selected": current is not None,
                "limit": (
                    current.limit
                    if current is not None
                    else ""
                ),
                "deductible": (
                    current.deductible
                    if current is not None
                    else ""
                ),
            }
        )

    return rows


def _save_application_answers(
    application,
    effective_questions,
    post_data,
):
    questions_by_id = {
        question.id: question
        for question in ApplicationQuestion.objects.filter(
            id__in=[
                item["question_id"]
                for item in effective_questions
            ]
        )
    }

    for item in effective_questions:
        question_id = item["question_id"]
        question = questions_by_id[question_id]

        if item["is_answer_locked"]:
            # Preserve an existing answer when present.
            # Otherwise persist the configured default.
            value = item["answer"]

            if value is None:
                value = (
                    item["default_answer"]
                    if item["default_answer"] is not None
                    else ""
                )

        else:
            value = post_data.get(
                f"question_{question_id}",
                "",
            )

        ApplicationAnswer.objects.update_or_create(
            application=application,
            question=question,
            defaults={
                "answer_text": value,
            },
        )


def _save_coverages(
    application,
    post_data,
    require_coverage=False,
):
    active_coverages = list(
        Coverage.objects
        .filter(is_active=True)
        .order_by("name")
    )

    selected_ids = []

    for coverage in active_coverages:
        selected = (
            post_data.get(
                f"coverage_{coverage.id}"
            )
            == "on"
        )

        if not selected:
            continue

        selected_ids.append(coverage.id)

        limit = _parse_decimal(
            post_data.get(
                f"coverage_{coverage.id}_limit"
            ),
            f"{coverage.name} limit",
        )

        deductible = _parse_decimal(
            post_data.get(
                f"coverage_{coverage.id}_deductible"
            ),
            f"{coverage.name} deductible",
        )

        ApplicationCoverage.objects.update_or_create(
            application=application,
            coverage=coverage,
            defaults={
                "limit": limit,
                "deductible": deductible,
            },
        )

    if require_coverage and not selected_ids:
        raise ValueError(
            "Select at least one coverage before submitting."
        )

    application.coverages.exclude(
        coverage_id__in=selected_ids
    ).delete()


def _get_discount_rows(application: Application):
    rating_engine_version = get_rating_engine_version(
        application
    )

    current_answers = {
        answer.question_id: answer.answer_text
        for answer in (
            application
            .answers
            .filter(
                question__is_pricing_modifier=True
            )
            .select_related("question")
        )
    }

    rows = []

    if application.program_version_id is not None:
        configs = (
            application
            .program_version
            .discount_configs
            .filter(is_active=True)
            .select_related("question")
            .order_by("display_order", "id")
        )

        for config in configs:
            current_value = current_answers.get(
                config.question_id
            )

            if (
                current_value is None
                and config.default_value is not None
            ):
                current_value = str(
                    config.default_value
                )

            rows.append(
                {
                    "question": config.question,
                    "name": config.name,
                    "description": config.description,
                    "minimum_value": (
                        config.minimum_value
                    ),
                    "maximum_value": (
                        config.maximum_value
                    ),
                    "requires_approval": (
                        config.requires_approval
                    ),
                    "current_value": (
                        current_value or ""
                    ),
                }
            )

        return rows

    # Legacy / standard applications use pricing-modifier
    # questions directly without program-specific rules.
    questions = (
        rating_engine_version
        .questions
        .filter(is_pricing_modifier=True)
        .order_by("id")
    )

    for question in questions:
        rows.append(
            {
                "question": question,
                "name": question.question_text,
                "description": "",
                "minimum_value": Decimal("0"),
                "maximum_value": Decimal("1"),
                "requires_approval": False,
                "current_value": (
                    current_answers.get(
                        question.id,
                        "",
                    )
                ),
            }
        )

    return rows


def _save_discounts(
    application,
    discount_rows,
    post_data,
):
    for row in discount_rows:
        question = row["question"]

        raw_value = (
            post_data
            .get(
                f"discount_{question.id}",
                "",
            )
            .strip()
        )

        if raw_value == "":
            ApplicationAnswer.objects.filter(
                application=application,
                question=question,
            ).delete()

            continue

        try:
            value = Decimal(raw_value)
        except InvalidOperation:
            raise ValueError(
                f"{row['name']} must be a valid number."
            )

        minimum = row["minimum_value"]
        maximum = row["maximum_value"]

        if (
            minimum is not None
            and value < minimum
        ):
            raise ValueError(
                f"{row['name']} cannot be less "
                f"than {minimum}."
            )

        if (
            maximum is not None
            and value > maximum
        ):
            raise ValueError(
                f"{row['name']} cannot exceed "
                f"{maximum}."
            )

        ApplicationAnswer.objects.update_or_create(
            application=application,
            question=question,
            defaults={
                "answer_text": format(
                    value,
                    "f",
                ),
            },
        )


# =========================================================
# 1. Start Application
# =========================================================


def application_new(request):
    companies = (
        Company.objects
        .all()
        .order_by("legal_name")
    )

    program_versions = (
        ProgramVersion.objects
        .filter(
            status=ProgramVersion.Status.PUBLISHED,
            program__is_active=True,
            program__distribution_partner__is_active=True,
        )
        .select_related(
            "program",
            "program__distribution_partner",
            "rating_engine_version",
        )
        .order_by(
            "program__distribution_partner__name",
            "program__name",
            "-version",
        )
    )

    if request.method == "POST":
        company = get_object_or_404(
            Company,
            pk=request.POST.get("company_id"),
        )

        program_version_id = (
            request.POST.get(
                "program_version_id"
            )
            or None
        )

        if program_version_id:
            program_version = get_object_or_404(
                ProgramVersion,
                pk=program_version_id,
                status=(
                    ProgramVersion.Status.PUBLISHED
                ),
            )

            rating_engine_version = (
                program_version
                .rating_engine_version
            )

        else:
            program_version = None

            rating_engine_version = (
                RatingEngineVersion.objects
                .order_by("-version")
                .first()
            )

        if rating_engine_version is None:
            messages.error(
                request,
                "No rating engine version is available.",
            )

            return redirect(
                "underwriting:application_new"
            )

        application = Application.objects.create(
            company=company,
            program_version=program_version,
            rating_engine_version=(
                rating_engine_version
            ),
            status=Application.Status.DRAFT,
        )

        messages.success(
            request,
            f"Application {application.id} started.",
        )

        return redirect(
            "underwriting:application_detail",
            application_id=application.id,
        )

    return render(
        request,
        "underwriting/application_new.html",
        {
            "companies": companies,
            "program_versions": program_versions,
        },
    )


# =========================================================
# 2. Applicant Questionnaire
# =========================================================


def application_detail(
    request,
    application_id,
):
    application = get_object_or_404(
        Application.objects.select_related(
            "company",
            "program_version",
            "program_version__program",
            "program_version__program__distribution_partner",
            "rating_engine_version",
        ),
        pk=application_id,
    )

    effective_questions = (
        get_application_questions(
            application
        )
    )

    if request.method == "POST":
        if application.status != Application.Status.DRAFT:
            messages.error(
                request,
                "Only draft applications can be edited.",
            )

            return redirect(
                "underwriting:application_detail",
                application_id=application.id,
            )

        action = request.POST.get(
            "action",
            "save",
        )

        try:
            with transaction.atomic():
                _save_application_answers(
                    application,
                    effective_questions,
                    request.POST,
                )

                _save_coverages(
                    application,
                    request.POST,
                    require_coverage=(
                        action == "submit"
                    ),
                )

                if action == "submit":
                    application.status = (
                        Application.Status.SUBMITTED
                    )

                    application.save(
                        update_fields=[
                            "status",
                            "updated_at",
                        ]
                    )

        except ValueError as exc:
            messages.error(
                request,
                str(exc),
            )

            return redirect(
                "underwriting:application_detail",
                application_id=application.id,
            )

        if action == "submit":
            messages.success(
                request,
                "Application submitted for underwriting.",
            )

            return redirect(
                "underwriting:underwriting_review",
                application_id=application.id,
            )

        messages.success(
            request,
            "Draft saved.",
        )

        return redirect(
            "underwriting:application_detail",
            application_id=application.id,
        )

    coverage_rows = _get_coverage_rows(
        application
    )

    return render(
        request,
        "underwriting/application_detail.html",
        {
            "application": application,
            "questions": effective_questions,
            "coverage_rows": coverage_rows,
            "is_editable": (
                application.status
                == Application.Status.DRAFT
            ),
        },
    )


# =========================================================
# 3. Underwriting Queue
# =========================================================


def underwriting_queue(request):
    submitted_applications = (
        Application.objects
        .filter(
            status=Application.Status.SUBMITTED
        )
        .select_related(
            "company",
            "program_version",
            "program_version__program",
        )
        .order_by("created_at")
    )

    rated_applications = (
        Application.objects
        .filter(
            status=Application.Status.RATED
        )
        .select_related(
            "company",
            "program_version",
            "program_version__program",
        )
        .order_by("-updated_at")[:10]
    )

    return render(
        request,
        "underwriting/underwriting_queue.html",
        {
            "submitted_applications": (
                submitted_applications
            ),
            "rated_applications": (
                rated_applications
            ),
        },
    )


# =========================================================
# 4. Underwriting Review
# =========================================================


def underwriting_review(
    request,
    application_id,
):
    application = get_object_or_404(
        Application.objects.select_related(
            "company",
            "program_version",
            "program_version__program",
            "program_version__program__distribution_partner",
            "rating_engine_version",
        ),
        pk=application_id,
    )

    discount_rows = _get_discount_rows(
        application
    )

    if request.method == "POST":
        if (
            application.status
            != Application.Status.SUBMITTED
        ):
            messages.error(
                request,
                "Only submitted applications can be "
                "modified or rated.",
            )

            return redirect(
                "underwriting:underwriting_review",
                application_id=application.id,
            )

        action = request.POST.get(
            "action",
            "save_discounts",
        )

        try:
            with transaction.atomic():
                _save_discounts(
                    application,
                    discount_rows,
                    request.POST,
                )

                if action == "rate":
                    if not application.coverages.exists():
                        raise ValueError(
                            "The application must have at "
                            "least one requested coverage."
                        )

                    rate_application(
                        application
                    )

        except ValueError as exc:
            messages.error(
                request,
                str(exc),
            )

            return redirect(
                "underwriting:underwriting_review",
                application_id=application.id,
            )

        if action == "rate":
            messages.success(
                request,
                "Application rated successfully.",
            )
        else:
            messages.success(
                request,
                "Underwriter discounts saved.",
            )

        return redirect(
            "underwriting:underwriting_review",
            application_id=application.id,
        )

    effective_questions = (
        get_application_questions(
            application
        )
    )

    application_coverages = (
        application
        .coverages
        .select_related("coverage")
        .order_by("coverage__name")
    )

    rating_request_preview = json.dumps(
        build_rating_request(application),
        indent=2,
    )

    return render(
        request,
        "underwriting/underwriting_review.html",
        {
            "application": application,
            "questions": effective_questions,
            "discount_rows": discount_rows,
            "application_coverages": (
                application_coverages
            ),
            "rating_request_preview": (
                rating_request_preview
            ),
            "can_rate": (
                application.status
                == Application.Status.SUBMITTED
            ),
        },
    )