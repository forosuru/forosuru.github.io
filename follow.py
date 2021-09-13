#!/usr/bin/env python3

import os
import sys
import json
import time
import socket
import requests
import yaml
from credentials import *

# ... credentials.py looks like this
#
# github_token            = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
# intra_uid               = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
# intra_secret            = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
#

github_headers = {"Authorization": "token " + github_token}
intra_token_file = "intra_token.json"
intra_oauth_url = "https://api.intra.42.fr/oauth/token"
intra_oauth_payload = {
    "grant_type": "client_credentials",
    "client_id": intra_uid,
    "client_secret": intra_secret,
}


def intra_get_token():  # returns token string or None
    if os.path.isfile(intra_token_file):
        with open(intra_token_file, "r") as fp:
            data = json.load(fp)
            fp.close()
        if data["created_at"] + data["expires_in"] > time.time():
            return data["access_token"]
    r = requests.post(intra_oauth_url, data=intra_oauth_payload)
    if r.status_code != 200:
        return None
    with open(intra_token_file, "w") as fp:
        fp.write(r.text)
        fp.close()
    data = json.loads(r.text)
    return data["access_token"]


def intra_is_valid_user(user):
    if not user:
        return False
    token = intra_get_token()
    if not token:
        print("failed to get intra token")
        return False
    headers = {"Authorization": "Bearer " + token}
    url = "https://api.intra.42.fr/v2/users/" + user
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return True
    else:
        return False


def github_check_user(user):
    url = "https://api.github.com/users/" + user
    r = requests.get(url, headers=github_headers)
    if r.status_code == 200:
        return (True, json.loads(r.text))
    else:
        print("github response code", r.status_code)
        return (False, None)


def github_follow(user):
    url = "https://api.github.com/user/following/" + user
    r = requests.put(url, headers=github_headers)  ## PUT
    if r.status_code == 204:
        return True
    else:
        return False


def is_online(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except:
        return False


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: github_name intra_name")
    if not is_online():
        sys.exit("offline")

    github_valid, gh_data = github_check_user(sys.argv[1])
    if not github_valid:
        sys.exit("invalid github user")
    print("github user ok")
    intra = sys.argv[2].lower()
    if not intra_is_valid_user(intra):
        sys.exit("invalid intra user")
    print("intra user ok")
    if not os.path.isfile("_data/users.yml"):
        sys.exit("_data/users.yml does not exist")

    with open("_data/users.yml", "r+") as fp:
        users = yaml.load(fp)
        if users == None:
            print("creating new yaml dict")
            users = {}

        record = {
            "avatar_url": gh_data["avatar_url"],
            "login": gh_data["login"],
            "node_id": gh_data["node_id"],
            "intra": intra,
            "event_counts": {
                "follow": 0,
                "fork": 0,
                "public": 0,
                "repo": 0,
                "watch_started": 0,
                "total": 0,
            },
        }

        uid = int(gh_data["id"])
        if uid in users:
            print("updating existing record")
        else:
            print("creating new record")
            users[uid] = record  # do not overwrite existing event counts

        fp.seek(0, 0)  # move file pointer
        yaml.dump(users, fp, default_flow_style=False)
        fp.close()

    print("file updated")

    if github_follow(gh_data["login"]):
        print("user followed")
    else:
        print("follow KO!!")
