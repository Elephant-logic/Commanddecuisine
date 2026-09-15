from pathlib import Path

index = Path('app/index.html')
text = index.read_text(encoding='utf-8')

replacements = {
    '<script>setTimeout(()=>window.print(),400)</script></body></html>': '<script>setTimeout(()=>window.print(),400)<\\/script></body></html>',
    '<script>setTimeout(()=>window.print(),350)</script></body></html>': '<script>setTimeout(()=>window.print(),350)<\\/script></body></html>',
}

changed = 0
for old, new in replacements.items():
    if old in text:
        changed += text.count(old)
        text = text.replace(old, new)

# Guard against any remaining unescaped nested print-script close in the inline app script.
needle = 'setTimeout(()=>window.print()'
for pos in [i for i in range(len(text)) if text.startswith(needle, i)]:
    close = text.find('</script>', pos)
    if close != -1 and close - pos < 200:
        text = text[:close] + '<\\/script>' + text[close+9:]
        changed += 1

index.write_text(text, encoding='utf-8')
print(f'Sanitized {changed} embedded print script closing tag(s)')
