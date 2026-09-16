from pathlib import Path
import re

app = Path('app')
js_path = app / 'manager_context_controls_v6.js'
index_path = app / 'index.html'

js = js_path.read_text(encoding='utf-8')

# Make the manager action explicit: active cleaning definitions can be deleted,
# while historic signed completion records remain untouched.
js = js.replace('>Remove</button>', '>Delete</button>')
js = js.replace("if(!confirm('Remove “'+(s.task||'this cleaning task')+'” from the active schedule?\\n\\nHistoric completed records will remain.'))return;",
                "if(!confirm('Delete “'+(s.task||'this cleaning task')+'” from the current cleaning schedule?\\n\\nHistoric completed cleaning records will remain.'))return;")
js = js.replace("status('Removing…',false);await mutateAndSave('manager remove cleaning task'",
                "status('Deleting…',false);await mutateAndSave('manager remove cleaning task'")
js = js.replace("status('Cleaning task removed.',false);", "status('Cleaning task deleted from the active schedule.',false);")

# Busy kitchens can generate a revision between opening the manager sheet and
# pressing Delete. Retry against fresh live state a few times rather than making
# the manager repeat the action.
js = js.replace('for(var attempt=0;attempt<2;attempt++){', 'for(var attempt=0;attempt<5;attempt++){')
js = js.replace('if(r.status===409&&attempt===0)continue;', 'if(r.status===409&&attempt<4)continue;')

js_path.write_text(js, encoding='utf-8')

html = index_path.read_text(encoding='utf-8')
html = re.sub(r'manager_context_controls_v6\.js\?v=[^"\']+',
              'manager_context_controls_v6.js?v=20260916-cleaning-delete3', html)
index_path.write_text(html, encoding='utf-8')

print('Cleaning manager now has explicit cache-busted Delete controls with conflict retries')
