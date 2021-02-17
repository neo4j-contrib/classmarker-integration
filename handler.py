import json
import hmac
import hashlib
import base64
import os
import boto3
import neo4j

import util.certificate as certificate
import util.neo4j_accounts as accts
import util.certification as certification

from util.encryption import decrypt_value, decrypt_value_str
from neo4j import GraphDatabase

import util.email as email

ssmc = boto3.client('ssm')

def get_ssm_param(key):
  resp = ssmc.get_parameter(
    Name=key,
    WithDecryption=True
  )
  return resp['Parameter']['Value']


db_driver = GraphDatabase.driver("bolt+routing://%s" % (get_ssm_param('com.neo4j.graphacademy.dbhostport')),
                                 auth=(get_ssm_param('com.neo4j.graphacademy.dbuser'),
                                       get_ssm_param('com.neo4j.graphacademy.dbpassword')),
                                 max_retry_time=15)


def get_email_lambda(request, context):
    json_payload = json.loads(request["body"])
    user_id = json_payload["user_id"]

    if ('Accept' in request['headers'] and request['headers']['Accept'].find('application/json') >= 0):
      return {"statusCode": 200, "body": json.dumps({"email": accts.get_email_address(user_id), "auth0": user_id}), "headers": {"Content-Type": "application/json"}}
    else:
      # plain text
      return {"statusCode": 200, "body": accts.get_email_address(user_id), "headers": {}}


def generate_certificate(request, context):
    print("Certificate request:", request)

    json_payload = json.loads(request["body"])
    result = json_payload["result"]

    expected_hmac = request["headers"].get("X-Classmarker-Hmac-Sha256")
    if not expected_hmac:
        raise Exception("No HMAC provided. Request did not come from Classmarker so not generating certificate")

    cm_secret_phrase = get_ssm_param('com.neo4j.graphacademy.classmarker.secret')

    dig = hmac.new(cm_secret_phrase.encode(), msg=request["body"].encode("utf-8"), digestmod=hashlib.sha256).digest()
    generated_hmac = base64.b64encode(dig).decode()

    if expected_hmac != generated_hmac:
        raise Exception("""\
        Generated HMAC did not match the one provided by Classmarker so not generating certificate.
        Expected: {expected}, Actual: {generated}""".format(expected=expected_hmac, generated=generated_hmac))

    event = {
        "user_id": result["link_result_id"],
        "given_name": result["first"],
        "family_name": result["last"],
        "name": "{first} {last}".format(first=result["first"], last=result["last"]),
        "email": accts.get_email_address(result["cm_user_id"]),
        "auth0_key": result["cm_user_id"],
        "score_percentage": result["percentage"],
        "score_absolute": result["points_scored"],
        "score_maximum": result["points_available"],
        "date": int(result["time_finished"]),
        "passed": result["passed"],
        "test_name": json_payload["test"]["test_name"],
        "test_id": json_payload["test"]["test_id"],
        "test_name_short": json_payload["link"]["link_name"],
        "ip": result["ip_address"]
    }

    print("Recording certificate attempt")
    try:
        certification.record_attempt(db_driver, event)
    except neo4j.exceptions.ServiceUnavailable as exception:
        print("Failed to record certificate attempt", exception)
        return {"statusCode": 500, "body": str(exception), "headers": {}}

    if not result["passed"]:
        print("Not generating certificate - did not pass!")
        certificate_path = None
    else:
        if event.get('test_name_short') == "neo4-3.x-certification-test":
            print("Assigning swag code")
            certification.assign_swag_code(db_driver, event.get('auth0_key'))

        certificate_number = certification.generate_certificate_number(db_driver, event)[0]["certificate_number"]
        event["certificate_number"] = int(certificate_number)

        certificate_path = certificate.generate(event)
        event["certificate"] = certificate_path
        certification.save_certificate_path(db_driver, event)

        print("Generating certificate")
        print("Certificate generated:", certificate_path, "Certificate Number: ", certificate_number)

        sns = boto3.client('sns')
        print("Adding message to topic for certificate to be emailed")
        topic_arn = create_topic_arn(context, "CertificatesToEmail")
        sns.publish(TopicArn=(topic_arn), Message=json.dumps(event))

    return {"statusCode": 200, "body": certificate_path, "headers": {}}


def create_topic_arn(context, topic_name):
    context_parts = context.invoked_function_arn.split(':')
    topic_name = topic_name
    topic_arn = "arn:aws:sns:{region}:{account_id}:{topic}".format(
        region=context_parts[3], account_id=context_parts[4], topic=topic_name)
    return topic_arn


def send_email(event, context):
    print(event)
    s3 = boto3.client('s3')
    email_client = boto3.client('ses')

    email_title = 'Congratulations! You are now a Neo4j Certified Professional'
    template_name = 'email'

    if event.get('test_name_short') == 'neo4-4.x-certification-test':
        email_title = 'Congratulations! You are now Neo4j 4.0 Certified'
        template_name = 'email_40'

    if event.get('test_name_short') == 'neo4j-gds-test':
        email_title = 'Congratulations! You are now Neo4j Graph Data Science Certified'
        template_name = 'email_gds'

    template_obj = email.plain_text_template(s3, template_name)
    template_html_obj = email.html_template(s3, template_name)

    for record in event["Records"]:
        message = json.loads(record["Sns"]["Message"])

        name = message["name"]
        email_address = message["email"]
        certificate_path = message["certificate"]
        certificate_number = message["certificate_number"]

        template_args = {"name": name, "certificate": certificate_path, "certificate_number": certificate_number}

        response = email.send(email_address, email_client, email_title, template_args, template_html_obj, template_obj)
        print(response)


def find_people_needing_swag(event, context):
    print(event)

    topic_arn = create_topic_arn(context, "SwagToEmail")

    sns = boto3.client('sns')

    rows = certification.find_unsent_swag_emails(db_driver)
    for row in rows:
        print(row)
        sns.publish(TopicArn=topic_arn, Message=json.dumps(row))


def send_swag_email(event, context):
    print(event)
    s3 = boto3.client('s3')
    email_client = boto3.client('ses')

    template_name = 'swag'

    template_obj = email.plain_text_template(s3, template_name)
    template_html_obj = email.html_template(s3, template_name)

    for record in event["Records"]:
        message = json.loads(record["Sns"]["Message"])

        first_name = message["first_name"]
        last_name = message["last_name"]
        email_address = message["email"]
        swag_code = message["swag_code"]

# Elaine subject changed
        email_title = "Way To Go! You've Unlocked Access to Exclusive Advanced Training as a Neo4j Certified Professional!"

        template_args = {"name": "{0} {1}".format(first_name, last_name), "swag_code": swag_code}

        certification.swag_email_sent(db_driver, swag_code)

        response = email.send(email_address, email_client, email_title, template_args, template_html_obj, template_obj)
        print(response)

# Added for 4.x Certification
# Need to check if 3.x certified

def check_certified(event, context):
    print("event", event)
    auth0_key = event["multiValueQueryStringParameters"]["auth0_key"][0]
    print("auth0_key", auth0_key)
    certified = certification.check_certified(db_driver,auth0_key)

    return {"statusCode": 200, "body": certified, "headers": {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Credentials': "true",
    }}
