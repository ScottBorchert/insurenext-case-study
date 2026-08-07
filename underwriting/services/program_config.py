from underwriting.models import Application


def get_rating_config(application: Application) -> dict:
    """
    Resolve active ProgramRatingConfig rows into the
    rating_config object sent to the rating engine.

    Standard applications return an empty dictionary.
    """

    if application.program_version_id is None:
        return {}

    configs = (
        application
        .program_version
        .rating_configs
        .filter(is_active=True)
    )

    return {
        config.config_key: config.config_value
        for config in configs
    }