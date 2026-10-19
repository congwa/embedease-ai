/** Local business state and render adapters; no backend calls or production writes. */
(() => {
  const state = { conversations: structuredClone(demoData.conversations), selectedId: 'c01', filter: 'all', query: '', sort: 'priority', special: null, drafts: {}, notes: {}, mobileView: 'queue', detailsOpen: false };
  const $ = (id) => document.getElementById(id);
  const escape = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const icon = (name, classes = '') => `<i data-lucide="${name}" class="${classes}" aria-hidden="true"></i>`;
  const selected = () => state.conversations.find(c => c.id === state.selectedId);
  const labels = { pending: '待接入', human: '人工处理中', ai: 'AI 处理中', resolved: '已解决' };
  const tones = { pending:'warning', human:'success', ai:'neutral', resolved:'success' };
  const badge = (text, tone='neutral') => `<span class="status-badge ${tone}">${escape(text)}</span>`;
  const avatar = (c, extra='') => `<span class="avatar ${c.avatar} ${extra}">${c.initial}${c.online?'<span class="online"></span>':''}</span>`;
  const stats = (list) => ({pending:list.filter(c=>c.status==='pending').length,human:list.filter(c=>c.status==='human').length,unread:list.reduce((n,c)=>n+c.unread,0),hot:list.filter(c=>c.heat>=80&&c.status!=='resolved').length});
  /** Match queue search/filter in data, keeping global load independent of the current view. */
  function filtered() {
    const query=state.query.toLowerCase();
    return state.conversations.filter(c=>(state.filter==='all'||c.status===state.filter)&&(!query||[c.name,c.topic,c.order].join(' ').toLowerCase().includes(query))&&(!state.special||(state.special==='unread'?c.unread>0:c.heat>=80&&c.status!=='resolved'))).sort((a,b)=>state.sort==='time'?a.minutes-b.minutes:(({pending:0,human:1,ai:2,resolved:3}[a.status]-{pending:0,human:1,ai:2,resolved:3}[b.status])||b.heat-a.heat));
  }
  function paintIcons(){lucide.createIcons();}
  /** Basecoat owns toast life cycle and tab selection; native JS owns demo business state. */
  function toast(title, description='', category='success') {
    $('live-status').textContent = `${title}${description?'，'+description:''}`;
    $('toaster').toast?.({title:escape(title), description:escape(description), category, duration:3500});
  }
  function renderMetrics() {
    const totals=stats(state.conversations);
    $('global-metrics').innerHTML=[['待接入',totals.pending,'headphones','pending','warning'],['人工处理中',totals.human,'user-round-check','human','success'],['未读消息',totals.unread,'mail','unread','neutral'],['高热会话',totals.hot,'flame','hot','warning']].map(([label,value,glyph,key,tone],i)=>`<button data-metric="${key}" class="flex min-w-0 items-center gap-3 rounded-md py-1 text-left ${i?'border-l border-border pl-3 md:pl-6':''} hover:bg-muted" title="查看${label}"><span class="hidden size-9 shrink-0 items-center justify-center rounded-lg ${tone==='warning'?'bg-[var(--warning-soft)] text-[var(--warning)]':tone==='success'?'bg-accent text-primary':'bg-muted text-muted-foreground'} lg:flex">${icon(glyph)}</span><span class="min-w-0"><span class="block whitespace-nowrap text-[11px] text-muted-foreground md:text-[12px]">${label}</span><span class="mt-0.5 block text-[23px] font-semibold leading-7 tracking-tight tabular-nums">${value.toString().padStart(2,'0')}</span></span></button>`).join('');
  }
  function renderQueue() {
    const rows=filtered(); const totals=state.conversations;
    $('queue-total').textContent=totals.length;
    $('queue-filters').innerHTML=[['all','全部'],['pending','待接入'],['human','人工'],['ai','AI']].map(([key,label])=>`<button class="queue-filter" data-filter="${key}" aria-pressed="${state.filter===key&&!state.special}">${label}<span class="count-label">${key==='all'?totals.length:totals.filter(c=>c.status===key).length}</span></button>`).join('');
    $('result-summary').innerHTML=`${rows.length} 个会话${state.special?` <button class="ml-1 text-primary underline underline-offset-2" data-action="clear-filter">${state.special==='unread'?'仅未读':'仅高热'} · 清除</button>`:''}`;
    $('queue-list').innerHTML=rows.length?rows.map(c=>`<button class="queue-row" data-conversation="${c.id}" aria-current="${state.selectedId===c.id}" aria-label="${c.name}，${c.topic}，${labels[c.status]}，${c.unread}条未读">${avatar(c)}<span class="min-w-0 flex-1"><span class="flex items-center justify-between gap-2"><span class="text-[14px] font-semibold">${c.name}</span><span class="shrink-0 text-[11px] text-muted-foreground tabular-nums">${c.time}</span></span><span class="mt-1 block truncate text-[13px] text-muted-foreground">${c.topic}</span><span class="mt-2.5 flex items-center justify-between gap-2"><span class="flex items-center gap-1.5">${badge(labels[c.status],tones[c.status])}${c.heat>=80&&c.status!=='resolved'?`<span class="inline-flex items-center gap-0.5 text-[11px] font-medium text-[var(--warning)]">${icon('flame','size-3')}${c.heat}</span>`:''}</span>${c.unread?`<span class="unread-dot">${c.unread}</span>`:c.online?'<span class="text-[11px] text-primary">在线</span>':''}</span></span></button>`).join(''):`<div class="empty-queue">${icon('search','mx-auto mb-3')}<p class="mb-2 text-sm font-medium text-foreground">没有找到相关会话</p><p class="text-xs leading-5">试试其他关键词，或清除当前筛选。</p><button class="btn mt-4" data-variant="outline" data-size="sm" data-action="clear-filter">清除筛选</button></div>`;
    const values=[['用户',rows.length,'当前用户'],['活跃',rows.filter(c=>c.status!=='resolved').length,'活跃客诉'],['高风险',rows.filter(c=>c.risk==='high').length,'高风险'],['返工',rows.filter(c=>c.score<70).length,'返工/阻塞'],['在线',rows.filter(c=>c.online).length,'在线用户']];
    $('filtered-metrics').innerHTML=values.map(([label,n,full])=>`<div title="${full}：${n}" aria-label="${full}：${n}"><span class="block text-[15px] font-semibold tabular-nums">${n}</span><span class="mt-0.5 block whitespace-nowrap text-[11px] text-muted-foreground">${label}</span></div>`).join('');
  }
  /** The same detail panel works as a desktop column and a small-screen information sheet. */
  function renderHeader() {
    const c=selected();
    $('conversation-header').innerHTML=`<div class="flex min-w-0 items-center gap-3"><button class="btn md:hidden" data-variant="ghost" data-size="icon-sm" data-action="back" aria-label="返回会话列表">${icon('arrow-left')}</button>${avatar(c)}<div class="min-w-0"><div class="flex items-center gap-2"><h2 class="text-[17px] font-semibold whitespace-nowrap">${c.name}</h2>${badge(labels[c.status],tones[c.status])}</div><p class="mt-1 truncate text-[11px] text-muted-foreground">${c.channel}<span class="mx-1.5">·</span>${c.online?'当前在线':'当前离线'}<span class="mx-1.5">·</span>${c.since}</p></div></div><div class="flex shrink-0 items-center gap-2"><button class="btn xl:hidden" data-variant="ghost" data-size="icon-sm" data-action="open-details" aria-label="查看会话详情" aria-expanded="${state.detailsOpen}">${icon('panel-right')}</button>${c.status==='human'?`<button class="btn" data-variant="outline" data-size="sm" data-action="resolve">${icon('check','size-3.5')}标记解决</button>`:c.status==='resolved'?`<button class="btn" data-variant="outline" data-size="sm" data-action="takeover">重新接入</button>`:`<button class="btn" data-size="sm" data-action="takeover">${icon('headphones','size-3.5')}接入会话</button>`}</div>`;
    $('handoff-notice').innerHTML=c.status==='human'?`<div class="flex items-center justify-between text-[12px]"><span class="flex items-center gap-2 text-primary">${icon('user-round-check','size-3.5')}你已接入，正在为 ${c.name} 服务</span><span class="text-muted-foreground">已分配给 ${demoData.operator}</span></div>`:c.status==='resolved'?`<div class="flex items-center gap-2 text-[12px] text-primary">${icon('circle-check','size-3.5')}会话已解决，处理结果已记录</div>`:`<div class="flex items-center gap-2 text-[12px] text-muted-foreground">${icon('sparkles','size-3.5')}<span>${c.status==='pending'?'AI 已完成初步核查，等待人工确认处理方案':'AI 正在服务，可随时接入协助'}</span></div>`;
    const canReply=c.status==='human'; $('reply-input').disabled=!canReply; $('send-reply').disabled=!canReply; $('reply-input').placeholder=canReply?'输入回复，帮助客户解决当前问题…':c.status==='resolved'?'当前会话已解决，重新接入后可继续回复…':'接入会话后，开始与客户沟通…'; $('reply-input').value=state.drafts[c.id]||''; $('composer-status').textContent=canReply?'人工服务中':c.status==='resolved'?'已解决':'接入后可回复';
  }
  function renderMessages() {
    const c=selected();
    $('messages').innerHTML=`<div class="flex items-center gap-4 py-1 text-[11px] text-muted-foreground"><span class="flex-1 border-t border-border"></span><span>今天 · 10 月 19 日</span><span class="flex-1 border-t border-border"></span></div>`+c.messages.map(m=>m.role==='system'?`<div class="flex items-center justify-center gap-1.5 text-center text-[11px] leading-5 text-muted-foreground">${icon(m.text.includes('接入')?'headphones':'circle-dot','size-3')}<span>${escape(m.text)}<span class="ml-2 opacity-75">${m.time}</span></span></div>`:`<div class="flex ${m.role==='customer'?'':'flex-row-reverse'} items-start gap-2.5">${m.role==='customer'?avatar(c):`<span class="flex size-7 shrink-0 items-center justify-center rounded-lg ${m.role==='ai'?'border border-border bg-card text-primary':'bg-primary text-primary-foreground'}">${icon(m.role==='ai'?'sparkles':'headphones','size-3.5')}</span>`}<div class="flex min-w-0 flex-1 flex-col ${m.role==='customer'?'items-start':'items-end'}"><p class="mb-1.5 flex items-center gap-2 text-[11px] text-muted-foreground"><span>${m.role==='customer'?c.name:m.role==='ai'?'AI 客服助手':`客服${demoData.operator}`}</span><time>${m.time}</time>${m.role==='ai'?'<span class="rounded border border-border px-1 text-[10px]">AI</span>':''}</p><div class="bubble ${m.role==='customer'?'':'outgoing'}"><p class="message-text">${escape(m.text)}</p>${m.attachment?`<div class="mt-3 flex items-center gap-3 rounded-lg border border-border bg-background p-3"><span class="flex size-11 items-center justify-center rounded-md border border-border bg-card text-muted-foreground">${icon('image')}</span><span class="min-w-0"><span class="block text-xs font-medium">商品破损照片.jpg</span><span class="mt-1 block text-[11px] text-muted-foreground">图片附件 · 演示占位</span></span>${icon('check','ml-auto size-3.5 text-primary')}</div>`:''}</div>${m.role==='agent'?'<span class="mt-1.5 text-[10px] text-muted-foreground">已发送</span>':''}</div></div>`).join('');
  }
  function renderDetails() {
    const c=selected();const riskText={low:'低风险',medium:'中风险',high:'高风险'};
    $('overview-panel').innerHTML=`<section class="details-section"><div class="mb-3 flex items-center justify-between"><h3 class="section-eyebrow !mb-0">当前问题单</h3><span class="text-[11px] text-muted-foreground">#TK-108${c.id.slice(-1)}</span></div><p class="mb-3 text-[14px] font-semibold leading-6">${c.topic}</p><div class="mb-4 flex flex-wrap gap-1.5">${badge(c.status==='resolved'?'已解决':c.ticket,c.status==='resolved'?'success':'neutral')}${badge(riskText[c.risk],c.risk==='high'?'danger':c.risk==='medium'?'warning':'success')}</div><dl class="space-y-3"><div class="flex justify-between gap-3"><dt class="detail-label">负责岗位</dt><dd class="detail-value">${['human','resolved'].includes(c.status)?'人工客服 · 小乔':c.status==='pending'?'等待人工分配':'AI 客服助手'}</dd></div><div class="flex justify-between gap-3"><dt class="detail-label">质量审查</dt><dd class="detail-value ${c.score<80?'text-[var(--warning)]':'text-primary'}">${c.score<80?'待复核':'已通过'} <span class="ml-1 tabular-nums">${c.score} 分</span></dd></div></dl></section>
      <section class="details-section"><h3 class="section-eyebrow flex items-center gap-1.5">${icon('sparkles','size-3.5 text-primary')}AI 交接摘要</h3><p class="text-[12px] leading-[1.9] text-muted-foreground">${c.summary}</p><div class="mt-3 rounded-lg border border-[var(--suggestion-border)] bg-accent p-3"><p class="mb-1 flex items-center gap-1 text-[11px] font-semibold text-accent-foreground">${icon('lightbulb','size-3')}建议下一步</p><p class="text-[12px] leading-[1.8] text-accent-foreground">${c.suggestion}</p><button class="mt-2 text-[11px] font-semibold text-primary underline underline-offset-4" data-action="use-suggestion">使用建议回复</button></div></section>
      <section class="details-section"><h3 class="section-eyebrow flex items-center justify-between">关联订单 ${icon('package','size-3.5 text-muted-foreground')}</h3><p class="mb-1 text-[12px] font-medium leading-5">${c.product}</p><p class="mb-3 text-[11px] text-muted-foreground tabular-nums">${c.order}</p><div class="flex items-center justify-between">${badge(c.orderStatus)}<span class="text-[14px] font-semibold tabular-nums">${c.price==='—'?'—':`¥ ${c.price}`}</span></div></section>
      <section class="details-section"><h3 class="section-eyebrow">客户信息</h3><div class="mb-4 flex flex-wrap gap-1.5">${c.tags.map(t=>badge(t)).join('')}</div><dl class="space-y-3"><div class="flex justify-between"><dt class="detail-label">首次访问</dt><dd class="detail-value">${c.customerSince}</dd></div><div class="flex justify-between"><dt class="detail-label">历史订单</dt><dd class="detail-value">${c.orders} 笔</dd></div><div class="flex justify-between"><dt class="detail-label">累计消费</dt><dd class="detail-value tabular-nums">¥ ${c.spent}</dd></div></dl></section>
      <section><h3 class="section-eyebrow">内部备注</h3><label class="sr-only" for="internal-note">当前客户内部备注</label><textarea id="internal-note" class="textarea w-full resize-none text-xs" rows="2" placeholder="记录仅团队可见的处理要点…">${escape(state.notes[c.id]||'')}</textarea><button class="btn mt-2 w-full" data-size="sm" data-variant="outline" data-action="save-note">保存备注</button></section>`;
    const activities=[['12:42','会话创建',`${c.name} 从${c.channel}发起咨询`],['12:43','AI 开始处理','已识别问题类型并检索售后规则'],['12:45','订单与信息核查',c.order==='—'?'当前无关联订单':`已关联订单 ${c.order}`],['12:46',c.status==='human'?'人工已接入':c.status==='resolved'?'会话已解决':'AI 交接已就绪',c.status==='human'?'小乔已接入并开始处理':c.status==='resolved'?'处理结果已保存':c.suggestion]];
    $('activity-panel').innerHTML=`<p class="mb-6 text-[11px] leading-5 text-muted-foreground">关键处理节点，帮助团队了解会话进展。</p>${activities.map(([time,title,text])=>`<div class="activity-item"><div class="mb-1 flex justify-between"><h3 class="text-xs font-semibold">${title}</h3><time class="text-[11px] text-muted-foreground">${time}</time></div><p class="text-[12px] leading-6 text-muted-foreground">${text}</p></div>`).join('')}`;
  }
  function renderAll(){ renderMetrics();renderQueue();renderHeader();renderMessages();renderDetails();paintIcons(); }
  function updateQueue(){renderMetrics();renderQueue();paintIcons();}
  function clearFilter(){state.filter='all';state.special=null;state.query='';$('queue-search').value='';updateQueue();}
  function setDetails(open){state.detailsOpen=open;$('app').dataset.detailsOpen=String(open);$('details-scrim').hidden=!open;document.querySelector('[data-action="open-details"]')?.setAttribute('aria-expanded',String(open));if(open)$('details-heading').focus();else document.querySelector('[data-action="open-details"]')?.focus();}
  /** Read the draft from state so switching conversations never leaks a reply to another customer. */
  function send() {
    const c=selected(), text=(state.drafts[c.id]||'').trim();
    if(c.status!=='human'){toast('请先接入会话','当前回复不会发送','info');return;}
    if(!text){$('reply-error').textContent='请输入回复内容后再发送。';$('reply-error').classList.remove('hidden');$('reply-input').focus();return;}
    if(text.length>2000){$('reply-error').textContent='回复内容最多 2000 字。';$('reply-error').classList.remove('hidden');return;}
    c.messages.push({role:'agent',text,time:'12:49'});state.drafts[c.id]='';c.time='12:49';c.minutes=0;renderHeader();renderMessages();renderQueue();paintIcons();$('reply-error').classList.add('hidden');$('message-scroll').scrollTop=$('message-scroll').scrollHeight;
    if(!matchMedia('(prefers-reduced-motion: reduce)').matches&&window.Motion)Motion.animate($('messages').lastElementChild,{opacity:[0,1],y:[7,0]},{duration:.18});
    toast('回复已发送','仅更新当前演示会话');$('reply-input').focus();
  }
  function insertReply(suggestion=false){const c=selected();if(c.status!=='human'){toast('接入后可使用建议回复','请先点击「接入会话」','info');return;}state.drafts[c.id]=suggestion?`您好，已核实您的反馈。${c.suggestion}`:'您好，我是客服小乔，已经了解您的情况，我来协助您处理。';$('reply-input').value=state.drafts[c.id];if(state.detailsOpen)setDetails(false);$('reply-input').focus();}
  document.addEventListener('click',event=>{
    const row=event.target.closest('[data-conversation]');
    if(row){state.selectedId=row.dataset.conversation;state.mobileView='conversation';$('app').dataset.mobileView='conversation';$('reply-error').classList.add('hidden');renderQueue();renderHeader();renderMessages();renderDetails();paintIcons();$('message-scroll').scrollTop=0;return;}
    const filter=event.target.closest('[data-filter]');if(filter){state.filter=filter.dataset.filter;state.special=null;updateQueue();return;}
    const metric=event.target.closest('[data-metric]');if(metric){state.query='';$('queue-search').value='';const key=metric.dataset.metric;state.filter=['pending','human'].includes(key)?key:'all';state.special=['unread','hot'].includes(key)?key:null;state.mobileView='queue';$('app').dataset.mobileView='queue';updateQueue();return;}
    const action=event.target.closest('[data-action]')?.dataset.action;if(!action)return;
    const c=selected();
    if(action==='takeover'){c.status='human';c.unread=0;c.since='刚刚接入';c.ticket='人工处理中';c.messages.push({role:'system',text:'客服小乔已接入会话',time:'12:49'});renderAll();$('reply-input').focus();toast('已接入会话',`正在为${c.name}服务`);}
    if(action==='send')send();
    if(action==='quick-reply')insertReply();
    if(action==='use-suggestion')insertReply(true);
    if(action==='resolve'){c.status='resolved';c.ticket='已解决';c.since='已解决';c.unread=0;c.messages.push({role:'system',text:'小乔已将当前会话标记为解决',time:'12:50'});renderAll();toast('会话已标记为解决','可点击「重新接入」继续处理');}
    if(action==='save-note'){state.notes[c.id]=$('internal-note').value;toast('备注已保存','保留在当前演示会话中，刷新页面后重置');}
    if(action==='refresh'){const button=event.target.closest('button');button.disabled=true;$('sync-status').textContent='正在同步…';setTimeout(()=>{button.disabled=false;$('sync-status').textContent='刚刚更新';updateQueue();toast('队列已更新','当前为写死的示例数据');},650);}
    if(action==='back'){state.mobileView='queue';$('app').dataset.mobileView='queue';}
    if(action==='open-details')setDetails(true);if(action==='close-details')setDetails(false);
    if(action==='clear-filter')clearFilter();
    if(action==='attachment')toast('附件演示','示例会话已包含附件样式，此预览不上传文件','info');
    if(action==='help')toast('客服工作台设计预览','可筛选、搜索、切换会话、接入、回复及标记解决；刷新重置','info');
    if(action==='navigation')toast('当前为客服工作台预览','其他产品模块不在本次静态设计范围内','info');
  });
  $('queue-search').addEventListener('input',e=>{state.query=e.target.value;renderQueue();paintIcons();});
  $('queue-sort').addEventListener('change',e=>{state.sort=e.target.value;renderQueue();paintIcons();});
  $('reply-input').addEventListener('input',e=>{state.drafts[state.selectedId]=e.target.value;$('reply-error').classList.add('hidden');});
  document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();state.mobileView='queue';$('app').dataset.mobileView='queue';$('queue-search').focus();}if((e.metaKey||e.ctrlKey)&&e.key==='Enter'&&document.activeElement===$('reply-input')){e.preventDefault();send();}if(e.key==='Escape'&&state.detailsOpen)setDetails(false);});
  document.addEventListener('DOMContentLoaded',()=>{renderAll();});
})();
