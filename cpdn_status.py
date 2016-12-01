# Standard python imports
import urllib2
import itertools
import datetime
import os
import time
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

def utc_now(now_datetime=None):
    """From http://stackoverflow.com/questions/15940280/utc-time-in-python
    Seconds since 1970.1.1 in UTC.
    """
    if now_datetime is None:
        now_datetime = datetime.datetime.utcnow()
    td = (now_datetime - datetime.datetime(1970, 1, 1))
    now_datetime = now_datetime.replace(microsecond=0)
    # backward compatible to timedelta.total_seconds() according to documentation.
    return now_datetime, (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6

def get_html(url, cache, attempt=0):
    logger.debug('Fetching %s', url)
    try:
        response = urllib2.urlopen(url)
        html = response.read()
    except Exception as e:
        if attempt > 10:
            logger.error('Fetch %d failed: %s', attempt, e)
            return ''
        else:
            logger.warning('Fetch %d failed, trying again: %s', attempt, e)            
            time.sleep(5)
            return get_html(url, cache, attempt=attempt+1)
    
    write_file(html, cache)
    return html

def prettify_header(header):
    for ix in range(len(header)):
        header[ix] = header[ix].replace(' Tasks ready to send', '')
        if len(header[ix]) > 100:
            header[ix] = header[ix][:49] + '...' + header[ix][-49:]
            
    return header

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
        #html = get_html('http://climateapps2.oerc.ox.ac.uk/cpdnboinc/' + page, cache)
        html = get_html('https://www.cpdn.org/cpdnboinc/' + page.replace('.html', '.php'), cache)
        if html == '': # fetch failed
            old = False
            fetch_failed = True
        else:
            age = 0
    else:
        html = read_file(cache)

    ready_to_send, in_progress = parse_server_status.parse(html)
    new_entries = list()
    table = list(itertools.chain(ready_to_send, in_progress))

    if len(table) == 0:
        old = False
        fetch_failed = True
    #else:
    for entry in table:
        if int(entry[1]) != 0:
            new_entries.append((entry[0], now, entry[1])) # name, time, count

    if old:
        database.insert(new_entries)

    oldest_seconds = now - 60*60*24*182.5 # half a year
    header, data = database.select_column_view(oldest_seconds, exclude=('Tasks in progress', 'Total  Tasks ready to send'))
    header_in_progress, data_in_progress = database.select_column_view(oldest_seconds, include_only=['Tasks in progress'])

    now_str = str(now_datetime)

    # print data[0], datetime.datetime.utcfromtimestamp(data[0][0])
    # print data[-1], datetime.datetime.utcfromtimestamp(data[-1][0])
    # print len(data)
    table_header = ['Name', 'Ready to send']
    # try:
    #     table, table_header = parse_server_status.prettify_table(table)
    # except Exception as e:
    #     logger.exception('Vops, prettify failed on %s', table)

    try:
        header = prettify_header(header)
    except Exception as e:
        logger.exception('Vops, prettify header failed on %s', header)

    for ix in range(len(data)):
        item = data[ix]
        data[ix] = [item[0]]
        data[ix].extend([None, None])
        data[ix].extend(item[1:])
        # data[ix] = list(data[ix])
        # data[ix].append('""')
        # data[ix].append('""')

    #data.append([now, 1,1,1,1,1,1,1,1,1,1, '"test"', '"Baz"'])
    # data.append([now, '"test"', '"Baz"', None,None,None,None,None,None,None,None,None,None])
    # _, d = utc_now(datetime.datetime(day=13,month=10,year=2015))
    # data.append([d,
    #              '"OSTIA 198512-201011 (afr_50km)"', '"OSTIA forced hadam3p_afr runs 198512-201011. All forcings spin up simulations, 10 ensemble members of each. (2500 simulations) "', None,None,None,None,None,None,None,None,None,None])
    # _, d = utc_now(datetime.datetime(day=28,month=9,year=2015))    
    # data.append([d,
    #              '"PNW full batch for No-MICPs and no aerosols"', '"World without major carbon producers and sulfate emissions set to 1900 levels (4991 simulations) "', None,None,None,None,None,None,None,None,None,None])
        
    t = Template(read_file(template))
    age_str = str(datetime.timedelta(seconds=age))
    r = t.render(now=now, now_str=now_str, table=table, table_header=table_header,
                 fetch_failed=fetch_failed, age_str=age_str,
                 header=header, data=data, header_in_progress=header_in_progress, data_in_progress=data_in_progress)
    write_file(r, output)

    return r

if __name__ == '__main__':
    main()
