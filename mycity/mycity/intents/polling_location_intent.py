"""Alexa intent used to find the closest polling location"""


import mycity.intents.intent_constants as intent_constants
import mycity.utilities.google_maps_utils as g_maps_utils
from mycity.utilities.finder.FinderCSV import FinderCSV
from mycity.mycity_response_data_model import MyCityResponseDataModel





# Constants 
POLLING_LOCATION_URL = ("http://bostonopendata-boston.opendata.arcgis.com/datasets/"
                    "053b0359485d435abfb525e07e298885_0.csv")
DRIVING_DIST = g_maps_utils.DRIVING_DISTANCE_TEXT_KEY
DRIVING_TIME = g_maps_utils.DRIVING_TIME_TEXT_KEY
OUTPUT_SPEECH_FORMAT = \
    ("The closest polling location, {Location2}, is at "
     "{Location3}. It is {" + DRIVING_DIST + "} away and should take "
     "you {" + DRIVING_TIME + "} to drive there. {WardsPrec}")
ADDRESS_KEY = "Location3"


def format_record_fields(record):
   record["WardsPrec"] = "This location belongs to {}.".format(record["WardsPrec"]) \
       if record["WardsPrec"].strip() != "" else ""   
   

def get_polling_location_intent(mycity_request):
    """
    Populate MyCityResponseDataModel with polling location response information.

    :param mycity_request: MyCityRequestDataModel object
    :return: MyCityResponseDataModel object
    """
    print(
        '[method: get_polling_location_intent]',
        'MyCityRequestDataModel received:',
        str(mycity_request)
    )

    mycity_response = MyCityResponseDataModel()
    if intent_constants.CURRENT_ADDRESS_KEY in mycity_request.session_attributes:
        finder = FinderCSV(mycity_request, POLLING_LOCATION_URL, ADDRESS_KEY, 
                           OUTPUT_SPEECH_FORMAT, format_record_fields)
        print("Finding polling location for {}".format(finder.origin_address))
        finder.start()
        mycity_response.output_speech = finder.get_output_speech()

    else:
        print("Error: Called polling_location_intent with no address")

    # Setting reprompt_text to None signifies that we do not want to reprompt
    # the user. If the user does not respond or says something that is not
    # understood, the session will end.
    mycity_response.reprompt_text = None
    mycity_response.session_attributes = mycity_request.session_attributes
    mycity_response.card_title = mycity_request.intent_name
    
    return mycity_response


