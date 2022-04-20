import pandas as pd
import os
import json
import tempfile
import pyTigerGraph as tg

# Connection parameters
with open('./tigergraph.json') as f:
    config = json.load(f)
    hostName = config['hostName']
    userName = config['userName']
    password = config['password']

tigergraph = None

class TigerGraph():

    def __init__(self, graphname = 'Claims'):
        self.conn = None
        self.graphname = graphname

    def connect(self):
        print('Connecting to TigerGraph...')
        conn = tg.TigerGraphConnection(host=hostName, username=userName, password=password)
        conn.graphname=self.graphname

        secret = conn.createSecret()
        authToken = conn.getToken(secret)
        authToken = authToken[0]

        conn = tg.TigerGraphConnection(host=hostName, graphname=self.graphname, username=userName, password=password, apiToken=authToken)

        print('Connect', conn)
        self.conn = conn

    def upload_job(self, data, job_name):
        if data is None or len(data) == 0:
            return None

        tmp_file = os.path.join(tempfile.gettempdir(), job_name + '.csv')
        # tmp_file = os.path.join('./tmp', job_name + '.csv')
        df = pd.DataFrame(data)
        df.to_csv(tmp_file, index=False, header=False)
        results = self.conn.uploadFile(tmp_file, fileTag='MyDataSource', jobName=job_name)
        return results

    def ping(self):
        return self.conn.runInstalledQuery("ping")

    def list_accounts(self):
        return self.conn.runInstalledQuery("list_accounts")

    def list_bad_actors(self):
        return self.conn.runInstalledQuery("list_bad_actors")

def get_tigergraph(graphname = 'Claims'):
    global tigergraph
    if tigergraph is None:
        tigergraph = TigerGraph(graphname)
        tigergraph.connect()
    return tigergraph