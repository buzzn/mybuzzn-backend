import json
from flask import make_response

class Error:
    """Represents an error which occurred in the application."""

    def __init__(self, name, description):
        self.name = name
        self.description = description

    def to_json(self):
        return json.dumps(self.__dict__)

    def make_json_response(self, status):
        response = make_response(self.__dict__, status)
        response.headers['Content-Type'] = 'application/json'
        return response


UNKNOWN_RESOURCE = Error('Unknown resource', 'This resource is not available.')
UNKNOWN_USER = Error('Unknown user', 'This user is not known.')
NO_USERS = Error('No users', 'There are no users in the database.')
UNKNOWN_GROUP = Error('Unknown group', 'This group is not known.')
NO_METER_ID = Error('No meter id', 'No meter id was received.')
NO_GLOBAL_CHALLENGE = Error(
    'No global challenge',
    'There are not enough historical energy values to calculate the saving \
prognosis for this user.')
NO_BASELINE = Error('No baseline', 'There are not enough historical energy \
values to calculate the baseline for this user.')
NO_PER_CAPITA_CONSUMPTION = Error('No per capita consumption', 'There is no \
per capita consumption value for this user in the database.')
exception_template = "An exception of type {0} occurred. Arguments:\n{1!r}"


def exception_message(e):
    """ Generate a proper formatted and meaningful exception message.
    :return: an exception message string
    :rtype: str
    """

    return exception_template.format(type(e).__name__, e.args)
