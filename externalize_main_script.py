from pathlib import Path

index = Path('app/index.html')
main_js = Path('app/main_app.js')
text = index.read_text(encoding='utf-8')

start = text.find('<script>')
end = text.rfind('</script>')
if start == -1 or end == -1 or end <= start:
    raise SystemExit('Could not locate main inline application script')

js = text[start + len('<script>'):end]
if len(js) < 50000:
    raise SystemExit(f'Main inline script unexpectedly short: {len(js)} bytes')

main_js.write_text(js.lstrip('\n'), encoding='utf-8')
replacement = '<script src="main_app.js?v=20260915-compliance1"></script>'
text = text[:start] + replacement + text[end + len('</script>'):]

# The production HTML must no longer contain the application source inline.
if 'function exportTempCSV()' in text or 'function printLabel(' in text:
    raise SystemExit('Application JavaScript still present inline after externalization')
if text.count(replacement) != 1:
    raise SystemExit('Versioned main_app.js script tag was not written exactly once')

index.write_text(text, encoding='utf-8')
print(f'Externalized {len(js)} bytes of application JavaScript to main_app.js')
