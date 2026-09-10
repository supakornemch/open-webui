# QAS Fabric Delegated User Token Experiment — Cloud Admin Runbook

## Scope

This enables the separate Open WebUI tool `fabric_query_delegated_user_qas` to receive the signed-in user's Microsoft OAuth token for Azure SQL / Fabric SQL. The existing Service Principal tool is unchanged.

## Prerequisites already prepared

- QAS App Registration client ID: `00ba48a9-111e-476f-9c45-ca9964595828`
- Delegated API permission requested: Azure SQL Database (`022907d3-0f1b-48f7-badc-1ba6abab6d66`) / `user_impersonation` (`c39ef2d1-04ce-46dc-8b5f-e9a5c60f0fc9`)
- QAS Web App: `app-entchat-owui-qas`
- Resource group: `RG-INCUBATION-AI-QAS-SEA`

## Cloud Admin commands

```bash
# 1) Make Open WebUI ask Entra for a delegated Azure SQL token.
az webapp config appsettings set \
  --resource-group RG-INCUBATION-AI-QAS-SEA \
  --name app-entchat-owui-qas \
  --settings \
  'MICROSOFT_OAUTH_SCOPE=openid email profile offline_access https://database.windows.net/user_impersonation'

# 2) Restart QAS Open WebUI so the new OAuth scope is active.
az webapp restart \
  --resource-group RG-INCUBATION-AI-QAS-SEA \
  --name app-entchat-owui-qas
```

If tenant policy requires explicit admin consent, an Entra Global Administrator or Privileged Role Administrator must run:

```bash
az ad app permission grant \
  --id 00ba48a9-111e-476f-9c45-ca9964595828 \
  --api 022907d3-0f1b-48f7-badc-1ba6abab6d66 \
  --scope user_impersonation
```

The project operator received `Insufficient privileges to complete the operation`, so this consent step is still outstanding. The same action can be completed in Entra ID > App registrations > API permissions > Grant admin consent.

## User re-consent

All testers must sign out of QAS Open WebUI and sign in again. Existing `oauth_session` records contain the old Microsoft Graph token and cannot gain the new audience without reauthorization.

## Expected token claims

The tool fails closed unless the Open WebUI-injected `__oauth_token__.access_token` contains:

- `aud`: `https://database.windows.net` (or Azure SQL application ID)
- `tid`: `5045d9c3-3b0b-4315-8594-64118bbd7495`
- `oid`: immutable end-user object ID
- `scp`: includes `user_impersonation`

The tool has no Service Principal, managed identity, static token, or Azure CLI fallback.

## Smoke test

Attach only the new tool and ask:

```text
Use query_fabric_delegated to run:
SELECT TOP 1 BillingDate
FROM dv.mlv_sale_preformance_aggregate
ORDER BY BillingDate DESC
```

Expected success prefix:

```text
Delegated user <UPN> (oid: <user-object-id>)
```

Expected failures are explicit (`wrong audience`, `missing delegated scope`, `unapproved tenant`, or Fabric permission denied). Do not add a Service Principal fallback to make a failed user query pass.
