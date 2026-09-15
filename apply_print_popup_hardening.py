from pathlib import Path

index = Path('app/index.html')
text = index.read_text(encoding='utf-8')

# Never embed a <script>...</script> block inside the main inline JavaScript.
# Browsers parse </script> at the HTML layer before JavaScript sees template
# strings, so one missed/normalised escape can dump the rest of the app source
# onto the page.  Remove the popup auto-print scripts entirely and invoke print
# from the parent window after document.close().
for delay in (300, 400):
    for closing in ('</script>', '<\\/script>', '<\\\\/script>'):
        text = text.replace(
            f'<script>setTimeout(()=>window.print(),{delay}){closing}',
            ''
        )

# Label popup: close the popup document, then print it from the parent context.
label_close = 'w.document.close(); audit("label",name);'
if label_close in text:
    text = text.replace(
        label_close,
        'w.document.close(); setTimeout(()=>{try{w.focus();w.print();}catch(_e){}},300); audit("label",name);',
        1,
    )

# Inspection pack popup: target the close immediately before exportTempCSV.
inspection_close = '  w.document.close();\n}\nfunction exportTempCSV(){'
if inspection_close in text:
    text = text.replace(
        inspection_close,
        '  w.document.close(); setTimeout(()=>{try{w.focus();w.print();}catch(_e){}},400);\n}\nfunction exportTempCSV(){',
        1,
    )

# Hard production guard. The generated index must not contain popup print script
# tags at all. The only literal </script> allowed is the actual closing tag for
# the main application script.
if 'setTimeout(()=>window.print()' in text:
    raise SystemExit('Unsafe popup window.print script remains in index.html')

# A valid page should have exactly one literal </script>: the real closing tag
# of the main inline application script. External scripts added later are handled
# separately and do not introduce inline template-string closers.
if text.count('</script>') != 1:
    raise SystemExit(f'Unexpected literal </script> count after hardening: {text.count("</script>")}')

index.write_text(text, encoding='utf-8')
