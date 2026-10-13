// Spreadsheet exports must remain text, even when a saved label resembles a formula.
export function csvCell(value) {
  const text = String(value ?? '');
  const guarded = /^[\s\uFEFF]*[=+\-@＝＋－＠]/u.test(text) || /^[\t\r\n]/u.test(text) ? "'" + text : text;
  return '"' + guarded.replaceAll('"', '""') + '"';
}
