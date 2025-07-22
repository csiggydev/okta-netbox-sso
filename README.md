# Okta NetBox SSO Mapper

Configure NetBox Docker to authenticate users via Okta SSO using OAuth2 and dynamically assign them to NetBox groups based on their Okta group membership.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Okta Setup](#okta-setup)
4. [NetBox Docker Configuration](#netbox-docker-configuration)
5. [Logging](#logging)
6. [Troubleshooting](#troubleshooting)
7. [Documentation](#documentation)

---

## Overview

This setup uses the `social-auth-app-django` backend provided by NetBox to integrate with Okta for SSO. A custom script is implemented to assign users to internal NetBox groups based on their membership in Okta groups returned via OAuth.

## Prerequisites

- NetBox Docker installation (`v4.2.7` or compatible)
- A registered Okta OIDC application
- Existing (local) NetBox groups (e.g., `NetBox Admins`, `NetBox Viewers`)

## Okta Setup

1. Create a new **Oauth2 Web Application** in Okta.
2. Set:
   - **Login redirect URI**: `https://<netbox-url>/oauth/complete/okta-oauth2/`
   - **Logout redirect URI**: `https://<netbox-url>/logout/`
3. Assign the app to the appropriate Okta groups.
4. In the Okta app's **General > Groups claim**, add a claim:
   - **Name**: `groups`
   - **Filter**: Starts with `Okta-Group-`
   - Include it in the ID token

> [!NOTE]
> Created Okta Group names must be specified as script constants.

## NetBox Docker Configuration

### Directory layout

```bash
configuration/
├── okta_netbox_sso.py   <--- Script to handle Okta/NetBox group mapping
├── configuration.py
├── extra.py
├── ldap
│   ├── extra.py
│   └── ldap_config.py
├── logging.py
└── plugins.py

1 directory, 7 files
```

In your NetBox Docker project:

#### 1. Add dependencies

Ensure `social-auth-app-django` is installed (already bundled with official NetBox Docker):

#### 2. Add script file to configuration alongside configuration.py and/or extra.py

>[!IMPORTANT]
> For custom scripts, location is important if NetBox is to process it.

#### 3. Reference script function in `extra.py`

Relevant configuration in **extra.py**

```yaml
LOGIN_REQUIRED = True
REMOTE_AUTH_ENABLED = True
REMOTE_AUTH_BACKEND = 'social_core.backends.okta.OktaOAuth2'
SOCIAL_AUTH_OKTA_OAUTH2_KEY = 'redacted'
SOCIAL_AUTH_OKTA_OAUTH2_SECRET = 'redacted'
SOCIAL_AUTH_OKTA_OAUTH2_API_URL = 'https://<your-domain>/oauth2/'
SOCIAL_AUTH_REDIRECT_IS_HTTPS = True
SOCIAL_AUTH_OKTA_OAUTH2_SCOPE = ['openid', 'profile', 'email', 'groups']

SOCIAL_AUTH_PIPELINE = [
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.social_auth.associate_by_email',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'netbox.authentication.user_default_groups_handler',
    "okta_netbox_sso.map_okta_groups_to_netbox_groups",     # maps to okta_netbox_sso.py function
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
]
```

#### 4. NetBox Groups

Create local NetBox groups using the `superuser` or admin equivalent. Okta groups will map to these.

>[!WARNING]
> NetBox group names are **case sensitive**

## Logging

Extensive logging was used to debug the implementation. To increase logging level in Docker, set environment variable `DB_WAIT_DEBUG=1` in `env/netbox.env`

For Python logging, the standard `logging` library was used.

1. Import logger and set level to `Informational`

>[!NOTE]
> To tail logs in docker, use the following command: `docker compose logs -f netbox`

### Expected Output

**Admin:**

```log
netbox-1  | [2025-04-18 17:23:18] INFO [netbox.auth:52] Invoking function: map_okta_groups_to_netbox_groups
netbox-1  | [2025-04-18 17:23:18] INFO [netbox.auth:61] Okta groups received: ['Domain-Grp-Admins-SSO', 'TEST-Admin-grp']
netbox-1  | [2025-04-18 17:23:18] INFO [netbox.auth:79] Skipping Okta group 'Domain-Grp-Admins-SSO' (SSO group) ** Optional if there's nested grouping **
netbox-1  | [2025-04-18 17:23:18] INFO [netbox.auth:88] Processing Okta group: Domain-Grp-Admins-SSO, Mapping to NetBox group: TEST-Admin-grp
netbox-1  | [2025-04-18 17:23:18] INFO [netbox.auth:93] Resolved group 'NetBox Admins' to instance: NetBox Admins (type: <class 'users.models.users.Group'>)
netbox-1  | [2025-04-18 17:23:18] INFO [netbox.auth:99] Assigned group 'NetBox Admins' to user.
```

**Viewer:**

```log
netbox-1  | [2025-04-18 17:23:18] INFO [netbox.auth:52] Invoking function: map_okta_groups_to_netbox_groups
netbox-1  | [2025-04-18 17:23:18] INFO [netbox.auth:61] Okta groups received: ['Domain-Grp-Admins-SSO', 'TEST-Users-grp']
netbox-1  | [2025-04-18 17:23:18] INFO [netbox.auth:79] Skipping Okta group 'Domain-Grp-Admins-SSO' (SSO group) ** Optional if there's nested grouping **
netbox-1  | [2025-04-18 17:23:18] INFO [netbox.auth:88] Processing Okta group: TEST-Users-grp, Mapping to NetBox group: NetBox Viewers
netbox-1  | [2025-04-18 17:23:18] INFO [netbox.auth:93] Resolved group 'NetBox Viewers' to instance: NetBox Viewers (type: <class 'users.models.users.Group'>)
netbox-1  | [2025-04-18 17:23:18] INFO [netbox.auth:99] Assigned group 'NetBox Viewers' to user.
```

## Troubleshooting

This section is a work in progress.

## Documentation

### Okta

- OAuth and OpenID: https://developer.okta.com/docs/concepts/oauth-openid/

### NetBox

- SSO Integration: https://netboxlabs.com/docs/netbox/en/stable/administration/authentication/okta/
- Integrating Okta SSO w/ NetBox: https://www.oasys.net/posts/okta-sso-with-netbox
