(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const root = $('#app');
  const BASE = String(window.PROMPT_WAR_CONFIG?.apiBase || '').replace(/\/$/, '');
  const S = { user:null, csrf:'', data:null, round:null, workspace:null, overview:null, queue:[], results:[], audit:[],
    draft:null, viewSubmission:null, entryDrafts:{}, practiceEntry:null, receipt:null, practice:null, tab:'', offset:0, busy:false, dirty:false, openSubmission:null };
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const title = value => String(value || '').replaceAll('_',' ').replace(/\b\w/g, c => c.toUpperCase());
  const time = value => value ? new Date(value).toLocaleString() : '—';
  const badge = (value, good=false) => `<span class="badge ${good ? 'good' : ''}">${esc(title(value))}</span>`;
  const button = (label, action, extra='', classes='') => `<button type="button" class="button ${classes}" data-action="${action}" ${extra}>${label}</button>`;
  const field = (label,name,value='',type='text',extra='') => `<div class="field"><label for="${name}">${esc(label)}</label><input id="${name}" name="${name}" type="${type}" value="${esc(value)}" ${extra}></div>`;
  const area = (label,name,value='',extra='') => `<div class="field"><label for="${name}">${esc(label)}</label><textarea id="${name}" name="${name}" ${extra}>${esc(value)}</textarea></div>`;
  const readBlock = (label,text) => text ? `<h3>${esc(label)}</h3><pre class="pre">${esc(text)}</pre>` : '';
  const now = () => Date.now()+S.offset;
  const bulkPreviews = new WeakMap();

  function bulkImportForm() {
    return `<div class="card"><h2>Bulk import participants</h2><p class="muted">Choose a UTF-8 CSV and enter its column headers. Up to two members per team, 22 teams total. The shared password applies to new accounts; existing accounts join their team with their current password. Admin and staff accounts are never changed.</p><form id="bulkParticipantForm"><div class="field"><label for="participant_csv">CSV file (64 KB maximum)</label><input id="participant_csv" name="participant_csv" type="file" accept=".csv,text/csv" required></div>${field('Email column header','email_column','email','text','required maxlength="200"')}${field('Team name column header','team_column','team_name','text','required maxlength="200"')}${field('Shared participant password','bulk_password','','password','autocomplete="new-password" minlength="12" maxlength="200"')}<p class="muted small-text">Enter one shared password here, or include a password column with the same value on every row. Use at least 12 characters. Passwords are not saved in participant records.</p><button class="button primary" type="submit">Preview import</button><div data-bulk-report aria-live="polite"></div></form></div>`;
  }

  function bulkReport(form, reply) {
    form.querySelector('[data-bulk-report]').innerHTML = `<h3>${reply.preview?'Preview — no changes made':'Import results'}</h3><div class="table-wrap"><table><thead><tr><th>Row</th><th>Email</th><th>Team</th><th>Status</th></tr></thead><tbody>${reply.rows.map(r=>`<tr><td>${r.row}</td><td>${esc(r.email)}</td><td>${esc(r.team_name)}</td><td>${esc(title(r.status))}${r.message?`<br>${esc(r.message)}`:''}</td></tr>`).join('')}</tbody></table></div><p class="muted small-text">Existing accounts are enrolled with their current password. Already enrolled: unchanged. Conflict: existing membership cannot be replaced.</p>`;
  }

  function clearPrivateState() {
    S.refreshGeneration=(S.refreshGeneration || 0)+1;
    Object.assign(S,{user:null,data:null,round:null,tab:'',draft:null,viewSubmission:null,entryDrafts:{},practiceEntry:null,practice:null,
      dirty:false,workspace:null,overview:null,queue:[],results:[],audit:[],bank:[],assignments:[],receipt:null});
  }

  function notify(message, kind='error') {
    const el = $('#status');
    el.hidden = false; el.className = 'status '+kind; el.textContent = message;
  }

  async function api(path, options={}) {
    const {blob=false,...request} = options;
    const headers = {...(request.headers || {})};
    if (request.body && !(request.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json'; request.body = JSON.stringify(request.body);
    }
    if (request.method && request.method !== 'GET') headers['X-CSRF-Token'] = S.csrf;
    const send = () => fetch(BASE+'/api'+path,{...request,headers,credentials:'include'});
    let response = await send();
    if (response.status===401 && !/^\/auth\/(login|otp|refresh|session)/.test(path)) {
      const renewed = await fetch(BASE+'/api/auth/refresh',{method:'POST',credentials:'include',headers:{'X-CSRF-Token':S.csrf}});
      if (renewed.ok) response = await send();
    }
    if (!response.ok) {
      let detail;
      try { detail = (await response.json()).detail; } catch { detail = 'The server could not complete this request.'; }
      if (Array.isArray(detail)) detail = detail.map(e => `${e.loc?.slice(1).join('.') || 'Input'}: ${e.msg}`).join('; ');
      const error = new Error(typeof detail==='string' ? detail : 'The request could not be completed.');
      error.status = response.status; throw error;
    }
    return blob ? response.blob() : response.json();
  }

  async function download(path, filename) {
    const data = await api(path,{blob:true});
    const url = URL.createObjectURL(data), link = document.createElement('a');
    link.href=url; link.download=filename; link.click(); setTimeout(() => URL.revokeObjectURL(url),1000);
  }

  function tabs() {
    return S.user.role==='participant' ? [['arena','My round'],['practice','Practice entry'],['results','Results']]
      : S.user.role==='organiser' ? [['control','Round control'],['questions','Questions & assignments'],['teams','Teams & staff'],['judging','Judging'],['monitor','Monitor'],['results','Results'],['records','Records']]
      : S.user.role==='judge' ? [['judging','Judging'],['results','Results']]
      : [['monitor','Monitor'],['results','Results']];
  }

  function loginScreen() {
    $('#account').textContent='';
    root.innerHTML = `<section class="login-wrap"><div class="login-copy"><span class="eyebrow">VYUHAM ’26 / PROMPT SMITH ARENA</span><h1>Prompt<br><em>War.</em></h1><p>Make every instruction count. Enter the official arena to access your challenge, submit your work and follow your team's progress.</p><div class="stats"><div><strong>22</strong><span>Starting teams</span></div><div><strong>11</strong><span>Second stage</span></div><div><strong>5</strong><span>Finalists</span></div></div><div class="login-mark"><img src="assets/duk-logo.png" alt="Digital University Kerala"><span>31 OCTOBER 2026<br>SUPPORTED BY REFLECTIONS</span></div></div><div class="card login-card"><span class="eyebrow">APPROVED ACCOUNTS ONLY</span><h2>Enter the arena</h2><form id="loginForm">${field('Registered email','email','','email','autocomplete="email" required maxlength="254"')}${field('Password','password','','password','autocomplete="current-password" required maxlength="200"')}<button class="button primary" type="submit">Sign in ↗</button></form><div class="notice">Use the email approved by your organiser. New participants cannot register here. Use your account password. Contact the organiser if you need a password set or reset.</div></div></section>`;
  }

  async function refresh(quiet=false) {
    if (quiet && S.busy) return;
    const generation=(S.refreshGeneration || 0)+1; S.refreshGeneration=generation;
    const data=await api('/dashboard'), user=data.user, receivedAt=Date.now();
    const eligible=data.rounds.filter(r=>user.role!=='participant' || data.entries.some(e=>e.round_id===r.id));
    const roundId=S.round || (eligible.find(r=>!['closed','results'].includes(r.status)) || eligible.at(-1) || data.rounds[0])?.id;
    const current=data.rounds.find(r=>r.id===roundId);
    const canAccess=user.role!=='participant' || data.entries.some(e=>e.round_id===roundId);
    const workspace=canAccess ? await api(`/rounds/${roundId}/workspace`) : null;
    const overview=['organiser','volunteer'].includes(user.role) ? await api('/admin/overview') : null;
    const queue=['organiser','judge'].includes(user.role) && ['evaluation','results','closed'].includes(current?.status) ? await api(`/judge/rounds/${roundId}/queue`) : [];
    const results=current?.published_at ? await api(`/rounds/${roundId}/results`) : [];
    const audit=S.tab==='records' && user.role==='organiser' ? await api('/admin/audit') : [];
    const panel=['organiser','judge'].includes(user.role) ? await api(`/judge/rounds/${roundId}/panel`) : null;
    const bank=user.role==='organiser' ? await api(`/admin/questions?kind=${current.kind}`) : [];
    const assignments=user.role==='organiser' ? await api(`/admin/rounds/${roundId}/assignments`) : [];
    if (generation!==S.refreshGeneration) return;
    Object.assign(S,{data,user,round:roundId,workspace,overview,queue,results,audit,panel,bank,assignments,offset:new Date(data.server_now).getTime()-receivedAt});
    if (!S.tab) S.tab=tabs()[0][0];
    if (!quiet || (!S.dirty && !S.busy)) render();
    tick();
  }

  function roundCards() {
    return `<div class="rounds">${S.data.rounds.map(r => {
      const entry=S.data.entries.find(e=>e.round_id===r.id);
      const permitted=S.user.role!=='participant' || !!entry || !!r.published_at;
      return `<button type="button" class="round-button ${r.id===S.round?'active':''}" data-action="round" data-id="${r.id}" ${permitted?'':'disabled'}><span class="eyebrow">STAGE 0${r.stage}</span><strong>${esc(r.title)}</strong><small>${esc(title(r.status))}${entry ? ' · '+esc(title(entry.outcome)) : !permitted ? ' · Qualification required' : ''}</small></button>`;
    }).join('')}</div>`;
  }

  function clock(r) {
    const deadline=r.status==='running' ? r.challenge_ends_at : r.entry?.extension_until || r.upload_ends_at;
    const label=r.status==='running' || r.paused_from==='running' ? 'Challenge time remaining' : 'Submission time remaining';
    return `<span class="eyebrow">${label}</span><div class="timer" data-deadline="${esc(deadline || '')}" data-paused="${esc(r.status==='paused' ? r.paused_at : '')}">—</div><p class="small-text muted">${r.status==='paused' ? 'Paused by the organiser. Stop all competition work.' : r.status==='running' ? 'Work only in the designated LLM. Paste and submit your answers after this timer ends.' : 'Prompting has ended. Paste, review and confirm your answers before this timer ends.'}</p>`;
  }

  function tick() {
    if(S.user?.role==='participant' && S.tab==='arena' && S.workspace){
      const r=S.workspace,open=maySubmit(r),editor=$('#directEntryForm [data-entry-fields]'),confirmButton=$('#confirmForm [type=submit]');
      if(editor)editor.disabled=!open;
      if(confirmButton && (!S.busy || !open))confirmButton.disabled=!open;
      document.querySelectorAll('[data-deadline]').forEach(el=>{
        el.dataset.deadline=(r.status==='running' || r.paused_from==='running'?r.challenge_ends_at:r.entry?.extension_until || r.upload_ends_at) || '';
        el.dataset.paused=r.status==='paused'?r.paused_at:'';
        if(el.previousElementSibling)el.previousElementSibling.textContent=r.status==='paused'?'Round paused':r.status==='running'?'Challenge time remaining':'Submission time remaining';
        if(el.nextElementSibling)el.nextElementSibling.textContent=r.status==='paused'?'Paused by the organiser. Your entered text is kept in this browser session.':r.status==='running'?'Work in the designated LLM. Direct submission opens after the challenge.':open?'Paste, review and confirm your answers before the deadline.':'The submission window is closed. Any confirmed version remains saved.';
      });
    }
    document.querySelectorAll('[data-deadline]').forEach(el => {
      const frozen=el.dataset.paused;
      const reference=frozen ? new Date(frozen).getTime() : now();
      const seconds=Math.max(0,Math.ceil((new Date(el.dataset.deadline).getTime()-reference)/1000));
      el.textContent=Number.isFinite(seconds) ? `${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}` : 'Waiting';
    });
  }

  function challenge(r) {
    return `<div class="card"><div class="stage-meta"><span class="eyebrow">STAGE 0${r.stage}</span>${badge(r.status)}</div><h2>${esc(r.title)}</h2>${r.question_title?`<h3>${esc(r.question_title)}</h3><p class="muted small-text">Assigned question: ${esc(r.question_key)}</p>`:''}${r.task?`<p>${esc(r.task)}</p>${readBlock('Flawed response',r.flawed_output)}${readBlock('Reference target',r.expected_output)}${r.banned_words?.length?`<h3>Banned words and phrases</h3><div class="button-row">${r.banned_words.map(word=>badge(word)).join('')}</div><details class="model-reasons"><summary>Included singular / plural forms</summary><p>${Object.entries(r.banned_word_variants || {}).map(([word,forms])=>`${esc(word)}: ${forms.map(esc).join(', ')}`).join('<br>')}</p></details>`:''}`:'<div class="notice">The organiser will start the round and reveal your randomly assigned question. Refreshing does not change your assignment.</div>'}${r.participant_rules?`<div class="notice accent">${esc(r.participant_rules)}</div>`:''}${readBlock('Judge-only guidance — suggested approaches are not mandatory',r.judge_notes)}<div class="notice">${esc(r.llm_instructions)}</div><ul class="rule-list"><li>Up to ${r.max_attempts} attempt${r.max_attempts===1?'':'s'}; preserve exact prompts and unedited answers.</li><li>Use only the approved LLM. External assistance and manual answer editing are prohibited.</li><li>Prompting stops at the challenge deadline. The following submission window is for pasting, reviewing and confirming your answers.</li></ul></div>`;
  }

  function preview(data, practice=false, readonly=false) {
    return `<div class="card" ${practice?'data-practice-preview':!readonly?'data-draft-preview':''}><h2>${practice?'Practice preview':readonly?'Saved submission':'Review your answers'}</h2><p class="muted small-text">${practice?'These practice answers are not stored or scored.':readonly?'This is a saved version. Confirmed versions cannot be edited.':'Check every prompt and answer, select an attempt and explicitly confirm. Saving a draft alone does not enter it for judging.'}</p><form id="${practice || readonly?'readOnlyPreview':'confirmForm'}" data-id="${esc(data.id || '')}">${data.attempts.map((a,i)=>`<section class="attempt"><label><input type="radio" name="selected_attempt" value="${i+1}" ${i+1===data.selected_attempt?'checked':''} ${practice || readonly?'disabled':''}> <strong>Attempt ${i+1}</strong></label>${readBlock('Prompt',a.prompt)}${readBlock('AI answer',a.answer)}</section>`).join('')}${practice || readonly?'':'<button class="button primary" type="submit">Confirm final submission ↗</button>'}</form></div>`;
  }

  function roundEntryModel(r) {
    if (!S.entryDrafts[r.id]) {
      const saved=r.submissions?.[0];
      S.entryDrafts[r.id]=saved ? window.PROMPT_WAR_ENTRY.copy(saved) : window.PROMPT_WAR_ENTRY.blank();
    }
    return S.entryDrafts[r.id];
  }

  function maySubmit(r) {
    const deadline=r?.entry?.extension_until || r?.upload_ends_at;
    return r && ['submission','evaluation'].includes(r.status) && r.entry?.outcome==='eligible' && deadline && new Date(deadline).getTime()>now();
  }

  function arena() {
    const r=S.workspace;
    if (!r) return '<div class="card empty">Your team has not qualified for this stage.</div>';
    const canSubmit=maySubmit(r), versions=r.submissions || [];
    const confirmed=versions.filter(version=>version.confirmed_at).sort((a,b)=>new Date(b.confirmed_at)-new Date(a.confirmed_at))[0];
    return `<div class="grid"><div>${challenge(r)}${canSubmit?window.PROMPT_WAR_ENTRY.render(roundEntryModel(r),r.max_attempts):''}${S.draft && canSubmit?preview(S.draft):''}${S.viewSubmission?preview(S.viewSubmission,false,true):''}</div><aside><div class="card">${['running','submission','paused'].includes(r.status) || canSubmit?clock(r):`<h3>${r.status==='evaluation'?'Evaluation in progress':r.published_at?'Results published':'Waiting for the organiser'}</h3><p class="muted small-text">${r.status==='evaluation'?'Take a break while judges evaluate the confirmed submissions.':'The organiser opens each challenge and its following submission window.'}</p>`}<div class="stats"><div><strong>${r.max_attempts}</strong><span>Maximum attempts</span></div><div><strong>100</strong><span>Available marks</span></div></div><p class="muted small-text">Paste your prompts and answers in the form when the submission window opens. Saving creates a draft; confirmation creates the final receipt.</p></div>${confirmed?`<div class="receipt"><strong>Final submission confirmed</strong><p>Receipt: <code>${esc(confirmed.id)}</code><br>${esc(time(confirmed.confirmed_at))}</p><small>Selected attempt ${confirmed.selected_attempt}. A later confirmed version replaces this one.</small><code class="submission-hash">Content SHA-256: ${esc(confirmed.sha256)}</code></div>`:'<div class="notice accent">No confirmed final submission for this stage yet.</div>'}<div class="card"><h3>Submission history</h3>${versions.length?versions.map((version,index)=>`<div class="history-row"><div>Version ${versions.length-index}<small>${esc(time(version.created_at))} · ${version.confirmed_at?'Confirmed':'Draft'} · ${version.attempts.length} attempt(s)</small></div><div class="button-row">${button('View','view-submission',`data-id="${version.id}"`,'small')}${!version.confirmed_at && canSubmit?button('Review & confirm','review-draft',`data-id="${version.id}"`,'small'):''}</div></div>`).join(''):'<p class="muted small-text">Saved versions appear here. Previous confirmed versions remain available.</p>'}</div><div class="card"><h3>Technical problem?</h3><form id="incidentForm">${area('Tell the volunteer what happened','description','','required minlength="5" maxlength="3000"')}<button class="button small" type="submit">Report problem</button></form></div></aside></div>`;
  }

  function practice() {
    S.practiceEntry ||= window.PROMPT_WAR_ENTRY.blank();
    return `<div class="grid"><div>${window.PROMPT_WAR_ENTRY.render(S.practiceEntry,5,true)}</div><div>${S.practice?preview(S.practice,true):'<div class="card"><h3>A reliable submission</h3><ol class="rule-list"><li>Paste each exact prompt and its unedited AI answer.</li><li>Add every attempt within the round limit.</li><li>Select the attempt you want judged.</li><li>Save, review and confirm before the submission deadline.</li><li>Check the timestamped confirmation receipt.</li></ol><p class="muted small-text">Practice supports up to five attempts. Word Ban competition submissions allow only one.</p></div>'}</div></div>`;
  }

  function teamOptions() {
    return (S.overview?.teams || []).map(t=>`<option value="${t.id}">${esc(t.name)}</option>`).join('');
  }

  function teams() {
    return `<div class="grid"><div><div class="card"><h2>Registered teams</h2><div class="table-wrap"><table><thead><tr><th>Team</th><th>Approved emails</th></tr></thead><tbody>${(S.overview?.teams || []).map(t=>`<tr><td><strong>${esc(t.name)}</strong></td><td>${(t.emails || []).filter(Boolean).map(esc).join('<br>')}</td></tr>`).join('') || '<tr><td colspan="2">No teams enrolled.</td></tr>'}</tbody></table></div></div><div class="card"><h3>Staff accounts</h3>${(S.overview?.staff || []).map(m=>`<div class="history-row"><span>${esc(m.email)}</span>${badge(m.role)}</div>`).join('')}</div><!-- Computer allocation disabled: this event does not track workstations. --></div><aside>${bulkImportForm()}<div class="card"><h2>Enrol a team</h2><p class="muted small-text">One or two members. Existing account passwords are preserved. For new accounts, the operator must set a password using the secure terminal setup command. Enrolment closes at the first briefing.</p><form id="teamForm">${field('Team name','team_name','','text','required minlength="2" maxlength="100"')}${area('Member emails — one per line','team_emails','','required')}<button class="button primary" type="submit">Enrol team ↗</button></form></div><div class="card"><h3>Approve staff</h3><form id="staffForm">${field('Email','staff_email','','email','required')}<div class="field"><label for="staff_role">Role</label><select id="staff_role" name="staff_role"><option value="volunteer">Volunteer</option><option value="judge">Judge</option><option value="organiser">Organiser</option></select></div><button class="button" type="submit">Approve staff</button></form></div></aside></div>`;
  }

  function questionBanks() {
    const r=S.workspace, bank=S.bank || [], assignments=S.assignments || [];
    return `<div class="card"><h2>Questions & assignments</h2><p class="muted">${esc(r?.title)} uses the ${esc(r?.kind)} bank. Original source round numbers are retained; Recreate the Target is still held last.</p><div class="stats"><div><strong>${bank.filter(q=>q.active).length}</strong><span>Active questions</span></div><div><strong>${assignments.length}</strong><span>Assigned teams</span></div></div><div class="notice">Question data is imported only with the separate import script. Start challenge shuffles eligible teams and the active bank in balanced cycles. Assignments are saved once and never rerolled by a refresh.</div></div><div class="card"><h3>Saved assignments</h3>${assignments.length?`<div class="table-wrap"><table><thead><tr><th>Team</th><th>Assigned question</th><th>Time</th></tr></thead><tbody>${assignments.map(a=>`<tr><td>${esc(a.team_name)}</td><td>${esc(a.snapshot.key)} · ${esc(a.snapshot.title)}</td><td>${esc(time(a.assigned_at))}</td></tr>`).join('')}</tbody></table></div>`:'<p class="muted">No assignments yet. The admin assigns questions by starting this stage.</p>'}</div><div class="card"><h3>Private question-bank preview</h3><p class="muted small-text">Organiser-only. Participants receive only their own assigned question when the challenge starts.</p>${bank.map(question=>`<details class="card"><summary><h3>${esc(question.key)} · ${esc(question.title)}</h3>${badge(question.active?'active':'inactive')}</summary><p>${esc(question.task)}</p>${readBlock('Flawed input',question.flawed_output)}${readBlock('Expected target',question.expected_output)}${question.banned_words.length?`<p>Banned words: ${question.banned_words.map(esc).join(', ')}</p>`:''}${readBlock('Private guidance',question.judge_notes)}<p class="muted small-text">Original source round ${question.original_round}, question ${question.source_number}. ${esc(question.participant_rules)}</p></details>`).join('') || '<div class="notice accent">No questions have been imported. Use the supplied import script after applying the migrations.</div>'}</div>`;
  }

  function control() {
    const r=S.workspace;
    if(!r)return '';
    const actions={waiting:[['Release briefing','brief']],briefing:[['Start & assign random questions','start']],running:[['Pause','pause'],['End challenge early','end_challenge']],submission:[['Pause','pause'],['Close submissions','close_uploads']],paused:[['Resume','resume']],evaluation:[['Close all extensions','close_uploads']],results:[['Close round','close']],closed:[]}[r.status] || [];
    const entries=(S.overview?.entries || []).filter(entry=>entry.round_id===r.id);
    return `<div class="grid"><div><div class="card"><div class="stage-meta"><h2>Stage ${r.stage} controls</h2>${badge(r.status)}</div><div class="stats"><div><strong>${entries.length}</strong><span>Entries</span></div><div><strong>${entries.filter(entry=>entry.confirmed_at).length}</strong><span>Confirmed</span></div><div><strong>${r.bank?.active_questions ?? 0}</strong><span>Bank questions</span></div></div>${['running','submission','paused'].includes(r.status)?clock(r):''}<div class="button-row">${actions.map(([label,action])=>button(esc(label),'round-action',`data-command="${action}" ${action==='brief' && !r.bank?.active_questions?'disabled':''}`,'primary')).join('')}${r.status==='evaluation'?button('Review & publish results','publish','','danger'):''}${button('Questions & assignments','tab','data-tab="questions"')}</div><div class="notice">Start challenge assigns a random question to every eligible team and starts the shared timer in one transaction. Each bank question is used once per shuffled cycle. The saved assignment and target are used for that team's evaluation.</div></div><div class="card"><h2>Stage settings</h2><form id="roundForm"><fieldset ${r.status!=='waiting'?'disabled':''}><div class="form-grid"><div class="full">${field('Stage title','title',r.title,'text','required maxlength="160"')}</div><div class="full">${area('Additional instructions for every question — optional','task',r.task || '','maxlength="12000"')}</div>${field('Challenge duration in seconds','duration_seconds',r.duration_seconds,'number','required min="30" max="7200"')}${field('Submission window in seconds','upload_seconds',r.upload_seconds,'number','required min="30" max="1800"')}${field(r.stage===3?'Prize places':'Teams qualifying','qualifier_count',r.qualifier_count,'number',`required min="1" max="22" ${r.stage===3?'readonly':''}`)}<div class="full">${area('Designated LLM, model and usage instructions','llm_instructions',r.llm_instructions,'required minlength="5" maxlength="3000"')}</div></div><button class="button primary" type="submit">Save stage settings</button></fieldset></form></div></div><aside><div class="card"><h3>Grant submission exception</h3><p class="muted small-text">For a verified technical incident. Reopens one team's entry window and invalidates provisional assessments, while keeping its original assigned question.</p><form id="extensionForm"><div class="field"><label for="extension_team">Team</label><select id="extension_team" name="team_id" required>${teamOptions()}</select></div>${field('Additional minutes','minutes',5,'number','required min="1" max="30"')}${area('Reason for exception','reason','','required minlength="5" maxlength="1000"')}<button class="button" type="submit">Grant extension</button></form></div><div class="card"><h3>Record a disqualification</h3><form id="disqualifyForm"><div class="field"><label for="disqualify_team">Team</label><select id="disqualify_team" name="team_id" required>${teamOptions()}</select></div>${area('Reason and evidence','reason','','required minlength="5" maxlength="1000"')}<button class="button danger" type="submit">Disqualify for this stage</button></form></div><div class="notice">Drafts are not final submissions. Check the monitor before publication. Teams without confirmed answers do not qualify.</div></aside></div>`;
  }

  function judging() {
    const r=S.workspace;
    if (!r || !['evaluation','results','closed'].includes(r.status)) return '<div class="card empty">The judging queue opens after this stage’s submission window closes.</div>';
    const locked=r.status!=='evaluation';
    const counts={complete:0,running:0,queued:0,incomplete:0};
    S.queue.forEach(row=>{const status=row.panel_run?.status;if(status in counts)counts[status]++;});
    return `<div class="card"><div class="stage-meta"><h2>Round evaluation panel</h2>${badge(`${S.queue.length} final submissions`)}</div><p class="muted small-text">Three Groq models and one OpenAI model independently evaluate the same selected prompt and answer. The suggested final score averages all four models per criterion. Judges review every model’s reasoning before approval.</p><div class="stats"><div><strong>${counts.complete}</strong><span>Complete panels</span></div><div><strong>${counts.queued+counts.running}</strong><span>Queued / running</span></div><div><strong>${S.queue.filter(row=>row.approved_at).length}</strong><span>Human approved</span></div></div>${S.panel?.roster?.length?`<div class="button-row">${S.panel.roster.map(slot=>badge(`${slot.provider}: ${slot.model}`)).join('')}</div><p class="muted small-text">${S.panel.locked?'Model roster locked for this round.':'Model roster locks when the first evaluation is requested.'}</p>`:''}<div class="notice ${!S.panel?.configured?'accent':''}">${esc(S.panel?.message || 'Checking evaluator configuration…')}</div>${!locked?button('Evaluate all final submissions','evaluate-all',!S.panel?.configured?'disabled':'','primary'):''}<p class="small-text muted">Requests are stored in the evaluation queue. Live updates show each result as it arrives. Incomplete panels have no combined score; successful evaluators are preserved when retrying failures.</p></div>${S.queue.map(row=>{
      const selected=row.attempts[row.selected_attempt-1];
      const active=['queued','running'].includes(row.panel_run?.status);
      const identity=row.candidate;
      return `<details class="card" data-submission="${row.id}" ${S.openSubmission===row.id?'open':''}><summary><h3>${esc(identity?.name || row.label)}</h3>${badge(row.approved_at ? `Approved · ${row.total}/100`:'Awaiting judge',!!row.approved_at)}</summary>${identity?`<p class="candidate-meta">Participants: ${(identity.emails || []).filter(Boolean).map(esc).join(', ')}</p>`:''}<p class="muted small-text">Confirmed: ${esc(time(row.confirmed_at))} · Selected attempt ${row.selected_attempt} of ${row.attempts.length}</p>${challenge({...r,...row.challenge})}${readBlock('Selected prompt',selected.prompt)}${readBlock('Selected AI answer',selected.answer)}${row.attempts.length>1?`<details class="model-reasons"><summary>Other submitted attempts</summary>${row.attempts.map((attempt,index)=>index===row.selected_attempt-1?'':`<section class="attempt"><h3>Attempt ${index+1}</h3>${readBlock('Prompt',attempt.prompt)}${readBlock('AI answer',attempt.answer)}</section>`).join('')}</details>`:''}<div class="notice ${row.checks.banned_matches.length || row.checks.possible_target_copy?'accent':''}">Banned matches: ${esc(row.checks.banned_matches.join(', ') || 'None')}<br>Exact target match: ${row.checks.exact_target_match?'Yes':'No'} · Similarity: ${row.checks.similarity_percent===null?'N/A':`${row.checks.similarity_percent}%`}<br>Original flawed input included verbatim: ${row.checks.flawed_input_literal_present===null?'N/A':row.checks.flawed_input_literal_present?'Yes':'Not found — review'}<br>Possible copied target in submitted attempts: ${row.checks.possible_target_copy?'Flagged — inspect manually':'Not flagged'}</div>${window.PROMPT_WAR_PANEL.render(row,locked)}<h3>Human judge approval</h3>${active?'<div class="notice accent">Wait for this panel to finish, or explicitly cancel it before recording a manual override.</div>':''}<form id="score-${row.id}" data-form="score" data-id="${row.id}"><fieldset ${locked || active?'disabled':''}><div class="score-grid">${Object.entries(row.rubric).map(([key,max])=>{
        const compliance=key==='banned_word_compliance';
        const value=compliance ? (row.checks.banned_matches.length?0:30) : row.scores?.[key] ?? '';
        return field(`${title(key)} / ${max}`,`${row.id}-${key}`,value,'number',`data-criterion="${key}" min="0" max="${max}" step="0.01" required ${compliance?'readonly':''}`);
      }).join('')}</div>${field('Surprise tie-break score / 100 — only if conducted',`tie-${row.id}`,row.tie_break_score ?? '','number','min="0" max="100" step="0.01" data-tie')}${area('Judge reasoning, score adjustments and tie-break evidence',`comments-${row.id}`,row.comments || '','required minlength="5" maxlength="5000" data-comments')}<label class="manual-override"><input type="checkbox" name="manual_override" ${row.manual_override?'checked':''}><span>Approve manually without a completed four-model panel. Explain the provider outage or exception in the reasoning above; this is recorded in the audit log.</span></label><button class="button primary" type="submit">Approve official score</button></fieldset></form></details>`;
    }).join('') || '<div class="card empty">No confirmed final submissions to judge.</div>'}`;
  }

  function monitor() {
    const r=S.data.rounds.find(x=>x.id===S.round), entries=(S.overview?.entries || []).filter(e=>e.round_id===S.round);
    return `<div class="card"><h2>Submission monitor</h2><p class="muted small-text">${esc(r.title)} · Check readiness in person, monitor the designated LLM and record technical incidents.</p><div class="table-wrap"><table><thead><tr><th>Team</th><th>Entry</th><th>Files</th><th>Final confirmed</th></tr></thead><tbody>${entries.map(e=>{const team=S.overview.teams.find(t=>t.id===e.team_id);return `<tr><td>${esc(team?.name)}</td><td>${badge(e.outcome)}</td><td>${e.uploads}</td><td>${esc(time(e.confirmed_at))}${e.extension_until?`<br>Exception until ${esc(time(e.extension_until))}`:''}</td></tr>`;}).join('') || '<tr><td colspan="4">No entries in this stage.</td></tr>'}</tbody></table></div></div><div class="grid equal"><div class="card"><h3>Report an incident</h3><form id="incidentForm"><div class="field"><label for="incident_team">Team</label><select id="incident_team" name="team_id" required>${teamOptions()}</select></div>${area('What happened?','description','','required minlength="5" maxlength="3000"')}<button class="button primary" type="submit">Record incident</button></form></div><div class="card"><h3>Recent incidents</h3>${(S.overview?.incidents || []).map(i=>`<div class="history-row"><div><strong>${esc(i.team_name)}</strong><p>${esc(i.description)}</p><small>${esc(time(i.created_at))}</small></div></div>`).join('') || '<p class="muted">No incidents recorded.</p>'}</div></div>`;
  }

  function resultsPage() {
    const r=S.data.rounds.find(x=>x.id===S.round);
    return `<div class="card"><h2>${esc(r.title)} results</h2>${!r.published_at ? '<div class="notice">Results have not been published. The organiser will announce the outcome after judging.</div>' : `<div class="table-wrap"><table><thead><tr><th>Place</th><th>Team</th><th>Marks / 100</th><th>Outcome</th></tr></thead><tbody>${S.results.map(row=>`<tr><td>${row.placement ?? '—'}</td><td><strong>${esc(row.name)}</strong></td><td>${row.final_score ?? '—'}</td><td>${badge(row.outcome,['qualified','winner','runner_up'].includes(row.outcome))}</td></tr>`).join('')}</tbody></table></div><p class="muted small-text">Each stage is scored independently. Qualification and final placements use judge-approved scores and any recorded surprise tie-break.</p>`}</div>`;
  }

  function records() {
    return `<div class="card"><h2>Competition records</h2><p class="muted">Export the current records, including final submissions, prompts, answers, approved scores and placements. Treat the export as private competition data.</p>${button('Download results CSV','export','','primary')}</div><div class="card"><h3>Recent administrative activity</h3><div class="table-wrap"><table class="audit"><thead><tr><th>Time</th><th>Action</th><th>Details</th></tr></thead><tbody>${S.audit.map(a=>`<tr><td class="nowrap">${esc(time(a.created_at))}</td><td>${esc(title(a.action))}</td><td><code>${esc(JSON.stringify(a.details))}</code></td></tr>`).join('')}</tbody></table></div></div>`;
  }

  function render() {
    if (!S.user || !S.data) return loginScreen();
    $('#account').innerHTML=`<span class="account-email">${esc(S.user.email)}<br>${esc(title(S.user.role))}</span>${button('Sign out','logout','','small')}`;
    const screens={arena,practice,teams,control,questions:questionBanks,judging,monitor,results:resultsPage,records};
    root.innerHTML=`<section class="hero"><span class="eyebrow">${esc(S.user.role==='participant' ? S.data.team?.name || 'TEAM ARENA' : title(S.user.role)+' DESK')}</span><h1>Prompt <em>War.</em></h1><p>${S.user.role==='participant' ? `One stage at a time. Work, submit, await results, then advance.` : 'Run the arena. Keep every deadline, submission and decision accountable.'}</p></section><section class="workspace"><nav class="tabs" aria-label="Competition sections">${tabs().map(([id,label])=>button(esc(label),'tab',`data-tab="${id}"`,S.tab===id?'active':'')).join('')}${button('Refresh','refresh','','quiet')}</nav>${roundCards()}${(screens[S.tab] || screens[tabs()[0][0]])()}</section>`;
    tick();
  }

  async function submit(form) {
    const data=new FormData(form), values=Object.fromEntries(data);
    if (form.id==='bulkParticipantForm') {
      const file = data.get('participant_csv');
      if (!file?.size || file.size>65536) throw new Error('Choose a nonempty CSV file of at most 64 KB.');
      const body = {csv_text:await file.text(),password:values.bulk_password,email_column:values.email_column,team_column:values.team_column,preview:true};
      const previous = bulkPreviews.get(form);
      if (previous===JSON.stringify(body)) {
        body.preview=false;
        bulkPreviews.delete(form);
        // Clear the password field before sending; never retain credentials in results.
        form.elements.bulk_password.value='';
        const reply=await api('/admin/participants/import',{method:'POST',body});
        form.elements.participant_csv.value='';
        bulkReport(form,reply);
        form.querySelector('[type=submit]').textContent='Preview import';
        S.dirty=true;
        notify('Import finished. Review each row below. Refresh the team list when ready.','info');
      } else {
        const reply=await api('/admin/participants/import',{method:'POST',body});
        bulkReport(form,reply);
        if (reply.rows.some(r=>r.status==='ready')) {
          bulkPreviews.set(form,JSON.stringify(body));
          form.querySelector('[type=submit]').textContent='Import previewed participants';
        }
        S.dirty=true;
      }
      return;
    }
    if (form.id==='loginForm') {
      await api('/auth/login',{method:'POST',body:{email:values.email,password:values.password}});
      S.dirty=false; await refresh(); notify('Signed in. Follow the organiser’s briefing.','success'); return;
    }
    if (form.id==='directEntryForm') {
      const entry=window.PROMPT_WAR_ENTRY.capture(form);
      S.entryDrafts[S.round]=entry;
      S.draft=await api(`/rounds/${S.round}/submissions`,{method:'POST',body:entry}); S.viewSubmission=null;
      S.dirty=false; await refresh(); notify('Draft saved. Review your pasted answers and confirm before the deadline.','info'); return;
    }
    if (form.id==='confirmForm') {
      const receipt=await api(`/submissions/${form.dataset.id}/confirm`,{method:'POST',body:{selected_attempt:Number(values.selected_attempt)}});
      if(S.entryDrafts[S.round])S.entryDrafts[S.round].selected_attempt=Number(values.selected_attempt);
      S.draft=null; S.receipt=receipt; S.dirty=false; await refresh(); notify(`Final submission confirmed at ${time(receipt.confirmed_at)}. Receipt ${receipt.id}`,'success'); return;
    }
    if (form.id==='practiceForm') {
      S.practiceEntry=window.PROMPT_WAR_ENTRY.capture(form);
      S.practice=await api('/practice/preview',{method:'POST',body:S.practiceEntry}); S.dirty=false; render(); notify(S.practice.message,'success'); return;
    }
    if (form.id==='teamForm') await api('/admin/teams',{method:'POST',body:{name:values.team_name,emails:values.team_emails.split(/[\s,;]+/).filter(Boolean)}});
    else if (form.id==='staffForm') await api('/admin/staff',{method:'POST',body:{email:values.staff_email,role:values.staff_role}});
    else if (form.id==='roundForm') await api(`/admin/rounds/${S.round}`,{method:'PUT',body:{title:values.title,task:values.task || '',duration_seconds:Number(values.duration_seconds),upload_seconds:Number(values.upload_seconds),qualifier_count:Number(values.qualifier_count),llm_instructions:values.llm_instructions}});
    else if (form.id==='extensionForm') await api(`/admin/rounds/${S.round}/extensions`,{method:'POST',body:{team_id:values.team_id,minutes:Number(values.minutes),reason:values.reason}});
    else if (form.id==='disqualifyForm') {
      if (!confirm('Disqualify this team for the selected stage? This records the supplied reason.')) return;
      await api(`/admin/rounds/${S.round}/disqualify`,{method:'POST',body:values});
    }
    else if (form.id==='incidentForm') await api('/incidents',{method:'POST',body:{team_id:S.user.team_id || values.team_id,round_id:S.round,description:values.description}});
    else if (form.dataset.form==='score') {
      const scores=Object.fromEntries([...form.querySelectorAll('[data-criterion]')].map(el=>[el.dataset.criterion,Number(el.value)]));
      const tie=form.querySelector('[data-tie]').value;
      await api(`/judge/submissions/${form.dataset.id}/score`,{method:'PUT',body:{scores,comments:form.querySelector('[data-comments]').value,tie_break_score:tie===''?null:Number(tie),manual_override:values.manual_override==='on'}});
      S.openSubmission=form.dataset.id;
    } else return;
    S.dirty=false; await refresh(); notify('Saved successfully.','success');
  }

  async function action(el) {
    const kind=el.dataset.action;
    if (kind==='logout') {
      if (S.dirty && !confirm('You have unsaved changes. Sign out anyway?')) return;
      S.refreshGeneration=(S.refreshGeneration || 0)+1;
      const result=await api('/auth/logout',{method:'POST'});
      clearPrivateState();S.csrf='';
      S.csrf=(await api('/auth/session')).csrf_token; loginScreen(); notify(result.message,'info'); return;
    }
    if (['tab','round','refresh'].includes(kind)) {
      if (S.dirty && !confirm('Discard unsaved form changes and refresh the view?')) return;
      if (S.dirty && S.tab==='arena') {delete S.entryDrafts[S.round];S.draft=null;}
      if (S.dirty && S.tab==='practice') {S.practiceEntry=null;S.practice=null;}
      S.dirty=false;
      if (kind==='tab') S.tab=el.dataset.tab;
      if (kind==='round') {S.round=el.dataset.id;S.draft=null;S.viewSubmission=null;if(S.user.role==='participant' && !S.data.entries.some(e=>e.round_id===S.round))S.tab='results';}
      return refresh();
    }
    if (kind==='export') return download('/admin/export','prompt-war-results.csv');
    if (kind==='view-submission') {S.viewSubmission=await api(`/submissions/${el.dataset.id}`);render();return;}
    if (kind==='review-draft') {
      if(S.dirty && !confirm('Replace unsaved entry text with this saved draft?'))return;
      S.draft=S.workspace.submissions.find(version=>version.id===el.dataset.id);
      S.entryDrafts[S.round]=window.PROMPT_WAR_ENTRY.copy(S.draft);S.viewSubmission=null;S.dirty=false;render();return;
    }
    if (kind==='entry-add' || kind==='entry-remove') {
      const practice=el.dataset.practice==='true', form=document.getElementById(practice?'practiceForm':'directEntryForm');
      const entry=window.PROMPT_WAR_ENTRY.capture(form),maximum=practice?5:S.workspace.max_attempts;
      if(kind==='entry-add') {if(entry.attempts.length>=maximum)return;entry.attempts.push({prompt:'',answer:''});}
      else {
        if(entry.attempts.length<=1)return;
        const index=Number(el.dataset.index),removed=entry.attempts[index];
        if(!Number.isInteger(index) || index<0 || index>=entry.attempts.length)return;
        if((removed.prompt || removed.answer) && !confirm('Remove this attempt from your unsaved draft? Preserve all actual competition attempts.'))return;
        entry.attempts.splice(index,1);
        if(entry.selected_attempt===index+1)entry.selected_attempt=1;
        else if(entry.selected_attempt>index+1)entry.selected_attempt--;
      }
      if(practice){S.practiceEntry=entry;S.practice=null;}else{S.entryDrafts[S.round]=entry;S.draft=null;}
      S.dirty=true;render();return;
    }
    if (kind==='round-action') {
      if (!confirm(el.dataset.command==='start'?'Start this stage and save random question assignments for all eligible teams? Assignments cannot be rerolled.':`Apply “${title(el.dataset.command)}” to this stage? All competing teams are affected.`)) return;
      await api(`/admin/rounds/${S.round}/action`,{method:'POST',body:{action:el.dataset.command}});
    } else if (kind==='publish') {
      if (!confirm('Publish judge-approved results and lock this stage? Teams without a confirmed submission will not qualify.')) return;
      await api(`/admin/rounds/${S.round}/publish`,{method:'POST'});
    } else if (kind==='evaluate-all') {
      if (!confirm('Queue four-model evaluation for every unapproved final submission in this round? Provider usage will be billed when the worker processes the jobs.')) return;
      await api(`/judge/rounds/${S.round}/evaluate`,{method:'POST'});
    } else if (kind==='suggest') {
      S.openSubmission=el.dataset.id; await api(`/judge/submissions/${el.dataset.id}/suggest`,{method:'POST'});
    } else if (kind==='retry-panel') {
      S.openSubmission=el.dataset.id; await api(`/judge/submissions/${el.dataset.id}/retry-panel`,{method:'POST'});
    } else if (kind==='cancel-panel') {
      const reason=prompt('Why should this pending evaluation be cancelled? In-flight provider calls may still be billed.');
      if (!reason) return;
      S.openSubmission=el.dataset.id; await api(`/judge/submissions/${el.dataset.id}/cancel-panel`,{method:'POST',body:{reason}});
    } else if (kind==='use-ai') {
      const row=S.queue.find(r=>r.id===el.dataset.id), form=document.getElementById('score-'+row.id);
      if (row.panel_run?.status!=='complete' || !row.panel_run.aggregate) throw new Error('All four evaluators must complete before combined scores can be used.');
      Object.entries(row.panel_run.aggregate.scores).forEach(([key,value])=>{const input=form.querySelector(`[data-criterion="${key}"]`);if(input)input.value=value;});
      form.querySelector('[name="manual_override"]').checked=false;
      S.dirty=true; notify('Combined four-model values filled. Review every model’s reasoning and write your approval comments.','info'); return;
    } else return;
    S.dirty=false; await refresh(); notify('Competition updated.','success');
  }

  async function perform(control, operation) {
    if (S.busy) return;
    S.busy=true;
    const previous=control?.textContent;
    if (control) {control.disabled=true;control.textContent='Please wait…';}
    try {await operation();}
    catch (error) {
      notify(error.message || 'The connection failed. Check your network and try again.');
      if (error.status===401 && S.user) {clearPrivateState();loginScreen();}
    } finally {
      S.busy=false;
      if (control?.isConnected) {control.disabled=false;if(control.closest('form')?.id!=='bulkParticipantForm')control.textContent=previous;else control.textContent=bulkPreviews.has(control.closest('form'))?'Import previewed participants':'Preview import';}
    }
  }

  document.addEventListener('submit', event=>{
    event.preventDefault(); const form=event.target;
    perform(form.querySelector('[type=submit]'),()=>submit(form));
  });
  document.addEventListener('click', event=>{
    const control=event.target.closest('[data-action]');
    if (control) perform(control,()=>action(control));
  });
  function rememberInput(event) {
    const form=event.target.closest('form');
    if(!form || !S.user)return;
    if(form.id==='bulkParticipantForm') {
      bulkPreviews.delete(form);
      form.querySelector('[type=submit]').textContent='Preview import';
      form.querySelector('[data-bulk-report]').textContent='';
    }
    S.dirty=true;
    if(form.dataset.entryEditor==='competition'){
      S.entryDrafts[S.round]=window.PROMPT_WAR_ENTRY.capture(form);S.draft=null;
      document.querySelector('[data-draft-preview]')?.remove();
    }else if(form.dataset.entryEditor==='practice'){
      S.practiceEntry=window.PROMPT_WAR_ENTRY.capture(form);S.practice=null;
      document.querySelector('[data-practice-preview]')?.remove();
    }else if(form.id==='confirmForm' && S.draft){
      S.draft.selected_attempt=Number(new FormData(form).get('selected_attempt'));
    }
  }
  document.addEventListener('input',rememberInput);
  document.addEventListener('change',rememberInput);
  document.addEventListener('toggle',event=>{if(event.target.matches('details[data-submission]') && event.target.open)S.openSubmission=event.target.dataset.submission;},true);
  window.addEventListener('beforeunload',event=>{if(S.dirty){event.preventDefault();event.returnValue='';}});
  async function boot() {
    try {
      S.csrf=(await api('/auth/session')).csrf_token;
      S.user=await api('/auth/me'); await refresh();
    } catch(error) {
      loginScreen(); if(error.status!==401) notify(error.message || 'Cannot connect to the competition server. Open this frontend through FastAPI.');
    }
  }
  setInterval(tick,1000);
  setInterval(()=>{if(S.user && !S.polling){S.polling=true;refresh(true).catch(error=>{if([401,403].includes(error.status)){clearPrivateState();loginScreen();}notify(error.message || 'Live status is unavailable. Use Refresh when the connection returns.');}).finally(()=>{S.polling=false;});}},8000);
  boot();
})();

