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
    for td in row.find_all('td', bgcolor='eeeeee'):
        if td.text.endswith(tag):
            data = [td.text]#[:-len(tag)-1]]
        elif data:
            data.append(td.text)
    return data

if __name__ == '__main__':
    c = read_file('server_status.html')
    ready_to_send, in_progress = parse(c)
    for row in ready_to_send:
        print row
    print in_progress
