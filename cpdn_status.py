# Standard python imports
import urllib2
import itertools
import datetime
import os
import logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M")
logger = logging.getLogger('cpdn_status')
logger.setLevel(logging.INFO)
# Non-standard python
from jinja2 import Template
# This project:
from file_util import *
from database_util import Database
import parse_server_status

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
    #csv = join(root, 'storage', page.replace('.html', '.csv'))
    database_name = join(root, 'storage', page.replace('.html', '.sqlite'))
    table_name = page.replace('.html', '')
    database = Database(database_name, table_name)
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
    else:
        html = read_file(cache)

    ready_to_send, in_progress = parse_server_status.parse(html)
    print 'READY', ready_to_send
    print 'INPROG', in_progress
    new_entries = list()
    table = list(itertools.chain(ready_to_send, in_progress))
    for entry in table:
        new_entries.append((entry[0], now, entry[1])) # name, time, count

    if old:
        database.insert(new_entries)

    header, data = database.select_column_view(exclude=('Tasks in progress', 'Total  Tasks ready to send'))
    header_in_progress, data_in_progress = database.select_column_view(include_only=['Tasks in progress'])

    now_str = str(now_datetime)

    t = Template(read_file(template))
    age_str = str(datetime.timedelta(seconds=age))
    r = t.render(now=now, now_str=now_str, table=table, fetch_failed=fetch_failed, age_str=age_str,
                 header=header, data=data, header_in_progress=header_in_progress, data_in_progress=data_in_progress)
    write_file(r, output)

    return r

if __name__ == '__main__':
    main()
