from jinja2 import Environment, FileSystemLoader, select_autoescape

_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "j2"]),
)


def render_web(raw: dict, brief: dict, generated_at: str) -> str:
    return _env.get_template("web.html.j2").render(
        raw=raw, brief=brief, generated_at=generated_at)


def render_email(brief: dict, web_url: str, generated_at: str) -> str:
    return _env.get_template("email.html.j2").render(
        brief=brief, web_url=web_url, generated_at=generated_at)
