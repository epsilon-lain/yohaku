import hashlib,http.client,io,json,ssl,types,unittest
from unittest.mock import patch
from pathlib import Path
import tempfile,os,shutil
import yohaku_codex_provider as p
import yohaku_provider_diagnostics as d
import yohaku_provider_transport as t
import yohaku_codex_diagnostics as cd
KEY='fixture-only-private-key-123456789'
PAYLOAD=dict(model=p.MODEL,reasoning={'effort':'high'},input=[{'role':'user','content':'PRIVATE_REQUEST_BODY'}])
SSE=b'data: {"type":"response.completed","response":{"status":"completed"}}\n\n'
class Response(io.BytesIO):
 def __init__(self,data,status=200,headers=None):super().__init__(data);self.status=status;self.headers={k.lower():v for k,v in (headers or {'Content-Type':'text/event-stream','Content-Length':str(len(data))}).items()}
 def getheader(self,name,default=None):return self.headers.get(name.lower(),default)
 @property
 def length(self):return len(self.getvalue())-self.tell()
class FailureTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.pc=patch.object(d,'DIRECTORY',self.root/'p');self.pc.start();self.addCleanup(self.pc.stop)
  self.rc=patch.object(cd,'DIRECTORY',self.root/'c');self.rc.start();self.addCleanup(self.rc.stop)
  self.relay=p.Relay(KEY);self.addCleanup(self.relay.close)
  def preserve():
   folder=os.environ.get('YOHAKU_RECOVERY_EVIDENCE')
   if folder:
    dest=Path(folder)/self.id().rsplit('.',1)[-1];shutil.copytree(self.root,dest,dirs_exist_ok=True)
    (dest/'relay-records.json').write_text(json.dumps(self.relay.evidence(),indent=2))
  self.addCleanup(preserve)
 def request(self,payload=PAYLOAD):
  c=http.client.HTTPConnection('127.0.0.1',self.relay.server.server_port,timeout=4)
  try:
   c.request('POST','/responses',body=json.dumps(payload),headers={'Authorization':'Bearer '+self.relay.token});r=c.getresponse();return r.status,r.read()
  finally:c.close()
 def diag(self):return json.loads(next((self.root/'p').glob('*.json')).read_text())
 def test_upstream_http_502_distinguished_and_bounded_redacted_body(self):
  body=(KEY+' PRIVATE_REQUEST_BODY').encode()*500
  with patch.object(p,'ObservedHTTPS') as h:
   h.return_value.getresponse.side_effect=lambda:Response(body,502,{'content-type':'text/html','content-length':str(len(body)),'x-request-id':KEY,'set-cookie':KEY})
   status,raw=self.request()
   self.assertEqual(h.return_value.request.call_count,3)
  e=json.loads(raw)['error'];self.assertEqual((status,e['kind'],e['upstream_http_status'],e['attempts']),(502,'upstream_http',502,3));self.assertTrue(e['retry_exhausted'])
  record=self.diag();meta=record['upstream_response'];self.assertEqual(meta['bytes_observed'],8192);self.assertFalse(meta['read_complete']);self.assertTrue(meta['limit_exceeded']);self.assertNotIn('set-cookie',meta['headers'])
  text=json.dumps(record)+raw.decode()+json.dumps(self.relay.evidence());self.assertNotIn(KEY,text);self.assertNotIn('PRIVATE_REQUEST_BODY',text);self.assertNotIn('set-cookie',text)
 def test_tls_no_http_classification_survives_into_codex_caller(self):
  def connection(trace,*a,**kw):
   def send(*a,**kw):
    error=ssl.SSLEOFError('fixture TLS EOF');trace.failure('tls_wrap_handshake',error);raise error
   return types.SimpleNamespace(request=send,close=lambda:None)
  with patch.object(p,'ObservedHTTPS',side_effect=connection):status,raw=self.request()
  e=json.loads(raw)['error'];self.assertEqual((e['kind'],e['phase'],e['upstream_http_status'],e['attempts']),('connection','tls_wrap_handshake',None,3))
  diag=cd.TurnDiagnostics({'config':{},'prompt':'PRIVATE_REQUEST_BODY'});diag.attach(types.SimpleNamespace(yohaku_provider_relay=self.relay))
  capture=types.SimpleNamespace(snapshot=lambda:('',0),thread=None);diag.process_closed(types.SimpleNamespace(returncode=0,yohaku_provider_relay=self.relay),capture,False);diag.fail(ValueError('native relay HTTP 502'))
  message=diag.failure_message();self.assertIn('kind=connection',message);self.assertIn('upstream HTTP not observed',message);self.assertIn(e['diagnostic_id'],message)
 def test_complete_http200_malformed_json_is_not_retried_and_no_fragments_delivered(self):
  fragment=b'data: {"type":"response.function_call_arguments.delta","delta":"PRIVATE_REQUEST_BODY"}\n\n'
  bad=b'data: {"type":"response.completed" "response":{}}\n\n';wire=fragment+bad
  with patch.object(p,'ObservedHTTPS') as h:
   h.return_value.getresponse.return_value=Response(wire);status,raw=self.request();self.assertEqual(h.return_value.request.call_count,1)
  e=json.loads(raw)['error'];self.assertEqual((status,e['kind'],e['upstream_http_status'],e['phase']),(502,'response_parse',200,'response_decode'));self.assertFalse(e['retryable']);self.assertNotIn(b'function_call_arguments',raw)
  meta=self.diag()['upstream_response'];self.assertTrue(meta['read_complete']);self.assertEqual(meta['declared_bytes'],len(wire));self.assertEqual(meta['parse']['frame_index'],1);self.assertIsInstance(meta['parse']['position'],int);self.assertEqual(meta['body_sha256'],hashlib.sha256(wire).hexdigest());self.assertNotIn('PRIVATE_REQUEST_BODY',json.dumps(self.diag()))
 def test_wrong_mime_http200_has_bounded_non_json_evidence(self):
  with patch.object(p,'ObservedHTTPS') as h:
   h.return_value.getresponse.return_value=Response(b'<html>PRIVATE_REQUEST_BODY</html>',200,{'content-type':'text/html'});status,raw=self.request();self.assertEqual(h.return_value.request.call_count,1)
  self.assertEqual(json.loads(raw)['error']['upstream_http_status'],200);meta=self.diag()['upstream_response'];self.assertEqual(meta['body_kind'],'html');self.assertTrue(meta['read_complete']);self.assertNotIn('PRIVATE_REQUEST_BODY',json.dumps(meta))
 def test_empty_and_missing_completion_never_forward_tools(self):
  for wire in [b'',b'data: {"type":"response.function_call_arguments.delta","delta":"NEVER_DELIVER"}\n\n']:
   with self.subTest(wire=bool(wire)),patch.object(p,'ObservedHTTPS') as h:
    h.return_value.getresponse.side_effect=lambda:Response(wire);status,raw=self.request();self.assertEqual(h.return_value.request.call_count,3)
   self.assertEqual(status,502);self.assertNotIn(b'NEVER_DELIVER',raw);self.assertEqual(json.loads(raw)['error']['kind'],'response_read')
 def test_valid_multiline_crlf_sse_roundtrip_and_logical_retry_scope(self):
  wire=b'data: {"type":"response.completed",\r\ndata: "response":{"status":"completed"}}\r\n\r\n'
  with patch.object(p,'ObservedHTTPS') as h:
   h.return_value.getresponse.return_value=Response(wire);self.assertEqual(self.request(),(200,wire))
  recovery=t.Recovery();attempts=[]
  def operation():
   attempts.append(1)
   if len(attempts)==1:raise ConnectionResetError()
   return 'ok'
  self.assertEqual(recovery.run(operation),'ok');self.assertEqual(len(recovery.request_events),1)
  self.assertEqual(recovery.run(lambda:'next'),'next');self.assertEqual(recovery.request_events,[]);self.assertEqual(len(recovery.events),1)
 def test_header_long_secret_is_redacted_before_bounding(self):
  key='x'*512;self.relay.key=key;self.relay.diagnostics.key=key
  with patch.object(p,'ObservedHTTPS') as h:
   h.return_value.getresponse.return_value=Response(b'no',401,{'content-type':'text/plain','x-request-id':key})
   self.request()
  self.assertNotIn(key[:128],json.dumps(self.diag()))
 def test_downstream_delivery_is_unknown_and_never_retryable(self):
  self.relay.diagnostics.begin();self.relay.diagnostics.transport.origin_status=200
  failure=self.relay.failure(BrokenPipeError(),{'delivery_started':True,'upstream_attempt_count':1})
  self.assertEqual((failure['kind'],failure['tools_delivered']),('downstream_delivery','unknown'));self.assertFalse(failure['retryable'])
  self.assertIn('unknown',self.relay.failure_message(failure))
 def test_cancel_before_next_request_has_no_previous_attempts(self):
  recovery=t.Recovery({'request_max_retries':0})
  with self.assertRaises(ConnectionResetError):recovery.run(lambda:(_ for _ in ()).throw(ConnectionResetError()))
  self.assertEqual(len(recovery.request_events),1);recovery.cancel()
  with self.assertRaises(t.RecoveryCancelled):recovery.run(lambda:'must not execute')
  self.assertEqual(recovery.request_events,[])
 def test_invalid_local_request_is_400_not_gateway_failure(self):
  c=http.client.HTTPConnection('127.0.0.1',self.relay.server.server_port,timeout=2)
  with patch.object(p,'ObservedHTTPS') as h:
   c.request('POST','/responses',body=b'bad json',headers={'Authorization':'Bearer '+self.relay.token});r=c.getresponse();self.assertEqual(r.status,400);r.read();h.assert_not_called()
  c.close()
if __name__=='__main__':unittest.main()
