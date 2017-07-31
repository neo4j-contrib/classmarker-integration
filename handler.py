import unzip_requirements
import json
import hmac
import hashlib
import base64
import os

import lib.certificate as certificate
from lib.encryption import decrypt_value


def generate_certificate(request, context):
    print("Generating certificate for {request}".format(request=request))

    json_payload = json.loads(request["body"])
    result = json_payload["result"]
    print("Payload:", result)

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
        "user_id": result["cm_user_id"],
        "name": "{first} {last}".format(first=result["first"], last=result["last"]),
        "score_percentage": result["percentage"],
        "score_absolute": result["points_scored"],
        "score_maximum": result["points_available"],
        "date": int(result["time_finished"])
    }

    certificate_path = certificate.generate(event)
    print("Certificate:", certificate_path)

    return {"statusCode": 200, "body": certificate_path, "headers": {}}
