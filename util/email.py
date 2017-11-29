from string import Template

EMAIL_TEMPLATES_BUCKET = "training-certificate-emails.neo4j.com"


def html_template(s3, template_name):
    response = s3.get_object(Bucket=EMAIL_TEMPLATES_BUCKET, Key="%s.html" % template_name)
    template_html = response['Body'].read().decode("utf-8")
    template_html_obj = Template(template_html)
    return template_html_obj


def plain_text_template(s3, template_name):
    response = s3.get_object(Bucket=EMAIL_TEMPLATES_BUCKET, Key="%s.txt" % template_name)
    template_plain_text = response['Body'].read().decode("utf-8")
    template_obj = Template(template_plain_text)
    return template_obj


def send(email_address, email_client, email_title, template_args, template_html_obj, template_obj):
    print(template_args)
    body_plain_text = template_obj.substitute(template_args)
    body_html = template_html_obj.substitute(template_args)
    response = email_client.send_email(
        Source='Neo4j DevRel <devrel+certification@neo4j.com>',
        SourceArn='arn:aws:ses:us-east-1:128916679330:identity/neo4j.com',
        Destination={
            'ToAddresses': [email_address]
        },
        Message={
            'Subject': {'Data': email_title},
            'Body': {
                'Text':
                    {'Data': body_plain_text},
                'Html':
                    {'Data': body_html},
            }
        }
    )
    return response
