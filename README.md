# Command de Cuisine

Kitchen-management web app for recipes, allergens, temperatures, cleaning,
stock, ordering, staff and reports. The production web service is deployed from
the [Render Blueprint](render.yaml).

## Data and release architecture

- PostgreSQL (through the configured `DATABASE_URL`) is the authoritative
  shared store for per-venue app state, staff accounts and audit records.
- Temperature readings and equipment-status events have their own
  `tenant_temperature_readings` table. Do **not** treat
  `venue_states.state.tempReadings` as the authoritative temperature archive.
- Supabase Storage stores tenant-separated document uploads and JSON backups.
  The service uses `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (secret) and
  `SUPABASE_STORAGE_BUCKET`. Keep service-role credentials server-side only.
- Backups include both venue app state and authoritative temperature history.
  Backups are written after the first successful state save of each UTC day
  *per running process*, and managers can request a backup from Settings.
  Backup creation depends on working Storage configuration and connectivity.
  **Restoring a backup has not been validated as an automated workflow.**
- The present release builds from
  `Command-de-Cuisine-clean-production.zip` followed by ordered patch scripts
  in `render.yaml`. Keep changes last-stage and fail-closed until the app is
  refactored into maintained source modules.

## Owner/manager handover

1. Open https://command-de-cuisine.onrender.com and enter the
   **username**, not a display name, plus the password issued by the venue
   manager. Usernames are case-insensitive.
2. If a team member cannot sign in, a logged-in manager can visit **Team**,
   select the person and use **Set / reset password** to issue a temporary
   password of 10 or more characters. Give it to that person privately;
   they can use **Change password** after signing in. Never share passwords
   in support tickets, messages or screenshots.
3. Start with **Temperatures**, record actual fridge/freezer readings, and
   choose an equipment status with a fault/action note if an appliance is
   not working. Historical corrections and voids require manager access.
4. Use **Daily** for opening/closing checks and cleaning tasks.
5. Under **Recipes**, tap a recipe to review ingredients and allergies.
   **Update from photo / notes** may create unverified drafts, not approved
   allergen declarations. A manager must confirm allergens using the actual
   ingredient label or supplier specification.
6. **Stock** is a catalogue until counted quantities, par levels and
   suppliers have been entered. The downloadable ordering sheet is a
   standalone editable file; it does not submit orders or update stock.
7. In **Reports**, distinguish recorded results from missing/unfinished
   checks. Do not use AI-created recipe costs, prices or allergen drafts as
   verified operational values.

## Important role rules

- Kitchen staff can log current-day temperatures, cleaning and operational
  data.
- Managers are responsible for protected allergen attestations, historical
  temperature corrections, deletion of saved temperature records and manager
  sign-offs.
- Changing or deleting a safety record must not masquerade as a new
  measurement. Temperature corrections use the existing audited manager API.

## Developer checks

The `.github/workflows/kitchen-safety-regression.yml` workflow builds the
exact Render release, validates role and backup protections, and browser-tests
recipe editing on desktop/mobile without touching production data.

Other regression suites cover timers, ordering sheet exports and unified recipe
editing. Do not merge or deploy a failing build. Verify production
`/api/health` and the expected current client scripts after a merge.

## Deployment configuration

See `render.yaml` for the Python version, Render service and environment
variables. Never commit `DATABASE_URL`, `SESSION_SECRET`, API keys or the
Supabase service role key.

The README previously described Google Drive backups; the current production
build uses **Supabase Storage**.
