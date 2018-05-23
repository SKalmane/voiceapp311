import ast
import arcgis.features as features
import collections
import csv
import json
import unittest
import unittest.mock as mock

import mycity.mycity_request_data_model as my_req
import mycity.intents.intent_constants as intent_constants
import mycity.intents.location_utils as location_utils
import mycity.utilities.gis_utils as gis_utils
import mycity.test.test_constants as test_constants



# char that indicates that line in a data file is a comment
COMMENT_CHAR = "#"
# mocked return value for _get_driving_info
GOOGLE_MAPS_JSON = [{'Driving distance': 2458, 'Driving distance text': '1.5 mi', 
                     'Driving time': 427, 'Driving time text': '7 mins', 
                     'test': '94 Sawyer Ave Boston, MA'}, 
                    {'Driving distance': 692625, 'Driving distance text': '430 mi',
                     'Driving time': 24533, 'Driving time text': '6 hours 49 mins',
                     'test': '4 Olivewood Ct Greenbelt, MD'}]


############################################################
# functions for pulling saved test data from "/test_data"  #
############################################################


def get_test_data(comment_tag, filename):
    """
    Reads test data from file that separates datum with newlines
    :param comment_tag: character indicating this value is 
     a comment
    :param is_json: flag to use json.load instead of ast 
     to build return
    : return ret: a list with all test data 
    """
    ret = []
    with open(filename, "r") as f:
        line =  f.readline()
        while line:
            if line[0] == comment_tag:
                pass
            else: 
                ret.append(ast.literal_eval(line.rstrip()))
            line = f.readline()
    return ret

    


#####################################################
# TestCase class for "../intents/location_utils.py" #
#####################################################



class LocationUtilsTestCase(unittest.TestCase):

    def setUp(self):
        """
        set up mock for MyCityRequestDataModel and start all patches used in
        tests
        
        patched:
            requests.sessions -> for calls to GoogleMaps
            requests.Response -> for functions that get data from Response objs
            arcgis.features.FeatureLayer -> for functions that query arcgis
            servers
        """
        self.mcrd = my_req.MyCityRequestDataModel()
        self.mcrd._session_attributes[intent_constants.CURRENT_ADDRESS_KEY] = ""
        
        # here come the patches
        # patch for utilities that use requests.session
        requests_patch_path = 'mycity.intents.location_utils.requests.sessions'
        self.requests_patch = mock.patch(requests_patch_path)


        # patch for utilities that use requests.Response
        response_patch_path = 'mycity.intents.location_utils.requests.Response'
        self.response_patch = mock.patch(response_patch_path)

        # patch for utilities that use arcgis FeatureLayer.query
        feature_patch_path = 'mycity.intents.location_utils.FeatureLayer'
        self.feature_layer_patch = mock.patch(feature_patch_path) 
                                                     

        # start the patches
        self.requests_patch.start()
        self.response_patch.start()
        self.feature_layer_patch.start()

    def tearDown(self):
        self.mcrd = None
        self.requests_patch.stop()
        self.response_patch.stop()
        self.feature_layer_patch.stop()

    def change_address(self, new_address):
        self.mcrd.session_attributes[intent_constants.CURRENT_ADDRESS_KEY] = \
            new_address

    def compare_built_address(self, expected_result):
        origin_addr = location_utils.build_origin_address(self.mcrd)
        self.assertEqual(origin_addr, expected_result)
 
    def test_build_origin_address_with_normal_address(self):
        self.change_address("46 Everdean St.")
        self.compare_built_address("46 Everdean St Boston MA")
        
    def test_get_dest_addresses_from_features(self):
        data = get_test_data(COMMENT_CHAR, test_constants.PARKING_LOTS_TEST_DATA)
        to_test = \
            location_utils._get_dest_addresses_from_features(
            test_constants.PARKING_LOTS_ADDR_INDEX, 
            data[0:5]
            )
        for address in to_test:
            self.assertTrue(address.find("Boston, MA"))

    def test_setup_google_maps_query_params(self):
        origin = "46 Everdean St Boston, MA"
        dests = ["123 Fake St Boston, MA", "1600 Penn Ave Washington, DC"]
        to_test = location_utils._setup_google_maps_query_params(origin, dests)
        self.assertEqual(origin, to_test["origins"])
        self.assertEqual(dests, to_test["destinations"].split("|"))
        self.assertEqual("imperial", to_test["units"])

    def test_parse_closest_location_info(self):
        feature_type = 'Fake feature'
        closest_location_info = {'Driving distance': 'fake',
                              'Driving distance text': 'also fake',
                              'Driving time': 'triply fake',
                              'Driving time text': 'fake like a mug',
                              feature_type: 'fake fake fake fake'}
        to_test = location_utils._parse_closest_location_info(feature_type, closest_location_info)
        self.assertIn(location_utils.DRIVING_DISTANCE_TEXT_KEY, to_test)
        self.assertIn(location_utils.DRIVING_TIME_TEXT_KEY, to_test)
        self.assertIn(feature_type, to_test)
        self.assertNotIn('Driving time', to_test)
        self.assertNotIn('Driving distance', to_test)

    @mock.patch('mycity.intents.location_utils._get_driving_info', 
                return_value=GOOGLE_MAPS_JSON)
    def test_get_closest_feature(self, mock_get_driving_info):
        test_origin = "46 Everdean St Boston, MA"
        test_features = [['close', '94 Sawyer Ave Boston, MA'],
                         ['far', '4 Olivewood Ct Greenbelt, MD']]
        feature_address_index = 1
        feature_type = "test"
        error_message = "Test error message"
        result = location_utils.get_closest_feature(test_origin, 
                                                   feature_address_index,
                                                    feature_type,
                                                    error_message,
                                                    test_features)
        self.assertEqual("94 Sawyer Ave Boston, MA", result[feature_type])
        self.assertEqual('7 mins', result[location_utils.DRIVING_TIME_TEXT_KEY])
        self.assertEqual('1.5 mi', result[location_utils.DRIVING_DISTANCE_TEXT_KEY])
    
    def test_create_record_model(self):
        Record = collections.namedtuple('TestRecord', ['field_1', 'field_2'])
        to_test = location_utils.create_record_model(model_name = 'TestRecord',
                                                     fields=['\tfield_1', 'field_2\n\n'])
        self.assertEqual(Record, to_test)

    def test_csv_to_namedtuples(self):
        csv = test_constants.PARKING_LOTS_TEST_CSV
        fields = ['X','Y','FID','OBJECTID','Spaces','Fee','Comments','Phone','Name','Address',
                  'Neighborho','Maxspaces','Hours','GlobalID','CreationDate','Creator',
                  'EditDate','Editor']
        Record = collections.namedtuple('Record', fields)
        with open(csv, 'r') as csv_file:
            csv_file.readline()        # remove header
            to_test= location_utils.csv_to_namedtuples(Record, csv_file)
        self.assertIsInstance(collections.namedtuple, to_test[0])

    def test_csv_to_namedtuples_address_field_not_null(self):
        csv = test_constants.PARKING_LOTS_TEST_CSV
        fields = ['X','Y','FID','OBJECTID','Spaces','Fee','Comments','Phone','Name','Address',
                  'Neighborho','Maxspaces','Hours','GlobalID','CreationDate','Creator',
                  'EditDate','Editor']
        Record = collections.namedtuple('Record', fields)
        with open(csv, 'r') as csv_file:
            csv_file.readline()        # remove header
            csv_reader = csv.reader(csv_file, delimiter = ",")
            records = location_utils.csv_to_namedtuples(Record, csv_reader)
        record_to_test = records[0]
        self.assertIsNotNone(record_to_test.Address)

    def test_add_city_and_state_to_records(self):
        Record = collections.namedtuple('Record', ['test_field', 'Address'])
        records = []
        records.append(Record(test_field='wes', Address = '1000 Dorchester Ave'))
        records.append(Record(test_field='drew', Address = '123 Fake St'))
        to_test = location_utils.add_city_and_state_to_records(records, 'Boston', 'MA')
        for record in to_test:
            self.assertIn("Boston, MA", record)

    def test_map_addresses_to_record(self):
        Record = collections.namedtuple('Record', ['test_field', 'Address'])
        records = []
        records.append(Record._make('wes', '1000 Dorchester Ave'))
        records.append(Record._make('drew', '123 Fake St'))
        to_test = location_utils.map_addresses_to_records(records)
        self.assertEqual(records[0].Address, to_test['1000 Dorchester Ave'])



    ####################################################################
    # Tests that should only be run if we're connected to the Internet #
    ####################################################################

