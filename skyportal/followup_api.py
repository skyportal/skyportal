import requests
from baselayer.app.models import DBSession
from abc import ABC, abstractmethod


def require_editable(func):
    """Require that an instance of FollowupAPI has requests_editable=True to
    call the wrapped function."""
    def wrapped_func(self, request):
        if not self.reqests_editable:
            raise RuntimeError(f'Cannot edit requests under API {self.__class__}')
        else:
            return func(self, request)
    return wrapped_func


# This is an abstract class designed to be subclassed and extended
class FollowupAPI(ABC):
    requests_editable = False

    @abstractmethod
    def _submit(self, request):
        pass

    @abstractmethod
    def _delete(self, request):
        pass

    @abstractmethod
    def _update(self, request, new_parameters):
        pass

    def submit(self, request):
        """Submit a RoboticFollowupRequest to the scheduler"""
        self._submit(request)

    @require_editable
    def delete(self, request):
        """Delete a RoboticFollowupRequest from the scheduler"""
        self._delete(request)

    @require_editable
    def update(self, request, new_parameters):
        """Modify an existing RoboticFollowupRequest in the scheduler"""
        self._update(request, new_parameters)


class ExampleAPI(FollowupAPI):
    """This is an Example API implementation"""

    def _submit(self, request):
        endpoint = 'https://dummy.api.tel.edu/submit/'
        obs = request.observations
        responses = []
        for i, o in enumerate(obs):
            # this is where you would call requests.post
            # requests.post(endpoint, data=o)
            response = {'id': i, 'packet': o, 'status': 'ok'}
            responses.append(response)
        request.status = 'submitted'

    def _delete(self, request):
        pass

    def _update(self, request, new_parameters):
        pass


apis = {c.__name__: c() for c in (FollowupAPI.__subclasses__() or [])}
