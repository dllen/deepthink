/**
 * Format an ISO-ish date string for display.
 *
 * Defaults: long month + day-only (e.g. "2026年7月30日").
 * Pass `{ withTime: true }` to include hour:minute (e.g. "2026/07/30 21:16").
 *
 * @param {string|Date} input
 * @param {{ withTime?: boolean, monthStyle?: 'long' | '2-digit' }} [opts]
 * @returns {string}
 */
export function formatDate(input, opts = {}) {
  const { withTime = false, monthStyle = 'long' } = opts;
  const d = input instanceof Date ? input : new Date(input);
  if (Number.isNaN(d.getTime())) return '';

  const month = monthStyle === '2-digit' ? '2-digit' : 'long';
  const day = monthStyle === 'long' ? 'numeric' : '2-digit';

  const fmt = {
    year: 'numeric',
    month,
    day,
  };
  if (withTime) {
    fmt.hour = '2-digit';
    fmt.minute = '2-digit';
  }

  return d.toLocaleDateString('zh-CN', fmt);
}
