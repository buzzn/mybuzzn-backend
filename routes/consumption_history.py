import os
from functools import wraps
from datetime import datetime

# We want to structure our routes in different modules and therefore use equal
# imports. Likewise, we want the logger in each module for now.
# pylint: disable=duplicate-code
import logging
# pylint: disable=duplicate-code
from flask import Blueprint, jsonify, request, redirect
# pylint: disable=duplicate-code
from flask_api import status
# pylint: disable=duplicate-code
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
# pylint: disable=duplicate-code
from flask import current_app as app
# pylint: disable=duplicate-code
from discovergy.discovergy import Discovergy
# pylint: disable=duplicate-code
from models.group import Group
# pylint: disable=duplicate-code
from models.user import User
# pylint: disable=duplicate-code
from util.database import db
# pylint: disable=duplicate-code
from util.error import UNKNOWN_USER, UNKNOWN_GROUP


# pylint: disable=duplicate-code
logger = logging.getLogger(__name__)
IndividualConsumptionHistory = Blueprint('IndividualConsumptionHistory',
                                         __name__)
GroupConsumptionHistory = Blueprint('GroupConsumptionHistory', __name__)


def login_required(fn):
    """ Wraps a function and injects a login check before each call. Redirects
    to the login page if the current user is not logged in.
    :param fn: the function to wrap.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        # pylint: disable=duplicate-code
        verify_jwt_in_request()
        # pylint: disable=duplicate-code
        user_id = get_jwt_identity()
        # pylint: disable=duplicate-code
        target_user = User.query.filter_by(id=user_id).first()
        if target_user is None:
            return redirect('/admin/login', code=403)
        return fn(*args, **kwargs)
    return wrapper


def read_parameters():
    """ Use the given parameters. """

    # Calculate the minimal time of "today", i.e. 00:00 am, as unix timestamp
    # as integer with milliseconds precision. The timestamp format is required
    # by the discovergy API, cf. https://api.discovergy.com/docs/
    start = round(datetime.combine(datetime.now(),
                                   datetime.min.time()).timestamp() * 1e3)
    begin = request.args.get('begin', default=start, type=int)
    end = request.args.get('end', default=None, type=int)
    tics = request.args.get('tics', default='one_hour', type=str)
    return begin, end, tics


@IndividualConsumptionHistory.route('/individual-consumption-history',
                                    methods=['GET'])
@login_required
def individual_consumption_history():
    """ Shows the history of consumption of the given time interval in mW.
    :param int begin: start time of consumption, default is today at 0:00
    :param int end: end time of consumption, default is
    datetime.datetime.now()
    :param str tics: time distance between returned readings with
    possible values 'raw', 'three_minutes', 'fifteen_minutes', 'one_hour',
    'one_day', 'one_week', 'one_month', 'one_year', default is 'one_hour'
    :return: (a JSON object where each meter reading is mapped to its point
    in time, 200) or ({}, 206) if there is no history
    :rtype: tuple
    """

    user_id = get_jwt_identity()
    user = db.session.query(User).filter_by(id=user_id).first()
    if user is None:
        return UNKNOWN_USER

    # Call discovergy API for the given meter
    begin, end, tics = read_parameters()
    client_name = app.config['CLIENT_NAME']
    d = Discovergy(client_name)
    d.login(os.environ['EMAIL'], os.environ['PASSWORD'])
    result = {}
    try:
        readings = d.get_readings(user.meter_id, begin, end, tics)
        for reading in readings:
            result[reading.get('time')] = reading.get('values').get('power')

        # Return result
        return jsonify(result), status.HTTP_200_OK

    except ValueError as e:
        logger.error("Exception: %s", e)

        # Return result
        return jsonify(result), status.HTTP_206_PARTIAL_CONTENT


@GroupConsumptionHistory.route('/group-consumption-history', methods=['GET'])
@login_required
def group_consumption_history():
    """ Shows the history of consumption of the given time interval in mW.
    :param int begin: start time of consumption, default is today at 0:00
    :param int end: end time of consumption, default is $now
    :param str tics: time distance between returned readings with possible
    values 'raw', 'three_minutes', 'fifteen_minutes', 'one_hour', 'one_day',
    'one_week', 'one_month', 'one_year', default is 'one_hour'
    :return: ({"consumed": str => int, "produced": str => int}, 200) or ({},
    206) if there is no history
    :rtype: tuple
    """

    user_id = get_jwt_identity()
    user = db.session.query(User).filter_by(id=user_id).first()
    if user is None:
        return UNKNOWN_USER
    group = db.session.query(Group).filter_by(_id=user.group_id).first()
    if group is None:
        return UNKNOWN_GROUP

    # Call discovergy API for the given group meter
    begin, end, tics = read_parameters()
    client_name = app.config['CLIENT_NAME']
    d = Discovergy(client_name)
    d.login(os.environ['EMAIL'], os.environ['PASSWORD'])
    result = {}
    produced = {}
    consumed = {}

    try:
        readings = d.get_readings(group._group_meter_id, begin, end,
                                  tics)
        for reading in readings:
            produced[reading.get('time')] = reading.get(
                'values').get('energyOut')
            consumed[reading.get('time')] = reading.get('values').get('power')

        # Return result
        result["consumed"] = consumed
        result["produced"] = produced
        return jsonify(result), status.HTTP_200_OK

    except TypeError as e:
        logger.error("Exception: %s", e)

        # Return result
        return jsonify(result), status.HTTP_206_PARTIAL_CONTENT
