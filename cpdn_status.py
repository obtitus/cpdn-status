import urllib2
import datetime
import itertools
import time
import os

from file_util import *
import parse_server_status

from jinja2 import Template

import subprocess
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('cpdn_status')
logger.setLevel(logging.DEBUG)

join = os.path.join
root = os.path.dirname(os.path.abspath(__file__))

def get_html(url, cache):
    logger.debug('Fetching %s', url)
    try:
        response = urllib2.urlopen(url)
        html = response.read()
    except:
        logger.exception('Fetch failed:')
        return ''
    write_file(html, cache)
    return html

def main(page='server_status.html'):
    cache = join(root, 'cache', page)
    csv = join(root, 'storage', page.replace('.html', '.csv'))
    template = join(root, 'templates', page)
    output = join(root, 'output', page)

    now = time.time()
    age = file_age(cache, now=now)
    old = age > 0.1*60*60 # 0.1 hour
    if old:
        html = get_html('http://climateapps2.oerc.ox.ac.uk/cpdnboinc/' + page, cache)
        if html == '': # fetch failed
            old = False
        else:
            age = 0
    if not(old):
        html = read_file(cache)

    ready_to_send, in_progress = parse_server_status.parse(html)
    table = list(itertools.chain(ready_to_send, in_progress))

    if old:
        if not(os.path.isfile(csv)): 
           header = ["%s" % row[0] for row in table]
           new_data.insert(0, 'date')
           header = ", ".join(header)
           logger.debug('Adding "%s" to %s', header, csv)
           append_line_file(header, csv)

        new_data = ["%s" % row[1] for row in table]
        new_data.insert(0, "%d" % now)
        new_data = ", ".join(new_data)
        logger.debug('Adding "%s" to %s', new_data, csv)
        append_line_file(new_data, csv)

    data = list(read_csv(csv))
    for row in data:
        try:
            row[0] = float(row[0])
        except ValueError:
            pass

    now_str = time.ctime(now-age)

    t = Template(read_file(template))
    r = t.render(now_str=now_str, now=now, table=table, data=data)
    write_file(r, output)
    #logger.debug(r)

    return r

if __name__ == '__main__':
    main()
