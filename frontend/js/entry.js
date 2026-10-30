// Direct text editor. Its state stays in memory; no shared-computer localStorage is used.
window.PROMPT_WAR_ENTRY = (() => {
  const esc=value=>String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const blank=()=>({attempts:[{prompt:'',answer:''}],selected_attempt:1});
  const copy=data=>({attempts:data.attempts.map(a=>({prompt:a.prompt,answer:a.answer})),selected_attempt:data.selected_attempt});
  function capture(form) {
    return {attempts:[...form.querySelectorAll('[data-entry-attempt]')].map(section=>({
      prompt:section.querySelector('[data-entry-prompt]').value,
      answer:section.querySelector('[data-entry-answer]').value,
    })),selected_attempt:Number(new FormData(form).get('selected_attempt') || 1)};
  }
  function render(data, maximum, practice=false) {
    const prefix=practice?'practice':'competition';
    return `<div class="card"><span class="eyebrow">${practice?'PRACTICE ENTRY':'DIRECT SUBMISSION'}</span><h2>${practice?'Try entering your work':'Enter prompts & answers'}</h2><p class="muted small-text">Paste the exact prompt and unedited AI answer for each attempt. Choose one attempt for judging. Formatting and whitespace are preserved by the server. No file upload is needed.</p><form id="${practice?'practiceForm':'directEntryForm'}" data-entry-editor="${practice?'practice':'competition'}"><fieldset data-entry-fields>${data.attempts.map((attempt,index)=>`<section class="attempt" data-entry-attempt><div class="stage-meta"><label><input type="radio" name="selected_attempt" value="${index+1}" ${data.selected_attempt===index+1?'checked':''} required> <strong>Attempt ${index+1} · select for judging</strong></label><button type="button" class="button quiet small" data-action="entry-remove" data-index="${index}" data-practice="${practice}" ${data.attempts.length===1?'disabled':''}>Remove</button></div><div class="field"><label for="${prefix}-prompt-${index}">Exact prompt</label><textarea id="${prefix}-prompt-${index}" data-entry-prompt required maxlength="16000" spellcheck="false">${esc(attempt.prompt)}</textarea><small>Up to 16,000 characters.</small></div><div class="field"><label for="${prefix}-answer-${index}">Unedited AI answer</label><textarea id="${prefix}-answer-${index}" data-entry-answer class="answer-editor" required maxlength="24000" spellcheck="false">${esc(attempt.answer)}</textarea><small>Up to 24,000 characters. Include every attempt; volunteers verify the external LLM history.</small></div></section>`).join('')}<div class="button-row"><button type="button" class="button" data-action="entry-add" data-practice="${practice}" ${data.attempts.length>=maximum?'disabled':''}>Add attempt (${data.attempts.length}/${maximum})</button><button type="submit" class="button primary">${practice?'Preview practice answers':'Save draft & review ↗'}</button></div><div class="notice">${practice?'Practice previews are not saved or scored.':'Only the latest explicitly confirmed version is judged. Text remains unsaved until you click Save draft & review; leaving or reloading beforehand can lose your changes.'}</div></fieldset></form></div>`;
  }
  return Object.freeze({blank,copy,capture,render});
})();
