/**
 * Parse a decimal string that may use either '.' or ',' as the separator.
 */
export const parseDecimal = val => parseFloat(String(val).replace(',', '.'))

/**
 * Format a decimal number using the locale-appropriate decimal separator.
 * @param {number|string} val   - value to format
 * @param {string}        locale - 'nb' for Norwegian (comma), anything else for English (dot)
 * @param {object}        opts  - Intl.NumberFormat options overrides (e.g. { minimumFractionDigits: 1 })
 */
export const formatDecimal = (val, locale, opts = {}) => {
  if (val == null || val === '') return ''
  const num = typeof val === 'number' ? val : parseDecimal(String(val))
  if (isNaN(num)) return String(val)
  const tag = locale === 'nb' ? 'nb-NO' : 'en-US'
  return num.toLocaleString(tag, { maximumFractionDigits: 2, ...opts })
}
