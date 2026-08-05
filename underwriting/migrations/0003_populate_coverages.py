from django.db import migrations


def populate_coverages(apps, schema_editor):
    Coverage = apps.get_model(
        "underwriting",
        "Coverage",
    )

    ApplicationCoverage = apps.get_model(
        "underwriting",
        "ApplicationCoverage",
    )

    coverage_names = {
        "epl": "Employment Practices Liability",
    }

    for application_coverage in ApplicationCoverage.objects.all():
        code = (
            application_coverage
            .legacy_coverage_code
            .strip()
            .lower()
        )

        coverage, _ = Coverage.objects.get_or_create(
            code=code,
            defaults={
                "name": coverage_names.get(
                    code,
                    code.upper(),
                ),
                "description": "",
                "is_active": True,
            },
        )

        application_coverage.coverage = coverage
        application_coverage.save(
            update_fields=["coverage"]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("underwriting", "0002_coverage_and_more"),
    ]

    operations = [
        migrations.RunPython(
            populate_coverages,
            migrations.RunPython.noop,
        ),
    ]