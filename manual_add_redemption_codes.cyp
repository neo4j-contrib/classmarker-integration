// add the codes
USING PERIODIC COMMIT 200
LOAD CSV WITH HEADERS FROM "https://docs.google.com/spreadsheets/d/e/2PACX-1vS7qhtHLsKQCd24owaLY46BsIJHliDDWoYOrkrw0FXl1fKkclFVEaEfL3Sf_MTlMsBkrDfmXj5cPPg2/pub?gid=903021539&single=true&output=csv" AS row
WITH row
WHERE row['claimed']='FALSE'
AND row['created_at'] STARTS WITH '2019-08-23'
WITH row
CREATE (src:SwagRedemptionCode)
SET src.code=row['code'],
src.redeemed=false,
src.type='certified'






// assign the codes to users who are missing them
WITH datetime({year: 2019, month: 1, day: 1}).epochSeconds AS testDate
MATCH (u:User)-[]-(c:Certification)
WHERE
c.passed = true AND
c.finished > testDate AND
NOT EXISTS(()-[:ISSUED_TO]->(u))
WITH DISTINCT u.auth0_key AS the_auth0_key
MATCH (u:User {auth0_key:the_auth0_key})
WHERE SIZE( (u)<-[:ISSUED_TO]-() ) = 0
WITH u 
MATCH (src:SwagRedemptionCode)
WHERE
  src.redeemed=false
  AND
  src.type='certified'
  AND
  size( (src)-[:ISSUED_TO]->(:User) ) = 0
WITH u, src
MERGE (src)-[:ISSUED_TO]->(u)
