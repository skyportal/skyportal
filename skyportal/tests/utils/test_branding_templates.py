"""The login page and About page are Jinja templates rendered against the
config at build time, so downstream deployments (Fritz, ICARE) can rebrand
without forking the files. These tests render them the same way
baselayer/tools/fill_conf_values.py does.
"""

import pathlib

import jinja2

from baselayer.app.auth_backends import configured_backends
from baselayer.app.env import load_env

ROOT = pathlib.Path(__file__).parents[3]
ABOUT_TEMPLATE = ROOT / "static/js/components/templates/AboutPlugins.tsx.template"
LOGIN_TEMPLATE = ROOT / "static/login.html.template"
APPLY_TEMPLATE = ROOT / "static/apply.html.template"

FRITZ_LIKE = {
    "auth_backends": [
        {"name": "google-oauth2", "label": "Sign in with Google"},
        {"name": "iam-oauth2", "label": "Sign in with IAM"},
    ],
    "app": {
        "title": "Fritz",
        "logos": [{"src": "/static/images/GROWTH_logo.png", "alt_text": "GROWTH"}],
        "login_message": "hello",
        "login_buttons": [
            {"url": "/login/google-oauth2", "image": "/g.png", "alt_text": "Google"},
            {"url": "/login/iam-oauth2", "image": "/iam.png", "alt_text": "IAM"},
        ],
        "about": {
            # the apostrophe and accent are load-bearing: they exercise the
            # JSX escaping the template applies to config prose
            "description": "Fritz is developed at Université Paris-Saclay; it's great.",
            "homepage_url": "https://fritz.science",
            "docs_url": "https://docs.fritz.science/",
            "api_docs_url": "https://docs.fritz.science/api.html",
            "repository_url": "https://github.com/fritz-marshal/fritz",
            "funding": "Fritz development is funded by the Moore Foundation.",
            "extra_paragraphs": [
                {
                    "text": "Fritz extends {BOOM} & {SkyPortal}.",
                    "links": {
                        "BOOM": "https://github.com/boom-astro/boom",
                        "SkyPortal": "https://skyportal.io",
                    },
                }
            ],
            "changelog_repositories": [
                {
                    "name": "Fritz",
                    "url": "https://github.com/fritz-marshal/fritz/pulls",
                },
                {"name": "BOOM", "url": "https://github.com/boom-astro/boom/pulls"},
            ],
        },
    },
}


def render(template_path, config):
    """Render as fill_conf_values does: no autoescape, loader rooted at the file,
    and the resolved auth backends injected (the login page draws its buttons
    from those, so leaving them out renders a page with no way to log in)."""
    if "auth_backends" not in config:
        config["auth_backends"] = configured_backends()
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(template_path.parent)))
    return env.get_template(template_path.name).render(config)


def test_about_template_renders_deployment_branding():
    out = render(ABOUT_TEMPLATE, FRITZ_LIKE)

    assert "This is Fritz" in out
    assert "https://docs.fritz.science/api.html" in out
    assert "https://github.com/fritz-marshal/fritz" in out
    assert "Fritz development is funded by the Moore Foundation." in out
    # every configured changelog repo is linked
    assert '<a href="https://github.com/fritz-marshal/fritz/pulls">Fritz</a>' in out
    assert '<a href="https://github.com/boom-astro/boom/pulls">BOOM</a>' in out
    # SkyPortal's own defaults must not leak through
    assert "This is SkyPortal" not in out


def test_about_template_expands_link_placeholders():
    out = render(ABOUT_TEMPLATE, FRITZ_LIKE)

    assert '<a href="https://github.com/boom-astro/boom">BOOM</a>' in out
    assert '<a href="https://skyportal.io">SkyPortal</a>' in out
    assert "{BOOM}" not in out


