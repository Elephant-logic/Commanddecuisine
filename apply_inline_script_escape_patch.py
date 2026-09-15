from pathlib import Path

index = Path('app/index.html')
text = index.read_text(encoding='utf-8')

# Inline JavaScript writes complete HTML documents into popup windows.  A literal
# </script> inside the main page's <script> block terminates that block in the
# browser, even when it appears inside a JavaScript template string.  Keep the
# slash escaped in the source so JavaScript still produces </script> in the
# popup, while the parent HTML parser does not terminate the app script early.
replacements = [
    (
        '<script>setTimeout(()=>window.print(),300)</script></body></html>`);',
        '<script>setTimeout(()=>window.print(),300)<\\/script></body></html>`);',
    ),
    (
        '<script>setTimeout(()=>window.print(),400)</script></body></html>`);',
        '<script>setTimeout(()=>window.print(),400)<\\/script></body></html>`);',
    ),
]

for bad, good in replacements:
    if bad in text:
        text = text.replace(bad, good)

# Production guard: neither known popup-print block may contain a literal
# closing script tag after all build patches have run.
unsafe = [
    '<script>setTimeout(()=>window.print(),300)</script>',
    '<script>setTimeout(()=>window.print(),400)</script>',
]
left = [marker for marker in unsafe if marker in text]
if left:
    raise SystemExit('Unsafe embedded print script marker(s) remain: ' + ', '.join(left))

safe = [
    '<script>setTimeout(()=>window.print(),300)<\\/script>',
    '<script>setTimeout(()=>window.print(),400)<\\/script>',
]
if not all(marker in text for marker in safe):
    raise SystemExit('Expected escaped popup print script marker(s) not found')

index.write_text(text, encoding='utf-8')
