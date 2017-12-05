import json
import hmac
import hashlib
import base64
import os
import boto3

import util.certificate as certificate
import util.neo4j_accounts as accts
import util.certification as certification

from util.encryption import decrypt_value, decrypt_value_str
from neo4j.v1 import GraphDatabase, basic_auth

import util.email as email

db_driver = GraphDatabase.driver("bolt://%s" % (decrypt_value_str(os.environ['GRAPHACADEMY_DB_HOST_PORT'])),
                                 auth=basic_auth(decrypt_value_str(os.environ['GRAPHACADEMY_DB_USER']),
                                                 decrypt_value_str(os.environ['GRAPHACADEMY_DB_PW'])))


def get_email_lambda(request, context):
    json_payload = json.loads(request["body"])
    user_id = json_payload["user_id"]
    return {"statusCode": 200, "body": accts.get_email_address(user_id), "headers": {}}


def generate_certificate(request, context):
    print("recording certificate: {request}".format(request=request))

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

    certification.record_attempt(db_driver, event)

    print("generate_certificate request: {request}".format(request=request))

    if not result["passed"]:
        print("Not generating certificate for {event}".format(event=event))
        certificate_path = None
    else:
        certification.assign_swag_code(db_driver, event.get('auth0_key'))

        certificate_number = certification.generate_certificate_number(db_driver, event)[0]["certificate_number"]
        event["certificate_number"] = int(certificate_number)

        certificate_path = certificate.generate(event)
        event["certificate"] = certificate_path
        certification.save_certificate_path(db_driver, event)

        print("Generating certificate for {event}".format(event=event))
        print("Certificate:", certificate_path, "Certificate Number: ", certificate_number)

        sns = boto3.client('sns')

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

        email_title = "{0}, now you're a Neo4j Certified Professional - Get your t-shirt!".format(first_name)

        template_args = {"name": "{0} {1}".format(first_name, last_name), "swag_code": swag_code}

        certification.swag_email_sent(db_driver, swag_code)

        response = email.send(email_address, email_client, email_title, template_args, template_html_obj, template_obj)
        print(response)
