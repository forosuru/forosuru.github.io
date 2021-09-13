#!/usr/bin/env python3

from bs4 import BeautifulSoup
import requests
import datetime, time, dateutil.parser
import socket, os, sys, re, yaml
import utils

prefix_dir = "_events/"
event_file_extension = ".html"
github_atom_url = "https://github.com/forosuru.private.atom?token=ArlnHUjh_30W3gk2EN-ScgRQ3n5_kw8Lks66K7xnwA=="

debug = True


def events_from_xml_string(data):
    soup = BeautifulSoup(data, "lxml-xml")
    res = []
    for e in soup.find_all("entry"):
        mtu = e.find("media:thumbnail")["url"]
        author_id = re.search("githubusercontent\.com\/u\/(\d+)", mtu)[1]
        elink = e.find("link")["href"]
        etitle = e.find("title").text
        eid = e.find("id").text.split("/")[1]
        econtent = e.find("content").text
        cnt = BeautifulSoup(econtent, features="html.parser")
        event_type = cnt.div["class"][0]
        language = "None"
        spanlang = cnt.find("span", {"itemprop": "programmingLanguage"})
        if spanlang:
            language = spanlang.get_text().strip()
        eauthor = e.find("author").find("name").text
        edate = e.find("published").text
        event = {
            "link": elink,
            "title": etitle,
            "id": eid,
            "content": econtent,
            "author_name": eauthor,
            "date": edate,
            "author_id": author_id,
            "type": event_type,
            "language": language,
        }
        res.append(event)
    return res


# logic: list all events by id ascending (asc in case they changed name multiple times, get last)
# for each event
#   if language does not exist in _lang/ then create it
#   get user data from yml dictionary by author_id
#   if github_name from yml file does not match event author name:
#       delete _user/github_name.html file
#       update yml dictionary with new github_name
#   if _user/github_name.html does not exist, create it
#   update event counts in yml dict
# save updated yml dictionary to disk


def language_filename(lang):
    tr = {
        "+": "plus",
        "#": "sharp",
        "*": "star",
        "'": "",
    }  # C++ => Cplusplus, C# => Csharp, F* => Fstar
    lang_tr = ""
    for c in list(lang):
        if c.isalnum():
            lang_tr += c
        else:
            if c in tr:
                lang_tr += tr[c]
            else:
                lang_tr += "_"
    return "_lang/" + lang_tr + ".html"


def lang_fwrite(lfn, lang):
    data = [
        "---",
        "layout: default",
        "language: " + lang,
        "filename: " + os.path.basename(lfn),
        "---",
        '{% assign events = site.events | where: "language","'
        + lang
        + '" | sort: "date" | reverse %}',
        "{% for event in events %}",
        "{{ event.content }}",
        "{% endfor %}",
    ]
    with open(lfn, "w") as fp:
        fp.write("\n".join(data))
        fp.close()


def user_fwrite(fn, uid, u):
    data = [
        "---",
        "layout: default",
        "intra: " + u["intra"],
        "login: " + u["login"],
        "id: " + str(uid),
        "avatar_url: " + u["avatar_url"],
        "---",
        '{% assign events = site.events | where: "author_id","'
        + str(uid)
        + '" | sort: "date" | reverse %}',
        "{% for event in events %}",
        "{{ event.content }}",
        "{% endfor %}",
    ]

    with open(fn, "w") as fp:
        fp.write("\n".join(data))
        fp.close()


