import util.neo4j_accounts as accts

record_attempt_query = """
MERGE (u:User {auth0_key:{auth0_key}})
SET u.email = coalesce(u.email, {email}),
    u.first_name = coalesce(u.first_name, {given_name}),
    u.last_name=coalesce(u.last_name, {family_name})
MERGE (e:Exam {id: [{auth0_key}, toString({test_id}), toString({date})] })
ON CREATE SET 
    e:Certification,
    e.finished={date},
    e.percent={score_percentage},
    e.points={score_absolute},
    e.maxPoints={score_maximum},
    e.testTakerName={name},
    e.passed={passed},
    e.name={test_name_short},
    e.testId={test_id}
MERGE (u)-[:TOOK]->(e)
RETURN e
"""


def record_attempt(db_driver, event):
    test_data = event
    print("Attempt:", event)

    profile = accts.get_profile(event['auth0_key'])
    print("Looking up profile:", profile)

    if "user_metadata" in profile:
        user_metadata = profile["user_metadata"]
        if "given_name" in user_metadata:
            print("Overriding given name from FullContact (user_metadata)")
            test_data["given_name"] = user_metadata.get("given_name")

        if "family_name" in user_metadata:
            print("Overriding family name from FullContact (user_metadata)")
            test_data["family_name"] = user_metadata.get("family_name")

    if "given_name" in profile:
        print("Overriding given name from FullContact")
        test_data["given_name"] = profile.get("given_name")

    if "family_name" in profile:
        print("Overriding family name from FullContact")
        test_data["family_name"] = profile.get("family_name")

    print("Record attempt:", test_data)
    with db_driver.session() as session:
        results = session.write_transaction(lambda tx: tx.run(record_attempt_query, parameters=test_data))
        results.consume()


certificate_number_query = """\
MATCH (c:Certification) 
WITH max(c.certificateNumber) AS maxCertificateNumber
WITH maxCertificateNumber + round(rand() * 150) AS certificateNumber
MATCH (e:Exam {id: [{auth0_key}, {test_id}, {date}] })
SET e.certificateNumber = coalesce(e.certificateNumber, certificateNumber)
RETURN e.certificateNumber AS certificateNumber  
"""


def generate_certificate_number(db_driver, event):
    params = {
        "auth0_key": event["auth0_key"],
        "test_id": str(event["test_id"]),
        "date": str(event["date"])
    }

    with db_driver.session() as session:
        results = session.write_transaction(lambda tx: tx.run(certificate_number_query, parameters=params))
        return [{"certificate_number": record["certificateNumber"]} for record in results]

record_certificate_query = """\
MATCH (e:Exam {id: [{auth0_key}, {test_id}, {date}] })
SET e.certificatePath = {certificate}  
"""


def save_certificate_path(db_driver, event):
    params = {
        "certificate": event["certificate"],
        "auth0_key": event["auth0_key"],
        "test_id": str(event["test_id"]),
        "date": str(event["date"])
    }

    with db_driver.session() as session:
        results = session.write_transaction(lambda tx: tx.run(record_certificate_query, parameters=params))
        results.consume()


assign_swag_query = """
MATCH (u:User {auth0_key:{auth0_key}})
WHERE SIZE( (u)<-[:ISSUED_TO]-() ) = 0
WITH u LIMIT 1
MATCH (src:SwagRedemptionCode)
WHERE
  src.redeemed=false
  AND
  src.type='certified'
  AND
  size( (src)-[:ISSUED_TO]->(:User) ) = 0
WITH u, src
LIMIT 1
MERGE (src)-[:ISSUED_TO]->(u)
"""

def assign_swag_code(db_driver, auth0_key):
    print(assign_swag_query)
    with db_driver.session() as session:
        results = session.run(assign_swag_query, parameters={"auth0_key": auth0_key})
        results.consume()


unsent_swag_emails_query = """
MATCH (u:User)<-[:ISSUED_TO]-(swag)
where exists(u.auth0_key) 
AND exists(u.first_name)
AND exists(u.last_name)
AND not exists(swag.email_sent)
return u.first_name AS firstName, u.last_name AS lastName, swag.code AS swagCode, u.email as email
"""


def find_unsent_swag_emails(db_driver):
    with db_driver.session() as session:
        results = session.run(unsent_swag_emails_query)

        return [{"first_name": record["firstName"],
                 "last_name": record["lastName"],
                 "swag_code": record["swagCode"],
                 "email": record["email"]}
                for record in results]


mark_swag_email_sent_query = """
MATCH (s:SwagRedemptionCode { code: {swag_code} })
SET s.email_sent = true
"""


def swag_email_sent(db_driver, swag_code):
    print("Marking swag email sent " + swag_code)
    with db_driver.session() as session:
        results = session.run(mark_swag_email_sent_query, parameters={"swag_code": swag_code})
        results.consume()
