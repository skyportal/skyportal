from baselayer.app.env import load_env

_, cfg = load_env()


def get_app_base_url():
    port = (
        f":{cfg['server.port']}"
        if cfg.get("server.port") not in (None, 80, 443)
        else ""
    )
    return f"{'https' if cfg['server.ssl'] else 'http'}://{cfg['server.host']}{port}"
