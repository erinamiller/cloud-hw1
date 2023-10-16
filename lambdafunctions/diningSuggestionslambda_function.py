import json
import dateutil.parser
import datetime
import time
import os
import logging
import re
import boto3

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/532016339310/ReservationRequestQueue"

""" ----------------- OUR CODE ----------------- """

def notifyValidationFailure(req, interp, slotName, msg, slots):
    slots[slotName] = None
    return {
        'sessionState': {
            "dialogAction": {
              "slotToElicit": slotName,
              "type": "ElicitSlot"
            },
            "intent": {
              'name': interp['intent']['name'],
              "state": "InProgress",
              "slots": slots,
          }
        },
        'messages': [
            {
                'contentType' : 'PlainText',
                'content' : msg
            }
        ]
    }

def createLexResponse(req, interp, slots):
    return {
        'sessionState': {
            "dialogAction": {
              "type": "Delegate"
            },
            "intent": {
              'name': interp['intent']['name'],
              "state": "InProgress",
              "slots": slots,
          }
        },
        'messages': [
            {
                'contentType' : 'PlainText',
                'content' : 'Next Message from the Lambda Func'
            }
        ]
    }

class slot:
    def __init__(self, value, failureMessage):
        self.value = value
        self.failureMessage = failureMessage
    def getValue(self):
        return self.value
    def getFailure(self):
        return self.failureMessage

def validate_location(req, interp):
    locationObj = interp['intent']['slots']['Location']
    if locationObj != None:
        locationStr = locationObj['value']['originalValue']
        if locationStr.lower() not in ["new york", "ny", "nyc"]:
            return slot(None, 'We do not serve in ' + locationStr + " yet. Please enter a valid location.")
        else:
          return slot("new york", None)

def validate_email(req, interp):
    emailObj = interp['intent']['slots']['Email']
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b' # Taken from https://www.geeksforgeeks.org/check-if-email-address-valid-or-not-in-python/
    if emailObj != None:
        emailStr = emailObj['value']['originalValue']
        if not re.fullmatch(regex, emailStr):
            return slot(None, 'Please enter a valid email address.')
        else:
          return slot(emailStr, None)
    
def validate_cuisine(req, interp):
    cuisineObj = interp['intent']['slots']['Cuisine']
    validCuisines = ['chinese', 'indian', 'italian']
    if cuisineObj != None:
        cuisineStr = cuisineObj['value']['originalValue']
        if cuisineStr.lower() not in validCuisines:
            return slot(None, 'We do not serve ' + cuisineStr + " restaurants yet. Please enter a valid cuisine.")
        else:
            return slot(cuisineStr.lower(), None)
            
def validate_num_people(req, interp):
    numberOfPeopleObj = interp['intent']['slots']['Numberofpeople']
    validNumbers = ['1', '2', '3', '4', '5', '6']
    if numberOfPeopleObj != None:
        numberOfPeopleStr = numberOfPeopleObj['value']['originalValue']
        if numberOfPeopleStr not in validNumbers:
            return slot(None, 'Please enter a valid number of people, between 1 and 6.')
        else:
            return slot(numberOfPeopleStr, None)
    
def validate_time(req, interp):
    timeObj = interp['intent']['slots']['Diningtime']
    # validate the time
    if timeObj != None:
        if len(timeObj['value']['resolvedValues']) < 1:
            return slot(None, 'Please enter a valid reservation time.')
        else:
            return slot(timeObj['value']['resolvedValues'][0], None)
    
def validate_slots(req, interp):
    locationRes = validate_location(req, interp)
    emailRes = validate_email(req, interp)
    cuisineRes = validate_cuisine(req, interp)
    numPeopleRes = validate_num_people(req, interp)
    timeRes = validate_time(req, interp)

    slots = interp['intent']['slots']
    if slots['Cuisine'] != None:
        if cuisineRes.getFailure() != None:
            return notifyValidationFailure(req, interp, 'Cuisine', cuisineRes.getFailure(), slots)
        else:
            slots['Cuisine']['value']['interpretedValue'] = cuisineRes.getValue()
    if slots['Location'] != None:
        if locationRes.getFailure() != None:
            return notifyValidationFailure(req, interp, 'Location', locationRes.getFailure(), slots)
        else:
            slots['Location']['value']['interpretedValue'] = locationRes.getValue()
    if slots['Email'] != None:
        if emailRes.getFailure() != None:
            return notifyValidationFailure(req, interp, 'Email', emailRes.getFailure(), slots)
        else:
            slots['Email']['value']['interpretedValue'] = emailRes.getValue()
    if slots['Numberofpeople'] != None:
        if numPeopleRes.getFailure() != None:
            return notifyValidationFailure(req, interp, 'Numberofpeople', numPeopleRes.getFailure(), slots)
        else:
            slots['Numberofpeople']['value']['interpretedValue'] = numPeopleRes.getValue()
    if slots['Diningtime'] != None:
        if timeRes.getFailure() != None:
            return notifyValidationFailure(req, interp, 'Diningtime', timeRes.getFailure(), slots)
        else:
            slots['Diningtime']['value']['interpretedValue'] = timeRes.getValue()
    return slots

def hasReachedConfirmationState(interp):
    return interp['intent']['confirmationState'] == "Confirmed"

def getDataToBePushed(interp):
    slots = interp['intent']['slots']
    print("Interp = ", interp)
    print("slots = ", slots)
    return json.dumps({
        'location': slots['Location']['value']['interpretedValue'],
        'cuisine': slots['Cuisine']['value']['interpretedValue'],
        'diningTime': slots['Diningtime']['value']['interpretedValue'],
        'numberOfPeople': slots['Numberofpeople']['value']['interpretedValue'],
        'email': slots['Email']['value']['interpretedValue'],
        })

def pushRequestToQueue(req, interp):
    pushData = getDataToBePushed(interp)
    sqs = boto3.client("sqs")
    # u = sqs.get_queue_url(QueueName='YOUR SQS QUEUE NAME').get('QueueUrl')
    try:
        resp = sqs.send_message(
                MessageBody=pushData,
                QueueUrl=QUEUE_URL 
            )
        logger.info("Successfully pushed data into the queue")
    except Exception as e:
        logger.error("Error when pushing data into queue: %s", str(e))

def sanitize_data(intent_request):
    currHighConf = -1
    bestInterp = {}
    
    for interp in intent_request['interpretations']:
        if ("nluConfidence" in interp) and (interp['nluConfidence'] > currHighConf):
            bestInterp = interp
            currHighConf = interp['nluConfidence']
    
    logger.info("Current Intent is %s", bestInterp['intent'])
    hasConf = hasReachedConfirmationState(bestInterp)
    if hasConf:
        pushRequestToQueue(intent_request, bestInterp)
    
    validationResult = validate_slots(intent_request, bestInterp)    
    if 'sessionState' in validationResult:
        return log_and_respond(validationResult)
    else:
        return log_and_respond(createLexResponse(intent_request, bestInterp, validationResult))

def log_and_respond(resp):
    logger.info("Returning the following: %s\n", resp)
    return resp

""" --- Main handler --- """

def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))
    
    return sanitize_data(event)
