from pathlib import Path

index = Path('app/index.html')
text = index.read_text(encoding='utf-8')

bad = '<script>setTimeout(()=>window.print(),400)</script></body></html>`);'
good = '<script>setTimeout(()=>window.print(),400)<\\/script></body></html>`);'

if bad in text:
    text = text.replace(bad, good, 1)
elif good not in text:
    raise SystemExit('Expected inspection-pack print script marker not found')

index.write_text(text, encoding='utf-8')
