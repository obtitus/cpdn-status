import re
import logging
logger = logging.getLogger('cpdn_status.parse_server_status')

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
    ready_to_send = list()
    in_progress = list()
    unique_names = set()
    # Get the unsent column of the tasks by application table and add to the ready_to_send
    for table in soup.find_all('table'):
        header = list()
        for header_row in table.find_all('th'):
            header.append(header_row.text)
        if len(header) > 1 and header[0] == u'Application':
            ix_unsent = header.index(u'Unsent') # get unsent column
            ix_inprogress = header.index(u'In progress') # get in progress column
            for row in table.find_all('tr'):
                data = list()
                for td in row.find_all('td'):
                    data.append(td.text)
                if len(data) > 1:
                    data[0] = unique(data[0], unique_names)
                    #print data[ix]
                    ready_to_send.append([data[0] + ' Tasks ready to send', int(data[ix_unsent])])

                    in_progress.append([data[0] + ' Tasks in progress', int(data[ix_inprogress])])
            #print 'TABLE', table.prettify()
    
    # Get the Tasks ready to send and Tasks in progress table
    for tr in soup.find_all('tr'):
        r = getRowData(tr, 'Tasks ready to send')
        if r and len(r) == 2:
            r[1] = toInt(r[1])
            ready_to_send.append(['Total  ' + r[0], r[1]])
        r = getRowData(tr, 'Tasks in progress')
        if r and len(r) == 2:
            r[1] = toInt(r[1])
            in_progress.append([r[0], r[1]])
    
    return ready_to_send, in_progress

def getRowData(row, tag='Tasks ready to send'):
    data = False
    for td in row.find_all('td'):#, bgcolor='eeeeee'):
        if td.text.endswith(tag):
            data = [td.text]#[:-len(tag)-1]]
        elif data:
            data.append(td.text)
    return data

def prettify_table(table, name='Tasks ready to send', apps_to_ops=None):
    """Parse the names and divide the data into operating systems"""
    ops = ['Windows', 'Linux', 'Mac']
    table_header = ['Name', name]

    # Strip name from all but last rows
    for ix_row in range(len(table)-1):
        table[ix_row][0] = table[ix_row][0].replace(name, '').strip()
        
    # Do we get op information in a dictionary?
    if apps_to_ops is not None:
        for ix_row in range(len(table)-1): # skip last row, assume Total row.
            app_name = table[ix_row][0]
            
            #print('app_name', app_name)
            try:
                op_names = ', '.join(apps_to_ops[app_name])
                table[ix_row][0] = '%s (%s)' % (table[ix_row][0], op_names)
            except KeyError:
                logger.error('Unable to map app: "%s" to ops dict: %s' % (app_name, apps_to_ops))
    
    total = [0]*len(ops)        # zeros
    op_found = False
    
    for ix_row in range(len(table)-1):
        row_name, number = table[ix_row]
        
        sp = re.split('(\([^)]+\))', row_name)

        if len(sp) <= 2: continue
        for o in ops:
            if o in sp[-2]:
                break
        else: # not found
            continue

        #print('sp', sp)
        current = [0]*len(ops)
        for op_ix in range(len(ops)):
            if ops[op_ix] in sp[-2]:
                total[op_ix]   += number
                current[op_ix] += number
                op_found = True

        table[ix_row].extend(current)

    if op_found:
        # Header
        table_header.extend(ops)
        # Last row
        ix_row += 1
        table[ix_row].extend(total)

    logger.debug('prettify_table: done')
    return table, table_header

if __name__ == '__main__':
    logger = logging.getLogger('cpdn_status')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    
    c = read_file('cache/server_status.html')
    ready_to_send, in_progress = parse(c)
    for row in ready_to_send:
        print('ready to send row', row)
    for row in in_progress:
        print('in progress row', row)

    table_ready, table_ready_header = prettify_table(in_progress, 'Tasks in progress', apps_to_ops=apps_to_ops)
    print('Header', table_ready_header)
    for row in table_ready:
        print('row', row)
