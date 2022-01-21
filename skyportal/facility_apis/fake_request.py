from tornado import httputil


class FakeApplication:
    def __init__(
        self,
    ) -> None:
        super().__init__()
        self.ui_methods = {}
        self.ui_modules = {}
        self.settings = {}


class FakeRequest(httputil.HTTPServerRequest):
    def __init__(
        self,
    ) -> None:
        self.test = True
        super().__init__()

        class FakeConnection(object):
            def __init__(
                self,
            ) -> None:
                def set_close_callback(self):
                    return True

                self.set_close_callback = set_close_callback

        self.connection = FakeConnection()


fake_request = FakeRequest()
