"""Read-only inspection of recipe UI in assembled production app."""
from pathlib import Path
import re
paths=[Path('app/main_app.js'),Path('app/recipe_import_patch.js'),Path('app/index.html'),Path('app/runtime_loader.js'),Path('app/recipe_management_patch.js'),Path('app/recipe_viewer_patch.js')]
patterns=[r'VIEWS\.recipes\s*=',r'function\s+editRecipe\s*\(',r'function\s+openRecipe\s*\(',r'window\.editRecipe',r'function\s+recipeCard\s*\(',r'function\s+recipeRow\s*\(',r'function\s+renderRecipes\s*\(',r'openRecipe\(',r'Recipe editor',r'edit recipe',r'Edit recipe',r'cdc-recipe-import-card',r'CDCRecipeImporter',r'CDCRecipeWorkspace']
for path in paths:
 if not path.exists():continue
 s=path.read_text(encoding='utf-8')
 print(f'\n######### FILE {path} size={len(s)} #########')
 for pattern in patterns:
  matches=list(re.finditer(pattern,s,re.I))
  if not matches:continue
  print(f'==== {pattern} matched {len(matches)} ====')
  for m in matches[:3]:
   a=max(0,m.start()-600);b=min(len(s),m.end()+3800)
   print(f'OFFSET {m.start()}:\n{s[a:b]}')
