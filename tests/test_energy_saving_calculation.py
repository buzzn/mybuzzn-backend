from unittest import mock
from datetime import datetime
import json
from models.user import User, GenderType
from tests.buzzn_test_case import BuzznTestCase
from tests.string_constants import ALL_USER_METER_IDS,\
    READINGS_ALL_TERMS, READINGS_ESTIMATION, READINGS_LAST_TERM, READINGS_ONGOING_TERM, \
    ENERGY_CONSUMPTION_LAST_TERM, ENERGY_CONSUMPTION_ONGOING_TERM, SQLALCHEMY_RETURN_VALUES
from util.database import db
from util.energy_saving_calculation import calc_ratio_values,\
    calc_energy_consumption_last_term, calc_energy_consumption_ongoing_term,\
    calc_estimated_energy_consumption, calc_estimated_energy_saving


class EnergySavingCalculationTestCase(BuzznTestCase):
    """ Unit tests for energy saving calculation methods. """

    def setUp(self):
        """ Create test users, test group and load profile in the database. """

        super().setUp()
        db.session.add(User(GenderType.FEMALE, 'judith', 'greif', 'judith@buzzn.net',
                            'TestToken2', '52d7c87f8c26433dbd095048ad30c8cf', 1))
        db.session.add(User(GenderType.MALE, 'danny', 'stey', 'danny@buzzn.net',
                            'TestToken3', '117154df05874f41bfdaebcae6abfe98', 1))
        db.session.commit()
        self.client.post('/login', data=json.dumps({'user': 'test@test.net',
                                                    'password': 'some_password1'}))

    # pylint: disable=unused-argument
    @mock.patch('sqlalchemy.engine.result.ResultProxy.first',
                side_effect=SQLALCHEMY_RETURN_VALUES)
    def test_calc_ratio_values(self, first):
        """ Unit tests for function calc_ratio_values(). """

        start = datetime(2019, 3, 12).date()
        result = calc_ratio_values(start)

        # Check result type
        self.assertIsInstance(result, float)

        # Check result value
        self.assertTrue(1.0 >= result >= 0.0)

    # pylint: disable=unused-argument
    @mock.patch('redis.Redis.get', side_effect=READINGS_LAST_TERM)
    def test_calc_energy_consumption_last_term(self, get):
        """ Unit tests for function calc_energy_consumption_last_term() """

        start = datetime(2020, 3, 12).date()
        result = calc_energy_consumption_last_term(
            ALL_USER_METER_IDS[1], start)

        # Check result type
        self.assertIsInstance(result, (int, type(None)))
        # Check result value
        self.assertEqual(result, ENERGY_CONSUMPTION_LAST_TERM)

    # pylint: disable=unused-argument
    @mock.patch('redis.Redis.get', side_effect=READINGS_ONGOING_TERM)
    def test_calc_energy_consumption_ongoing_term(self, get):
        """ Unit tests for function calc_energy_consumption_ongoing_term() """

        start = datetime(2019, 3, 12).date()
        result = calc_energy_consumption_ongoing_term(ALL_USER_METER_IDS[1],
                                                      start)

        # Check result type
        self.assertIsInstance(result, (int, type(None)))
        # Check result value
        self.assertEqual(result, ENERGY_CONSUMPTION_ONGOING_TERM)

    # pylint: disable=unused-argument
    @mock.patch('redis.Redis.get', side_effect=READINGS_ALL_TERMS)
    def test_calc_estimated_energy_consumption(self, get):
        """ Unit tests for function calc_estimated_energy_consumption() """

        start = datetime(2019, 3, 12).date()
        result = calc_estimated_energy_consumption(
            ALL_USER_METER_IDS[1], start)

        # Check result types
        self.assertIsInstance(result, (float, type(None)))

    # pylint: disable=unused-argument
    @mock.patch('redis.Redis.get', side_effect=READINGS_ESTIMATION)
    def test_calc_estimated_energy_saving(self, get):
        """ Unit tests for function calc_estimated_energy_saving() """

        start = datetime(2019, 3, 12).date()
        result = calc_estimated_energy_saving(ALL_USER_METER_IDS[1], start)

        # Check result types
        self.assertIsInstance(result, (float, type(None)))
