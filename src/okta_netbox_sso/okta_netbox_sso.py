#!/usr/bin/env/python

"""
Description:
    Map Okta SSO Groups to NetBox Groups

Requirements:
    - requirements.txt

Notes:
    - Tested on NetBox Community v4.2.7-Docker-3.2.0

Documentation:
    Django: 
        - Auth: https://docs.djangoproject.com/en/5.1/ref/contrib/auth/
        - Exceptions: https://docs.djangoproject.com/en/5.1/ref/exceptions/
"""

from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
import logging
logger = logging.getLogger("netbox.auth")
logger.setLevel(logging.INFO)
from rich.logging import RichHandler

# Rich Logging
LOG_FORMAT = '%(asctime)s %(levelname)s: %(message)s'
logging.basicConfig(
    format=LOG_FORMAT,
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[RichHandler()]
)

GROUP_MAPPINGS = {
    "TEST-Admin-grp": {
        "group_name": "NetBox Admins",
        "is_superuser": True,
        "is_staff": True,
    },
    "TEST-Users-grp": {
        "group_name": "NetBox Viewers",
        "is_staff": True,
    }
}

def map_okta_groups_to_netbox_groups(backend, user, response, *args, **kwargs):
    """
    Description:
        Maps Okta groups to local NetBox groups
            - '-Users' mapped to NetBox Viewers
            - '-Admin' mapped to NetBox Admins
    Args:
        backend (str)
        user (str)
        response

    Notes:
        *Import django functions here because netbox container fails upon global import
    """
    logger.info("Invoking function: %s", map_okta_groups_to_netbox_groups.__name__)

    SKIP_GROUP = "<Placeholder for groups to skip, if any>"

    okta_groups = response.get('groups', [])
    logger.info("Okta groups received: %s", okta_groups)

    if not okta_groups:
        user.groups.clear()
        user.is_staff = False
        user.is_superuser = False
        logger.warning("User has no Okta groups; all NetBox groups cleared")
        user.save()
        return

    # Clear groups before assignment
    user.groups.clear()

    for okta_group in okta_groups:
        if okta_group == SKIP_GROUP:
            logger.info(f"Skipping Okta group '{okta_group}' (SSO group)")
            continue

        mapping = GROUP_MAPPINGS.get(okta_group)
        if not mapping:
            logger.info(f"Unmapped Okta group: {okta_group}")
            continue

        group_name = mapping["group_name"]
        logger.info(f"Processing Okta group: {okta_group}, Mapping to NetBox group: {group_name}")

        try:
            group_instance = user.groups.model.objects.get(name=group_name)
            # django object check
            logger.info(f"Resolved group '{group_name}' to instance: {group_instance} (type: {type(group_instance)})")
        except ObjectDoesNotExist:
            logger.error(f"NetBox group '{group_name}' does not exist")
            continue

        user.groups.add(group_instance)
        logger.info(f"Assigned group '{group_name}' to user.")

        if mapping.get("is_staff"):
            user.is_staff = True
        if mapping.get("is_superuser"):
            user.is_superuser = True

    user.save()
    logger.info(f"User groups after assignment: {user.groups.all()}")
