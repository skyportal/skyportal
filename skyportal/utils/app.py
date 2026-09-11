from baselayer.app.env import load_env

_, cfg = load_env()


def get_app_base_url():
    default_port = 443 if cfg["server.ssl"] else 80
    port = (
        f":{cfg['server.port']}"
        if cfg["server.port"] not in (None, default_port)
        else ""
    )
    return f"{'https' if cfg['server.ssl'] else 'http'}://{cfg['server.host']}{port}"
