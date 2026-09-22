"""Give the container its own app.secret_key before the app starts."""

from skyportal.utils.secret_key import ensure_secret_key

if __name__ == "__main__":
    raise SystemExit(ensure_secret_key())
