from pathlib import Path
import shutil

app_dir = Path('app')
shutil.copyfile('supabase_storage_override.py', app_dir / 'drive_storage.py')
shutil.copyfile('settings_supabase_override.js', app_dir / 'settings_pro_patch.js')

app_py = app_dir / 'app.py'
text = app_py.read_text()
old = '"googleDriveConfigured": bool(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") and os.environ.get("GOOGLE_DRIVE_FOLDER_ID")),'
new = '"supabaseStorageConfigured": bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY")),'
if old not in text:
    raise SystemExit('Expected Google Drive config marker not found in app.py')
app_py.write_text(text.replace(old, new))