#     def test_get_features_from_feature_server(self):
#         url = ('https://services.arcgis.com/sFnw0xNflSi8J0uh/'
#                'ArcGIS/rest/services/SnowParking/FeatureServer/0')
#         query = '1=1'
#         test_set = location_utils.get_features_from_feature_server(url, query)
#         self.assertIsInstance(test_set[0], list)


#     def test_get_closest_feature(self):
#         origin = "46 Everdean St"
#         features = [ ["far", "19 Ashford St"],
#                   ["close", "94 Sawyer Ave"],
#                   ["closest", "50 Everdean St"] ]
#         address_index = 1
#         feature_type = "test_feature"
#         closest = location_utils.get_closest_feature(origin, address_index, 
#                                                      feature_type,
#                                                      "A fake error message",
#                                                      features)
#         self.assertEqual("50 Everdean St Boston, MA", closest[feature_type])
#         self.assertIsInstance(closest[location_utils.DRIVING_DISTANCE_TEXT_KEY],
#                               str)
#         self.assertIsInstance(closest[location_utils.DRIVING_TIME_TEXT_KEY],
#                               str)
#         # check to make sure DRIVING_DISTANCE and DRIVING_TIME are not 
#         # empty strings
#         self.assertNotEqual("", closest[location_utils.DRIVING_DISTANCE_TEXT_KEY])
#         self.assertNotEqual("", closest[location_utils.DRIVING_TIME_TEXT_KEY])

#     def test_get_closest_feature_with_error(self):
#         """
#         A call to get_closest_feature that fails should return a dict
#         with these key:value pairs
#             { feature_type: False,
#               DRIVING_DISTANCE_TEXT_KEY: False,
#               DRIVING_TIME_TEXT_KEY: False 
#             }
#         """
#         origin = "46 Everdean St"
#         features = [ ]
#         address_index = 1
#         feature_type = "test_feature"
#         closest = location_utils.get_closest_feature(origin, address_index,
#                                                      feature_type,
#                                                      "A fake error message",
#                                                      features)
#         self.assertFalse(closest[feature_type])
#         self.assertFalse(closest[location_utils.DRIVING_DISTANCE_TEXT_KEY])
#         self.assertFalse(closest[location_utils.DRIVING_TIME_TEXT_KEY])

