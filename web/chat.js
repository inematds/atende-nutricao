'use strict';
const $ = id => document.getElementById(id);
let phone = '';
function bubble(author, text, mine = false) {
  const item = document.createElement('div'); item.className = 'message' + (mine ? ' mine' : '');
  const title = document.createElement('strong'); title.textContent = author;
  item.append(title, document.createTextNode(text)); $('messages').append(item); item.scrollIntoView({block:'nearest'});
}
$('identity').onsubmit = event => {
  event.preventDefault(); phone = $('telefone').value.trim();
  if (!/^(?:55)?\d{10,11}$/.test(phone.replace(/\D/g,''))) { $('chat-status').textContent='Informe um telefone válido com DDD.'; return; }
  $('identity').hidden=true; $('conversation').hidden=false; $('identity-label').textContent='Conversa de ' + phone;
  $('chat-status').textContent=''; $('texto').focus();
};
$('change-phone').onclick=()=>{phone=''; $('messages').replaceChildren(); $('texto').value=''; $('conversation').hidden=true; $('identity').hidden=false; $('telefone').focus();};
$('send').onsubmit=async event=>{
  event.preventDefault(); const text=$('texto').value.trim(); if(!text)return;
  const button=$('send').querySelector('button'); button.disabled=true; $('change-phone').disabled=true; $('chat-status').textContent='Enviando…';
  try {
    const response=await fetch('/api/mensagens',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({telefone:phone,texto:text})});
    const data=await response.json(); if(!response.ok)throw new Error(data.erro || 'Mensagem não aceita.');
    bubble('Você',text,true); data.respostas.forEach(t=>bubble('Consultório',t)); $('texto').value='';
    $('chat-status').textContent=data.respostas.length?'':'Mensagem recebida. Seu atendimento está com a equipe.';
  } catch(error){$('chat-status').textContent='Não foi possível confirmar o envio: '+error.message+' Sua mensagem foi mantida. Verifique antes de reenviar.';}
  finally{button.disabled=false; $('change-phone').disabled=false; $('texto').focus();}
};
