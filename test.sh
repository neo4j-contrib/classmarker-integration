./node_modules/serverless/bin/serverless invoke local \
  --function generate-certificate \
  -d '{"score_percentage": 86.1,
       "name": "Praveena Fernandes",
       "user_id": 123456,
       "score_absolute": 79,
       "score_maximum": 92,
       "date": "Fri 28th July 2017"}' &&
wkhtmltopdf /tmp/123456.html certificate.pdf &&
open certificate.pdf
