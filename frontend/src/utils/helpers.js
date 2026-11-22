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
    bg: 'bg-[#f2ede7]',
    text: 'text-[#62545d]',
    border: 'border-[#e5d9d2]',
    dot: 'bg-[#9a8b8e]',
  },
  'Email Available': {
    bg: 'bg-[#f1e7eb]',
    text: 'text-[#715768]',
    border: 'border-[#e5d3dc]',
    dot: 'bg-[#9c7d8b]',
  },
  'Email Sent': {
    bg: 'bg-[#ece7ed]',
    text: 'text-[#54445a]',
    border: 'border-[#dcd1df]',
    dot: 'bg-[#725565]',
  },
  'Follow-up Due': {
    bg: 'bg-[#f8ebdf]',
    text: 'text-[#805c47]',
    border: 'border-[#eed9c5]',
    dot: 'bg-[#bd8b63]',
  },
  'Replied': {
    bg: 'bg-[#f2e3e1]',
    text: 'text-[#754d59]',
    border: 'border-[#e9cfcd]',
    dot: 'bg-[#b57d86]',
  },
  'Interested': {
    bg: 'bg-[#efe8dc]',
    text: 'text-[#6e5c40]',
    border: 'border-[#e3d6c1]',
    dot: 'bg-[#a38a5d]',
  },
  'Not Interested': {
    bg: 'bg-[#f4e4e3]',
    text: 'text-[#804d55]',
    border: 'border-[#ebd0d0]',
    dot: 'bg-[#b46d78]',
  },
  'Pricing Enquiry': {
    bg: 'bg-[#f8ebdf]',
    text: 'text-[#805c47]',
    border: 'border-[#eed9c5]',
    dot: 'bg-[#bd8b63]',
  },
  'Collaboration Request': {
    bg: 'bg-[#f1e7eb]',
    text: 'text-[#715768]',
    border: 'border-[#e5d3dc]',
    dot: 'bg-[#9c7d8b]',
  },
  'General Query': {
    bg: 'bg-[#f2ede7]',
    text: 'text-[#62545d]',
    border: 'border-[#e5d9d2]',
    dot: 'bg-[#9a8b8e]',
  },
  'Collaboration Confirmed': {
    bg: 'bg-[#ece7ed]',
    text: 'text-[#54445a]',
    border: 'border-[#dcd1df]',
    dot: 'bg-[#725565]',
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
      class: 'bg-[#f2ede7] text-[#75686e] border border-[#e5d9d2]',
      barColor: 'bg-[#b5a6a4]',
    };
  }
  if (score >= 85) {
    return {
      text: `${score}/100 Excellent`,
      class: 'bg-[#ece7ed] text-[#54445a] border border-[#dcd1df]',
      barColor: 'bg-[#725565]',
    };
  }
  if (score >= 70) {
    return {
      text: `${score}/100 Strong`,
      class: 'bg-[#f1e7eb] text-[#715768] border border-[#e5d3dc]',
      barColor: 'bg-[#9c7d8b]',
    };
  }
  if (score >= 55) {
    return {
      text: `${score}/100 Moderate`,
      class: 'bg-[#f8ebdf] text-[#805c47] border border-[#eed9c5]',
      barColor: 'bg-[#bd8b63]',
    };
  }
  return {
    text: `${score}/100 Low`,
    class: 'bg-[#f4e4e3] text-[#804d55] border border-[#ebd0d0]',
    barColor: 'bg-[#b46d78]',
  };
}
