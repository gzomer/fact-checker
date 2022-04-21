import sys
import json
import pyTigerGraph as tg

# Connection parameters
with open('./tigergraph.json') as f:
    config = json.load(f)
    hostName = config['hostName']
    userName = config['userName']
    password = config['password']

def setup(graph_name):
  conn = tg.TigerGraphConnection(host=hostName, username=userName, password=password)
  print("Connected")
  # Create graph
  results = conn.gsql(f'CREATE GRAPH {graph_name}()')
  print('Create graph', results)

  change_schema = f'''
    USE GRAPH {graph_name}
    CREATE SCHEMA_CHANGE JOB add_structure FOR GRAPH {graph_name} {{
      ADD VERTEX Claim(PRIMARY_ID id UINT, Text STRING, Year INT, IsTrue BOOL) WITH primary_id_as_attribute="true";
      ADD VERTEX Mention(PRIMARY_ID id UINT, Name STRING, EntityType STRING) WITH primary_id_as_attribute="true";
      ADD VERTEX Source(PRIMARY_ID id UINT, Name STRING, URL STRING) WITH primary_id_as_attribute="true";
      ADD DIRECTED EDGE mentions (From Claim, To Mention) WITH REVERSE_EDGE="mention_claims";
      ADD DIRECTED EDGE sources (From Claim, To Source) WITH REVERSE_EDGE="source_claims";
    }}
    RUN SCHEMA_CHANGE JOB add_structure
  '''
  results = conn.gsql(change_schema)
  print('Create edges/vertices', results)

  # Connect to graph
  conn.graphname=graph_name
  secret = conn.createSecret()
  authToken = conn.getToken(secret)
  authToken = authToken[0]
  conn = tg.TigerGraphConnection(host=hostName, graphname=graph_name, username=userName, password=password, apiToken=authToken)

  # Create loading jobs
  results = conn.gsql(f'''
    USE GRAPH {graph_name}
    BEGIN
    CREATE LOADING JOB load_claims FOR GRAPH {graph_name} {{
    DEFINE FILENAME MyDataSource;
    LOAD MyDataSource TO VERTEX Claim VALUES($0, $1, $2, $3) USING SEPARATOR=",", HEADER="true", EOL="\\n", QUOTE="double";
    }}
    END
    ''')
  print('Create load claims', results)

  results = conn.gsql(f'''
    USE GRAPH {graph_name}
    BEGIN
    CREATE LOADING JOB load_mentions FOR GRAPH {graph_name} {{
    DEFINE FILENAME MyDataSource;
    LOAD MyDataSource TO VERTEX Mention VALUES($0, $1, $2) USING SEPARATOR=",", HEADER="true", EOL="\\n", QUOTE="double";
    }}
    END
    ''')
  print('Create load mentions', results)

  results = conn.gsql(f'''
    USE GRAPH {graph_name}
    BEGIN
    CREATE LOADING JOB load_claims_mentions FOR GRAPH {graph_name} {{
    DEFINE FILENAME MyDataSource;
    LOAD MyDataSource TO EDGE mentions VALUES($0, $1) USING SEPARATOR=",", HEADER="true", EOL="\\n", QUOTE="double";
    }}
    END
    ''')
  print('Create load claims mentions', results)


  results = conn.gsql(f'''
    USE GRAPH {graph_name}
    BEGIN
    CREATE LOADING JOB load_sources FOR GRAPH {graph_name} {{
    DEFINE FILENAME MyDataSource;
    LOAD MyDataSource TO VERTEX Source VALUES($0, $1, $2) USING SEPARATOR=",", HEADER="true", EOL="\\n", QUOTE="double";
    }}
    END
    ''')
  print('Create load sources', results)

  results = conn.gsql(f'''
    USE GRAPH {graph_name}
    BEGIN
    CREATE LOADING JOB load_claims_sources FOR GRAPH {graph_name} {{
    DEFINE FILENAME MyDataSource;
    LOAD MyDataSource TO EDGE sources VALUES($0, $1) USING SEPARATOR=",", HEADER="true", EOL="\\n", QUOTE="double";
    }}
    END
    ''')
  print('Create load claims sources', results)


  # Create queries
  results = conn.gsql(f'''
    USE GRAPH {graph_name}
    CREATE QUERY similarity(Set<UINT> A, Set<UINT> B) FOR GRAPH {graph_name} RETURNS (FLOAT){{
    SetAccum<UINT> @@inter, @@uni;
    FLOAT similarity;

    IF A.size() != 0 AND B.size() !=0 THEN
      @@inter = A INTERSECT B;
      @@uni = A UNION B;

      IF @@inter.size() == 0 THEN
        similarity = 0;
      ELSE
        similarity = @@inter.size()*1.0/@@uni.size();
        END;
    ELSE
      similarity = 0;
      END;

    PRINT similarity;
    RETURN similarity;
  }}
  ''')
  print('Create similarity query', results)

  results = conn.gsql(r'''
    USE GRAPH ''' + graph_name + r'''
    CREATE QUERY similar_claims(SET <STRING> Entities, INT maxReturn) FOR GRAPH '''+ graph_name + r''' SYNTAX v2{
      TYPEDEF tuple<JSONOBJECT claim, FLOAT similarity> simMentions;
      FLOAT result;
      HeapAccum<simMentions>(maxReturn, similarity DESC) @@topMentionResults;
      SetAccum<UINT> @mentions;
      SetAccum<UINT> @@inMentions;

      // Get the mentions of the input
      ourMentions = SELECT m FROM Mention:m WHERE m.EntityType IN Entities
      ACCUM
        @@inMentions += m.id;

      // Get the mentions of all claims
      simPeople = SELECT c FROM Claim:c - (mentions>) - Mention:m
      ACCUM
        c.@mentions += m.id
      POST-ACCUM
        STRING text = "",
        IF c.IsTrue
        THEN text = "{\"text\":\""+c.Text + "\",\"truth\": true}"
        ELSE text = "{\"text\":\""+c.Text + "\",\"truth\": false}"
        END,
        @@topMentionResults += simMentions(parse_json_object(text), similarity(@@inMentions, c.@mentions));


      PRINT @@topMentionResults;
    }
    ''')
  print('Create query similar_claims', results)

  results = conn.gsql(f'''
    CREATE QUERY ping() FOR GRAPH {graph_name} {{
      PRINT "ping works!";
    }}
  ''')
  print('Create query ping', results)

  result = conn.gsql(f'''
    USE GRAPH {graph_name}
    INSTALL QUERY ping
    INSTALL QUERY similarity
    INSTALL QUERY similar_claims
  ''')
  print('Install query', result)

# Call setup from args (extract first arg as graph name)
if __name__ == '__main__':
  if not len(sys.argv) > 1:
    print('Usage: setup.py <graph_name> (FactChecking or NewsFacts)')
    sys.exit(1)
  # Validate graph name
  graph_name = sys.argv[1]
  if graph_name != 'FactChecking' and graph_name != 'NewsFacts':
    print('Invalid graph name (FactChecking or NewsFacts)')
    sys.exit(1)
  setup(graph_name)
