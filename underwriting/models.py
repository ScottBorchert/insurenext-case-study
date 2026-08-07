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

class Coverage(models.Model):
    code = models.CharField(
        max_length=50,
        unique=True,
    )

    name = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    def __str__(self) -> str:
        return f"{self.code.upper()} - {self.name}"

class RatingEngineVersion(models.Model):
    version = models.PositiveIntegerField(unique=True)
    effective_date = models.DateField()
    endpoint_url = models.URLField()

    def __str__(self) -> str:
        return f"Rating Engine v{self.version}"

class DistributionPartner(models.Model):
    name = models.CharField(max_length=255)

    code = models.CharField(
        max_length=100,
        unique=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

class Program(models.Model):
    distribution_partner = models.ForeignKey(
        DistributionPartner,
        on_delete=models.PROTECT,
        related_name="programs",
    )

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "distribution_partner",
                    "code",
                ],
                name="unique_program_code_per_partner",
            )
        ]

    def __str__(self) -> str:
        return (
            f"{self.distribution_partner.code} / "
            f"{self.name}"
        )

class ProgramVersion(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        RETIRED = "retired", "Retired"

    program = models.ForeignKey(
        Program,
        on_delete=models.PROTECT,
        related_name="versions",
    )

    rating_engine_version = models.ForeignKey(
        RatingEngineVersion,
        on_delete=models.PROTECT,
        related_name="program_versions",
    )

    version = models.PositiveIntegerField()

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    effective_date = models.DateField()

    expiration_date = models.DateField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "program",
                    "version",
                ],
                name="unique_version_per_program",
            )
        ]

        ordering = [
            "program",
            "-version",
        ]

    def __str__(self) -> str:
        return (
            f"{self.program.name} "
            f"v{self.version}"
        )

class ProgramQuestionConfig(models.Model):
    program_version = models.ForeignKey(
        ProgramVersion,
        on_delete=models.CASCADE,
        related_name="question_configs",
    )

    question = models.ForeignKey(
        "ApplicationQuestion",
        on_delete=models.PROTECT,
        related_name="program_question_configs",
    )

    question_text_override = models.TextField(
        null=True,
        blank=True,
    )

    default_answer_text = models.TextField(
        null=True,
        blank=True,
    )

    is_answer_locked = models.BooleanField(
        default=False,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "program_version",
                    "question",
                ],
                name="unique_question_config_per_program_version",
            )
        ]

        ordering = [
            "display_order",
            "id",
        ]

    def __str__(self) -> str:
        return (
            f"{self.program_version}: "
            f"{self.question.rating_engine_question_key}"
        )

class ProgramRatingConfig(models.Model):
    program_version = models.ForeignKey(
        ProgramVersion,
        on_delete=models.CASCADE,
        related_name="rating_configs",
    )

    config_key = models.CharField(
        max_length=100,
    )

    config_value = models.JSONField()

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "program_version",
                    "config_key",
                ],
                name="unique_rating_config_per_program_version",
            )
        ]

    def __str__(self) -> str:
        return (
            f"{self.program_version}: "
            f"{self.config_key}"
        )
    
class ProgramDiscountConfig(models.Model):
    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage"
        FIXED_AMOUNT = "fixed_amount", "Fixed Amount"

    class ApplicationType(models.TextChoices):
        AUTOMATIC = "automatic", "Automatic"
        MANUAL = "manual", "Manual"

    program_version = models.ForeignKey(
        ProgramVersion,
        on_delete=models.CASCADE,
        related_name="discount_configs",
    )

    question = models.ForeignKey(
        "ApplicationQuestion",
        on_delete=models.PROTECT,
        related_name="program_discount_configs",
    )

    name = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    discount_type = models.CharField(
        max_length=30,
        choices=DiscountType.choices,
    )

    application_type = models.CharField(
        max_length=30,
        choices=ApplicationType.choices,
    )

    default_value = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
    )

    minimum_value = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
    )

    maximum_value = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
    )

    requires_approval = models.BooleanField(
        default=False,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "program_version",
                    "question",
                ],
                name="unique_discount_config_per_program_version",
            )
        ]

        ordering = [
            "display_order",
            "id",
        ]

    def __str__(self) -> str:
        return self.name

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

    program_version = models.ForeignKey(
        ProgramVersion,
        on_delete=models.PROTECT,
        related_name="applications",
        null=True,
        blank=True,
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

    answer_text = models.TextField(
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "application",
                    "question",
                ],
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

    coverage = models.ForeignKey(
        Coverage,
        on_delete=models.PROTECT,
        related_name="application_coverages",
    )

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
                fields=["application", "coverage"],
                name="unique_coverage_per_application",
            )
        ]

    def __str__(self) -> str:
        return f"Application {self.application_id}: {self.coverage.code}"


