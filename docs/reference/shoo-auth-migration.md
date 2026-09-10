# Shoo ownership migration

Shoo auth never assigns existing private data from an email or display name. Those claims may be absent and are not ownership keys.

## Existing single-profile deployment

1. Back up `data/career_os.db` and persistent `data/` volume.
2. Deploy migration `x6y7z8a9b0c1`. Existing profiles remain intact with `account_id = NULL`.
3. Set exact browser origin and enable one-time claim:

   ```env
   SHOO_AUTH_ENABLED=true
   SHOO_APP_ORIGIN=https://your-kestrel-origin.example
   SHOO_CLAIM_LEGACY_DATA=true
   ```

4. Sign in once with intended owner Google account through Shoo. Kestrel assigns every unowned legacy profile to verified `pairwise_sub` account in one transaction.
5. Confirm private data appears. Set `SHOO_CLAIM_LEGACY_DATA=false` and restart.
6. Keep backup until normal reads and writes pass.

Never leave claim flag enabled on shared or internet-reachable deployment. Later accounts receive new empty profiles and cannot access claimed records.

## Fresh deployment

Leave `SHOO_CLAIM_LEGACY_DATA=false`. First verified login creates account-owned profile. No claim step needed.

## Rollback

Restore backup before migration. Downgrade drops ownership/session tables and `profiles.account_id`; it does not delete existing profile-owned records.
