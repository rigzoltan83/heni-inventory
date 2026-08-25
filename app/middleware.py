class PrefixMiddleware:
    def __init__(self, app, prefix=""):
        self.app = app
        self.prefix = prefix.rstrip("/")

    def __call__(self, environ, start_response):
        if self.prefix:
            environ["SCRIPT_NAME"] = self.prefix

        return self.app(
            environ,
            start_response,
        )
