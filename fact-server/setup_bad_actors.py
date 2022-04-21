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
        ADD VERTEX Account(
            PRIMARY_ID id UINT,
            Name STRING,
            ScreenName STRING,
            Location STRING,
            Description STRING,
            FollowersCount INT,
            FriendsCount INT,
            ListedCount INT,
            StatusesCount INT,
            ProfileImage STRING,
            CreatedAt STRING,
            ActorType STRING DEFAULT 'unknown',
            OriginalActorType STRING DEFAULT 'unknown'
        ) WITH primary_id_as_attribute="true";
        ADD VERTEX Tweet(
            PRIMARY_ID id UINT,
            Text STRING,
            CreatedAt STRING,
            QuoteCount INT DEFAULT 0,
            ReplyCount INT DEFAULT 0,
            RetweetCount INT DEFAULT 0,
            FavoriteCount INT DEFAULT 0
        ) WITH primary_id_as_attribute="true";
      ADD DIRECTED EDGE link (From Account, To Account) WITH REVERSE_EDGE="reverse_link";
      ADD DIRECTED EDGE tweet (From Account, To Tweet) WITH REVERSE_EDGE="reverse_tweet";
    }}
    RUN SCHEMA_CHANGE JOB add_structure
  '''
  results = conn.gsql(change_schema)
  print('Create edges/vertices', results)

  results = conn.gsql(f'''
    USE GRAPH {graph_name}
    BEGIN
    CREATE LOADING JOB load_relations FOR GRAPH {graph_name} {{
    DEFINE FILENAME MyDataSource;
    LOAD MyDataSource TO VERTEX Account VALUES($0, $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12) USING SEPARATOR=",", HEADER="true", EOL="\\n", QUOTE="double";
    LOAD MyDataSource TO VERTEX Account VALUES($13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25) USING SEPARATOR=",", HEADER="true", EOL="\\n", QUOTE="double";
    LOAD MyDataSource TO EDGE link VALUES($0, $13) USING SEPARATOR=",", HEADER="true", EOL="\\n", QUOTE="double";
    }}
    END
    ''')

  print('Create loading job', results)

  results = conn.gsql(f'''
    USE GRAPH {graph_name}
    BEGIN
    CREATE QUERY list_accounts() FOR GRAPH {graph_name} {{
        TYPEDEF TUPLE <Account String, ActorType String> accountType;

        SetAccum<accountType> @@accounts;
        res = SELECT a FROM Account:a -(:e) - Account:b
        WHERE a.ActorType == "bad_actor"
        ACCUM
          @@accounts += accountType(a.ScreenName, a.ActorType),
          @@accounts += accountType(b.ScreenName, b.ActorType);

        print(@@accounts);
    }}
    END
    ''')
  print('Create list_accounts query', results)

  results = conn.gsql(f'''
    USE GRAPH {graph_name}
    BEGIN
    CREATE QUERY list_bad_actors() FOR GRAPH {graph_name} {{
        SetAccum<UINT> @@accounts;
        res = SELECT a FROM Account:a
        WHERE a.ActorType == "bad_actor"
        ACCUM
          @@accounts += a.id;

        print(@@accounts);
    }}
    END
    ''')
  print('Create list_bad_actors query', results)

  result = conn.gsql(f'''
    CREATE QUERY cycle_detection (INT depth) FOR GRAPH TwitterBadActors {{
          ListAccum<ListAccum<VERTEX>> @currList, @newList;
          ListAccum<ListAccum<VERTEX>> @@cycles;
          SumAccum<INT> @uid;

          # initialization
          Active = {{Account.*}};
          Active = SELECT s
                  FROM Active:s
                  ACCUM s.@currList = [s];

          WHILE Active.size() > 0 LIMIT depth DO
          Active = SELECT t
                  FROM Active:s -(link:e)-> :t
                  ACCUM BOOL t_is_min = TRUE,
                        FOREACH sequence IN s.@currList DO
                                IF t == sequence.get(0) THEN  # cycle detected
                                          FOREACH v IN sequence DO
                                                  IF getvid(v) < getvid(t) THEN
                                                          t_is_min = FALSE,
                                                          BREAK
                                                  END
                                          END,
                                          IF t_is_min == TRUE THEN  # if it has the minimal label in the list, report
                                                  @@cycles += sequence
                                          END
                                ELSE IF sequence.contains(t) == FALSE THEN   # discard the sequences containing t
                                          t.@newList += [sequence + [t]]   # store sequences in @newList to avoid confliction with @currList
                                END
                        END
                  POST-ACCUM s.@currList.clear(),
                              t.@currList = t.@newList,
                              t.@newList.clear()
                  HAVING t.@currList.size() > 0;  # IF receive no sequences, deactivate it;
          END;
          PRINT @@cycles;
  }}''')
  print('Create cycle_detection query', result)

  result = conn.gsql(f'''
    USE GRAPH {graph_name}
    INSTALL QUERY cycle_detection
    INSTALL QUERY list_accounts
    INSTALL QUERY list_bad_actors
  ''')
  print('Install query', result)


setup('TwitterBadActors')