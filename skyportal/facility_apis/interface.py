from ._base import _Base


class FollowUpAPI(_Base):
    """An interface that User-contributed remote facility APIs must provide."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request):
        """Submit a follow-up request to a remote observatory."""
        raise NotImplementedError

    # subclasses should implement this if desired
    @staticmethod
    def update(request):
        """Update an already submitted request."""
        raise NotImplementedError

    # subclasses should implement this if desired
    @staticmethod
    def get(request):
        """Check the status of a submitted request."""
        raise NotImplementedError

    # subclasses should implement this if desired
    @staticmethod
    def delete(request):
        """Delete a submitted request from the facility's queue."""
        raise NotImplementedError

    form_json_schema = None
    ui_json_schema = None
    alias_lookup = {}
