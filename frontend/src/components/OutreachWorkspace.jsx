import React, { useEffect, useMemo, useState } from 'react';
import {
  X,
  Mail,
  Sparkles,
  Check,
  XCircle,
  Send,
  ShieldAlert,
  RefreshCw,
  Clock,
  Inbox,
  Ban,
  Pencil,
  Loader2,
  MessageSquare,
  BarChart3,
} from 'lucide-react';
import { api } from '../services/api';
import ReplyManagementPanel from './ReplyManagementPanel';
import CampaignAnalyticsPanel from './CampaignAnalyticsPanel';

const TRACKING_STAGES = [
  'Email Sent',
  'Follow-up Due',
  'Replied',
  'Interested',
  'Not Interested',
  'Pricing Enquiry',
  'Collaboration Request',
  'General Query',
  'Collaboration Confirmed',
];

export default function OutreachWorkspace({
  isOpen,
  onClose,
  selectedInfluencers,
  onChanged,
  showToast,
}) {
  const [stepBrand, setStepBrand] = useState('NovaFlow');
  const [campaignDesc, setCampaignDesc] = useState(
    'We help growing consumer brands launch authentic creator partnerships with clear briefs and fair compensation.'
  );
  const [offer, setOffer] = useState('A paid Instagram collaboration with creative freedom, product seeding, and usage rights limited to organic posts.');
  const [cta, setCta] = useState('Reply to this email with your rates and a 2-week window if you would like the full brief.');
  const [senderName, setSenderName] = useState('Alex Rivera, Partnerships');
  const [keywords, setKeywords] = useState('creators, authentic, collaboration');

  const [campaigns, setCampaigns] = useState([]);
  const [activeCampaignId, setActiveCampaignId] = useState(null);
  const [emails, setEmails] = useState([]);
  const [events, setEvents] = useState([]);
  const [tracking, setTracking] = useState(null);
  const [selectedEmailId, setSelectedEmailId] = useState(null);
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [isBusy, setIsBusy] = useState(false);
  const [filterStatus, setFilterStatus] = useState('');
  const [workspaceTab, setWorkspaceTab] = useState('outreach');

  const selectedEmail = useMemo(
    () => emails.find((e) => e.id === selectedEmailId) || null,
    [emails, selectedEmailId]
  );
  const canEditSelected = selectedEmail
    ? !['sent', 'rejected', 'cancelled', 'sending'].includes(selectedEmail.status)
    : false;

  const loadAll = async (campaignId = activeCampaignId) => {
    const [campRes, trackRes] = await Promise.all([
      api.getCampaigns(),
      api.getOutreachTracking(),
    ]);
    setCampaigns(campRes.campaigns || []);
    setTracking(trackRes);
    const cid = campaignId || (campRes.campaigns?.[0]?.id ?? null);
    if (cid) {
      setActiveCampaignId(cid);
      const [emailRes, eventRes] = await Promise.all([
        api.getOutreachEmails({ campaign_id: cid }),
        api.getOutreachEvents({ campaign_id: cid }),
      ]);
      const list = emailRes.emails || [];
      setEmails(list);
      setEvents(eventRes.events || []);
      if (list.length && !list.find((e) => e.id === selectedEmailId)) {
        setSelectedEmailId(list[0].id);
        setSubject(list[0].subject);
        setBody(list[0].body);
      }
    } else {
      setEmails([]);
      setEvents([]);
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    loadAll().catch((err) => showToast(err.message, 'error'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  useEffect(() => {
    if (selectedEmail) {
      setSubject(selectedEmail.subject);
      setBody(selectedEmail.body);
    }
  }, [selectedEmailId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!isOpen) return null;

  const gmail = tracking?.gmail || {};
  const quota = tracking?.quota || {};
  const sendMode = gmail.needs_reauth
    ? 'RECONNECT REQUIRED'
    : gmail.connected
      ? 'LIVE GMAIL'
      : 'SIMULATED GMAIL';

  const withBusy = async (fn) => {
    setIsBusy(true);
    try {
      await fn();
    } catch (err) {
      showToast(err.message || 'Outreach action failed', 'error');
    } finally {
      setIsBusy(false);
    }
  };

  const handleGenerate = () => withBusy(async () => {
    const ids = selectedInfluencers.map((i) => i.id);
    if (ids.length === 0) {
      showToast('Select at least one influencer with an email on the dashboard.', 'error');
      return;
    }
    const res = await api.createCampaign({
      brand_name: stepBrand,
      campaign_description: campaignDesc,
      collaboration_offer: offer,
      call_to_action: cta,
      sender_name: senderName,
      relevant_keywords: keywords,
      influencer_ids: ids,
    });
    showToast(`Generated ${res.created_count} draft(s) via ${res.generation_mode}. Human approval required before send.`);
    setActiveCampaignId(res.campaign.id);
    await loadAll(res.campaign.id);
    onChanged?.();
  });

  const handleSaveEdits = () => withBusy(async () => {
    if (!selectedEmail) return;
    await api.updateOutreachEmail(selectedEmail.id, { subject, body });
    showToast('Draft saved');
    await loadAll(activeCampaignId);
  });

  const handleApprove = () => withBusy(async () => {
    if (!selectedEmail) return;
    if (subject !== selectedEmail.subject || body !== selectedEmail.body) {
      await api.updateOutreachEmail(selectedEmail.id, { subject, body });
    }
    await api.approveOutreachEmail(selectedEmail.id);
    showToast('Approved. This email can now be sent.');
    await loadAll(activeCampaignId);
  });

  const handleReject = () => withBusy(async () => {
    if (!selectedEmail) return;
    await api.rejectOutreachEmail(selectedEmail.id);
    showToast('Rejected — will not send.');
    await loadAll(activeCampaignId);
  });

  const handleSendApproved = () => withBusy(async () => {
    const res = await api.sendApprovedEmails({ campaign_id: activeCampaignId });
    const errors = (res.failed || []).map((item) => item.error).filter(Boolean);
    const sheetsError = res.sheets_sync?.success === false
      ? `Google Sheets sync failed: ${res.sheets_sync.error || 'check backend logs'}`
      : '';
    const details = [...errors, sheetsError].filter(Boolean);
    showToast(details.length ? `${res.message} ${details.join('; ')}` : res.message, details.length ? 'error' : 'success');
    await loadAll(activeCampaignId);
    onChanged?.();
  });

  const handleOutcome = (outcome) => withBusy(async () => {
    if (!selectedEmail) return;
    await api.recordOutreachOutcome(selectedEmail.id, outcome);
    showToast(`Tracking updated: ${outcome}`);
    await loadAll(activeCampaignId);
    onChanged?.();
  });

  const handleSimulateReply = (decline) => withBusy(async () => {
    if (!selectedEmail) return;
    await api.simulateReply(selectedEmail.id, decline);
    showToast(decline ? 'Simulated decline received — follow-ups stopped' : 'Simulated reply received — follow-ups stopped');
    await loadAll(activeCampaignId);
    onChanged?.();
  });

  const handleForceFollowups = () => withBusy(async () => {
    const res = await api.processDueFollowups(true);
    showToast(`Queued ${res.created?.length || 0} follow-up draft(s) for approval (forced demo tick).`);
    await loadAll(activeCampaignId);
    onChanged?.();
  });

  const handleConnectGmail = () => withBusy(async () => {
    const res = await api.getGmailAuthUrl();
    window.location.href = res.auth_url;
  });

  const filteredEmails = emails.filter((e) => !filterStatus || e.status === filterStatus);
  const approvedCount = emails.filter((e) => e.status === 'approved').length;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-3">
      <div
        data-editorial-theme="true"
        className="relative w-full max-w-6xl h-[92vh] bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col"
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <Mail className="w-4 h-4 text-indigo-400" />
              <h2 className="text-base font-bold text-white">Influencer Outreach & Reply Workspace</h2>
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                gmail.connected
                  ? 'bg-emerald-950 text-emerald-300 border-emerald-700'
                  : 'bg-amber-950 text-amber-200 border-amber-700'
              }`}>
                {sendMode}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Human approval is required before every initial send and follow-up. Daily cap {quota.daily_limit ?? 40} ({quota.used ?? 0} used).
            </p>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-800 text-slate-400">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-5 py-2 border-b border-slate-800 flex flex-wrap items-center gap-2 text-[11px]">
          <span className="text-slate-400">Gmail:</span>
          <span className="text-slate-200">{gmail.email_address || 'Not connected'}</span>
          {gmail.connected ? (
            <button
              onClick={() => withBusy(async () => { await api.disconnectGmail(); await loadAll(); showToast('Gmail disconnected — sending is simulated.'); })}
              className="px-2 py-1 rounded bg-slate-800 border border-slate-700"
            >
              Disconnect
            </button>
          ) : gmail.oauth_client_configured ? (
            <button onClick={handleConnectGmail} className="px-2 py-1 rounded bg-indigo-600 text-white font-medium">
              {gmail.needs_reauth ? 'Reconnect Gmail OAuth' : 'Connect Gmail OAuth'}
            </button>
          ) : (
            <span className="text-slate-500">OAuth credentials/encryption key not configured</span>
          )}
          {gmail.needs_reauth && <span className="text-rose-300">Token expired — reconnect required</span>}
          <span className="ml-auto text-slate-500">Live sent {quota.live_sent || 0} · Simulated sent {quota.simulated_sent || 0}</span>
        </div>

        <div className="px-5 py-2 border-b border-slate-800 flex gap-2">
          {[
            ['outreach', 'Outreach', Mail],
            ['replies', `Replies${tracking?.pending_reply_approvals ? ` (${tracking.pending_reply_approvals})` : ''}`, MessageSquare],
            ['analytics', 'Analytics', BarChart3],
          ].map(([tab, label, Icon]) => (
            <button
              key={tab}
              onClick={() => setWorkspaceTab(tab)}
              className={`px-3 py-1.5 rounded-lg text-xs flex items-center gap-1.5 ${
                workspaceTab === tab ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'
              }`}
            >
              <Icon className="w-3.5 h-3.5" /> {label}
            </button>
          ))}
        </div>

        {workspaceTab === 'outreach' ? (
        <div className="flex-1 min-h-0 overflow-hidden grid grid-cols-1 lg:grid-cols-12">
          <div className="lg:col-span-3 border-r border-slate-800 overflow-y-auto p-4 space-y-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">New campaign</p>
            <input className="w-full px-2 py-1.5 rounded bg-slate-800 border border-slate-700 text-xs" value={stepBrand} onChange={(e) => setStepBrand(e.target.value)} placeholder="Brand name" />
            <textarea className="w-full px-2 py-1.5 rounded bg-slate-800 border border-slate-700 text-xs h-16" value={campaignDesc} onChange={(e) => setCampaignDesc(e.target.value)} />
            <textarea className="w-full px-2 py-1.5 rounded bg-slate-800 border border-slate-700 text-xs h-14" value={offer} onChange={(e) => setOffer(e.target.value)} />
            <textarea className="w-full px-2 py-1.5 rounded bg-slate-800 border border-slate-700 text-xs h-12" value={cta} onChange={(e) => setCta(e.target.value)} />
            <input className="w-full px-2 py-1.5 rounded bg-slate-800 border border-slate-700 text-xs" value={senderName} onChange={(e) => setSenderName(e.target.value)} />
            <button
              disabled={isBusy}
              onClick={handleGenerate}
              className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold disabled:opacity-50"
            >
              {isBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
              Generate AI drafts ({selectedInfluencers.length})
            </button>
            <p className="text-[10px] text-slate-500">Uses selected dashboard rows. Creators without email, opted-out, or already contacted are skipped.</p>

            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 pt-2">Campaigns</p>
            {campaigns.map((c) => (
              <button
                key={c.id}
                onClick={() => withBusy(async () => { setActiveCampaignId(c.id); await loadAll(c.id); })}
                className={`w-full text-left px-2 py-2 rounded-lg border text-xs ${
                  activeCampaignId === c.id ? 'border-purple-500 bg-purple-950/40' : 'border-slate-800 bg-slate-800/40'
                }`}
              >
                <div className="font-medium text-white">{c.name}</div>
                <div className="text-[10px] text-slate-400">{c.status}</div>
              </button>
            ))}
          </div>

          <div className="lg:col-span-4 border-r border-slate-800 overflow-y-auto p-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Email queue</p>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded text-[10px] px-1 py-0.5"
              >
                <option value="">All</option>
                <option value="pending_approval">Pending approval</option>
                <option value="approved">Approved</option>
                <option value="sent">Sent</option>
                <option value="rejected">Rejected</option>
                <option value="failed">Failed</option>
                <option value="sending">Sending</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
            {filteredEmails.map((e) => (
              <button
                key={e.id}
                onClick={() => setSelectedEmailId(e.id)}
                className={`w-full text-left mb-2 p-2 rounded-lg border ${
                  selectedEmailId === e.id ? 'border-indigo-500 bg-indigo-950/30' : 'border-slate-800 bg-slate-800/30'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-white truncate">{e.influencer_name}</span>
                  <span className="text-[10px] text-slate-400">{e.email_type}</span>
                </div>
                <div className="text-[10px] text-slate-400 truncate">{e.subject}</div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">{e.status}</span>
                  {e.send_mode && (
                    <span className={`text-[10px] ${e.send_mode === 'live_gmail' ? 'text-emerald-400' : 'text-amber-300'}`}>
                      {e.send_mode}
                    </span>
                  )}
                </div>
              </button>
            ))}
            {filteredEmails.length === 0 && (
              <p className="text-xs text-slate-500 p-4">No emails yet. Generate drafts from selected influencers.</p>
            )}
          </div>

          <div className="lg:col-span-5 overflow-y-auto p-4 space-y-3">
            {selectedEmail ? (
              <>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-white">@{selectedEmail.instagram_username} · {selectedEmail.to_email}</p>
                    <p className="text-[11px] text-slate-400">Seq {selectedEmail.sequence_number} · {selectedEmail.email_type}</p>
                  </div>
                  {selectedEmail.status !== 'sent' && (
                    <span className="text-[10px] text-amber-200 flex items-center gap-1">
                      <ShieldAlert className="w-3 h-3" /> Approval required
                    </span>
                  )}
                </div>
                <label className="text-[11px] text-slate-400">Subject</label>
                <input
                  disabled={!canEditSelected}
                  className="w-full px-2 py-1.5 rounded bg-slate-800 border border-slate-700 text-sm"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                />
                <label className="text-[11px] text-slate-400">Body</label>
                <textarea
                  disabled={!canEditSelected}
                  className="w-full h-56 px-2 py-1.5 rounded bg-slate-800 border border-slate-700 text-xs leading-relaxed"
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                />
                <div className="flex flex-wrap gap-2">
                  {canEditSelected && (
                    <button onClick={handleSaveEdits} className="px-3 py-1.5 rounded bg-slate-800 border border-slate-700 text-xs flex items-center gap-1">
                      <Pencil className="w-3 h-3" /> Save edits
                    </button>
                  )}
                  {['pending_approval', 'approved', 'failed'].includes(selectedEmail.status) && (
                    <>
                      <button onClick={handleApprove} className="px-3 py-1.5 rounded bg-emerald-700 text-white text-xs flex items-center gap-1">
                        <Check className="w-3 h-3" /> Approve
                      </button>
                      <button onClick={handleReject} className="px-3 py-1.5 rounded bg-rose-800 text-white text-xs flex items-center gap-1">
                        <XCircle className="w-3 h-3" /> Reject
                      </button>
                    </>
                  )}
                </div>
                <div className="flex flex-wrap gap-2 pt-1">
                  <button
                    disabled={isBusy || approvedCount === 0}
                    onClick={handleSendApproved}
                    className="px-3 py-1.5 rounded bg-indigo-600 text-white text-xs font-semibold flex items-center gap-1 disabled:opacity-40"
                  >
                    <Send className="w-3 h-3" /> Send {approvedCount} approved via {sendMode}
                  </button>
                </div>
                {selectedEmail.status === 'sent' && (
                  <div className="space-y-2 pt-2 border-t border-slate-800">
                    <p className="text-[11px] font-semibold text-slate-400 uppercase">Campaign tracking</p>
                    <div className="flex flex-wrap gap-1.5">
                      {['replied', 'interested', 'not_interested', 'opt_out'].map((o) => (
                        <button key={o} onClick={() => handleOutcome(o)} className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-[11px] capitalize">
                          {o.replace('_', ' ')}
                        </button>
                      ))}
                    </div>
                    {tracking?.demo_mode && (
                      <div className="flex flex-wrap gap-1.5">
                        <button onClick={() => handleSimulateReply(false)} className="px-2 py-1 rounded bg-cyan-950 border border-cyan-800 text-[11px] text-cyan-200 flex items-center gap-1">
                          <Inbox className="w-3 h-3" /> Simulate reply
                        </button>
                        <button onClick={() => handleSimulateReply(true)} className="px-2 py-1 rounded bg-rose-950 border border-rose-800 text-[11px] text-rose-200 flex items-center gap-1">
                          <Ban className="w-3 h-3" /> Simulate decline
                        </button>
                      </div>
                    )}
                    {selectedEmail.follow_up_due_at && (
                      <p className="text-[11px] text-amber-200 flex items-center gap-1">
                        <Clock className="w-3 h-3" /> Follow-up due {new Date(selectedEmail.follow_up_due_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                )}
                {tracking?.demo_mode && (
                  <button onClick={handleForceFollowups} className="text-[11px] text-slate-400 hover:text-white flex items-center gap-1">
                    <RefreshCw className="w-3 h-3" /> Demo: generate due follow-up drafts now
                  </button>
                )}
              </>
            ) : (
              <p className="text-sm text-slate-500">Select an email to preview and approve.</p>
            )}

            <div className="pt-3 border-t border-slate-800">
              <p className="text-[11px] font-semibold uppercase text-slate-500 mb-2">Pipeline tracking</p>
              <div className="grid grid-cols-2 gap-2">
                {TRACKING_STAGES.map((s) => (
                  <div key={s} className="px-2 py-1.5 rounded bg-slate-800/60 border border-slate-800 text-[11px] flex justify-between">
                    <span className="text-slate-400">{s}</span>
                    <span className="text-white font-semibold">{tracking?.pipeline?.[s] || 0}</span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <p className="text-[11px] font-semibold uppercase text-slate-500 mb-1">History</p>
              <div className="max-h-32 overflow-y-auto space-y-1">
                {events.slice(0, 12).map((ev) => (
                  <p key={ev.id} className="text-[10px] text-slate-500">
                    {ev.created_at ? new Date(ev.created_at).toLocaleString() : ''} · {ev.event_type} · {ev.detail}
                  </p>
                ))}
              </div>
            </div>
          </div>
        </div>
            ) : workspaceTab === 'replies' ? (
              <ReplyManagementPanel
                campaignId={activeCampaignId}
                emails={emails}
                demoMode={Boolean(tracking?.demo_mode)}
                aiMode={tracking?.reply_ai_mode}
                onChanged={async () => {
                  await loadAll(activeCampaignId);
                  onChanged?.();
                }}
                showToast={showToast}
              />
            ) : (
              <CampaignAnalyticsPanel campaignId={activeCampaignId} />
            )}
      </div>
    </div>
  );
}
