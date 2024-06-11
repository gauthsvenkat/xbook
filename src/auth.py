import json

import requests


def auth(username, passw):
    """
    Authenticates through X's authentication portal for non-TUD users.
    """
    auth_url = "https://backbone-web-api.production.delft.delcom.nl/auth"

    s = requests.Session()
    r0 = s.post(auth_url, data={"email": username, "password": passw})

    # Extract and set authorisation headers
    tokens = json.loads(r0.text)
    s.headers["authorization"] = f"Bearer {tokens['access_token']}"
    s.headers["authority"] = "backbone-web-api.production.delft.delcom.nl"

    # Authenticated requests now allow us to obtain user information
    member_id = json.loads(s.get(auth_url).text)["id"]

    return (s, tokens["access_token"], member_id)


def terminate_session(s):
    """
    Cleanly terminates the given session `s` by closing it.
    """
    # TODO: Cleanly log out of X's backend if required
    s.close()
