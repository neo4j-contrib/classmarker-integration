serverless invoke local \
  --function generate-certificate \
  -d '{ "body": {
          "result": {
            "first": "Praveena",
            "last": "Fernandes",
            "link_result_id": 123456,
            "percentage": 86.1,
            "points_scored": 79,
            "points_available": 92,
            "time_finished": 12345678,
            "passed": true
          }
        }
      }' &&
wkhtmltopdf /tmp/123456.html certificate.pdf &&
open certificate.pdf


serverless invoke \
  --function send-email \
  -d '{"Records": [
    {"EventSource": "aws:sns",
     "EventVersion": "1.0",
     "EventSubscriptionArn": "arn:aws:sns:us-east-1:715633473519:CertificatesToEmail:eac5c653-b5b5-4dce-9e3c-794debd7b007",
     "Sns": {
        "Type": "Notification",
        "MessageId": "e163a540-96e9-5802-8d4f-f7d7e4c91214",
        "TopicArn": "arn:aws:sns:us-east-1:715633473519:SwagToEmail",
        "Subject": "None",
        "Message": "{
            \"user_id\": 17472377,
            \"first_name\": \"Mark\",
            \"last_name\": \"Needham\",
            \"email\": \"m.h.needham@gmail.com\",
            \"swag_code\": \"zyy7fwf6zqsvhihmvw4jha\",
         }",
         "Timestamp": "2017-11-28T14:17:04.258Z",
         "SignatureVersion": "1",
         "Signature": "dp0mswTb4X1ixueNZ3GuR0I60EcWMZ68KVVyf4emwEShU+336FeHVJwxt0L0A+3h+KPkzOtGAeF35l/6+bGKmmdhaJQ+J9uCmn9B5A97Gs9RvSNtawLDJ3VroUA0wYlO6IGT2w/SmMLhAZQUEcHArGxMHdyU2y/WsRKvPdKjsmFPR8aalxkBwmmCi1iFG+88t7HaHtMV6GqmSxbPIoZVuaRw9iTGWhAOP19YOnwWpzx3HRXaAG2HbwLEwecCaR0NK5XFexjKLCLmHzxi+hrJEoK0QqwdWNj+Xa29j5jtgSvLAeAsy7pfkE/I6NRuzxwssKeylBI5JgH9QgNBDDbSbA==",
         "SigningCertUrl": "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-433026a4050d206028891664da859041.pem",
         "UnsubscribeUrl": "https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:715633473519:CertificatesToEmail:eac5c653-b5b5-4dce-9e3c-794debd7b007",
         "MessageAttributes": {}}}]}'

#--data '{"Records":[{"Sns": {"Message":"{\"last_name\": \"Needham\", \"first_name\": \"Mark\", \"swag_code\": \"zyy7fwf6zqsvhihmvw4jha\"  }"}}]}'
#--data '{"Records":[{"Sns": {"Message":"{\"last_name\": \"Needham\", \"first_name\": \"Mark\", \"certificate\": \"zyy7fwf6zqsvhihmvw4jha\"  }"}}]}'