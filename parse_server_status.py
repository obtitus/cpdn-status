import re
from bs4 import BeautifulSoup

from file_util import read_file

def toInt(string):
    try:
        return int(string.replace(',', ''))
    except:                     # todo: logging
        return -1

def parse(html):
    soup = BeautifulSoup(html)
    #print soup.prettify()
    ready_to_send = list()
    in_progress = list()
    # Get the unsent column of the tasks by application table and add to the ready_to_send
    for table in soup.find_all('table'):
        header = list()
        for header_row in table.find_all('th'):
            header.append(header_row.text)
        if len(header) > 1 and header[0] == u'Tasks by application':
            ix = header.index(u'Unsent') - 1 # get unsent column, -1 since the u'Tasks by application' counts
            for row in table.find_all('tr'):
                data = list()
                for td in row.find_all('td'):
                    data.append(td.text)
                if len(data) > 1:
                    #print data[ix]
                    ready_to_send.append((data[0], int(data[ix])))
            #print 'TABLE', table.prettify()
    
    # Get the Tasks ready to send and Tasks in progress table
    for tr in soup.find_all('tr'):
        r = getRowData(tr, 'Tasks ready to send')
        if r and len(r) == 2:
            r[1] = toInt(r[1])
            ready_to_send.append(r)
        r = getRowData(tr, 'Tasks in progress')
        if r and len(r) == 2:
            r[1] = toInt(r[1])
            in_progress = [r]
    
    return ready_to_send, in_progress

def getRowData(row, tag='Tasks ready to send'):
    data = False
    for td in row.find_all('td'):#, bgcolor='eeeeee'):
        if td.text.endswith(tag):
            data = [td.text]#[:-len(tag)-1]]
        elif data:
            data.append(td.text)
    return data

def prettify_table(table):
    """Parse the names and divide the data into operating systems"""
    ops = ['Windows', 'Linux', 'Mac']
    total = [0]*len(ops)        # zeros
    
    table_header = ['Name', 'Total']
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
    return table, table_header

if __name__ == '__main__':
    c = read_file('cache/server_status.html')
    ready_to_send, in_progress = parse(c)
    for row in ready_to_send:
        print 'row', row
    print in_progress
