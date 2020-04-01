import json
from datetime import datetime, timedelta, date
from discovergy.discovergy import Discovergy
import redis
from models.user import User, GenderType, StateType
from models.group import Group
from tests.buzzn_test_case import BuzznTestCase
from util.database import db
from util.task import get_all_meter_ids, get_all_users, calc_term_boundaries, calc_end,\
    calc_support_year_start, calc_support_year_start_datetime,\
    calc_support_week_start, calc_two_days_back,\
    check_and_nullify_power_value, client_name, Task


ALL_METER_IDS = ['dca0ec32454e4bdd9ed719fbc9fb75d6', '6fdbd41a93d8421cac4ea033203844d1',
                 'bf60438327b1498c9df4e43fc9327849', '0a0f65e992c042e4b86956f3f080114d',
                 '5e769d5b83934bccae11a8fa95e0dc5f', 'e2a7468f0cf64b7ca3f3d1350b893c6d']

READING = {'time': 1585177200000, 'values': {'power': 5727055, 'power3': 1898229,
                                             'energyOut': 0, 'power1': 1917350,
                                             'energy': 1551192369639000, 'power2': 1900643}}

READING_NEGATIVE_POWER = {'time': 1584572400000, 'values': {'power': -4784541, 'power3': 1583777,
                                                            'energyOut': 0, 'power1': 1599778,
                                                            'energy': 1541570917834000,
                                                            'power2': 1589981}}


