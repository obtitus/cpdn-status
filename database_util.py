import sqlite3
import logging
logger = logging.getLogger('cpdn_status.database_util')

def scrub(table_name):
    ret = []
    for char in table_name:
        if char.isalnum():
            ret.append(char)
        else:
            ret.append('_')
    return ''.join(ret)
    #return ''.join( chr for chr in table_name if chr.isalnum() )

class Database(object):
    def __init__(self, database_name, table_name):
        self.conn = sqlite3.connect(database_name)
        self.c = self.conn.cursor()
        self.table_name = scrub(table_name)
        self.createNewTable()
    
    def __del__(self):
        # Save (commit) the changes
        self.conn.commit()
        # We can also close the connection if we are done with it.
        # Just be sure any changes have been committed or they will be lost.
        self.conn.close()

    def createNewTable(self):
        # Create table
        try:
            self.c.execute('''CREATE TABLE %s
            (name text not null, timestamp INTEGER not null, count INTEGER, PRIMARY KEY (name, timestamp))''' % self.table_name)

            #self.c.execute('CREATE INDEX idx1 ON %s(date)')
        except sqlite3.OperationalError as e:
            logger.debug(e)
        
        self.conn.commit()

    def insert(self, values):
        try:
            logger.debug('inserting %s values into database', len(values))
            self.c.executemany('INSERT INTO %s VALUES (?, ?, ?)' % self.table_name, values)
        except sqlite3.IntegrityError as e:
            logger.warning('Insert of "%s" failed: %s' % (values, e))

        self.conn.commit()

    def select_timestamps(self):
        for row in self.c.execute('SELECT DISTINCT timestamp FROM %s ORDER BY timestamp' % self.table_name):
            yield row[0]

    def select_names(self, oldest_seconds):
        for row in self.c.execute('SELECT DISTINCT name FROM %s WHERE timestamp > %s ORDER BY name' % (self.table_name, oldest_seconds)):
            yield row[0]

    def select_count(self, name, timestamp):
        for row in self.c.execute('SELECT count FROM %s WHERE timestamp=%s AND name="%s"' % (self.table_name, timestamp, name)):
            yield row

    def select_column_view(self, oldest_seconds, include_only=(), exclude=(), exclude_endswith=''):
        if include_only != ():
            header = include_only
        else:
            header = list()
            for h in self.select_names(oldest_seconds):
                if not(h in exclude) and not(h.endswith(exclude_endswith)):
                    header.append(h)

        cmd  = "CREATE VIEW server_status_column AS\n"
        cmd += "  SELECT timestamp,\n"
        for name in header:
            cmd += "    SUM(CASE WHEN name = '{0}' THEN count END) AS '{0}',\n".format(name)
        cmd = cmd[:-2] + '\n'   # strip ','
        cmd += "FROM server_status\n"
        cmd += "WHERE timestamp > {0}\n".format(oldest_seconds)
        #cmd += "AND instr(name, 'Mac') > 0\n"
        cmd += "GROUP BY timestamp;"

        logger.debug('select_column_view:\n"%s"', cmd)

        try:
            self.c.executescript(cmd)
        except sqlite3.OperationalError as e:
            logger.exception('vops %s', e)

        data = list(self.c.execute('SELECT * FROM server_status_column'))

        self.c.execute('DROP VIEW server_status_column')
        logger.debug('select_column_view done, returning %s elements', len(data))
        
        return header, data

def importFromCSV(csv_filename, database_filename):
    """Used to convert from old .csv format to database"""
    import file_util
    data = list(file_util.read_csv(csv_filename))
    header = data[0]
    new_entries = list()

    header = ['date', 
              'Weather At Home European region   (hadam3p_eu) Tasks ready to send', 
              'Weather At Home Pacific North West region (hadam3p_pnw) Tasks ready to send', 
              'Weather At Home Australia New Zealand region (hadam3p_anz) Tasks ready to send', 
              'hadcm3n Tasks ready to send',
              #'RAPIT project (hadcm3n) Tasks ready to send', 
              'hadam3p (Global model only) with MOSES II land scheme Tasks ready to send', 
              'Total  Tasks ready to send', 
              'Tasks in progress']

    for row in data[1:]:
        if len(row) == len(header) and int(row[0]) > 1406206802-7*24*60*60:
            for ix in range(1, len(row)):
               new_entries.append((header[ix].strip(), row[0], row[ix])) # name, time, count
            pass # added
        elif len(row) == 1:
            pass # ignore
        else:
            print len(row), row

    d = Database(database_filename, 'server_status')
    d.insert(new_entries)

    header, data = d.select_column_view()
    print header
    for d in data:
        print d
if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                        datefmt="%Y-%m-%d %H:%M")
    logger = logging.getLogger('cpdn_status')
    logger.setLevel(logging.DEBUG)

    #d = Database('test.sqlite', 'server_status')
    # d.insert((('name1', 2014, 123),
    #           ('name2', 2014, 456),
    #           ('name2', '2015', '231')))

    # for row in d.select_column_view():
    #     print row

    #importFromCSV('storage/server_status.csv', 'storage/server_status.sqlite')
    
    d = Database('storage/server_status.sqlite', 'server_status')
    print list(d.c.executescript('''SELECT * FROM server_status WHERE timestamp > 1479460965'''))
    #d.c.executescript('''DELETE FROM server_status
    #                     WHERE count = 0;''')
    d.c.execute('VACUUM')
