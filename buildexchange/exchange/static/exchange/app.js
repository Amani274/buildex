'use strict';
let state, tab='catalogue';
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=n=>`ZMW ${(n/100).toFixed(2)}`;
const date=s=>s?new Date(s).toLocaleString('en-GB',{timeZone:'Africa/Lusaka'})+' CAT':'';
const empty=s=>`<p class="empty">${esc(s)}</p>`;
const input=(name,label,type='text',value='',extra='')=>`<label>${esc(label)}<input name="${name}" type="${type}" value="${esc(value)}" ${extra}></label>`;
const select=(name,label,options)=>`<label>${esc(label)}<select name="${name}">${options.map(([v,l])=>`<option value="${esc(v)}">${esc(l)}</option>`).join('')}</select></label>`;
const hidden=(name,value)=>`<input type="hidden" name="${name}" value="${esc(value)}">`;
const form=(action,fields,label,values={})=>`<form data-action="${action}">${Object.entries(values).map(([k,v])=>hidden(k,v)).join('')}${fields}<button>${esc(label)}</button></form>`;
const supervisor=()=>select('supervisor','Assigned site supervisor',state.supervisors.map(s=>[s.id,s.username]));
const site=()=>input('site','Site address / landmarks and delivery instructions','text','','required maxlength="240"');
const note=(label='Notes',required=false)=>`<label>${esc(label)}<textarea name="notes" maxlength="500" ${required?'required':''}></textarea></label>`;
const reference=()=>input('reference','Manual reference (demo bookkeeping only)','text','','required maxlength="120"');
async function api(action,data,multipart=false){
 const csrf=document.cookie.split('; ').find(v=>v.startsWith('csrftoken='))?.split('=')[1];
 const response=await fetch(`/api/action/${action}/`,{method:'POST',headers:{'X-CSRFToken':csrf,...(multipart?{}:{'Content-Type':'application/json'})},body:multipart?data:JSON.stringify(data)});
 const result=await response.json(); if(!response.ok)throw Error(typeof result==='string'?result:JSON.stringify(result));return result;
}
function feedback(message,error=false){const n=$('#feedback');n.textContent=message;n.className=error?'error':'success';}
async function load(){
 try{const r=await fetch('/api/state/');if(r.status===403){throw Error('Account is unverified, suspended or signed out. Ask an administrator to verify your account.');}if(!r.ok)throw Error('Unable to read workspace. Sign in again or retry.');state=await r.json();render();}
 catch(e){feedback(e.message,true);}
}
function render(){
 const r=state.me.role;
 $('#identity').textContent=`${state.me.username} · ${r}`;
 const tabs=[['catalogue','Materials & equipment'],['orders',r==='supervisor'?'Site reconciliation':'Orders & tracking'],['quotes','Quotations'],['rentals','Rental bookings']];
 if(r==='transporter')tabs.unshift(['jobs','Open delivery jobs']);
 if(r==='supplier')tabs.push(['listings','Manage listings']);
 if(r==='admin')tabs.push(['admin','Verification & audit']);
 if(!tabs.some(t=>t[0]===tab))tab=tabs[0][0];
 $('#tabs').innerHTML=tabs.map(([id,label])=>`<button data-tab="${id}" class="${id===tab?'active':''}">${esc(label)}</button>`).join('');
 $('#content').innerHTML=({catalogue,orders,quotes,rentals,jobs,listings,admin}[tab])();
}
function catalogue(){
 const buyer=state.me.role==='purchaser';
 const cards=state.listings.map(l=>`<article><span class="badge">${esc(l.kind==='sale'?'MATERIAL / EQUIPMENT SALE':'GENERAL EQUIPMENT RENTAL')}</span><h2>${esc(l.name)}</h2><p class="muted">${esc(l.supplier)} · ${l.stock} ${l.kind==='sale'?'in stock':'units in fleet'}</p><p class="money">${money(l.price_ngwee)} <small>per ${esc(l.unit)}</small></p>${l.kind==='rental'?`<p>Refundable deposit record: ${money(l.deposit_ngwee)} per unit</p>`:''}${buyer?(l.kind==='sale'?form('cart',input('quantity','Cart quantity (0 removes)','number',state.cart.find(c=>c.listing_id===l.id)?.quantity||1,'min="0" required'),'Update cart',{listing:l.id})+`<details><summary>Request a supplier quotation</summary>${form('quote-request',input('quantity','Quantity','number',1,'min="1" required')+note(),'Request quote',{listing:l.id})}</details>`:`<details><summary>Check availability / book equipment</summary>${form('rental-book',input('starts_at','Start (Lusaka time)','datetime-local','','required')+input('ends_at','End (Lusaka time)','datetime-local','','required')+input('quantity','Units','number',1,'min="1" required'),'Book rental',{listing:l.id})}<button type="button" data-availability="${l.id}">Check this time range</button><p class="muted">Billed per started 24-hour day. Availability uses [start, end) time ranges. Check before booking.</p></details>`):''}</article>`).join('');
 const cart=buyer?`<section class="panel"><h2>Your multi-supplier cart</h2>${state.cart.length?`<ul>${state.cart.map(c=>{const l=state.listings.find(l=>l.id===c.listing_id);return `<li>${esc(l?.name||'Unavailable listing')} × ${c.quantity} · ${l?money(l.price_ngwee*c.quantity):'refresh availability'}</li>`;}).join('')}</ul><p>Orders split by supplier. Prices and stock are checked by the server at checkout. Transport charges are arranged separately in the order thread.</p>${form('checkout',site()+supervisor(),'Place supplier orders',{key:crypto.randomUUID()})}`:empty('Add materials from one or more suppliers. Rental bookings are separate.')}</section>`:'';
 return cart+`<h2>Verified supplier catalogue</h2><div class="row"><label>Search materials or equipment<input id="catalogue-search" type="search" placeholder="Cement, generator, pump…"></label></div><div class="grid" id="listing-cards">${cards||empty('No active listings.')}</div>`;
}
function orderCard(o){
 const r=state.me.role;let controls='';
 if(r==='supplier'&&o.supplier===state.me.username){
  if(o.state==='PLACED')controls+=form('supplier-order','','Accept order',{id:o.id,operation:'ACCEPTED'})+form('supplier-order',note('Reason for rejection',true),'Reject & release stock',{id:o.id,operation:'REJECTED'});
  if(o.state==='ACCEPTED')controls+=form('supplier-order','','Ready for collection',{id:o.id,operation:'READY'});
 }
 if(r==='admin'){
  if(o.payment_status==='PENDING'&&o.state!=='REJECTED')controls+=form('payment',reference(),'Record manual payment',{id:o.id,operation:'record'});
  if(o.payment_status==='REFUND_PENDING')controls+=form('payment',reference(),'Record manual refund',{id:o.id,operation:'refund'});
 }
 const d=o.delivery;
 if(r==='transporter'&&d?.transporter===state.me.username){
  const next={ASSIGNED:'PICKED_UP',PICKED_UP:'IN_TRANSIT',IN_TRANSIT:'ARRIVED'}[d.state];
  if(next)controls+=form('delivery',note('Pickup / delivery checkpoint note',true)+select('source','Location source',[['status-only','Status only — no location'],['demo','Demo coordinates (simulated)'],['consented-gps','Consented location reported by transporter']])+`<div class="row">${input('latitude','Latitude','number','','step="any"')}${input('longitude','Longitude','number','','step="any"')}</div><label><input type="checkbox" name="consent">I consent to share the coordinates with order participants.</label>`,`Record ${next.replaceAll('_',' ').toLowerCase()}`,{id:d.id,state:next});
  if(['PICKED_UP','IN_TRANSIT'].includes(d.state))controls+=form('delivery',note('Additional checkpoint',true),'Add status checkpoint',{id:d.id,state:'CHECKPOINT',source:'status-only'});
 }
 if(r==='supervisor'&&o.supervisor===state.me.username&&o.state==='ARRIVED'){
  const fields=o.lines.map(l=>`<fieldset data-receipt-line="${l.id}"><legend>${esc(l.name)} · ordered ${l.quantity} ${esc(l.unit)}</legend><div class="row">${input(`received_${l.id}`,'Actually received','number',l.quantity,`min="0" max="${l.quantity}" required`)}${select(`condition_${l.id}`,'Condition',[['good','Good'],['damaged','Damaged'],['missing','Missing']])}</div>${input(`notes_${l.id}`,'Shortage / damage explanation (required for discrepancies)')}</fieldset>`).join('');
  controls+=`<details open><summary>Reconcile delivery and sign site receipt</summary>${form('receipt',fields+note('Overall inspection notes')+input('photos','Evidence photos (optional, max 4 × 2 MB)','file','','accept="image/jpeg,image/png,image/webp" multiple')+'<label><input type="checkbox" name="attest" required>I inspected these quantities and conditions at the site.</label>','Sign inspection receipt',{id:o.id})}</details>`;
 }
 return `<article><span class="badge">BE-${o.id} · ${esc(o.state)}</span><h2>${esc(o.site)}</h2><p>${esc(o.supplier)} → ${esc(o.purchaser)} · Supervisor: ${esc(o.supervisor)}</p><p class="money">${money(o.total_ngwee)}</p><p>Payment: <strong>${esc(o.payment_status)}</strong> ${esc(o.payment_reference)}<br><small>No payment gateway or money transfer is connected.</small></p><table><thead><tr><th>Material</th><th>Ordered</th><th>Unit price</th></tr></thead><tbody>${o.lines.map(l=>`<tr><td>${esc(l.name)}</td><td>${l.quantity} ${esc(l.unit)}</td><td>${money(l.unit_price_ngwee)}</td></tr>`).join('')}</tbody></table>${controls}${d?`<details open><summary>Delivery tracking · ${esc(d.state)}</summary><p>Transporter: ${esc(d.transporter||'Awaiting job acceptance')}</p><div class="timeline">${d.checkpoints.map(c=>`<p><strong>${esc(c.state)}</strong> · ${date(c.created_at)}<br>${esc(c.note)}<br><small>Location source: ${esc(c.source)}${c.latitude!==null?` · ${c.latitude}, ${c.longitude}`:''}</small></p>`).join('')||'<p>No checkpoints yet.</p>'}</div><small>Manually reported updates; no automatic or independently verified live GPS.</small></details>`:''}${o.receipt?`<div class="notice">Site inspection: ${o.receipt.discrepancies?'Discrepancies recorded — follow up with supplier':'Quantities and conditions reconciled'} · ${date(o.receipt.created_at)}</div><p><a href="/receipt/${o.id}/" target="_blank" rel="noopener">Open printable signed receipt & evidence</a></p>`:''}<details><summary>Supplier / site / transport communication</summary>${o.messages.map(m=>`<p><strong>${esc(m.author)}</strong> <small>${date(m.created_at)}</small>${esc(m.text)}</p>`).join('')||'<p>No messages yet.</p>'}${form('message',input('text','Message to order participants','text','','required maxlength="1000"'),'Send to order thread',{id:o.id})}</details><details><summary>Auditable event trail (${o.events.length})</summary>${o.events.map(e=>`<p>${date(e.created_at)} · ${esc(e.actor)} · <strong>${esc(e.action)}</strong><small>${esc(JSON.stringify(e.detail))}</small></p>`).join('')}</details></article>`;
}
function orders(){return `<p>Tracking and receipts are visible only to the order’s purchaser, supplier, assigned transporter, assigned supervisor and administrators.</p>${state.orders.map(orderCard).join('')||empty('No orders assigned to your account yet.')}`;}
function quotes(){return state.quotes.map(q=>`<article><span class="badge">QUOTE ${q.id} · ${esc(q.state)}</span><h2>${esc(q.listing)} × ${q.quantity}</h2><p>${esc(q.purchaser)} ↔ ${esc(q.supplier)}</p><p>${esc(q.notes)}</p><p>${esc(q.response)}</p>${q.unit_price_ngwee?`<p>Offered unit price: ${money(q.unit_price_ngwee)} · Total: ${money(q.unit_price_ngwee*q.quantity)}</p>`:''}${state.me.role==='supplier'&&q.state==='REQUESTED'?form('quote',input('price_ngwee','Offered unit price (integer ngwee)','number','','min="1" required')+note('Supplier response'),'Send offer',{id:q.id,operation:'reply'}):''}${state.me.role==='purchaser'&&q.state==='OFFERED'?form('quote',site()+supervisor(),'Accept offer & reserve stock',{id:q.id,operation:'accept'}):''}<small>Stock is reserved on acceptance, not while requesting a quote. No automatic expiry in this demo.</small></article>`).join('')||empty('Request a quotation from a sale listing.');}
function rentals(){return '<p>Rentals are separate from material purchases. Deposits are manual records, and return inspections do not automatically refund money.</p>'+state.rentals.map(r=>{
 let controls='';const role=state.me.role;
 if(role==='admin'&&r.deposit_status==='PENDING')controls+=form('rental',reference(),'Record manual deposit',{id:r.id,operation:'deposit'});
 if(role==='admin'&&r.deposit_status==='REFUND_PENDING')controls+=form('rental',reference(),'Record manual deposit refund',{id:r.id,operation:'refund'});
 if(role==='supplier'&&r.state==='BOOKED')controls+=form('rental','','Record equipment collection',{id:r.id,operation:'collect'});
 if(role==='supplier'&&r.state==='COLLECTED')controls+=form('rental',note('Return condition / damages',true),'Record inspected return',{id:r.id,operation:'return'});
 if(role==='purchaser'&&r.state==='BOOKED')controls+=form('rental','','Cancel booking',{id:r.id,operation:'cancel'});
 return `<article><span class="badge">RENTAL ${r.id} · ${esc(r.state)}</span><h2>${esc(r.name)} × ${r.quantity}</h2><p>${esc(r.supplier)} → ${esc(r.purchaser)}<br>${date(r.starts_at)} → ${date(r.ends_at)}</p><p class="money">${money(r.total_ngwee)} <small>Rental charge (manual arrangement)</small></p><p>Deposit: ${money(r.deposit_ngwee)} · ${esc(r.deposit_status)}</p>${controls}${r.returned_at?`<p>Returned ${date(r.returned_at)}<br>Inspection: ${esc(r.return_condition)}</p>`:''}</article>`;
 }).join('')+(state.rentals.length?'':empty('Book a generator, pump or power tool from the catalogue.'));}
