import lib.neo4j_accounts as accts

record_attempt_query = """
MERGE (u:User {auth0_key:{auth0_key}})
ON CREATE
SET u.email={email},
    u.firstName={given_name},
    u.lastName={family_name}
MERGE (e:Exam {id: [{auth0_key}, toString({test_id}), toString({date})] })
SET e:Certification,
    e.finished={date},
    e.percent={score_percentage},
    e.points={score_absolute},
    e.maxPoints={score_maximum},
    e.testTakerName={name},
    e.passed={passed},
    e.name={test_name_short},
    e.testId={test_id}
MERGE (u)-[:TOOK]->(e)
"""


def record_attempt(db_driver, event):
    test_data = event

    profile = accts.get_profile(event['auth0_key'])
    print(profile)

    test_data["given_name"] = profile.get("given_name")
    test_data["family_name"] = profile.get("family_name")

    print(record_attempt_query)
    session = db_driver.session()
    results = session.run(record_attempt_query, parameters=test_data)
    results.consume()


assign_swag_query = """
MATCH (u:User {auth0_key:{auth0_key}})
WITH u
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
RETURN src.code AS code
"""


def assign_swag_code(db_driver, auth0_key):
    print(assign_swag_query)
    code = ''
    session = db_driver.session()
    results = session.run(assign_swag_query, parameters={"auth0_key": auth0_key})
    for record in results:
        record = dict((el[0], el[1]) for el in record.items())
        code = record['code']
    return code


unsent_swag_emails_query = """
MATCH (u:User)<-[:ISSUED_TO]-(swag)
where exists(u.auth0_key) 
AND exists(u.firstName)
AND exists(u.lastName)
AND not exists(swag.email_sent)
return u.firstName AS firstName, u.lastName AS lastName, swag.code AS swagCode
"""


def find_unsent_swag_emails(db_driver):
    with db_driver.session() as session:
        results = session.run(unsent_swag_emails_query)

        return [{"first_name": record["firstName"],
                 "last_name": record["lastName"],
                 "swag_code": record["swagCode"]}
                for record in results]

