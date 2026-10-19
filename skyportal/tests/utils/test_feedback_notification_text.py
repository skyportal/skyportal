import html

from skyportal.utils.notifications import (
    escape_markdown,
    escape_slack,
    feedback_notification_text,
)

CONTENT = {
    "author": "sam_r",
    "label": "bug report",
    "snippet": "<!channel> ![](https://tracker/x.png) <b>hi</b>",
    "reply": False,
}


def test_markdown_text_has_no_image_or_html():
    text = feedback_notification_text(CONTENT, escape_markdown)
    assert text.startswith("New bug report from *sam\\_r*: ")
    assert "![" not in text
    assert "<b>" not in text


def test_slack_text_cannot_mention_the_channel():
    text = feedback_notification_text(CONTENT, escape_slack)
    assert "<!channel>" not in text
    assert "&lt;!channel&gt;" in text


def test_email_text_has_no_html():
    text = feedback_notification_text({**CONTENT, "reply": True}, html.escape, bold="")
    assert text.startswith("sam_r replied to your bug report: ")
    assert "<b>" not in text
    assert "&lt;b&gt;hi&lt;/b&gt;" in text
