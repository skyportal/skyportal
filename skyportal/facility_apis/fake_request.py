from tornado import httputil


class FakeApplication:
    """Mimics the Application class of tornado.web.

    Subclasses were minimum required to import the class.
    """

    def __init__(
        self,
    ) -> None:
        super().__init__()
        self.ui_methods = {}
        self.ui_modules = {}
        self.settings = {}


class FakeRequest(httputil.HTTPServerRequest):
    """Mimics the HTTP request handler of tornado.web.

    Subclasses were minimum required to import the class.
    """

    def __init__(
        self,
    ):
        self.test = True
        super().__init__()

        class FakeConnection(object):
            """Mimics the connection within the HTTP request handler."""

            def __init__(
                self,
            ):
                def set_close_callback(self):
                    return True

                self.set_close_callback = set_close_callback

        self.connection = FakeConnection()
