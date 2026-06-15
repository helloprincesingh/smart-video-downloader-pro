import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Optionally run with a self-signed HTTPS certificate for local testing.
    # Set the environment variable `USE_HTTPS=1` to enable HTTPS (adhoc cert).
    use_https = os.environ.get('USE_HTTPS', '').lower() in ('1', 'true', 'yes')
    if use_https:
        app.run(host="0.0.0.0", port=5000, debug=True, ssl_context='adhoc')
    else:
        app.run(host="0.0.0.0", port=5000, debug=True)
