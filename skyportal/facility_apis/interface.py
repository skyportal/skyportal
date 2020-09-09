from ._base import _Base


class FacilityResponseHandler:
    """An interface that User-contributed remote facility message listeners
    must provide."""

    # subclasses *must* implement the method below
    @staticmethod
    def receive_message(message):
        """Handle a POSTed message from a remote facility.

        Parameters
        ----------
        message: skyportal.models.FacilityMessage
           The message sent by the remote facility.
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
