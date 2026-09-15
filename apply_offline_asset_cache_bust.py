from pathlib import Path
import re

index = Path('app/index.html')
text = index.read_text(encoding='utf-8')

# The packaged build has used several version strings over time. If the
# kitchen fixes asset is present, normalize it to the current cache-bust
# value; if it is already embedded elsewhere, do not fail the whole deploy.
pattern = r'kitchen_fixes_20260810\.js(?:\?v=[^"\']+)?'
new = 'kitchen_fixes_20260810.js?v=20260915-offline2'
if re.search(pattern, text):
    text = re.sub(pattern, new, text)
    index.write_text(text, encoding='utf-8')
    print('Bumped kitchen compliance asset version for offline-unit rules')
else:
    print('Kitchen fixes script URL not present in this bundle; cache-bust step skipped')
