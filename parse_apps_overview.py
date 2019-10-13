import re
import logging
logger = logging.getLogger('cpdn_status.parse_apps_overview')

from bs4 import BeautifulSoup

from file_util import read_file

def toInt(string):
    try:
        return int(string.replace(',', ''))
    except:                     # todo: logging
        return -1

def unique(name, unique_names, recursion=1):
    if name not in unique_names:
        unique_names.add(name)
        return name
    else:
        prev = r'(%d)' % (recursion-1)
        new = r'(%d)' % recursion
        if prev in name:
            name = name.replace(prev, new)
        else:                   # first iter
            name = name + r'(%d)' % recursion
        
        return unique(name, unique_names, recursion=recursion+1)

def parse(html):
    soup = BeautifulSoup(html)
    #print soup.prettify()
    apps = dict()
    last_table = soup.find_all('table')[-1]
    for row in last_table.find_all('tr'):
        header = list()
        for header_row in row.find_all('th'):
            header.append(header_row.text)

        if len(header) == 1:    # New application
            current_app = header[0]
            apps[current_app] = list()
            logger.debug('Application %s', current_app)
            
        elif len(header) == 0: # No header, content?
            td = row.find_all('td')[0]
            apps[current_app].append(td.text)

    return apps

def simplify_ops(apps):
    apps = dict(apps)
    ops = ['Windows', 'Linux', 'Mac']
    for name in apps:
        for ix in range(len(apps[name])):
            for o in ops:
                if o in apps[name][ix]:
                    apps[name][ix] = o

    return apps

if __name__ == '__main__':
    c = read_file('cache/apps.html')
    apps = parse(c)
    apps = simplify_ops(apps)
    
    for name in apps:
        print name, apps[name]
