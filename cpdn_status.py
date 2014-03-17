import urllib2
import datetime
import itertools
import time
import os

from file_util import *
import parse_server_status

from jinja2 import Template

import logging
logger = logging.getLogger('cpdn_status')

def strfdelta(total_seconds):
    hours, remainder = divmod(total_seconds, 60*60)
    minutes, seconds = divmod(remainder, 60)
    ret = ''
    if hours != 0:
        ret += '{:.0f} hour'.format(hours)
        if hours > 1:
            ret += 's'
    if minutes != 0:
        ret += ' {:.0f} minute'.format(minutes)
        if minutes > 1:
            ret += 's'
    ret += ' {:.0f} second'.format(seconds)
    if seconds != 1:
        ret += 's'
    return ret

def main():
    now = time.time()
    server_status = 'cache/server_status.html'
    age = file_age(server_status, now=now)
    old = age > 1*60*60 # 1 hour
    if old:
        logger.debug('Fetching %s', server_status)
        response = urllib2.urlopen('http://climateapps2.oerc.ox.ac.uk/cpdnboinc/server_status.html')
        html = response.read()
        write_file(html, server_status)
        age = 0
    else:
        html = read_file(server_status)

    ready_to_send, in_progress = parse_server_status.parse(html)
    table = list(itertools.chain(ready_to_send, in_progress))

    csv = 'storage/server_status.csv'
    if old:
        if not(os.path.isfile(csv)): 
           header = ["%s" % row[0] for row in table]
           header = ", ".join(header)
           logger.debug('Adding "%s" to server_status.csv', header)
           append_line_file(header, csv)

        new_data = ["%s" % row[1] for row in table]
        new_data.insert(0, "%d" % now)
        new_data = ", ".join(new_data)
        logger.debug('Adding "%s" to server_status.csv', new_data)
        append_line_file(new_data, csv)

    data = list(read_csv(csv))
    for row in data:
        try:
            row[0] = float(row[0])
        except ValueError:
            pass
    #now = strfdelta(age)
    now = time.ctime(now)
    template = Template(read_file('templates/server_status.html'))
    #r = render_template('server_status.html', now=now, table=table, data=data)
    r = template.render(now=now, table=table, data=data)
    write_file(r, 'output/server_status.html')
    #logger.debug(r)
    return r

if __name__ == '__main__':
    main()
