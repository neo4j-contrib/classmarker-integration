import base64
import datetime
import hashlib

import boto3
import flask
from flask import render_template

from util.wkhtmltopdf import wkhtmltopdfV2

app = flask.Flask('my app')

BUCKET_NAME = "graphacademy.neo4j.com"

def suffix(d):
    return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')


def generate(event):
    print("Generating certificate: ", event)
    t = datetime.datetime.fromtimestamp(event["date"])
    event["date_formatted"] = t.strftime('%a {S} %b %Y').replace('{S}', str(t.day) + suffix(t.day))

    user_id = event["user_id"]

    if event.get('test_name_short') == "Sample Link Name":
        return "Test OK"
        
    # 3.x certificate
    if event.get('test_name_short') == "neo4-3.x-certification-test":
        with app.app_context():
            with open("static/neo4j.png", "rb") as neo4j_image:
                base_64_logo_image = base64.b64encode(neo4j_image.read())
       
            with open("static/certified-transparent-logo.png", "rb") as cert_image:
                base_64_cert_image = base64.b64encode(cert_image.read())

            with open("static/emil-signature.png", "rb") as sig_image:
                base_64_sig_image = base64.b64encode(sig_image.read())

            with open("static/grid_graph.png", "rb") as bg_image:
                base_64_bg_image = base64.b64encode(bg_image.read())

            rendered = render_template('certificate_new.html',
                                   base_64_logo_image=base_64_logo_image.decode("utf-8"),
                                   base_64_cert_image=base_64_cert_image.decode("utf-8"),
                                   base_64_sig_image=base_64_sig_image.decode("utf-8"),
                                   base_64_bg_image=base_64_bg_image.decode("utf-8"),
                                   name=event["name"],
                                   test_name="Neo4j Certification",
                                   score_percentage=event["score_percentage"],
                                   score_absolute=event["score_absolute"],
                                   score_maximum=event["score_maximum"],
                                   certificate_number=event["certificate_number"],
                                   date=event["date_formatted"]
                                   )

    # 4.x certificate
    if event.get('test_name_short') == "neo4-4.x-certification-test":
        with app.app_context():
            with open("static/neo4j.png", "rb") as neo4j_image:
                base_64_logo_image = base64.b64encode(neo4j_image.read())

            with open("static/Neo4j4.0_certified_transparent.png", "rb") as cert_image:
                base_64_cert_image = base64.b64encode(cert_image.read())

            with open("static/emil-signature.png", "rb") as sig_image:
                base_64_sig_image = base64.b64encode(sig_image.read())

            with open("static/grid_graph.png", "rb") as bg_image:
                base_64_bg_image = base64.b64encode(bg_image.read())

            rendered = render_template('certificate_40.html',
                                       base_64_logo_image=base_64_logo_image.decode("utf-8"),
                                       base_64_cert_image=base_64_cert_image.decode("utf-8"),
                                       base_64_sig_image=base_64_sig_image.decode("utf-8"),
                                       base_64_bg_image=base_64_bg_image.decode("utf-8"),
                                       name=event["name"],
                                       test_name="Neo4j 4.0 Certified",
                                       score_percentage=event["score_percentage"],
                                       score_absolute=event["score_absolute"],
                                       score_maximum=event["score_maximum"],
                                       certificate_number=event["certificate_number"],
                                       date=event["date_formatted"]
                                       )
        
    s3 = boto3.client('s3')

    local_html_file_name = "/tmp/{file_name}.html".format(file_name=user_id)
    with open(local_html_file_name, "wb") as file:
        file.write(rendered.encode('utf-8'))

    html_location = generate_html_location(event)
    with open(local_html_file_name, 'rb') as data:
        s3.put_object(ACL="public-read", Body=data, Bucket=BUCKET_NAME, Key=html_location)

    local_pdf_file_name = "/tmp/{file_name}.pdf".format(file_name=user_id)
    wkhtmltopdfV2(local_html_file_name, local_pdf_file_name)

    pdf_location = generate_pdf_location(event)

    with open(local_pdf_file_name, 'rb') as data:
        s3.put_object(ACL="public-read", Body=data, Bucket=BUCKET_NAME, Key=pdf_location)

    return "https://{bucket_name}/{pdf_location}".format(bucket_name=BUCKET_NAME,
                                                             pdf_location=pdf_location)


def generate_pdf_location(event):
    return "certificates/{certificate_hash}.pdf".format(certificate_hash=generate_certificate_hash(event))

def generate_html_location(event):
    return "certificates/{certificate_hash}.html".format(certificate_hash=generate_certificate_hash(event))

def generate_certificate_hash(event):
    unhashed_key = "{0}-{1}-{2}".format(event["user_id"], event["test_id"], event["auth0_key"])
    return hashlib.sha256(unhashed_key.encode("utf-8")).hexdigest()