function jobs(){return '<p>Accepting a job reveals the site and authorized order thread. Collection checkpoints precede arrival; only the site supervisor can confirm receipt.</p>'+state.jobs.map(j=>`<article><span class="badge">OPEN JOB ${j.id} · BE-${j.order_id}</span><h2>Collect from ${esc(j.supplier)}</h2><ul>${j.materials.map(m=>`<li>${esc(m.name)} × ${m.quantity} ${esc(m.unit)}</li>`).join('')}</ul>${form('accept-job','','Accept delivery job',{id:j.id})}</article>`).join('')+(state.jobs.length?'':empty('No open delivery jobs. Check Orders & tracking for your accepted jobs.'));}
function listings(){const fields=l=>input('name','Listing name','text',l?.name||'','required maxlength="120"')+input('unit','Unit / rental billing period','text',l?.unit||'each','required maxlength="24"')+`<div class="row">${input('price_ngwee','Price per unit (ngwee)','number',l?.price_ngwee||'','min="1" required')}${input('stock','Available stock / total rental units','number',l?.stock??0,'min="0" required')}${input('deposit_ngwee','Rental deposit per unit (ngwee)','number',l?.deposit_ngwee||0,'min="0" required')}</div>`;
 return `<article><h2>Create material or equipment listing</h2><p>100 ngwee = ZMW 1. Rental capacity cannot change while bookings are active.</p>${form('listing',select('kind','Listing type',[['sale','Sale'],['rental','General equipment rental']])+fields(),'Create listing')}</article>`+state.listings.filter(l=>l.supplier_id===state.me.id).map(l=>`<article><h2>${esc(l.name)}</h2>${form('listing',fields(l),'Save listing',{id:l.id})}</article>`).join('');}