class TaskTestCase(BuzznTestCase):
    """ Unit tests for class Task and helper methods. """

    def setUp(self):
        """ Create test users and a test group in the database. """

        db.drop_all()
        db.create_all()
        self.test_user = User(GenderType.MALE, 'Some', 'User', 'test@test.net',
                              'TestToken', 'dca0ec32454e4bdd9ed719fbc9fb75d6', 1)
        self.test_user.flat_size = 60.0
        self.test_user.inhabitants = 2
        self.test_user.set_password('some_password')
        self.test_user.state = StateType.ACTIVE
        db.session.add(self.test_user)
        self.test_user2 = User(GenderType.FEMALE, 'judith', 'greif', 'judith@buzzn.net',
                               'TestToken2', '6fdbd41a93d8421cac4ea033203844d1', 1)
        db.session.add(self.test_user2)
        self.test_user3 = User(GenderType.MALE, 'danny', 'stey', 'danny@buzzn.net',
                               'TestToken3', 'bf60438327b1498c9df4e43fc9327849', 1)
        db.session.add(self.test_user3)
        db.session.add(Group('TestGroup',
                             '0a0f65e992c042e4b86956f3f080114d',
                             '5e769d5b83934bccae11a8fa95e0dc5f',
                             'e2a7468f0cf64b7ca3f3d1350b893c6d'))
        db.session.commit()
        self.client.post('/login', data=json.dumps({'user': 'test@test.net',
                                                    'password': 'some_password'}))
        self.task = Task()

    def test_get_all_meter_ids(self):
        """ Unit tests for function get_all_meter_ids(). """

        result = get_all_meter_ids(db.session)

        # Check return types
        self.assertIsInstance(result, list)
        for meter_id in result:
            self.assertIsInstance(meter_id, str)
            self.assertTrue(meter_id.isalnum())

        # Check return values
        self.assertEqual(result, ALL_METER_IDS)
        for meter_id in result:
            self.assertEqual(len(meter_id), 32)

    def test_get_all_users(self):
        """ Unit tests for function get_all_users(). """

        result = get_all_users(db.session)

        # Check result types
        self.assertIsInstance(result, list)
        for user in result:
            self.assertIsInstance(user, User)

        # Check result values
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], self.test_user)
        self.assertEqual(result[1], self.test_user2)
        self.assertEqual(result[2], self.test_user3)

    def test_calc_term_boundaries(self):
        """ Unit tests for function calc_term_boundaries().
        Expect begin_ongoing_term to equal the s_term_boundaries of the current support
        year at 00:00:00 UTC.
        Expect end_ongoing_term to equal today at 00:00:00 UTC.
        Expect begin_previous_term to equal the start of the previous support
        year at 00:00:00 UTC.
        Expect end_previous_term to equal the end of the previous support year
        at 00:00:00 UTC.
        """

        result = calc_term_boundaries()
        today = datetime.today()

        # Check result types
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 4)
        for timestamp in result:
            self.assertIsInstance(timestamp, int)

        # Check result values
        self.assertEqual(result[0], calc_support_year_start())
        begin_ongoing_term = datetime.fromtimestamp(result[0]/1000)

        end_ongoing_term = datetime.fromtimestamp(result[1]/1000)
        self.assertEqual(end_ongoing_term.year, today.year)
        self.assertEqual(end_ongoing_term.month, today.month)
        self.assertEqual(end_ongoing_term.day, today.day)
        for value in end_ongoing_term.hour, end_ongoing_term.minute, end_ongoing_term.second:
            self.assertEqual(value, 0)

        begin_previous_term = datetime.fromtimestamp(result[2]/1000)
        self.assertEqual(begin_previous_term.year, begin_ongoing_term.year - 1)
        self.assertEqual(begin_previous_term.month, 3)
        self.assertEqual(begin_previous_term.day, 12)
        for value in begin_previous_term.hour, begin_previous_term.minute,\
                begin_previous_term.second:
            self.assertEqual(value, 0)

        end_previous_term = datetime.fromtimestamp(result[3]/1000)
        self.assertEqual(end_previous_term.year, begin_ongoing_term.year)
        self.assertEqual(end_previous_term.month, 3)
        self.assertEqual(end_previous_term.day, 11)
        for value in end_previous_term.hour, end_previous_term.minute, end_previous_term.second:
            self.assertEqual(value, 0)

    def test_calc_end(self):
        """ Unit tests for function calc_end(). """

        result = calc_end()

        # Check return type
        self.assertIsInstance(result, int)

    def test_calc_support_year_start(self):
        """ Unit tests for function calc_support_year_start().
        Expect Mar-12 last year if today is between Jan-01 and Mar-11.
        Expect Mar-12 this year if today is after Mar-11.
        """

        result = calc_support_year_start()

        # Check result type
        self.assertIsInstance(result, int)

        # Check result values
        d = datetime.fromtimestamp(
            float(result/1000))
        self.assertEqual(d.day, 12)
        self.assertEqual(d.month, 3)
        if (datetime.utcnow().month < d.month) or (datetime.utcnow().month == d.month
                                                   and datetime.utcnow().day < d.day):
            self.assertEqual(d.year, datetime.utcnow().year - 1)
        else:
            self.assertEqual(d.year, datetime.utcnow().year)

    def test_calc_support_year_start_datetime(self):
        """ Unit tests for function calc_support_year_start_datetime().
        Expect Mar-12 last year as datetime.datetime.date object if today is
        between Jan-01 and Mar-11.
        Expect Mar-12 this year as datetime.datetime.date object if today is
        after Mar-11.
        """

        result = calc_support_year_start_datetime()

        # Check result type
        self.assertIsInstance(result, date)

        # Check result values
        self.assertEqual(result.day, 12)
        self.assertEqual(result.month, 3)

        if datetime.utcnow().month < result.month:
            self.assertEqual(result.year, datetime.utcnow().year - 1)
        elif datetime.utcnow().month == result.month and datetime.utcnow().day < result.day:
            self.assertEqual(result.year, datetime.utcnow().year - 1)
        else:
            self.assertEqual(result.year, datetime.utcnow().year)

    def test_calc_support_week_start(self):
        """ Unit tests for function calc_support_week_start().
        Expect one week back if today is before Mar-12 or after Mar-18.
        Expect start of support year, i.e. Mar-12 this year, if today is
        between Mar-11 and Mar-19.
        """

        result = calc_support_week_start()

        # Check result type
        self.assertIsInstance(result, int)

        # Check result values
        d = datetime.fromtimestamp(
            float(result/1000))
        if (datetime.utcnow().month == 3) and (11 < datetime.utcnow().day < 19):
            self.assertEqual(d.year, datetime.utcnow().year)
            self.assertEqual(d.month, 3)
            self.assertEqual(d.day, 12)
        else:
            self.assertEqual(d.date(), (datetime.utcnow() -
                                        timedelta(days=7)).date())

    def test_calc_two_days_back(self):
        """ Unit tests for function calc_two_days_back(). """

        result = calc_two_days_back()

        # Check return type
        self.assertIsInstance(result, int)

    def test_check_and_nullify_power_value(self):
        """ Unit tests for function check_and_nullify_power_value(). """

        result = check_and_nullify_power_value(
            READING, self.test_user.meter_id)
        result_adjusted = check_and_nullify_power_value(READING_NEGATIVE_POWER,
                                                        self.test_user.meter_id)

        # Check result types
        self.assertIsInstance(result, dict)
        self.assertIsInstance(result_adjusted, dict)

        # Check result values
        self.assertEqual(result['values']['power'], READING['values']['power'])
        self.assertEqual(result_adjusted['values']['power'], 0)

    def check_init(self):
        """ Unit tests for function Task.__init__(). """

        # Check class variables
        self.assertIsInstance(self.task.d, Discovergy)
        self.assertIsInstance(self.task.redis_client, redis.Redis)
        self.assertEqual(self.task.d.client_name, client_name)
