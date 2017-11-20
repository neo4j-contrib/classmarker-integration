import json
import hmac
import hashlib
import base64
import os
import boto3

import lib.certificate as certificate
import lib.neo4j_accounts as accts

from lib.encryption import decrypt_value

from string import Template

EMAIL_TEMPLATES_BUCKET = "training-certificate-emails.neo4j.com"

def get_email_lambda(request, context):
    json_payload = json.loads(request["body"])
    user_id = json_payload["user_id"]
    return {"statusCode": 200, "body": accts.get_email_address(user_id), "headers": {}}

def generate_certificate(request, context):
    print("generate_certificate request: {request}".format(request=request))

    json_payload = json.loads(request["body"])
    result = json_payload["result"]

    expected_hmac = request["headers"].get("X-Classmarker-Hmac-Sha256")
    if not expected_hmac:
        raise Exception("No HMAC provided. Request did not come from Classmarker so not generating certificate")

    cm_secret_phrase = decrypt_value(os.environ['CM_SECRET_PHRASE'])

    dig = hmac.new(cm_secret_phrase, msg=request["body"].encode("utf-8"), digestmod=hashlib.sha256).digest()
    generated_hmac = base64.b64encode(dig).decode()

    if expected_hmac != generated_hmac:
        raise Exception("""\
        Generated HMAC did not match the one provided by Classmarker so not generating certificate.
        Expected: {expected}, Actual: {generated}""".format(expected=expected_hmac, generated=generated_hmac))

    event = {
        "user_id": result["link_result_id"],
        "name": "{first} {last}".format(first=result["first"], last=result["last"]),
        "email": accts.get_email_address(result["link_result_id"]),
        "score_percentage": result["percentage"],
        "score_absolute": result["points_scored"],
        "score_maximum": result["points_available"],
        "date": int(result["time_finished"])
    }

    if not result["passed"]:
        print("Not generating certificate for {event}".format(event = event))
        certificate_path = None
    else:
        print("Generating certificate for {event}".format(event = event))
        certificate_path = certificate.generate(event)
        print("Certificate:", certificate_path)

        context_parts = context.invoked_function_arn.split(':')
        topic_name = "CertificatesToEmail"
        topic_arn = "arn:aws:sns:{region}:{account_id}:{topic}".format(region=context_parts[3], account_id=context_parts[4], topic=topic_name)

        sns = boto3.client('sns')
        event["certificate"] = certificate_path
        sns.publish(TopicArn= topic_arn, Message= json.dumps(event))

    return {"statusCode": 200, "body": certificate_path, "headers": {}}


def send_email(event, context):
    print(event)

    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=EMAIL_TEMPLATES_BUCKET,Key="%s.txt" % ('email'))
    templatePlainText = response['Body'].read().decode("utf-8")

    response = s3.get_object(Bucket=EMAIL_TEMPLATES_BUCKET,Key="%s.html" % ('email'))
    templateHtml = response['Body'].read().decode("utf-8")

    templateObj = Template(templatePlainText)
    templateHtmlObj = Template(templateHtml)

    for record in event["Records"]:
        message = json.loads(record["Sns"]["Message"])

        name = message["name"]
        # email = message["email"]
        email = "m.h.needham@gmail.com"
        certificate_path = message["certificate"]

        email_client = boto3.client('ses')

        bodyPlainText = templateObj.substitute(name=name, certificate=certificate_path)
        bodyHtml = templateHtmlObj.substitute(name=name, certificate=certificate_path)


        response = email_client.send_email(
            Source = 'Neo4j DevRel <devrel+certification@neo4j.com>',
            SourceArn = 'arn:aws:ses:us-east-1:128916679330:identity/neo4j.com',
            Destination = {
                'ToAddresses': [ email ]
            },
            Message = {
                'Subject': { 'Data': 'Congratulations! You are now a Neo4j Certified Professional' },
                'Body': {
                    'Text':
                        { 'Data': bodyPlainText },
                    'Html':
                        { 'Data': bodyHtml },
                }
            }
        )
        print(response)
