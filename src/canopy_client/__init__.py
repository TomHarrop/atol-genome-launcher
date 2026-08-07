#!/usr/bin/env python3

from urllib.parse import urljoin

from common import check_env_var
import requests


class CanopySession(requests.Session):
    def __init__(self, base_url: str = None):
        super().__init__()
        self.base_url = base_url

    def request(self, method, url, *args, **kwargs):
        base_url = self.base_url + ("/" if not self.base_url.endswith("/") else "")
        joined_url = urljoin(base_url, url)
        return super().request(method, joined_url, *args, **kwargs)


def canopy_login() -> CanopySession:
    """
    Open an authorised session on the Canopy API. Credentials are parsed from
    the environment.
    """

    canopy_base_url = check_env_var("CANOPY_BASE_URL")
    canopy_username = check_env_var("CANOPY_USERNAME")
    canopy_password = check_env_var("CANOPY_PASSWORD")

    _auth_login = "auth/login"

    s = CanopySession(base_url=canopy_base_url)

    login = s.post(
        _auth_login,
        data={"username": canopy_username, "password": canopy_password},
    )

    # Stop if login failed
    login.raise_for_status()

    canopy_token = login.json().get("access_token")

    auth_header = {"Authorization": f"Bearer {canopy_token}"}

    s.headers.update(auth_header)

    return s
