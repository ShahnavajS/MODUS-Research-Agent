/**
 * Date and Time Formatting Utilities.
 * 
 * Accurately parses UTC timestamps from SQLite/FastAPI and converts them
 * to the user's local timezone with human-readable relative and absolute formatting.
 */

export function parseUtcDate(dateInput: number | string | Date | null | undefined): Date {
  if (!dateInput && dateInput !== 0) return new Date();
  if (dateInput instanceof Date) return dateInput;
  if (typeof dateInput === 'number') return new Date(dateInput);

  let str = String(dateInput).trim();
  if (!str) return new Date();

  // If already has timezone indicator (Z or +HH:mm or -HH:mm), parse directly
  if (str.endsWith('Z') || /[+-]\d{2}(:\d{2})?$/.test(str)) {
    return new Date(str);
  }

  // If ISO format with 'T' (e.g. "2026-08-17T14:35:22.709384"), append 'Z'
  if (str.includes('T')) {
    return new Date(str + 'Z');
  }

  // If SQL format with space (e.g. "2026-08-17 14:35:22.709384"), convert to ISO UTC
  if (str.includes(' ')) {
    return new Date(str.replace(' ', 'T') + 'Z');
  }

  return new Date(str);
}

/**
 * Format in local date and time (e.g. "Aug 17, 2026, 8:05:22 PM").
 */
export function formatLocalDateTime(dateInput: number | string | Date | null | undefined): string {
  const d = parseUtcDate(dateInput);
  if (isNaN(d.getTime())) return '';
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * Format in local date (e.g. "Aug 17, 2026").
 */
export function formatLocalDate(dateInput: number | string | Date | null | undefined): string {
  const d = parseUtcDate(dateInput);
  if (isNaN(d.getTime())) return '';
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format in local time (e.g. "8:05:22 PM").
 */
export function formatLocalTime(dateInput: number | string | Date | null | undefined): string {
  const d = parseUtcDate(dateInput);
  if (isNaN(d.getTime())) return '';
  return d.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * Human-friendly relative time (e.g. "Just now", "2m ago", "1h ago").
 */
export function formatRelativeTime(dateInput: number | string | Date | null | undefined): string {
  const d = parseUtcDate(dateInput);
  if (isNaN(d.getTime())) return '';
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 15) return 'Just now';
  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay === 1) return 'Yesterday';
  if (diffDay < 7) return `${diffDay}d ago`;
  return formatLocalDate(d);
}
