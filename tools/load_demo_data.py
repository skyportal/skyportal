from baselayer.app.env import load_env
from skyportal.model_util import load_demo_data


if __name__ == "__main__":
    """Insert test data"""
    env, cfg = load_env()
    print(f"Running load_demo_data with cfg['database']: {cfg['database']}")
    load_demo_data(cfg)
