./node_modules/serverless/bin/serverless invoke local \
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
