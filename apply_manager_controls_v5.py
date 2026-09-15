from runpy import run_path

# Render's existing service build command still calls this legacy v5 step.
# Delegate it to the current contextual v6 installer so old global manager bars
# are removed and only Cleaning Schedule / Daily Checks receive controls.
run_path('apply_manager_context_v6.py', run_name='__main__')
