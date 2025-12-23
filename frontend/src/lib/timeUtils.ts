function normalizeToISO(iso?: string | null): string | null {
  if (!iso) return null;
  // If the string already has timezone info (Z or ±HH:MM), return as-is
  if (/[Zz]$/.test(iso) || /[+-]\d{2}:\d{2}$/.test(iso)) return iso;
  // If it looks like a naive YYYY-MM-DDTHH:MM:SS, treat it as UTC
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$/.test(iso)) return `${iso}Z`;
  return iso;
}

export function formatHeaderTime(isoString?: string | null): string {
  const normalized = normalizeToISO(isoString);
  if (!normalized) return '';

  // Use Kolkata timezone for both the reference "now" and the message datetime
  const dt = new Date(normalized);
  const now = new Date();
  const dtKolkata = new Date(dt.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  const nowKolkata = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));

  const diffMs = nowKolkata.getTime() - dtKolkata.getTime();
  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 60) return 'just now';
  if (seconds < 3600) {
    const mins = Math.floor(seconds / 60);
    return `${mins} min ago`;
  }
  if (seconds < 3600 * 6) {
    const hours = Math.floor(seconds / 3600);
    return `${hours} hour${hours > 1 ? 's' : ''} ago`;
  }

  // After 6 hours: show time in IST if same day, else date
  const dtOptions: Intl.DateTimeFormatOptions = { hour: '2-digit', minute: '2-digit', hour12: true };
  if (nowKolkata.toDateString() === dtKolkata.toDateString()) {
    return dtKolkata.toLocaleTimeString('en-US', dtOptions) + ' IST';
  }
  const dateOptions: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' };
  return dtKolkata.toLocaleDateString('en-US', dateOptions);
}

export function formatTimeShort(isoString?: string | null): string {
  const normalized = normalizeToISO(isoString);
  if (!normalized) return '';
  const dt = new Date(normalized);
  const dtKolkata = new Date(dt.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  const nowKolkata = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));

  // If same day, show time, else show date
  if (nowKolkata.toDateString() === dtKolkata.toDateString()) {
    return dtKolkata.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }) + ' IST';
  }
  return dtKolkata.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