def update_pages(events):
    all_users = None
    with open("_data/users.yml", "r") as fp:
        all_users = yaml.load(fp)
        fp.close()

    for e in events:
        lfn = language_filename(e["language"])
        if e["language"] != "None":
            if not os.path.exists(lfn):
                lang_fwrite(lfn, e["language"])

        uid = int(e["author_id"])
        if all_users[uid]["login"] != e["author_name"]:
            ufn = "_user/" + all_users[uid]["login"] + ".html"
            if os.path.exists(ufn):  # if they changed their github name
                os.unlink(ufn)  # remove existing file
            all_users[uid]["login"] = e["author_name"]

        all_users[uid]["event_counts"][e["type"]] += 1
        all_users[uid]["event_counts"]["total"] += 1

        ufn = "_user/" + all_users[uid]["login"] + ".html"
        if not os.path.exists(ufn):
            user_fwrite(ufn, uid, all_users[uid])

    with open("_data/users.yml", "w") as fp:
        yaml.dump(all_users, fp, default_flow_style=False)
        fp.close()


def fetch_events(page_num):  # page_num numeric page number
    url = github_atom_url + "&page=" + str(page_num)
    req = requests.get(url)
    if req.status_code == 200:
        data = req.content.decode("utf-8")
        return events_from_xml_string(data)
    else:
        if debug:
            print("feed_fetch_entries() failed, requests status code != 200")
        return None


def event_filename(datetime, event_id):
    dt = dateutil.parser.parse(datetime)
    return prefix_dir + dt.strftime("%Y/%m/%d/") + str(event_id) + event_file_extension


def event_mkdir(datetime):
    dt = dateutil.parser.parse(datetime)
    year_dir = prefix_dir + dt.strftime("%Y/")
    month_dir = prefix_dir + dt.strftime("%Y/%m/")
    event_dir = prefix_dir + dt.strftime("%Y/%m/%d/")
    if not os.path.exists(year_dir):
        os.makedirs(year_dir)
    if not os.path.exists(month_dir):
        os.makedirs(month_dir)
    if not os.path.exists(event_dir):
        os.makedirs(event_dir)


def symlink_event_to_posts(event_fn):
    # create a relative symlink from a file in _events/ to a file in _posts/
    # assuming we're in root folder that contains _events/
    if not os.path.exists("_events/"):
        return
    if "_events/" not in event_fn:
        return
    if event_fn.index("_events/") != 0:
        return
    if not os.path.exists(event_fn):
        return

    cwd = os.getcwd()
    if not os.path.exists("_posts/"):
        os.makedirs("_posts/")
    os.chdir("_posts/")
    symlink = event_fn[8:].replace("/", "-")
    os.symlink("../" + event_fn, symlink)
    os.chdir(cwd)


def event_fwrite(e, fn):
    fdata = [
        "---",
        "event_id: " + e["id"],
        "date: " + e["date"],
        "link: " + e["link"],
        "title: " + e["title"],
        "event_type: " + e["type"],
        "language: " + e["language"],
        "author_id: " + e["author_id"],
        "author_name: " + e["author_name"],
        "---",
        e["content"],
    ]
    event_mkdir(e["date"])
    with open(fn, "w") as fp:
        fp.write("\n".join(fdata))
        fp.close()
    symlink_event_to_posts(fn)  # make relative symlink XXX


def forosuru_update():
    i = 1
    done = False
    authors = set()
    new_events = []
    while not done:
        done = True
        events = fetch_events(i)
        i += 1
        for e in events:
            fn = event_filename(e["date"], e["id"])
            if not os.path.exists(fn):
                done = False
                event_fwrite(e, fn)
                authors.add(e["author_name"])
                new_events.append(e)
    update_pages(sorted(new_events, key=lambda k: k["id"]))
    utils.write_stats_file()
    return authors


def is_online(host="8.8.8.8", port=53, timeout=3):  # returns true if we can ping google
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except:
        return False


if __name__ == "__main__":
    if not is_online():
        if debug:
            print("offline")
        sys.exit()

    new_events = forosuru_update()  ## returns a set of event author names
    if new_events:
        commit_msg = "new activity from: " + ", ".join(sorted(list(new_events)))
        cmd = 'git add --all; git commit -m "' + commit_msg + '"; git push'
        print(cmd)
        os.system(cmd)
