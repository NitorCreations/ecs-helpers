import os
import json
import time
import boto3
from botocore.exceptions import ClientError
import requests

ECS = boto3.client('ecs')
SSM = boto3.client('ssm')
REGION = os.environ['AWS_REGION']
AMI_ID_SSM_KEY = os.getenv('ECS_AMI_SSM_KEY', '/ecs-helpers/ECS_AMI_ID')
WEBHOOKS_SSM_KEY = os.getenv('WEBHOOKS_SSM_KEY', '/ecs-helpers/webhooks')


def lambda_handler(event, context):
    msg = json.loads(event['Records'][0]['Sns']['Message'])
    print(msg)
    ami_id = None
    ami_name = None
    for ami_set in msg['ECSAmis']:
        if ami_set['OsType'] != "linux" or ami_set['OperatingSystemName'] != "Amazon Linux":
            print("Skipping AMI for %s" % ami_set['OperatingSystemName'])
            continue
        region_ami = ami_set['Regions'][REGION]
        ami_id = region_ami['ImageId']
        ami_name = region_ami['Name']

    print("The new AMI for %s is %s (%s)" % (REGION, ami_id, ami_name))

    if ami_id is None or ami_name is None:
        print("No suitable AMI found")
        return

    response = SSM.put_parameter(
        Name=AMI_ID_SSM_KEY,
        Description='ECS instance AMI id',
        Value=ami_id,
        Type='String',
        Overwrite=True,
    )

    print("Stored parameter %s=%s (parameter version %s)"
          % (AMI_ID_SSM_KEY, ami_id, response.get('Version')))

    notify_webhooks()

def notify_webhooks():
    response = SSM.get_parameter(
        Name=WEBHOOKS_SSM_KEY,
        WithDecryption=True
    )
    print(response)
    hooks = json.loads(response['Parameter']['Value'])
    for hook in hooks:
        r = requests.post(hook['url'], data=hook['data'])
        print("Webhook %s response: %s" % (hook['url'], r.status_code))
        if not (200 <= r.status_code < 300):
            print("WARNING: Webhook %s did not return success status!" % hook['url'])

# Sample SNS message:
# {
#   "ECSAgent": {
#     "ReleaseVersion": "1.17.2"
#   },
#   "ECSAmis": [
#     {
#       "ReleaseVersion": "2017.09.l",
#       "AgentVersion": "1.17.2",
#       "ReleaseNotes": "This AMI includes the latest ECS agent 1.17.2",
#       "OsType": "linux",
#       "OperatingSystemName": "Amazon Linux",
#       "Regions": {
#         "ap-northeast-1": {
#           "Name": "amzn-ami-2017.09.j-amazon-ecs-optimized",
#           "ImageId": "ami-bb5f13dd"
#         },
#         "ap-northeast-2": {
#           "Name": "amzn-ami-2017.09.j-amazon-ecs-optimized",
#           "ImageId": "ami-3b19b455"
#         },
#         "ap-south-1": {
#           "Name": "amzn-ami-2017.09.j-amazon-ecs-optimized",
#           "ImageId": "ami-9e91cff1"
#         },
#         "ap-southeast-1": {
#           "Name": "amzn-ami-2017.09.j-amazon-ecs-optimized",
#           "ImageId": "ami-f88ade84"
#         },
#         "ap-southeast-2": {
#           "Name": "amzn-ami-2017.09.j-amazon-ecs-optimized",
#           "ImageId": "ami-a677b6c4"
#         },
#         "ca-central-1": {
#           "Name": "amzn-ami-2017.09.j-amazon-ecs-optimized",
#           "ImageId": "ami-db48cfbf"
#         },
#         "cn-north-1": {
#           "Name": "amzn-ami-2017.09.j-amazon-ecs-optimized",
#           "ImageId": "ami-ca508ca7"
#         },
#         "eu-central-1": {
#           "Name": "amzn-ami-2017.09.j-amazon-ecs-optimized",
#           "ImageId": "ami-3b7d1354"
#         },
#         "eu-west-1": {
#           "Name": "amzn-ami-2017.09.l-amazon-ecs-optimized",
#           "ImageId": "ami-2d386654"
#         },
#         "eu-west-2": {
#           "Name": "amzn-ami-2017.09.j-amazon-ecs-optimized",
#           "ImageId": "ami-25f51242"
#         },
#         "eu-west-3": {
#           "Name": "amzn-ami-2017.09.j-amazon-ecs-optimized",
#           "ImageId": "ami-0356e07e"
#         },
#         "sa-east-1": {
#           "Name": "amzn-ami-2017.09.j-amazon-ecs-optimized",
#           "ImageId": "ami-da2c66b6"
#         },
#         "us-east-1": {
#           "Name": "amzn-ami-2017.09.j-amazon-ecs-optimized",
#           "ImageId": "ami-cad827b7"
#         },
#         "us-east-2": {
#           "Name": "amzn-ami-2017.09.j-amazon-ecs-optimized",
#           "ImageId": "ami-ef64528a"
#         },
#         "us-gov-west-1": {
#           "Name": "amzn-ami-2017.09.j-amazon-ecs-optimized",
#           "ImageId": "ami-cc3cb7ad"
#         },
#         "us-west-1": {
#           "Name": "amzn-ami-2017.09.j-amazon-ecs-optimized",
#           "ImageId": "ami-29b8b249"
#         },
#         "us-west-2": {
#           "Name": "amzn-ami-2017.09.j-amazon-ecs-optimized",
#           "ImageId": "ami-baa236c2"
#         }
#       }
#     }
#   ]
# }


