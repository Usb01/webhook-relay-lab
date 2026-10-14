"""Signed event intake and SQLite-backed retries, demonstrated without network sends."""
import argparse,hashlib,hmac,json,sqlite3,time,math
from pathlib import Path
from report import report

def signature(body,secret):return hmac.new(secret.encode(),body,hashlib.sha256).hexdigest()

class Queue:
 def __init__(self,path):
  self.db=sqlite3.connect(path);self.db.row_factory=sqlite3.Row
  self.db.execute('CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL, due REAL NOT NULL, last_error TEXT NOT NULL)');self.db.commit()
 def close(self):self.db.close()
 def ingest(self,body,sig,secret,now=None):
  now=time.time() if now is None else now
  if not secret or len(secret)<16:raise ValueError('Use a secret with at least 16 characters')
  if len(body)>100000:raise ValueError('Event too large')
  if not hmac.compare_digest(signature(body,secret),sig):raise ValueError('Invalid signature')
  event=json.loads(body)
  if not isinstance(event,dict) or not isinstance(event.get('id'),str) or not 1<=len(event['id'])<=100:raise ValueError('Invalid event ID')
  if not isinstance(event.get('timestamp'),(float,int)) or isinstance(event['timestamp'],bool) or not math.isfinite(event['timestamp']) or abs(now-event['timestamp'])>300:raise ValueError('Expired or future event timestamp')
  with self.db:cur=self.db.execute('INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?)',(event['id'],body.decode(),'pending',0,now,''))
  return 'accepted' if cur.rowcount else 'duplicate'
 def run_due(self,deliver,now=None,max_attempts=3):
  now=time.time() if now is None else now
  rows=self.db.execute("SELECT * FROM events WHERE status='pending' AND due<=? ORDER BY due,id",(now,)).fetchall()
  for row in rows:
   attempt=row['attempts']+1
   try:
    deliver(json.loads(row['payload']),row['id'])
    with self.db:self.db.execute("UPDATE events SET status='delivered',attempts=?,last_error='' WHERE id=?",(attempt,row['id']))
   except Exception:
    # Do not persist potentially sensitive exception contents.
    status='dead_letter' if attempt>=max_attempts else 'pending'
    with self.db:self.db.execute('UPDATE events SET status=?,attempts=?,due=?,last_error=? WHERE id=?',(status,attempt,now+2**attempt,'Delivery failed',row['id']))
  return len(rows)
 def rows(self):return [dict(r) for r in self.db.execute('SELECT id,status,attempts,due,last_error FROM events ORDER BY id')]

def demo(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);q=Queue(out/'events.sqlite');now=1800000000;secret='demo-secret-not-for-production'
 for name in ['evt-success','evt-retry','evt-dead']:
  body=json.dumps({'id':name,'timestamp':now,'type':'lead.created','data':{'reference':'synthetic-example'}}).encode();q.ingest(body,signature(body,secret),secret,now)
 def deliver(event,key):
  attempt=q.db.execute('SELECT attempts FROM events WHERE id=?',(key,)).fetchone()[0]
  if key=='evt-dead' or key=='evt-retry' and attempt<1:raise RuntimeError('Simulated delivery failure')
 for tick in [now,now+2,now+6]:q.run_due(deliver,tick)
 rows=q.rows();q.close();(out/'result.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
 report(out/'report.html','Webhook Relay','Signed intake → durable queue → bounded retries → delivery or dead-letter review. Simulated delivery only.',rows,{'events':len(rows),'delivered':sum(r['status']=='delivered' for r in rows),'dead letter':sum(r['status']=='dead_letter' for r in rows)})
 print(json.dumps({'events':len(rows),'simulation':True}))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--demo',action='store_true');p.add_argument('--output',default='runs');a=p.parse_args();demo(a.output)
if __name__=='__main__':main()
