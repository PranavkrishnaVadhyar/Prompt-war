// Read-only rendering of saved provider assessments. Never calls an LLM from the browser.
window.PROMPT_WAR_PANEL = (() => {
  const esc=value=>String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const label=value=>String(value || '').replaceAll('_',' ');
  const action=(text,kind,id)=>`<button type="button" class="button small" data-action="${kind}" data-id="${id}">${text}</button>`;
  function render(row,locked) {
    const run=row.panel_run, combined=run?.status==='complete' ? run.aggregate : null;
    const roster=run?.roster || [
      {slot:'groq_1',provider:'groq',model:'Evaluator 1'}, {slot:'groq_2',provider:'groq',model:'Evaluator 2'},
      {slot:'groq_3',provider:'groq',model:'Evaluator 3'}, {slot:'openai',provider:'openai',model:'Evaluator 4'},
    ];
    const succeeded=Object.values(run?.model_results || {}).filter(r=>r.status==='success').length;
    const active=['queued','running'].includes(run?.status);
    return `<section class="evaluation-panel"><div class="stage-meta"><h3>Four-model evaluation</h3><span class="badge">${succeeded} / 4 complete · ${esc(run?.status || 'not requested')}</span></div>
      <div class="model-grid">${roster.map(slot=>{
        const result=run?.model_results?.[slot.slot];
        return `<article class="model-card ${result?.status==='error'?'model-error':''}"><span class="eyebrow">${esc(slot.provider)} · ${esc(slot.slot)}</span><h4>${esc(slot.model)}</h4><div class="model-score">${result?.status==='success'?`<strong>${result.total}</strong><span>/ 100</span>`:`<span>${result?.status==='error'?'Needs retry':active?'Awaiting response':'Not evaluated'}</span>`}</div>
          ${result?.status==='success'?`<div class="table-wrap"><table><thead><tr><th>Criterion</th><th>Marks</th></tr></thead><tbody>${Object.entries(row.rubric).map(([key,max])=>`<tr><td>${esc(label(key))}</td><td>${result.scores[key]} / ${max}</td></tr>`).join('')}</tbody></table></div><details class="model-reasons"><summary>Reasoning</summary><p>${esc(result.explanation)}</p>${Object.keys(row.rubric).map(key=>`<p><strong>${esc(label(key))}:</strong> ${esc(result.criterion_reasons[key])}</p>`).join('')}${result.adjustments?.map(text=>`<p class="notice accent">${esc(text)} Model reported ${esc(result.reported_scores.banned_word_compliance)}; the rule requires ${esc(result.scores.banned_word_compliance)}.</p>`).join('') || ''}<small class="muted">Returned model: ${esc(result.response_model)} · ${result.elapsed_ms ?? '—'} ms</small></details>`:result?.error?`<p class="small-text">${esc(result.error)}</p>`:'<p class="muted small-text">An independent assessment of this exact submission and rubric.</p>'}</article>`;
      }).join('')}</div>
      ${combined?`<div class="combined-score"><div><span class="eyebrow">COMBINED SUGGESTED FINAL SCORE</span><strong>${combined.total}<small>/ 100</small></strong><p>${esc(combined.method)}</p></div><div><p class="small-text">Model score spread: <strong>${combined.score_spread}</strong> points.</p>${combined.review_required?'<p class="notice accent">The models differ by at least 15 marks. Inspect the disagreement before approving.</p>':''}${!locked?action('Fill combined scores','use-ai',row.id):''}</div></div><p class="muted small-text">This suggestion is not an official score. A human judge must approve the criterion scores and write their reasoning.</p>`:`<div class="notice ${run?.error?'accent':''}">${esc(run?.error || (active?'Evaluators are independent and run in parallel. The combined score appears only when all four complete.':'Request the panel to evaluate this submission. Missing or failed models are never treated as zero.'))}</div>`}
      ${!locked && !row.approved_at?`<div class="button-row">${!run?action('Evaluate with all four models','suggest',row.id):['incomplete','failed'].includes(run.status)?action('Retry failed / missing evaluators','retry-panel',row.id):''}${active?action('Cancel pending panel','cancel-panel',row.id):''}</div>`:''}
      ${(row.panel_history || []).length>1?`<details class="model-reasons"><summary>Evaluation run history</summary>${row.panel_history.map(history=>`<div class="notice"><strong>${esc(history.status)}</strong> · ${esc(history.created_at)}<br><code>${esc(history.id)}</code><p>${esc(history.error || '')}</p>${Object.values(history.model_results).map(result=>`<p class="small-text">${esc(result.provider)} / ${esc(result.model)}: ${result.status==='success'?`${result.total}/100`:esc(result.error || result.status)}</p>`).join('')}</div>`).join('')}</details>`:''}
    </section>`;
  }
  return Object.freeze({render});
})();

