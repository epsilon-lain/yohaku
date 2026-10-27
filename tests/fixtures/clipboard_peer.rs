//! Minimal protocol-test peer for the published clipboard bridge.
//! Uses a caller-owned Wayland connection, synthetic text, and bounded I/O.
use std::{collections::HashMap, io::{Read, Write}, os::fd::{AsFd, AsRawFd}, os::unix::net::UnixStream, time::{Duration, Instant}};
use wayland_client::{Connection, Dispatch, Proxy, QueueHandle, EventQueue};
use wayland_client::protocol::{wl_registry::WlRegistry, wl_seat::WlSeat, wl_data_device_manager::WlDataDeviceManager, wl_data_device::WlDataDevice, wl_data_offer::WlDataOffer, wl_data_source::WlDataSource};
const READ: &str = "application/x-yohaku-clipboard-read-v1";
const WRITE: &str = "application/x-yohaku-clipboard-write-v1";
const ACK: &str = "application/x-yohaku-clipboard-ack-v1";
#[repr(C)] struct PollFd {fd:i32,events:i16,revents:i16}
unsafe extern "C" {fn poll(fds:*mut PollFd,nfds:usize,timeout:i32)->i32;}
#[derive(Default)] struct Peer {
 manager:Option<WlDataDeviceManager>, seat:Option<WlSeat>, selection:Option<WlDataOffer>,
 offers:HashMap<wayland_client::backend::ObjectId,Vec<String>>, payload:Vec<u8>,
}
impl Dispatch<WlRegistry,()> for Peer {
 fn event(s:&mut Self,r:&WlRegistry,e:wayland_client::protocol::wl_registry::Event,_:&(),_:&Connection,q:&QueueHandle<Self>) {
  if let wayland_client::protocol::wl_registry::Event::Global{name,interface,version}=e {
   match interface.as_str() {"wl_seat"=>s.seat=Some(r.bind(name,version.min(7),q,())),"wl_data_device_manager"=>s.manager=Some(r.bind(name,version.min(3),q,())),_=>()}
  }
 }
}
wayland_client::delegate_noop!(Peer:ignore WlSeat);
wayland_client::delegate_noop!(Peer:ignore WlDataDeviceManager);
impl Dispatch<WlDataDevice,()> for Peer {
 fn event(s:&mut Self,_:&WlDataDevice,e:wayland_client::protocol::wl_data_device::Event,_:&(),_:&Connection,_:&QueueHandle<Self>) {
  if let wayland_client::protocol::wl_data_device::Event::Selection{id}=e {s.selection=id;}
 }
 wayland_client::event_created_child!(Peer,WlDataDevice,[0=>(WlDataOffer,())]);
}
impl Dispatch<WlDataOffer,()> for Peer {
 fn event(s:&mut Self,o:&WlDataOffer,e:wayland_client::protocol::wl_data_offer::Event,_:&(),_:&Connection,_:&QueueHandle<Self>) {
  if let wayland_client::protocol::wl_data_offer::Event::Offer{mime_type}=e {s.offers.entry(o.id()).or_default().push(mime_type);}
 }
}
impl Dispatch<WlDataSource,()> for Peer {
 fn event(s:&mut Self,_:&WlDataSource,e:wayland_client::protocol::wl_data_source::Event,_:&(),_:&Connection,_:&QueueHandle<Self>) {
  if let wayland_client::protocol::wl_data_source::Event::Send{mime_type,fd}=e {if mime_type==WRITE {let bytes=s.payload.clone();std::thread::spawn(move||{let _=std::fs::File::from(fd).write_all(&bytes);});}}
 }
}
fn pump(c:&Connection,q:&mut EventQueue<Peer>,s:&mut Peer,end:Instant)->Result<(),String> {
 q.dispatch_pending(s).map_err(|e|e.to_string())?;c.flush().map_err(|e|e.to_string())?;
 let remaining=end.saturating_duration_since(Instant::now());if remaining.is_zero(){return Err("clipboard peer timeout".into());}
 if let Some(guard)=q.prepare_read() {let mut p=PollFd{fd:guard.connection_fd().as_raw_fd(),events:1,revents:0};let n=unsafe{poll(&mut p,1,remaining.as_millis().min(50) as i32)};if n>0 {guard.read().map_err(|e|e.to_string())?;}else if n<0 && std::io::Error::last_os_error().kind()!=std::io::ErrorKind::Interrupted {return Err("clipboard peer poll failed".into());}}
 q.dispatch_pending(s).map_err(|e|e.to_string())?;Ok(())
}
fn receive(c:&Connection,offer:&WlDataOffer,mime:&str)->Result<serde_json::Value,String> {
 let(mut reader,writer)=UnixStream::pair().map_err(|e|e.to_string())?;reader.set_read_timeout(Some(Duration::from_secs(2))).map_err(|e|e.to_string())?;
 offer.receive(mime.into(),writer.as_fd());drop(writer);c.flush().map_err(|e|e.to_string())?;
 let mut bytes=Vec::new();(&mut reader).take(8*1024*1024+1).read_to_end(&mut bytes).map_err(|e|e.to_string())?;
 if bytes.len()>8*1024*1024 {return Err("clipboard receipt exceeds bound".into());}serde_json::from_slice(&bytes).map_err(|e|e.to_string())
}
pub fn transfer(c:Connection,text:Option<&str>)->Result<String,String> {
 if text.is_some_and(|s|s.len()>1024*1024){return Err("clipboard text exceeds 1 MiB".into());}
 let end=Instant::now()+Duration::from_millis(2500);let mut q=c.new_event_queue::<Peer>();let h=q.handle();let registry=c.display().get_registry(&h,());let mut s=Peer::default();
 while s.manager.is_none()||s.seat.is_none(){pump(&c,&mut q,&mut s,end)?;}
 let device=s.manager.as_ref().unwrap().get_data_device(s.seat.as_ref().unwrap(),&h,());let source=s.manager.as_ref().unwrap().create_data_source(&h,());
 let nonce=format!("fixture-{}-{}",std::process::id(),std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos());
 if let Some(t)=text {s.payload=serde_json::to_vec(&serde_json::json!({"nonce":nonce,"text":t})).unwrap();source.offer(WRITE.into());}else{source.offer(READ.into());}
 device.set_selection(Some(&source),0);
 let result=(||loop{
  if let Some(offer)=s.selection.clone(){let wanted=if text.is_some(){ACK}else{READ};if s.offers.get(&offer.id()).is_some_and(|types|types.iter().any(|m|m==wanted)) {
   let value=receive(&c,&offer,wanted)?;
   if text.is_none()||value["nonce"]==nonce {if value["ok"]!=true{return Err(value["error"].as_str().unwrap_or("clipboard rejected request").to_owned());}return value["text"].as_str().map(str::to_owned).ok_or("missing clipboard text".into());}
   s.selection=None;
  }}
  pump(&c,&mut q,&mut s,end)?;
 })();
 source.destroy();for id in s.offers.keys(){if let Ok(offer)=WlDataOffer::from_id(&c,id.clone()){offer.destroy();}}device.release();s.seat.unwrap().release();drop(registry);c.flush().map_err(|e|e.to_string())?;result
}