function admin(){return `<article><h2>Create team / pilot account</h2><p>Roles are assigned by administrators. New accounts require verification before use.</p>${form('account',input('username','Username','text','','required pattern="[a-zA-Z0-9_]+"')+input('password','Initial password (at least 12 characters)','password','','required minlength="12"')+select('role','Role',['purchaser','supplier','transporter','supervisor'].map(r=>[r,r])),'Create unverified account')}</article><article><h2>Account verification</h2>${state.accounts.map(a=>`<div class="row"><p><strong>${esc(a.user__username)}</strong> · ${esc(a.role)} · ${a.verified?'Verified':'Unverified / suspended'}</p>${a.role!=='admin'?form('verify','',''+(a.verified?'Suspend access':'Verify account'),{id:a.user_id,verified:a.verified?'false':'true'}):''}</div>`).join('')}</article><article><h2>Audit trail · latest 200 events</h2><p>Application accounts cannot edit or delete these records. A database administrator still has database access.</p>${state.audit.map(e=>`<p>#${e.id} · ${date(e.created_at)} · ${esc(e.actor)} · <strong>${esc(e.action)}</strong> · ${esc(e.target)}<small>${esc(JSON.stringify(e.detail))}</small></p>`).join('')||'<p>No events yet.</p>'}</article>`;}
document.addEventListener('click',async e=>{
 const t=e.target.closest('[data-tab]');if(t){tab=t.dataset.tab;render();return;}
 const a=e.target.closest('[data-availability]');if(a){try{const f=a.parentElement.querySelector('form');const data=Object.fromEntries(new FormData(f));const result=await api('rental-availability',data);feedback(`${result.available} units available · ${result.billing_days} billing day(s).`);}catch(error){feedback(error.message,true);}}
});
document.addEventListener('input',e=>{if(e.target.id==='catalogue-search'){const q=e.target.value.toLowerCase();document.querySelectorAll('#listing-cards>article').forEach(c=>{c.hidden=!c.textContent.toLowerCase().includes(q);});}});
document.addEventListener('submit',async e=>{
 const f=e.target.closest('form[data-action]');if(!f)return;e.preventDefault();const button=f.querySelector('button');button.disabled=true;
 try{let data=Object.fromEntries(new FormData(f));const action=f.dataset.action;let multi=false;
  if(action==='receipt'){const fd=new FormData(f);const lines=[...f.querySelectorAll('[data-receipt-line]')].map(el=>{const id=el.dataset.receiptLine;return {line:id,received:data[`received_${id}`],condition:data[`condition_${id}`],notes:data[`notes_${id}`]};});fd.set('lines',JSON.stringify(lines));data=fd;multi=true;}
  const result=await api(action,data,multi);if(action==='accept-job')tab='orders';if(['checkout','quote'].includes(action)&&result.order_ids)tab='orders';if(action==='rental-book')tab='rentals';
  feedback(result.message||`Saved successfully.${result.order_ids?' Orders: '+result.order_ids.join(', '):''}`);await load();
 }catch(error){feedback(error.message,true);button.disabled=false;}
});
$('#refresh').addEventListener('click',load);load();
