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


def get_application_questions(application: Application,) -> list[dict]:
    """
    Return the effective questions for an application.

    RatingEngineVersion owns the canonical questions.
    ProgramQuestionConfig may override display/default behavior.
    """

    if application.program_version_id is not None:
        rating_engine_version = (
            application
            .program_version
            .rating_engine_version
        )
    else:
        rating_engine_version = (
            application.rating_engine_version
        )

    questions = (
        rating_engine_version
        .questions
        .filter(is_pricing_modifier=False)
        .order_by("id")
    )

    existing_answers = {
        answer.question_id: answer.answer_text
        for answer in application.answers.all()
    }

    program_configs = {}

    if application.program_version_id is not None:
        program_configs = {
            config.question_id: config
            for config in (
                application
                .program_version
                .question_configs
                .filter(is_active=True)
                .select_related("question")
            )
        }

    results = []

    for question in questions:
        config = program_configs.get(
            question.id
        )

        question_text = question.question_text
        default_answer = None
        is_answer_locked = False
        display_order = question.id

        if config is not None:
            if config.question_text_override:
                question_text = (config.question_text_override)

            default_answer = (config.default_answer_text)
            is_answer_locked = (config.is_answer_locked)

        answer = existing_answers.get(
            question.id
        )

        if answer is None:
            answer = default_answer

        results.append(
            {
                "question_id": question.id,
                "key": (
                    question
                    .rating_engine_question_key
                ),
                "question_text": question_text,
                "answer": answer,
                "default_answer": default_answer,
                "is_answer_locked": (
                    is_answer_locked
                ),
                "display_order": display_order,
            }
        )

    return sorted(
        results,
        key=lambda item: item["display_order"],
    )