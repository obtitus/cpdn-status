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
        # seems to be stuck at 322
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

def prettify_table(table, name='Tasks ready to send'):
    """Parse the names and divide the data into operating systems"""
    ops = ['Windows', 'Linux', 'Mac']
    table_header = ['Name', name]
    
    # do we still have op-information?
    for o in ops:
        if o in table[0][0]: break
    else:
        # guess not
        logger.debug('prettify_table: no operating-system information found, removing "%s" from all names', name)
        for ix_row in range(len(table)-1):
            if table[ix_row][0].endswith(name):
                table[ix_row][0] = table[ix_row][0][:-len(name)]
        return table, table_header
    
    total = [0]*len(ops)        # zeros
    
    for ix_row in range(len(table)):
        row_name, number = table[ix_row]
        
        sp = re.split('(\([^)]+\))', row_name)
        if len(sp) == 1 and sp[0].endswith('Tasks ready to send'):
            table[ix_row].extend(total)
        
        if len(sp) <= 2: continue
        
        if sp[-1].strip() == 'Tasks ready to send' and '(' in sp[-2] and ')' in sp[-2]:
            current = ['']*len(ops)
            for ix in range(len(ops)):
                if ops[ix] in sp[-2]: # 'Windows', 'Linux' or 'Mac'
                    total[ix] += number
                    current[ix] = number

            table[ix_row].extend(current)

    table_header.extend(ops)
    logger.debug('prettify_table: done')
    return table, table_header

if __name__ == '__main__':
    c = read_file('cache/server_status.html')
    ready_to_send, in_progress = parse(c)
    for row in ready_to_send:
        print 'ready to send row', row
    for row in in_progress:
        print 'in progress row', row

