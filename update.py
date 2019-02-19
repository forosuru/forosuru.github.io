#!/usr/bin/env python3

from bs4 import BeautifulSoup
import requests
import datetime
import time
import dateutil.parser
import socket
import os
import re
import sys

prefix_dir = '_events/'
event_file_extension = '.html'
github_atom_url = 'https://github.com/forosuru.private.atom?token=ArlnHUjh_30W3gk2EN-ScgRQ3n5_kw8Lks66K7xnwA=='

debug = True

def events_from_xml_string(data):
    soup = BeautifulSoup(data, 'lxml-xml')
    res = []
    for e in soup.find_all('entry'):
        mtu = e.find('media:thumbnail')['url']
        author_id = re.search('githubusercontent\.com\/u\/(\d+)', mtu)[1] #stephen thinks regex is cool
        elink = e.find('link')['href']
        etitle = e.find('title').text
        eid  = e.find('id').text.split('/')[1]
        econtent = e.find('content').text
        cnt = BeautifulSoup(econtent, features='html.parser')
        event_type = cnt.div['class'][0]
        language = 'None'
        spanlang = cnt.find('span', {'itemprop': 'programmingLanguage'})
        if spanlang: language = spanlang.get_text().strip()
        eauthor = e.find('author').find('name').text
        edate = e.find('published').text            
        event = {
            'link':elink,
            'title':etitle,
            'id':eid,
            'content':econtent, 
            'author_name':eauthor,
            'date':edate,
            'author_id':author_id,
            'type':event_type,
            'language':language
            }
        res.append(event)
    return res

def fetch_events(page_num):   #page_num numeric page number
    url = github_atom_url + '&page=' + str(int(page_num))
    req = requests.get(url)
    if req.status_code == 200:
        data = req.content.decode('utf-8')
        return events_from_xml_string(data)
    else:
        if debug:
            print('feed_fetch_entries() failed, requests status code != 200')
        return None

def event_filename(datetime, event_id):
    dt = dateutil.parser.parse(datetime)
    return prefix_dir + dt.strftime("%Y/%m/%d/") + str(event_id) + event_file_extension

def event_mkdir(datetime):
    dt = dateutil.parser.parse(datetime)
    year_dir =  prefix_dir + dt.strftime("%Y/")
    month_dir = prefix_dir + dt.strftime("%Y/%m/")
    event_dir = prefix_dir + dt.strftime("%Y/%m/%d/")
    if not os.path.exists(year_dir):  os.makedirs(year_dir)
    if not os.path.exists(month_dir): os.makedirs(month_dir)
    if not os.path.exists(event_dir): os.makedirs(event_dir)

def event_fwrite(e, fn):
    fdata = [
        '---',
        'event_id: '    + e['id'],
        'date: '  	    + e['date'],
        'link: '        + e['link'],
        'title: '       + e['title'],
        'event_type: '  + e['type'],
        'language: '    + e['language'],
        'author_id: '   + e['author_id'],
        'author_name: ' + e['author_name'],
        '---',
        e['content']
    ]
    event_mkdir(e['date'])
    with open(fn, 'w+') as fp:
        fp.write('\n'.join(fdata))
        fp.close()


def forosuru_update():
    i = 1
    done = False
    authors = set()
    while not done:
        done = True
        events = fetch_events(i)
        for e in events:
            fn = event_filename(e['date'], e['id'])
            if not os.path.exists(fn):
                done = False
                event_fwrite(e, fn)
                authors.add(e['author_name'])
        i += 1
    return authors

def is_online(host="8.8.8.8", port=53, timeout=3):      # returns true if we can ping google
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except:
        return False

if __name__ == '__main__':
    if is_online():
        new_events = forosuru_update() ## returns a set of event author names
        if new_events:
            commit_msg = 'new activity from: ' + ', '.join(sorted(list(new_events)))
            cmd = 'git add --all; git commit -m "' + commit_msg + '"; git push'
            print(cmd)
            os.system(cmd)
    else:
        if debug:
            print('offline')

