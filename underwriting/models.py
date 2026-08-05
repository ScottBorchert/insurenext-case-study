from django.db import models


class Company(models.Model):
    legal_name = models.CharField(max_length=255)
    dba_name = models.CharField(max_length=255, blank=True)
    url = models.URLField(blank=True)

    address1 = models.CharField(max_length=255, blank=True)
    address2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    zip = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.legal_name


class RatingEngineVersion(models.Model):
    version = models.PositiveIntegerField(unique=True)
    effective_date = models.DateField()
    endpoint_url = models.URLField()

    def __str__(self) -> str:
        return f"Rating Engine v{self.version}"


class Application(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        RATED = "rated", "Rated"
        DECLINED = "declined", "Declined"

    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="applications",
    )

    rating_engine_version = models.ForeignKey(
        RatingEngineVersion,
        on_delete=models.PROTECT,
        related_name="applications",
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Application {self.pk}: {self.company.legal_name}"


class ApplicationQuestion(models.Model):
    rating_engine_version = models.ForeignKey(
        RatingEngineVersion,
        on_delete=models.PROTECT,
        related_name="questions",
    )

    # Confirmed authoritative key.
    rating_engine_question_key = models.CharField(max_length=100)

    question_text = models.TextField()
    is_pricing_modifier = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "rating_engine_version",
                    "rating_engine_question_key",
                ],
                name="unique_question_key_per_engine_version",
            )
        ]

    def __str__(self) -> str:
        return self.question_text


class ApplicationAnswer(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="answers",
    )

    question = models.ForeignKey(
        ApplicationQuestion,
        on_delete=models.PROTECT,
        related_name="answers",
    )

    answer_text = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["application", "question"],
                name="unique_answer_per_application_question",
            )
        ]

    def __str__(self) -> str:
        return (
            f"{self.question.rating_engine_question_key}: "
            f"{self.answer_text}"
        )


class ApplicationCoverage(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="coverages",
    )

    coverage_id = models.CharField(max_length=50)

    computed_premium = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    limit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    deductible = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    coverage_denied = models.BooleanField(default=False)
    additional_details = models.JSONField(default=dict, blank=True)
    rating_engine_response = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["application", "coverage_id"],
                name="unique_coverage_per_application",
            )
        ]

    def __str__(self) -> str:
        return f"Application {self.application_id}: {self.coverage_id}"