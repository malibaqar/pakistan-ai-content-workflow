import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def node(name,kind,params,x,version=1,**extra):
    return dict(id=name.lower().replace(' ','-'),name=name,type='n8n-nodes-base.'+kind,typeVersion=version,position=[x,200],parameters=params,**extra)

def http(name,path,x,body=None,timeout=30000):
    params={'method':'POST','url':'http://worker:8787'+path,'authentication':'genericCredentialType','genericAuthType':'httpHeaderAuth','options':{'timeout':timeout}}
    if body is not None: params.update(sendBody=True,specifyBody='json',jsonBody=body)
    return node(name,'httpRequest',params,x,4.2,credentials={'httpHeaderAuth':{'name':'Editorial worker'}})

def workflow(name,nodes,connections):
    return {'name':name,'nodes':nodes,'connections':connections,'active':False,'settings':{'executionOrder':'v1','timezone':'Asia/Karachi'},'pinData':{},'tags':[]}

def edge(target,index=0): return {'node':target,'type':'main','index':index}
research=workflow('Pakistan AI — collect and draft (free)',[
 node('Research schedule','scheduleTrigger',{'rule':{'interval':[{'field':'cronExpression','expression':'0 8,18 * * *'}]}},0,1.2),
 http('Collect and draft','/research',260,timeout=1500000)
],{'Research schedule':{'main':[[edge('Collect and draft')]]}})
publish=workflow('Pakistan AI — publish approved queue',[
 node('Publication slots','scheduleTrigger',{'rule':{'interval':[{'field':'cronExpression','expression':'0 12,19 * * *'}]}},0,1.2),
 http('Reserve post','/claim',220),
 node('Ready','if',{'conditions':{'options':{'caseSensitive':True,'leftValue':'','typeValidation':'strict','version':2},'conditions':[{'id':'ready','leftValue':'={{ $json.ready }}','rightValue':True,'operator':{'type':'boolean','operation':'true','singleValue':True}}],'combinator':'and'},'options':{}},440,2.2),
 node('Publish to LinkedIn','linkedIn',{'resource':'post','operation':'create','postAs':'person','person':'REPLACE_WITH_YOUR_LINKEDIN_PERSON_ID','text':'={{ $json.text }}','additionalFields':{}},680,1,credentials={'linkedInOAuth2Api':{'name':'LinkedIn account'}},retryOnFail=False),
 http('Record receipt','/receipt',920,'={{ JSON.stringify({ id: $("Reserve post").item.json.id, claim_token: $("Reserve post").item.json.claim_token, receipt: $json.id || $json.urn || $json["x-restli-id"] || "" }) }}')
],{'Publication slots':{'main':[[edge('Reserve post')]]},'Reserve post':{'main':[[edge('Ready')]]},'Ready':{'main':[[edge('Publish to LinkedIn')],[]]},'Publish to LinkedIn':{'main':[[edge('Record receipt')]]}})
for name,data in [('01_research.json',research),('02_publish.json',publish)]:
 (ROOT/'workflows'/name).write_text(json.dumps(data,indent=2)+'\n')