# Full SNS event
# {
#   "Records": [
#     {
#         "EventVersion": "1.0",
#         "EventSubscriptionArn": "eventsubscriptionarn",
#         "EventSource": "aws:sns",
#         "Sns": {
#             "Type" : "Notification",
#             "MessageId" : "e2534930-337d-5561-8636-1a2be5ba802e",
#             "TopicArn" : "arn:aws:sns:us-west-2:917786371007:ecs-optimized-amazon-ami-update",
#             "Message" : "{\"ECSAgent\":{\"ReleaseVersion\":\"1.17.2\"},\"ECSAmis\":[{\"ReleaseVersion\":\"2017.09.j\",\"AgentVersion\":\"1.17.2\",\"ReleaseNotes\":\"This AMI includes the latest ECS agent 1.17.2\",\"OsType\":\"linux\",\"OperatingSystemName\":\"Amazon Linux\",\"Regions\":{\"ap-northeast-1\":{\"Name\":\"amzn-ami-2017.09.j-amazon-ecs-optimized\",\"ImageId\":\"ami-bb5f13dd\"},\"ap-northeast-2\":{\"Name\":\"amzn-ami-2017.09.j-amazon-ecs-optimized\",\"ImageId\":\"ami-3b19b455\"},\"ap-south-1\":{\"Name\":\"amzn-ami-2017.09.j-amazon-ecs-optimized\",\"ImageId\":\"ami-9e91cff1\"},\"ap-southeast-1\":{\"Name\":\"amzn-ami-2017.09.j-amazon-ecs-optimized\",\"ImageId\":\"ami-f88ade84\"},\"ap-southeast-2\":{\"Name\":\"amzn-ami-2017.09.j-amazon-ecs-optimized\",\"ImageId\":\"ami-a677b6c4\"},\"ca-central-1\":{\"Name\":\"amzn-ami-2017.09.j-amazon-ecs-optimized\",\"ImageId\":\"ami-db48cfbf\"},\"cn-north-1\":{\"Name\":\"amzn-ami-2017.09.j-amazon-ecs-optimized\",\"ImageId\":\"ami-ca508ca7\"},\"eu-central-1\":{\"Name\":\"amzn-ami-2017.09.j-amazon-ecs-optimized\",\"ImageId\":\"ami-3b7d1354\"},\"eu-west-1\":{\"Name\":\"amzn-ami-2017.09.l-amazon-ecs-optimized\",\"ImageId\":\"ami-2d386654\"},\"eu-west-2\":{\"Name\":\"amzn-ami-2017.09.j-amazon-ecs-optimized\",\"ImageId\":\"ami-25f51242\"},\"eu-west-3\":{\"Name\":\"amzn-ami-2017.09.j-amazon-ecs-optimized\",\"ImageId\":\"ami-0356e07e\"},\"sa-east-1\":{\"Name\":\"amzn-ami-2017.09.j-amazon-ecs-optimized\",\"ImageId\":\"ami-da2c66b6\"},\"us-east-1\":{\"Name\":\"amzn-ami-2017.09.j-amazon-ecs-optimized\",\"ImageId\":\"ami-cad827b7\"},\"us-east-2\":{\"Name\":\"amzn-ami-2017.09.j-amazon-ecs-optimized\",\"ImageId\":\"ami-ef64528a\"},\"us-gov-west-1\":{\"Name\":\"amzn-ami-2017.09.j-amazon-ecs-optimized\",\"ImageId\":\"ami-cc3cb7ad\"},\"us-west-1\":{\"Name\":\"amzn-ami-2017.09.j-amazon-ecs-optimized\",\"ImageId\":\"ami-29b8b249\"},\"us-west-2\":{\"Name\":\"amzn-ami-2017.09.j-amazon-ecs-optimized\",\"ImageId\":\"ami-baa236c2\"}}}]}",
#             "Timestamp" : "2018-03-09T00:25:43.483Z",
#             "SignatureVersion" : "1",
#             "Signature" : "XWox8GDGLRiCgDOXlo/fG9Lu/88P8S0FL6M6oQYOmUFzkucuhoblsdea3BjqdCHcWR7qdhMPQnLpN7y9iBrWVUqdAGJrukAI8athvAS+4AQD/V/QjrhsEnlj+GaiW+ozAu006X6GopOzFGnCtPMROjCMrMonjz7Hpv/8KRuMZR3pyQYm5d4wWB7xBPYhUMuLoZ1V8YFs55FMtgQV/YLhSYuEu0BP1GMtLQauxDkscOtPP/vjhGQLFx1Q9LTadcQiRHtNIBxWL87PSI+BVvkin6AL7PhksvdQ7FAgHfXsit+6p8GyOvKCqaeBG7HZhR1AbpyVka7JSNRO/6ssyrlj1g==",
#             "SigningCertURL" : "https://sns.us-west-2.amazonaws.com/SimpleNotificationService-433026a4050d206028891664da859041.pem",
#             "UnsubscribeURL" : "https://sns.us-west-2.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-west-2:917786371007:ecs-optimized-amazon-ami-update:8ad8798e-3bbf-4490-89b1-76136fca61dc"
#         },
#         "Type": "Notification",
#         "UnsubscribeUrl": "EXAMPLE",
#         "TopicArn": "topicarn",
#         "Subject": "TestInvoke"
#     }
#   ]
# }
