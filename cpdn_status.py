# Standard python imports
import urllib2
import itertools
import datetime
import os
import time
import logging
# logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")#,
#                     #datefmt="%Y-%m-%d %H:%M")
logger = logging.getLogger('cpdn_status')
logger.setLevel(logging.INFO)

# Non-standard python
from jinja2 import Template
# This project:
from file_util import *
from database_util import Database
import parse_server_status
import parse_apps_overview

join = os.path.join
root = os.path.dirname(os.path.abspath(__file__))

# fixme: move
log_filename = join(root, 'cpdn_status.log')
import logging.handlers
handler = logging.handlers.RotatingFileHandler(log_filename, maxBytes=1024*32,
                                               backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


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
        response = urllib2.urlopen(url, timeout=60)
        html = response.read()
        logger.debug('Fetch successful %s', response)
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

def get_html_cached(cache, url, old_age_hours=0.1):
    fetch_failed = False
    
    now_datetime, now = utc_now()
    age = file_age(cache, now=now)
    
    old = age > old_age_hours*60*60 # 
    if old:
        html = get_html(url, cache)
        if html == '': # fetch failed
            old = False
            fetch_failed = True
        else:
            age = 0
    else:
        html = read_file(cache)

    return old, age, html, fetch_failed


def get_apps_to_ops():
    # Figure out operating system
    page = 'apps.html'
    cache = join(root, 'cache', page)
    url = 'https://www.cpdn.org/cpdnboinc/' + page.replace('.html', '.php')
    
    old, age, html, fetch_failed = get_html_cached(cache, url, old_age_hours=24*7) # expire once a week
    
    apps_to_ops = parse_apps_overview.parse(html)
    apps_to_ops = parse_apps_overview.simplify_ops(apps_to_ops)
    return apps_to_ops
        

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
    # print 'now - 14 days', now, now - 60*60*24*14
    # exit(1)

    url = 'https://www.cpdn.org/cpdnboinc/' + page.replace('.html', '.php')
    old, age, html, fetch_failed = get_html_cached(cache, url, old_age_hours=0.1)

    logger.debug('parsing html, age = %s, old = %s, fetch_failed = %s',
                 age, old, fetch_failed)
    ready_to_send, in_progress = parse_server_status.parse(html)
    new_entries = list()
    table_ready = ready_to_send
    table_progress = in_progress

    # table_ready = []
    # html = ''
    if len(table_ready) == 0:
        logger.warning('table empty, html = "%s"', html)
        old = False
        fetch_failed = True
    #else:
    for entry in itertools.chain(table_ready, table_progress):
        if int(entry[1]) != 0:
            e = (entry[0], now, entry[1])
            new_entries.append(e) # name, time, count
            #print 'new_entrie', e
    
    if old:
        database.insert(new_entries)

    oldest_seconds = now - 60*60*24*182.5 # half a year
    header_ready, data_ready = database.select_column_view(oldest_seconds,
                                               exclude=('Tasks in progress', 'Total  Tasks ready to send'),
                                               exclude_endswith='Tasks in progress')

    header_progress, data_progress = database.select_column_view(oldest_seconds,
                                               exclude=('Tasks in progress', 'Total  Tasks ready to send'),
                                               exclude_endswith='Tasks ready to send')
    # print header_progress
    # exit(1)
    header_in_progress, data_in_progress = database.select_column_view(oldest_seconds, include_only=['Tasks in progress'])
    
    now_str = str(now_datetime)

    # Figure out mapping between operating system and application
    apps_to_ops = get_apps_to_ops()
    
    # print data[0], datetime.datetime.utcfromtimestamp(data[0][0])
    # print data[-1], datetime.datetime.utcfromtimestamp(data[-1][0])
    # print len(data)
    table_header = ['Name', 'Tasks']
    table_ready_header = []
    table_progress_header = []
    try:
        table_ready, table_ready_header = parse_server_status.prettify_table(table_ready, apps_to_ops=apps_to_ops)
        table_progress, table_progress_header = parse_server_status.prettify_table(table_progress, 'Tasks in progress')
    except Exception as e:
        logger.exception('Vops, prettify failed on %s', table_ready)

    try:
        table_ready_header = prettify_header(table_ready_header)
        table_progress_header = prettify_header(table_progress_header)
    except Exception as e:
        logger.exception('Vops, prettify header failed on %s, %s', table_ready_header, table_progress_header)

    # If only I remembered what this did
    for ix in range(len(data_ready)):
        item = data_ready[ix]
        data_ready[ix] = [item[0]]
        data_ready[ix].extend([None, None])
        data_ready[ix].extend(item[1:])
        # data_ready[ix] = list(data_ready[ix])
        # data_ready[ix].append('""')
        # data_ready[ix].append('""')

    # fixme, avoid duplicate
    for ix in range(len(data_progress)):
        item = data_progress[ix]
        data_progress[ix] = [item[0]]
        data_progress[ix].extend([None, None])
        data_progress[ix].extend(item[1:])
        # data_progress[ix] = list(data_progress[ix])
        # data_progress[ix].append('""')
        # data_progress[ix].append('""')    

    #data_ready.append([now, 1,1,1,1,1,1,1,1,1,1, '"test"', '"Baz"'])
    # data_ready.append([now, '"test"', '"Baz"', None,None,None,None,None,None,None,None,None,None])
    # _, d = utc_now(datetime.datetime(day=13,month=10,year=2015))
    # data_ready.append([d,
    #              '"OSTIA 198512-201011 (afr_50km)"', '"OSTIA forced hadam3p_afr runs 198512-201011. All forcings spin up simulations, 10 ensemble members of each. (2500 simulations) "', None,None,None,None,None,None,None,None,None,None])
    # _, d = utc_now(datetime.datetime(day=28,month=9,year=2015))    
    # data_ready.append([d,
    #              '"PNW full batch for No-MICPs and no aerosols"', '"World without major carbon producers and sulfate emissions set to 1900 levels (4991 simulations) "', None,None,None,None,None,None,None,None,None,None])

    logger.debug('creating html')
    table_template = Template(read_file(join(root, 'templates', 'table.html')))
    table_ready_html = table_template.render(table=table_ready, table_header=table_ready_header)
    table_progress = table_template.render(table=table_progress, table_header=table_progress_header)

    chart_template = Template(read_file(join(root, 'templates', 'draw_chart.js')))
    chart_ready = chart_template.render(data=data_ready, title='Ready to send', chart_id='ready', header=header_ready)
    chart_progress = chart_template.render(data=data_progress, title='Tasks in progress', chart_id='progress', header=header_progress)
#    print chart_progress
    
    t = Template(read_file(template))
    age_str = str(datetime.timedelta(seconds=age))
    r = t.render(now=now, now_str=now_str, table=table_ready_html+ '\n' + table_progress, 
                 fetch_failed=fetch_failed, age_str=age_str, chart=chart_ready + '\n' + chart_progress,
                 header_in_progress=header_in_progress, data_in_progress=data_in_progress)
    write_file(r, output)

    logger.debug('main: completed successfully')
    return r

if __name__ == '__main__':
    # page = 'apps.html'
    # cache = join(root, 'cache', page)
    # html = get_html('https://www.cpdn.org/cpdnboinc/' + page.replace('.html', '.php'), cache)
    main()
