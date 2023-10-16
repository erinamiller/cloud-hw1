import json
from botocore.vendored import requests
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
import boto3
import json
import logging
import aws_requests_auth

emailClient = boto3.client('ses', region_name='us-east-1')

sqs = boto3.client("sqs")
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/532016339310/ReservationRequestQueue"
ES_HOST = "https://search-restaurant-mktfqcghh5c6w6qpfu6b24i7da.us-east-1.es.amazonaws.com/_dashboards"
INDEX_PATH = "https://search-restaurant-mktfqcghh5c6w6qpfu6b24i7da.us-east-1.es.amazonaws.com/restaurants?pretty"
region = 'us-east-1' 
service = 'es'
access_key='xxx'
secret_key='yyy'

def getSqsData():
    response = sqs.receive_message(
        QueueUrl= QUEUE_URL)
    if not response:
        logger.debug('Response missing from sqs')
    try:
        message = response['Messages'][0]
        if message is None:
            logger.debug("Message missing")
            return None
    except KeyError:
        logger.debug("Queue is empty")
        return None
    sqs.delete_message(
            QueueUrl=QUEUE_URL,
            ReceiptHandle=message['ReceiptHandle']
        )
    messagesBody = extractMessageBody(response['Messages'])
    qData = json.loads(messagesBody)
    logger.debug('Received and deleted message: %s', messagesBody)
    return qData

def extractMessageBody(messages):
    res = []
    for msg in messages:
        res.append(msg['Body'])
    return res[0]

def generateEmailBody(qData, restaurantName):
    if qData != None:
        return ("You reservation for table of " + qData['numberOfPeople'] + " at " + restaurantName + " is confirmed. Please find the details of the reservation below: " + "\n" + \
            "Restaurant Name: " + restaurantName + "\n" +\
            "Reservation Time: " + qData['diningTime'] + "\n" +\
            "\n" + "\n" +\
            "Enjoy your food!\n")
    else:
        return None

def queryEs(qData):
    auth = AWSRequestsAuth(aws_access_key=access_key,
                              aws_secret_access_key=secret_key,
                              aws_host=ES_HOST,
                              aws_region=region,
                              aws_service=service)
    url = f'https://{es_host}/restaurants/_search'
    query = {
        "query": {
            "match": {
                "cuisine": qData['cuisine']
            }
        }
    }
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(url, auth=auth, headers=headers, json=query)
    return response.json()['hits']['hits'][0]

def lambda_handler(event, context):
    # TODO implement
    qData = getSqsData()
    if qData != None:
        restaurantName = queryEs(qData)
        emailBod = generateEmailBody(qData, restaurantName)
        response = emailClient.send_email(
            Destination={'ToAddresses': [qData['email']]},
            # Destination={'ToAddresses': ["aa10770@nyu.edu"]},
            Message=
                {
                    'Body': {'Text': {'Data': emailBod}},
                    'Subject': {'Data': 'Test email'}
                },
                Source='aa10770@nyu.edu'
            )
    
        return {
            'statusCode': 200,
            'body': json.dumps("Email Sent Successfully. MessageId is: " + response['MessageId'])
        }
    else:
        return {
            'statusCode': 200,
            'body': json.dumps("Unable to fetch message. Aborted")
        }