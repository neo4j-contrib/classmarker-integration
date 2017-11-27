import json
import hmac
import hashlib
import base64
import os
import boto3
import requests

def get_auth0_management_token():
    AUTH0_CREDS = boto3.client('kms').decrypt(CiphertextBlob=base64.b64decode(os.environ["AUTH0_CREDS"]))['Plaintext']

    authci = json.loads(AUTH0_CREDS)
    clientSecret = authci['client_secret']
    clientId = authci['client_id']
    audience = authci['audience']
    tokenEndpoint = authci['token_endpoint']
    apiEndpoint = authci['api_endpoint']

    payload_obj = {
      "grant_type": "client_credentials",
      "client_id": clientId,
      "client_secret": clientSecret,
      "audience": audience
    }
    r = requests.post(tokenEndpoint,
              headers={"Content-type": "application/json"},
              data = json.dumps(payload_obj))
    data = r.content
    data_obj = json.loads(data.decode("utf-8"))
    return_obj = {
      "access_token": data_obj["access_token"],
      "api_endpoint": apiEndpoint
    }
    return return_obj

def get_profile(user):
    apiInfo = get_auth0_management_token()

    try:
      r = requests.get(
            '%susers/%s' % (apiInfo['api_endpoint'], user),
            headers={"Authorization": "bearer %s" % apiInfo['access_token'] })

      jsonProfile = r.text
      profile = json.loads(jsonProfile)
      return profile
    except:
      return False

def get_email_address(user):
  profile = get_profile(user)
  if 'email' in profile:
    return profile['email']
  else:
    return False

