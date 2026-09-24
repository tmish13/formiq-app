"""G-16: log redaction. One rule set, two hooks (structlog processor, stdlib filter)."""
import logging

import pytest

from app.core.redaction import MASK, RedactingFilter, redact_event, redact_obj, redact_text

pytestmark = pytest.mark.unit


def test_email_loses_its_local_part_and_keeps_the_domain():
    assert redact_text("user tarpan.m+x@example.com registered") == f"user {MASK}@example.com registered"


def test_jwt_and_bearer_credentials_are_masked():
    tok = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.abcdefghijklmnopqrstuv"
    assert tok not in redact_text(f"Authorization: Bearer {tok}")
    assert redact_text("Bearer abcdefghijklmnop") == "Bearer ***"


def test_key_value_fragments_are_masked_but_placeholders_are_not():
    assert redact_text("login failed password=hunter22 for x") == "login failed password=*** for x"
    assert redact_text("token=%s") == "token=%s"


def test_sensitive_keys_are_masked_whole_and_nested_values_are_scrubbed():
    out = redact_obj({
        "event": "login",
        "extra": {"email": "a@b.co", "access_token": "eyJx.eyJy.zz", "ip": "1.2.3.4"},
        "password": "p",
        "items": [{"Authorization": "Bearer abcdefghijkl"}],
    })
    assert out["password"] == MASK
    assert out["extra"]["access_token"] == MASK
    assert out["extra"]["email"] == f"{MASK}@b.co"
    assert out["extra"]["ip"] == "1.2.3.4" and out["event"] == "login"
    assert out["items"][0]["Authorization"] == MASK


def test_structlog_processor_returns_the_scrubbed_dict():
    assert redact_event(None, "info", {"event": "x", "token": "t"}) == {"event": "x", "token": MASK}


def test_stdlib_filter_scrubs_the_formatted_message(caplog):
    logger = logging.getLogger("redaction-test")
    logger.addFilter(RedactingFilter())
    with caplog.at_level(logging.INFO, logger="redaction-test"):
        logger.info("user %s token=%s", "me@example.com", "abcd1234")
    assert caplog.records[-1].getMessage() == f"user {MASK}@example.com token={MASK}"


def test_the_app_logging_config_uses_both_hooks():
    import structlog
    from app.core import logging as app_logging  # noqa: F401  (configures structlog on import)
    names = [getattr(p, "__name__", type(p).__name__) for p in structlog.get_config()["processors"]]
    assert "redact_event" in names
    assert names.index("redact_event") < names.index("JSONRenderer")