def test_about_template_escapes_characters_jsx_treats_specially():
    """Config prose becomes JSX text, so `'` and `&` must be escaped or the
    generated component fails to build."""
    out = render(ABOUT_TEMPLATE, FRITZ_LIKE)

    assert "Université Paris-Saclay; it&apos;s great." in out
    assert "it's great" not in out
    # the `&` between the two placeholder links
    assert "&amp;" in out


def test_about_template_leaves_bibtex_and_jsx_braces_alone():
    """BibTeX (`{{SkyPortal}`) and JSX object props (`sx={{ p: 1 }}`) both look
    like Jinja expressions; they are wrapped in {% raw %} and must survive."""
    out = render(ABOUT_TEMPLATE, FRITZ_LIKE)

    assert "title = {{SkyPortal}: An Astronomical Data Platform}" in out
    assert "author = {{Duev}, Dmitry A." in out
    assert "sx={{ p: 1 }}" in out


def test_login_template_renders_configured_buttons():
    out = render(LOGIN_TEMPLATE, FRITZ_LIKE)

    assert '<a href="/login/google-oauth2">' in out
    assert '<a href="/login/iam-oauth2">' in out
    assert '<img src="/iam.png" alt="IAM" />' in out
    assert out.count('class="loginButton"') == 2


def test_templates_render_against_the_shipped_config():
    """Guards the config/template pair: a key removed from config.yaml.defaults
    renders as empty rather than raising, so assert the real copy comes out."""
    _, cfg = load_env()

    about = render(ABOUT_TEMPLATE, cfg)
    assert f"This is {cfg['app.title']}" in about
    assert cfg["app.about.repository_url"] in about
    assert "undefined" not in about.lower().split("bibtex")[0]

    login = render(LOGIN_TEMPLATE, cfg)
    for button in cfg["app.login_buttons"]:
        assert button["url"] in login
        assert button["image"] in login


def test_login_template_skips_artwork_for_an_unconfigured_backend():
    """Artwork is matched to a provider by url; an entry naming a provider that
    is not configured must not render a button pointing nowhere."""
    config = {
        "auth_backends": [{"name": "google-oauth2", "label": "Sign in with Google"}],
        "app": {
            **FRITZ_LIKE["app"],
            "login_buttons": [
                {"url": "/login/google-oauth2", "image": "/g.png", "alt_text": "G"},
                {"url": "/login/retired", "image": "/old.png", "alt_text": "Retired"},
            ],
        },
    }

    out = render(LOGIN_TEMPLATE, config)

    assert out.count('class="loginButton"') == 1
    assert "/login/retired" not in out
    assert "/old.png" not in out


def login_config(**user_applications):
    return {
        **FRITZ_LIKE,
        "user_applications": {"enabled": True, **user_applications},
        "invitations": {"enabled": True},
    }


def test_login_template_carries_the_application_form_when_enabled():
    out = render(LOGIN_TEMPLATE, login_config())

    assert 'id="applyForm"' in out
    assert 'name="endorserEmail"' in out
    assert "/api/user_applications" in out


def test_login_template_carries_no_form_when_applications_are_off():
    # applications are approved by issuing an invitation, so they are inert
    # without the invitation pipeline
    assert 'id="applyForm"' not in render(
        LOGIN_TEMPLATE, {**login_config(), "invitations": {"enabled": False}}
    )
    assert 'id="applyForm"' not in render(LOGIN_TEMPLATE, login_config(enabled=False))
    # a config predating the feature must still render a login page
    out = render(LOGIN_TEMPLATE, dict(FRITZ_LIKE))
    assert 'id="applyForm"' not in out
    assert out.count('class="loginButton"') == 2


def test_apply_template_renders_the_configured_preamble():
    _, cfg = load_env()

    out = render(APPLY_TEMPLATE, cfg)

    assert cfg["user_applications.form_preamble"].strip().split("\n")[0] in out
    assert f"Apply for a {cfg['app.title']} account" in out
    assert 'action="/api/user_applications"' not in out  # posted by fetch, not a form
