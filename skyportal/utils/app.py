from baselayer.app.env import load_env

_, cfg = load_env()


def get_app_base_url():
    ports_to_ignore = {True: 443, False: 80}  # True/False <-> server.ssl=True/False
    return f"{'https' if cfg['server.ssl'] else 'http'}://{cfg['server.host']}" + (
        f":{cfg['server.port']}"
        if (
            cfg["server.port"] is not None
            and cfg["server.port"] != ports_to_ignore[cfg["server.ssl"]]
        )
        else ""
    )
