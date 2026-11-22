export const LEAD_STATUSES = [
  'New Lead',
  'Email Available',
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

export const STATUS_CONFIG = {
  'New Lead': {
    bg: 'bg-slate-100',
    text: 'text-slate-700',
    border: 'border-slate-200',
    dot: 'bg-slate-400',
  },
  'Email Available': {
    bg: 'bg-sky-50',
    text: 'text-sky-800',
    border: 'border-sky-200',
    dot: 'bg-sky-500',
  },
  'Email Sent': {
    bg: 'bg-indigo-50',
    text: 'text-indigo-800',
    border: 'border-indigo-200',
    dot: 'bg-indigo-500',
  },
  'Follow-up Due': {
    bg: 'bg-amber-50',
    text: 'text-amber-800',
    border: 'border-amber-200',
    dot: 'bg-amber-500',
  },
  'Replied': {
    bg: 'bg-cyan-50',
    text: 'text-cyan-800',
    border: 'border-cyan-200',
    dot: 'bg-cyan-500',
  },
  'Interested': {
    bg: 'bg-emerald-50',
    text: 'text-emerald-800',
    border: 'border-emerald-200',
    dot: 'bg-emerald-500',
  },
  'Not Interested': {
    bg: 'bg-rose-50',
    text: 'text-rose-800',
    border: 'border-rose-200',
    dot: 'bg-rose-500',
  },
  'Pricing Enquiry': {
    bg: 'bg-amber-50',
    text: 'text-amber-800',
    border: 'border-amber-200',
    dot: 'bg-amber-500',
  },
  'Collaboration Request': {
    bg: 'bg-violet-50',
    text: 'text-violet-800',
    border: 'border-violet-200',
    dot: 'bg-violet-500',
  },
  'General Query': {
    bg: 'bg-slate-100',
    text: 'text-slate-700',
    border: 'border-slate-200',
    dot: 'bg-slate-400',
  },
  'Collaboration Confirmed': {
    bg: 'bg-violet-50',
    text: 'text-violet-800',
    border: 'border-violet-200',
    dot: 'bg-violet-500',
  },
};

export const NICHES = [
  'Tech & AI',
  'Fashion & Beauty',
  'Fitness & Health',
  'Travel & Lifestyle',
  'Food & Beverage',
  'Gaming',
  'Business & Finance',
  'Sustainability & Eco',
];

export function formatFollowers(count) {
  if (!count && count !== 0) return '0';
  if (count >= 1000000) {
    return (count / 1000000).toFixed(1).replace(/\.0$/, '') + 'M';
  }
  if (count >= 1000) {
    return (count / 1000).toFixed(1).replace(/\.0$/, '') + 'K';
  }
  return count.toLocaleString();
}

export function getScoreBadge(score) {
  if (score === null || score === undefined) {
    return {
      text: 'Unranked',
      class: 'bg-slate-100 text-slate-600 border border-slate-200',
      barColor: 'bg-slate-400',
    };
  }
  if (score >= 85) {
    return {
      text: `${score}/100 Excellent`,
      class: 'bg-emerald-50 text-emerald-800 border border-emerald-200',
      barColor: 'bg-emerald-600',
    };
  }
  if (score >= 70) {
    return {
      text: `${score}/100 Strong`,
      class: 'bg-sky-50 text-sky-800 border border-sky-200',
      barColor: 'bg-sky-600',
    };
  }
  if (score >= 55) {
    return {
      text: `${score}/100 Moderate`,
      class: 'bg-amber-50 text-amber-800 border border-amber-200',
      barColor: 'bg-amber-600',
    };
  }
  return {
    text: `${score}/100 Low`,
    class: 'bg-rose-50 text-rose-800 border border-rose-200',
    barColor: 'bg-rose-600',
  };
}
