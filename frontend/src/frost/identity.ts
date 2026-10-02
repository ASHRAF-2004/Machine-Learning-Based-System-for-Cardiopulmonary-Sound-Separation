// Presentation validation only. Uniqueness and the one-change rule live in SQLite.
const reserved = new Set(['admin','administrator','root','system','support','stethofuse','official','security','api','help','staff']);
export function canonicalHandle(value: string) { return value.trim().toLowerCase(); }
export function handleProblem(value: string): string {
  const handle = canonicalHandle(value);
  if (handle.length < 3 || handle.length > 20) return 'Use between 3 and 20 characters.';
  if (!/^[a-z][a-z0-9_.]*[a-z0-9]$/.test(handle) || /[_.]{2}/.test(handle))
    return 'Start with a letter. Use letters, numbers, dots or underscores, without consecutive or ending separators.';
  if (reserved.has(handle)) return 'That handle is reserved. Try another name.';
  return '';
}
