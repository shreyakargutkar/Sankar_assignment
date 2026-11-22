const BASE_URL = '/api/v1';

export async function fetchJson(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let errorMsg = `Request failed (${response.status})`;
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorMsg = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
      }
    } catch (e) {
      // ignore json parse error
    }
    throw new Error(errorMsg);
  }

  return response.json();
}

export const api = {
  // Influencers
  getInfluencers: async (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        query.append(key, val);
      }
    });
    return fetchJson(`/influencers?${query.toString()}`);
  },

  getStats: async () => {
    return fetchJson('/influencers/stats');
  },

  getInfluencer: async (id) => {
    return fetchJson(`/influencers/${id}`);
  },

  createInfluencer: async (data) => {
    return fetchJson('/influencers', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  updateInfluencer: async (id, data) => {
    return fetchJson(`/influencers/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  updateStatus: async (id, status) => {
    return fetchJson(`/influencers/${id}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status }),
    });
  },

  deleteInfluencer: async (id) => {
    return fetchJson(`/influencers/${id}`, {
      method: 'DELETE',
    });
  },

  batchAnalyzeAI: async (data) => {
    return fetchJson('/influencers/batch-analyze-ai', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Discovery
  discoverInfluencers: async (criteria) => {
    return fetchJson('/discovery/search', {
      method: 'POST',
      body: JSON.stringify(criteria),
    });
  },

  uploadCSV: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${BASE_URL}/discovery/upload-csv`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'CSV upload failed');
    }
    return response.json();
  },

  // Google Sheets
  syncToGoogleSheets: async (payload = {}) => {
    return fetchJson('/sheets/sync', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getIntegrationsStatus: async () => {
    return fetchJson('/sheets/status');
  },

  // Gmail
  getGmailStatus: async () => fetchJson('/gmail/status'),
  getGmailAuthUrl: async () => fetchJson('/gmail/auth-url'),
  disconnectGmail: async () => fetchJson('/gmail/disconnect', { method: 'POST' }),

  // Outreach
  getOutreachTracking: async () => fetchJson('/outreach/tracking'),
  getCampaignAnalytics: async (campaignId) => fetchJson(
    `/outreach/analytics${campaignId ? `?campaign_id=${campaignId}` : ''}`
  ),
  pollOutreachReplies: async () => fetchJson('/outreach/jobs/poll-replies', { method: 'POST' }),
  getCampaigns: async () => fetchJson('/outreach/campaigns'),
  createCampaign: async (data) => fetchJson('/outreach/campaigns', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  getOutreachEmails: async (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') query.append(key, val);
    });
    return fetchJson(`/outreach/emails?${query.toString()}`);
  },
  getInfluencerReplies: async (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') query.append(key, val);
    });
    return fetchJson(`/outreach/replies?${query.toString()}`);
  },
  getConversation: async (influencerId) => fetchJson(`/outreach/conversations/${influencerId}`),
  updateReplyDraft: async (id, data) => fetchJson(`/outreach/replies/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  approveReply: async (id) => fetchJson(`/outreach/replies/${id}/approve`, { method: 'POST' }),
  rejectReply: async (id) => fetchJson(`/outreach/replies/${id}/reject`, { method: 'POST' }),
  sendApprovedReplies: async (data = {}) => fetchJson('/outreach/send-replies', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  updateOutreachEmail: async (id, data) => fetchJson(`/outreach/emails/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  approveOutreachEmail: async (id) => fetchJson(`/outreach/emails/${id}/approve`, { method: 'POST' }),
  rejectOutreachEmail: async (id) => fetchJson(`/outreach/emails/${id}/reject`, { method: 'POST' }),
  sendApprovedEmails: async (data = {}) => fetchJson('/outreach/send', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  recordOutreachOutcome: async (id, outcome) => fetchJson(`/outreach/emails/${id}/outcome`, {
    method: 'POST',
    body: JSON.stringify({ outcome }),
  }),
  getOutreachEvents: async (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') query.append(key, val);
    });
    return fetchJson(`/outreach/events?${query.toString()}`);
  },
  processDueFollowups: async (force = false) => fetchJson(`/outreach/jobs/process-due?force=${force}`, {
    method: 'POST',
  }),
  simulateReply: async (emailId, decline = false) => fetchJson('/outreach/demo/simulate-reply', {
    method: 'POST',
    body: JSON.stringify({ email_id: emailId, decline }),
  }),
  simulateIncomingReply: async (data) => fetchJson('/outreach/demo/incoming-reply', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
};
