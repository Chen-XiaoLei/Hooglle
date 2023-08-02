import numpy as np
from logparser.parser.prefix_tree import prefixTree, match_wildcard_with_content
import pandas as pd
import os
import re
from gradio_client import Client
import json
import time
from sentence_transformers import SentenceTransformer
import faiss

class LogCluster:
    def __init__(self, logIDL=[], template=""):
        self.template = template
        self.logIDL = logIDL
        self.constant = ""
        for ch in template:
            if (ch.isalpha()):
                self.constant += ch
        self.countVariable=len(re.findall("<\*>",template))

def containNoConstant(template):
    for ch in template:
        if(ch!=" " and ch!="<" and ch!="*" and ch!=">"):
            return False
    return True


class LogParser:
    def __init__(self, log_format, indir='./', outdir='./result/',flagged_path='./flagged/'):
        self.path = indir
        self.savePath = outdir
        self.log_format = log_format
        self.prefix_tree = prefixTree()
        self.logClusters = []
        self.flagged_path=flagged_path

    def log_to_dataframe(self, log_file, regex, headers):
        log_messages = []
        linecount = 0
        with open(log_file, 'r', encoding='utf-8') as fin:
            lines = fin.readlines()
            for line in lines:
                try:
                    match = regex.search(line.strip())
                    message = [match.group(header) for header in headers]
                    log_messages.append(message)
                    linecount += 1
                except Exception as e:
                    pass
        logdf = pd.DataFrame(log_messages, columns=headers)
        logdf.insert(0, 'LineId', None)
        logdf['LineId'] = [i + 1 for i in range(linecount)]
        return logdf

    def load_data(self):
        headers, regex = self.generate_logformat_regex(self.log_format)
        self.df_log = self.log_to_dataframe(os.path.join(self.path, self.logName), regex, headers)

    def generate_logformat_regex(self, logformat):
        headers = []
        splitters = re.split(r'(<[^<>]+>)', logformat)
        regex = ''
        for k in range(len(splitters)):
            if k % 2 == 0:
                splitter = re.sub(' +', '\\\s+', splitters[k])
                regex += splitter
            else:
                header = splitters[k].strip('<').strip('>')
                regex += '(?P<%s>.*?)' % header
                headers.append(header)
        regex = re.compile('^' + regex + '$')
        return headers, regex


    def parse_log_with_LLM(self, logmessage):
        logmessage_process=re.sub('\*','&star;', logmessage)
        logmessage_process=re.sub('\$','&dollar;',logmessage_process)
        self.Count_Call_LLM+=1
        self.client = Client("XXX.XXX.XXX.XXX:XXXX", output_dir=self.flagged_path,verbose=False)
        length=min(100+len(logmessage_process),4000)
        job = self.client.submit(logmessage_process, "1.json", length, 0.7, 0.5, fn_index=0)
        while(1):
            if(job.done()):
                break
        result_paths=job.communicator.job.outputs

        result_path=result_paths[-1]
        if(not result_path):
            return logmessage
        f=open(result_path)
        result = json.load(f)
        f.close()
        resultString=result[0][1]
        resultString=self.process(resultString)
        if('<*>' not in resultString):
            resultString=logmessage
        return resultString

    def process(self, parsed_log):
        parsed_log = re.sub("<p>", "", parsed_log)
        parsed_log = re.sub("</p>", "", parsed_log)
        parsed_log = re.sub("<em>", "*", parsed_log)
        parsed_log = re.sub("</em>", "*", parsed_log)
        parsed_log = re.sub("\\\<Number>", "<*>", parsed_log)
        parsed_log = re.sub("<\w+>", "<*>", parsed_log)
        parsed_log = re.sub("&dollar;", "$", parsed_log)
        parsed_log = re.sub("&gt;", ">", parsed_log)
        parsed_log = re.sub("&lt;", "<", parsed_log)
        parsed_log = re.sub("&star;", "*", parsed_log)

        return parsed_log

    def outputResults(self):
        print("Parsing done, outputing results. Call LLM for "+str(self.Count_Call_LLM)+ " times.")

        filename = self.logName
        df_event=[]
        ids=[-1] * self.df_log.shape[0]
        templates=[""] * self.df_log.shape[0]

        for cid in range(len(self.logClusters)):
            cluster=self.logClusters[cid]
            df_event.append([cid,cluster.template,len(cluster.logIDL)])

            for id in cluster.logIDL:
                ids[id]=cid
                templates[id]=cluster.template

        df_event = pd.DataFrame(df_event, columns=['EventId', 'EventTemplate', 'Occurrences'])

        self.df_log['EventId'] = ids
        self.df_log['EventTemplate'] = templates
        self.df_log.to_csv(os.path.join(self.savePath, filename + '_structured.csv'), index=False,
                           encoding="utf-8")
        df_event.to_csv(os.path.join(self.savePath, filename + '_templates.csv'), index=False, encoding="utf-8")



    def clean(self):
        time.sleep(1)
        path=self.flagged_path
        files=os.listdir(path)
        for file in files:
            filepath=path+'/'+file
            os.remove(filepath)

    def load_others(self):
        self.embeddingModel = SentenceTransformer('all-MiniLM-L6-v2')
        self.dim = 384
        index = faiss.IndexFlatIP(self.dim)
        self.index = faiss.IndexIDMap(index)


    def parse(self, logName):
        self.logName = logName
        self.clean()
        self.load_others()
        self.load_data()
        self.Count_Call_LLM=0

        for idx, line in self.df_log.iterrows():
            if idx % 2000 == 0:
                print('Processed {0:.1f}% of log lines.'.format(idx * 100.0 / len(self.df_log)))
            lineID = line['LineId']
            logmessage = line['Content'].strip()
            logid = lineID - 1
            logmessage=re.sub("  "," ",logmessage)
            match_id = self.prefix_tree.match(logmessage, self.prefix_tree.root)

            if (match_id != -1):
                self.logClusters[match_id].logIDL.append(logid)
                continue

            parsed_log = self.parse_log_with_LLM(logmessage)

            # print("============Log to Template==============")
            # print(logmessage)
            # print(parsed_log)
            # print("templates : "+str(len(self.logClusters)))
            # print("Call LLM : "+str(self.Count_Call_LLM))
            # print("============Log to Template==============")

            embedding=self.embeddingModel.encode([parsed_log])
            _, I = self.index.search(embedding, 1)
            most_similar_cid=I.tolist()[0][0]
            if(most_similar_cid!=-1):
                countV = self.logClusters[most_similar_cid].countVariable
                countVariable = len(re.findall("<\*>", parsed_log))
                if(countV==0):
                    template_most_similar = self.logClusters[most_similar_cid].template
                    constant=parsed_log
                else:
                    template_most_similar = self.logClusters[most_similar_cid].constant
                    constant = ""
                    for ch in parsed_log:
                        if (ch.isalpha()):
                            constant += ch
                if(template_most_similar=="" and constant=="" and countVariable==countV and containNoConstant(parsed_log)):
                    template=logmessage
                    wildcards=[]
                    cid = most_similar_cid
                    self.prefix_tree.add_prefix_tree_with_templateTree_with_compress(template, cid, wildcards)
                    self.logClusters[most_similar_cid].logIDL.append(logid)
                    continue
                if (template_most_similar == constant and countVariable==countV):
                    template, wildcards = match_wildcard_with_content(parsed_log, logmessage)
                    cid = most_similar_cid
                    self.prefix_tree.add_prefix_tree_with_templateTree_with_compress(template, cid, wildcards)
                    self.logClusters[most_similar_cid].logIDL.append(logid)
                    continue

            template, wildcards = match_wildcard_with_content(parsed_log, logmessage)
            cid=len(self.logClusters)
            newCluster=LogCluster([logid],parsed_log)
            self.logClusters.append(newCluster)
            if(containNoConstant(template)):
                self.prefix_tree.add_prefix_tree_with_templateTree_with_compress(logmessage, cid, [])
            else:
                self.prefix_tree.add_prefix_tree_with_templateTree_with_compress(template,cid,wildcards)
            embedding=self.embeddingModel.encode([template])
            self.index.add_with_ids(np.array(embedding),np.asarray(np.array([cid]).astype('int64')))

        self.outputResults()
        self.clean()
        return


