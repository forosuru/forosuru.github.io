#!/usr/bin/env python3

import sys, os, glob, yaml
from copy import deepcopy


def symlink_events_to_posts():
    if not os.path.exists("_events/"):
        sys.exit("_events/ not found")
    if not os.path.exists("_posts/"):
        sys.exit("_posts/ not found")
    os.chdir("_posts/")
    for fn in glob.glob("../_events/**/*.html", recursive=True):
        symlink = fn[11:].replace("/", "-")
        os.symlink(fn, symlink)


def write_event_counts_to_users_file():

    event_counts = {
        "follow": 0,
        "fork": 0,
        "public": 0,
        "repo": 0,
        "watch_started": 0,
        "total": 0,
    }

    users = None
    with open("_data/users.yml") as fp:
        users = yaml.load(fp)
        fp.close()

    for uid in users:
        users[uid]["event_counts"] = deepcopy(event_counts)

    for fn in glob.glob("_posts/*.html"):
        data = None
        with open(fn) as fp:
            data = fp.read().split("\n---\n")[0]
            fp.close()
        e = yaml.load(data)
        uid = int(e["author_id"])
        users[uid]["event_counts"][e["event_type"]] += 1
        users[uid]["event_counts"]["total"] += 1

    with open("_data/users.yml", "w") as fp:
        yaml.dump(users, fp, default_flow_style=False)
        fp.close()


def write_stats_file():

    data = [
        "---",
        "layout: default",
        "---",
        '<script type="text/javascript" src="https://code.jquery.com/jquery-3.3.1.min.js"></script>',
        '<link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/v/dt/dt-1.10.18/datatables.min.css"/>',
        '<script type="text/javascript" src="https://cdn.datatables.net/v/dt/dt-1.10.18/datatables.min.js"></script>',
        "<script>",
        "$(document).ready( function () {",
        '    $("#table_id").DataTable()',
        "} );",
        "</script>",
        '<table id="table_id" class="display">',
        "<thead><tr> <th>user</th> <th>create</th> <th>follow</th> <th>fork</th> <th>public</th> <th>star</th> </tr></thead>",  # XXX column names
        "<tbody>",
    ]

    users = None
    with open("_data/users.yml") as fp:
        users = yaml.load(fp)
        fp.close()

    for k in users:
        v = users[k]
        if v["event_counts"]["total"] < 1:
            continue

        user_img = (
            '<img src="%s" style="margin-right: 5px; width: 20px; height: 20px">'
            % (v["avatar_url"],)
        )
        user_link = '<div style="display: flex;"> <a class="link-gray-dark no-underline text-bold wb-break-all" style="font-size: 12px; display: contents"'
        user_link += ' href="{{ site.this_site }}/user/%s.html">%s%s</a></div>' % (
            v["login"],
            user_img,
            v["login"],
        )
        ec = v["event_counts"]
        row = (
            "<tr> <td>%s</td> <td>%d</td> <td>%d</td> <td>%d</td> <td>%d</td> <td>%d</td> </tr>"
            % (
                user_link,
                ec["repo"],
                ec["follow"],
                ec["fork"],
                ec["public"],
                ec["watch_started"],
            )
        )
        data.append(row)

    data.append("</tbody></table>")

    with open("stats.html", "w") as fp:
        fp.write("\n".join(data))
        fp.close()
