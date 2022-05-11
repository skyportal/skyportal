from ._base import _Base, _ListenerBase


class Listener(_ListenerBase):
    """An interface that User-contributed remote facility message listeners
    must provide. User-contributed classes must subclass this."""

    # JSON schema of the incoming messages. All user-contributed fields
    # should go here (followup-request ID is added automatically in the base
    # class and does not need to be added here).
    schema = {}

    # subclasses *must* implement the method below
    @staticmethod
    def receive_message(handler_instance):
        """Handle a POSTed message from a remote facility.

        Parameters
        ----------
        handler_instance: skyportal.handlers.FacilityMessageHandler
           The instance of the handler that received the request.
        """
        raise NotImplementedError


class FollowUpAPI(_Base):
    """An interface that User-contributed remote facility APIs must provide."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request):
        """Submit a follow-up request to a remote observatory.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to submit.
        """
        raise NotImplementedError

    # subclasses should implement this if desired
    @staticmethod
    def update(request):
        """Update an already submitted request.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The updated request.
        """
        raise NotImplementedError

    # subclasses should implement this if desired
    @staticmethod
    def get(request):
        """Check the status of a submitted request.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to check the status of.
        """
        raise NotImplementedError

    # subclasses should implement this if desired
    @staticmethod
    def delete(request):
        """Delete a submitted request from the facility's queue.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        """
        raise NotImplementedError

    # subclasses should implement this if desired
    @staticmethod
    def send(request):
        """Send an observation plan to the facility's queue.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        """
        raise NotImplementedError

    # subclasses should implement this if desired
    @staticmethod
    def remove(request):
        """Remove an observation plan from the facility's queue.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to remove from the queue and the SkyPortal database.
        """
        raise NotImplementedError

    # subclasses should implement this if desired
    @staticmethod
    def retrieve():
        """Retrieve the status of executed observations."""
        raise NotImplementedError

    # subclasses should implement this if desired
    @staticmethod
    def queued():
        """Retrieve the status of planned observations."""
        raise NotImplementedError

    # jsonschema outlining the schema of the frontend form. See
    # https://github.com/rjsf-team/react-jsonschema-form
    # for examples.
    form_json_schema = None

    # ui dictionary outlining any ui overrides for the form See
    # https://react-jsonschema-form.readthedocs.io/en/latest/api-reference/uiSchema/
    # for documentation
    ui_json_schema = None

    # mapping of any jsonschema property names to how they shoud be rendered
    # on the frontend. example - {"observation_mode": "Observation Mode"}
    alias_lookup = {}
