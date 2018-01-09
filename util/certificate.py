import base64
import datetime
import hashlib

import boto3
import flask
from flask import render_template

from util.wkhtmltopdf import wkhtmltopdf

app = flask.Flask('my app')

BUCKET_NAME = "graphacademy.neo4j.com"


def suffix(d):
    return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')


def generate(event):
    t = datetime.datetime.fromtimestamp(event["date"])
    event["date_formatted"] = t.strftime('%a {S} %b %Y').replace('{S}', str(t.day) + suffix(t.day))

    user_id = event["user_id"]

    with app.app_context():
        with open("static/neo4j.png", "rb") as neo4j_image:
            base_64_image = base64.b64encode(neo4j_image.read())

        rendered = render_template('certificate.html',
                                   base_64_image=base_64_image.decode("utf-8"),
                                   name=event["name"],
                                   test_name="Neo4j Certification",
                                   score_percentage=event["score_percentage"],
                                   score_absolute=event["score_absolute"],
                                   score_maximum=event["score_maximum"],
                                   certificate_number=event["certificate_number"],
                                   date=event["date_formatted"]
                                   )

        local_html_file_name = "/tmp/{file_name}.html".format(file_name=user_id)
        with open(local_html_file_name, "wb") as file:
            file.write(rendered.encode('utf-8'))

        local_pdf_file_name = "/tmp/{file_name}.pdf".format(file_name=user_id)
        wkhtmltopdf(local_html_file_name, local_pdf_file_name)

        pdf_location = generate_pdf_location(event)

        s3 = boto3.client('s3')
        with open(local_pdf_file_name, 'rb') as data:
            s3.put_object(ACL="public-read", Body=data, Bucket=BUCKET_NAME, Key=pdf_location)

        return "https://{bucket_name}/{pdf_location}".format(bucket_name=BUCKET_NAME,
                                                             pdf_location=pdf_location)


def generate_pdf_location(event):
    return "certificates/{certificate_hash}.pdf".format(certificate_hash=generate_certificate_hash(event))


def generate_certificate_hash(event):
    unhashed_key = "{0}-{1}-{2}".format(event["user_id"], event["test_id"], event["auth0_key"])
    return hashlib.sha256(unhashed_key.encode("utf-8")).hexdigest()