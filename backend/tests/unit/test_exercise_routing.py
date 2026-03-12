"""Unit tests for Bug 4+5: ExerciseTemplate lookup and _is_squat routing.

Bug 4: lookup must be case-insensitive (DB may have "Squat"; enum value is "squat").
Bug 5: _is_squat must be True when ExerciseTemplate is None but
       video.exercise_type / classified_exercise_slug contains "squat".

Uses inline replicas to avoid Celery/DB imports.
"""

# ---------------------------------------------------------------------------
# Inline replica of _is_squat computation (from analysis_tasks.py)
# ---------------------------------------------------------------------------


def _compute_is_squat(
    exercise_template_name: str | None,
    classified_exercise_slug: str | None,
    video_exercise_type: str | None,
) -> tuple[str, bool]:
    """Mirror of the _exercise_slug / _is_squat block in analysis_tasks.py."""
    _exercise_slug = (
        (exercise_template_name.lower() if exercise_template_name else None)
        or (classified_exercise_slug or "").lower()
        or (video_exercise_type or "").lower()
    ).strip()
    _is_squat = "squat" in _exercise_slug if _exercise_slug else False
    return _exercise_slug, _is_squat


# ---------------------------------------------------------------------------
# Inline replica of the case-insensitive name comparison (Bug 4)
# ---------------------------------------------------------------------------


def _names_match_case_insensitive(db_name: str, enum_value: str) -> bool:
    """Mirrors the func.lower() comparison used in form_check_service.py."""
    return db_name.lower() == enum_value.lower()


# ---------------------------------------------------------------------------
# Tests — Bug 4: case-insensitive ExerciseTemplate name match
# ---------------------------------------------------------------------------


class TestExerciseTemplateCaseInsensitiveMatch:
    def test_exact_lowercase_matches(self):
        assert _names_match_case_insensitive("squat", "squat")

    def test_title_case_db_name_matches_lowercase_enum(self):
        """DB has "Squat", enum value is "squat" — must match."""
        assert _names_match_case_insensitive("Squat", "squat")

    def test_uppercase_db_name_matches(self):
        assert _names_match_case_insensitive("SQUAT", "squat")

    def test_mixed_case_matches(self):
        assert _names_match_case_insensitive("Squat Back", "squat back")

    def test_different_names_do_not_match(self):
        assert not _names_match_case_insensitive("Lunge", "squat")

    def test_enum_uppercase_matches_lowercase_db(self):
        assert _names_match_case_insensitive("squat", "SQUAT")


# ---------------------------------------------------------------------------
# Tests — Bug 5: _is_squat routing robustness
# ---------------------------------------------------------------------------


class TestIsSquatRouting:
    def test_exercise_template_name_squat(self):
        _, is_squat = _compute_is_squat("squat", None, None)
        assert is_squat is True

    def test_exercise_template_name_Squat_title_case(self):
        """Template name "Squat" (capitalised) must still route to PostureV1."""
        _, is_squat = _compute_is_squat("Squat", None, None)
        assert is_squat is True

    def test_template_none_falls_back_to_classified_slug(self):
        """Bug 5 core: template lookup returned None, but classified_slug = 'squat'."""
        _, is_squat = _compute_is_squat(None, "squat", None)
        assert is_squat is True

    def test_template_none_slug_none_falls_back_to_video_exercise_type(self):
        """Bug 5 core: template and slug both missing; video.exercise_type saves routing."""
        _, is_squat = _compute_is_squat(None, None, "squat")
        assert is_squat is True

    def test_all_none_returns_false(self):
        """No exercise info at all → _is_squat = False (no inference attempted)."""
        slug, is_squat = _compute_is_squat(None, None, None)
        assert is_squat is False
        assert slug == ""

    def test_non_squat_exercise_returns_false(self):
        _, is_squat = _compute_is_squat("deadlift", None, None)
        assert is_squat is False

    def test_partial_slug_containing_squat_matches(self):
        """'back_squat' or 'squat_variation' should still route to PostureV1."""
        _, is_squat = _compute_is_squat(None, "back_squat", None)
        assert is_squat is True

    def test_video_exercise_type_uppercase_squat(self):
        """video.exercise_type = 'SQUAT' (uppercase) — should still route."""
        _, is_squat = _compute_is_squat(None, None, "SQUAT")
        assert is_squat is True

    def test_exercise_slug_priority_order(self):
        """Template name takes priority over classified slug and video type."""
        slug, is_squat = _compute_is_squat("deadlift", "squat", "squat")
        assert is_squat is False, (
            "Expected template name 'deadlift' to win over slug/video_type"
        )
        assert slug == "deadlift"

    def test_empty_string_sources_treated_as_none(self):
        _, is_squat = _compute_is_squat("", "", "")
        assert is_squat is False
