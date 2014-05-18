import urllib2
import itertools
import datetime
import os

from file_util import *
import parse_server_status

from jinja2 import Template

import subprocess
import logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M")
logger = logging.getLogger('cpdn_status')
logger.setLevel(logging.DEBUG)

join = os.path.join
root = os.path.dirname(os.path.abspath(__file__))

def utc_now():
    """From http://stackoverflow.com/questions/15940280/utc-time-in-python
    Seconds since 1970.1.1 in UTC.
    """
    now_datetime = datetime.datetime.utcnow()
    td = (now_datetime - datetime.datetime(1970, 1, 1))
    now_datetime = now_datetime.replace(microsecond=0)
    # backward compatible to timedelta.total_seconds() according to documentation.
    return now_datetime, (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6

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

    fetch_failed = False
    now_datetime, now = utc_now()
    age = file_age(cache, now=now)
    old = age > 0.1*60*60 # 0.1 hour
    if old:
        html = get_html('http://climateapps2.oerc.ox.ac.uk/cpdnboinc/' + page, cache)
        if html == '': # fetch failed
            old = False
            fetch_failed = True
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
    ix = 0
    while ix < len(data):
        row = data[ix]
        if len(row) != 9:
            logger.warning('Illegal row, %s %d', row, len(row))
            del data[ix]
        else:
            ix += 1

        try:
            row[0] = float(row[0])
        except ValueError:
            pass

    now_str = str(now_datetime)

    t = Template(read_file(template))
    age_str = str(datetime.timedelta(seconds=age))
    r = t.render(now=now, now_str=now_str, table=table, data=data, fetch_failed=fetch_failed, age_str=age_str)
    write_file(r, output)

    return r

if __name__ == '__main__':
    main()
