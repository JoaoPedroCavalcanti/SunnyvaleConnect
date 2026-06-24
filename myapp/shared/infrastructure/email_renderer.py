"""Render HTML email templates and a plain-text fallback."""

import re

from django.template.loader import render_to_string
from django.utils.html import strip_tags


def render_email(template_name: str, context: dict) -> tuple[str, str]:
    """Return (html_body, plain_text_body) for emails/<template_name>.html."""
    html = render_to_string(f"emails/{template_name}.html", context)
    plain = _html_to_plain(html)
    return html, plain


def _html_to_plain(html: str) -> str:
    text = strip_tags(html)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
