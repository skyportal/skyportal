from marshmallow import fields


# These are just throwaway helper classes to help with deserialization
class UTCTZnaiveDateTime(fields.DateTime):
    """
    DateTime object that deserializes both timezone aware iso8601
    strings and naive iso8601 strings into naive datetime objects
    in utc

    See discussion in https://github.com/Scille/umongo/issues/44#issuecomment-244407236
    """

    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data, **kwargs)
        if value and value.tzinfo:
            value = (value - value.utcoffset()).replace(tzinfo=None)
        return value
