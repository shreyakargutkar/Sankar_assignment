import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Check, Inbox, Loader2, RefreshCw, Send, XCircle } from 'lucide-react';
import { api } from '../services/api';

const EMPTY_DEMO_REPLY = 'Thanks for your note. I am interested in learning more about the collaboration details.';

export default function ReplyManagementPanel({
  campaignId,
  emails,
  demoMode,
  aiMode,
  onChanged,
  showToast,
}) {
  const [replies, setReplies] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [conversation, setConversation] = useState([]);
  const [draftSubject, setDraftSubject] = useState('');
  const [draftBody, setDraftBody] = useState('');
  const [demoEmailId, setDemoEmailId] = useState('');
  const [demoBody, setDemoBody] = useState(EMPTY_DEMO_REPLY);
  const [isLoading, setIsLoading] = useState(true);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState('');

  const selectedReply = useMemo(
    () => replies.find((reply) => reply.id === selectedId) || null,
    [replies, selectedId]
  );
  const sentEmails = emails.filter((email) => email.status === 'sent');

  const loadReplies = useCallback(async () => {
    setIsLoading(true);
    setError('');
    try {
      const result = await api.getInfluencerReplies(
        campaignId ? { campaign_id: campaignId } : {}
      );
      const list = result.replies || [];
      setReplies(list);
      setSelectedId((current) => list.some((reply) => reply.id === current)
        ? current
        : (list[0]?.id ?? null));
    } catch (loadError) {
      setError(loadError.message || 'Could not load replies.');
    } finally {
      setIsLoading(false);
    }
  }, [campaignId]);

  useEffect(() => {
    loadReplies();
  }, [loadReplies]);

  useEffect(() => {
    if (!selectedReply) {
      setConversation([]);
      return;
    }
    let active = true;
    api.getConversation(selectedReply.influencer_id)
      .then((result) => {
        if (active) setConversation(result.messages || []);
      })
      .catch((loadError) => {
        if (active) showToast(loadError.message || 'Could not load conversation history.', 'error');
      });
    setDraftSubject(selectedReply.draft_subject || '');
    setDraftBody(selectedReply.draft_body || '');
    return () => { active = false; };
  }, [selectedId, selectedReply?.influencer_id]); // eslint-disable-line react-hooks/exhaustive-deps

  const runAction = async (action, successMessage) => {
    setIsBusy(true);
    try {
      const result = await action();
      if (successMessage) showToast(successMessage);
      await loadReplies();
      onChanged?.();
      return result;
    } catch (actionError) {
      showToast(actionError.message || 'Reply action failed.', 'error');
      return null;
    } finally {
      setIsBusy(false);
    }
  };

  const pollInbox = () => runAction(async () => {
    const result = await api.pollOutreachReplies();
    showToast(result.detected?.length
      ? `Processed ${result.detected.length} new Gmail reply/replies.`
      : (result.message || 'No new replies found.'));
  });

  const sendDemoReply = () => runAction(async () => {
    if (!demoEmailId) {
      showToast('Choose a sent outreach email first.', 'error');
      return;
    }
    const result = await api.simulateIncomingReply({
      email_id: Number(demoEmailId),
      body: demoBody,
    });
    showToast(`Demo reply classified as ${result.reply.classification}; follow-ups stopped.`);
  });

  const saveDraft = () => runAction(async () => {
    await api.updateReplyDraft(selectedReply.id, {
      subject: draftSubject,
      body: draftBody,
    });
  }, 'Reply draft saved. Re-approve if its previous approval was revoked.');

  const approve = () => runAction(async () => {
    if (draftSubject !== selectedReply.draft_subject || draftBody !== selectedReply.draft_body) {
      await api.updateReplyDraft(selectedReply.id, {
        subject: draftSubject,
        body: draftBody,
      });
    }
    await api.approveReply(selectedReply.id);
  }, 'Reply approved. It can now be sent.');

  const reject = () => runAction(
    () => api.rejectReply(selectedReply.id),
    'Reply rejected; it will not be sent.'
  );

  const sendApproved = () => runAction(async () => {
    const approvedIds = replies
      .filter((reply) => reply.status === 'approved' && reply.human_approved)
      .map((reply) => reply.id);
    const result = await api.sendApprovedReplies({ reply_ids: approvedIds });
    const errors = (result.failed || []).map((item) => item.error).filter(Boolean);
    showToast(errors.length
      ? `${result.message} ${errors.join('; ')}`
      : result.message,
    errors.length ? 'error' : 'success');
  });

  const canEdit = selectedReply && ['pending_approval', 'approved', 'failed'].includes(selectedReply.status);

  return (
    <div className="flex-1 min-h-0 overflow-y-auto p-4">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div>
          <h3 className="text-sm font-bold text-white">Influencer reply inbox</h3>
          <p className="text-[11px] text-slate-400">
            {aiMode === 'live_claude' ? 'Claude AI' : 'Simulated reply AI'} ·
            {' '}Classified replies stop follow-ups immediately. Drafts are never sent without human approval.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            disabled={isBusy}
            onClick={pollInbox}
            className="px-3 py-2 rounded-lg bg-indigo-600 text-xs font-semibold flex items-center gap-2 disabled:opacity-50"
          >
            {isBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            Check Gmail inbox
          </button>
          <button
            disabled={isBusy || !replies.some((reply) => reply.status === 'approved')}
            onClick={sendApproved}
            className="px-3 py-2 rounded-lg bg-emerald-700 text-xs font-semibold flex items-center gap-2 disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            Send approved replies ({replies.filter((reply) => reply.status === 'approved').length})
          </button>
        </div>
      </div>

      {demoMode && (
        <div className="grid md:grid-cols-[minmax(180px,1fr)_2fr_auto] gap-2 p-3 mb-4 rounded-xl border border-amber-900/70 bg-amber-950/20">
          <select
            value={demoEmailId}
            onChange={(event) => setDemoEmailId(event.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-2 py-2 text-xs"
          >
            <option value="">Select sent email for demo reply</option>
            {sentEmails.map((email) => (
              <option key={email.id} value={email.id}>
                @{email.instagram_username} · {email.to_email}
              </option>
            ))}
          </select>
          <textarea
            value={demoBody}
            onChange={(event) => setDemoBody(event.target.value)}
            maxLength={10000}
            rows={2}
            className="bg-slate-900 border border-slate-700 rounded-lg px-2 py-2 text-xs"
            aria-label="Demo incoming reply text"
          />
          <button
            disabled={isBusy || !demoEmailId || !demoBody.trim()}
            onClick={sendDemoReply}
            className="px-3 py-2 rounded-lg border border-amber-700 text-amber-200 text-xs font-semibold disabled:opacity-50"
          >
            Add demo reply
          </button>
        </div>
      )}

      {error && <p role="alert" className="mb-3 text-xs text-rose-300">{error}</p>}
      {isLoading ? (
        <div className="p-8 flex justify-center text-indigo-300"><Loader2 className="w-5 h-5 animate-spin" /></div>
      ) : (
        <div className="grid lg:grid-cols-12 gap-3 min-h-[420px]">
          <div className="lg:col-span-3 space-y-2">
            {replies.map((reply) => (
              <button
                key={reply.id}
                onClick={() => setSelectedId(reply.id)}
                className={`w-full text-left p-3 rounded-xl border ${
                  selectedId === reply.id ? 'border-indigo-500 bg-indigo-950/40' : 'border-slate-800 bg-slate-800/30'
                }`}
              >
                <p className="text-xs font-semibold text-white truncate">{reply.influencer_name}</p>
                <p className="text-[10px] text-slate-400 truncate">{reply.subject || '(no subject)'}</p>
                <div className="flex justify-between gap-1 mt-2">
                  <span className="text-[10px] text-cyan-300">{reply.classification}</span>
                  <span className="text-[10px] text-slate-500">{reply.status.replaceAll('_', ' ')}</span>
                </div>
              </button>
            ))}
            {!replies.length && <p className="p-4 text-xs text-slate-500">No replies yet. Check Gmail or add a simulated reply in demo mode.</p>}
          </div>

          {selectedReply ? (
            <>
              <div className="lg:col-span-4 rounded-xl border border-slate-800 bg-slate-800/20 p-3 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-white">{selectedReply.influencer_name}</p>
                    <p className="text-[10px] text-slate-400">{selectedReply.from_email}</p>
                  </div>
                  <span className="rounded-full bg-cyan-950 border border-cyan-800 px-2 py-1 text-[10px] text-cyan-200">
                    {selectedReply.classification} · {selectedReply.confidence}%
                  </span>
                </div>
                <p className="text-xs font-semibold text-slate-200">{selectedReply.subject || '(no subject)'}</p>
                <div className="max-h-40 overflow-y-auto whitespace-pre-wrap text-xs leading-relaxed text-slate-300">{selectedReply.body}</div>
                <p className="text-[10px] text-slate-500">{selectedReply.classification_reason}</p>
                <div className="border-t border-slate-800 pt-2">
                  <p className="text-[10px] uppercase text-slate-500 mb-2">Conversation history</p>
                  <div className="max-h-48 overflow-y-auto space-y-2">
                    {conversation.map((message) => (
                      <div key={message.id} className={`rounded-lg p-2 ${message.direction === 'inbound' ? 'bg-slate-800' : 'bg-indigo-950/50'}`}>
                        <p className="text-[9px] uppercase text-slate-500">
                          {message.direction} · {message.timestamp ? new Date(message.timestamp).toLocaleString() : ''}
                        </p>
                        <p className="text-[10px] font-medium text-slate-200">{message.subject}</p>
                        <p className="text-[10px] text-slate-400 whitespace-pre-wrap line-clamp-4">{message.body}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="lg:col-span-5 rounded-xl border border-slate-800 bg-slate-800/20 p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-[11px] uppercase tracking-wide text-slate-400">AI reply draft</p>
                  {selectedReply.status !== 'sent' && selectedReply.status !== 'no_reply_required' && (
                    <span className="text-[10px] text-amber-300">Human approval required</span>
                  )}
                </div>
                {selectedReply.status === 'no_reply_required' ? (
                  <p className="rounded-lg bg-rose-950/40 border border-rose-900 p-3 text-xs text-rose-200">Opt-out detected. No reply was generated; this influencer is suppressed from future outreach.</p>
                ) : (
                  <>
                    <input
                      disabled={!canEdit}
                      value={draftSubject}
                      onChange={(event) => setDraftSubject(event.target.value)}
                      maxLength={998}
                      aria-label="Reply subject"
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-2 text-xs disabled:opacity-60"
                    />
                    <textarea
                      disabled={!canEdit}
                      value={draftBody}
                      onChange={(event) => setDraftBody(event.target.value)}
                      maxLength={20000}
                      rows={10}
                      aria-label="Reply draft body"
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-2 text-xs leading-relaxed disabled:opacity-60"
                    />
                    {canEdit && (
                      <div className="flex flex-wrap gap-2">
                        <button disabled={isBusy} onClick={saveDraft} className="rounded-lg bg-slate-700 px-3 py-2 text-xs disabled:opacity-50">
                          Save edits
                        </button>
                        {['pending_approval', 'approved', 'failed'].includes(selectedReply.status) && (
                          <button disabled={isBusy} onClick={approve} className="rounded-lg bg-emerald-700 px-3 py-2 text-xs flex items-center gap-1 disabled:opacity-50">
                            <Check className="w-3 h-3" /> Approve
                          </button>
                        )}
                        {['pending_approval', 'approved', 'failed'].includes(selectedReply.status) && (
                          <button disabled={isBusy} onClick={reject} className="rounded-lg bg-rose-900 px-3 py-2 text-xs flex items-center gap-1 disabled:opacity-50">
                            <XCircle className="w-3 h-3" /> Reject
                          </button>
                        )}
                      </div>
                    )}
                    {selectedReply.status === 'sent' && (
                      <p className="text-[10px] text-emerald-300 flex items-center gap-1"><Inbox className="w-3 h-3" /> Sent via {selectedReply.send_mode}</p>
                    )}
                    {selectedReply.error_message && <p role="alert" className="text-xs text-rose-300">{selectedReply.error_message}</p>}
                  </>
                )}
              </div>
            </>
          ) : (
            <div className="lg:col-span-9 flex items-center justify-center rounded-xl border border-slate-800 text-xs text-slate-500">
              Select an influencer reply to review.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
