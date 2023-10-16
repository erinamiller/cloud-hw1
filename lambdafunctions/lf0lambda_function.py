import json
import boto3

BOT_ID = "DJCLCYZWLK"
BOT_ALIAS_ID = "TSTALIASID"

def processLexResponse(resp):
    print("Lex response = ", resp)
    msgArr = resp['messages']
    respMsgs = []
    for msg in msgArr:
        respMsgs.append(
            {'unstructured':{
                'text': msg['content']
            },
            'type': "unstructured"}
        )
    return respMsgs

def prepareFailureMessage(msg):
    return [
        {'unstructured':{
                'text': msg
            },
        'type': "unstructured"
        }
    ]

def processReqMessage(messages):
    return messages[0]['unstructured']['text']

def lambda_handler(event, context):
    print("Event.body = ", event['body'])
    reqBody = json.loads(event['body'])
    print("reqBody = ", reqBody)
    m = reqBody['messages']
    print("messages = ", m)
    try:
        reqMessages = reqBody['messages']
        chatBotMessage = processReqMessage(reqMessages)
        sessionId = "123" # reqBody['sessionId']
        lexClient = boto3.client('lexv2-runtime')
        lexResponse = lexClient.recognize_text(
            botId=BOT_ID,
            botAliasId=BOT_ALIAS_ID,
            localeId='en_US',
            sessionId=sessionId,
            text=chatBotMessage
            )
        print("lexResponse = ", lexResponse)
        respMsgArr = []
        if lexResponse != None:
            respMsgArr = processLexResponse(lexResponse)
        else:
            respMsgArr = prepareFailureMessage("Oops, the Lex bot seems to have encountered an error")
        resp = {
            'messages' : respMsgArr
        }
    except Exception as e:
        print("error ", e)
        resp = {
            'messages' : prepareFailureMessage("Exception: " + str(e))
        }
    
    return {
        'statusCode': 200,
        'body': json.dumps(resp),
        'headers': { 'Access-Control-Allow-Origin': '*'},
    }

# {
#   “messages”: [
#     {
#       “type”: “unstructured”,
#       “unstructured”: {
#         “text”: “gra”
#       }
#     }
#   ]
# }