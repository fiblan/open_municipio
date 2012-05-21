from data_import.utils import create_table_schema, get_row_dicts
from data_import.votations.lib import Ballot, Sitting, Vote, BaseVotationReader, VotationDataSource
from data_import.municipalities.senigallia import conf

import re, os, sqlite3


class MdbDataSource(VotationDataSource):
    """
    A set of MDB files generated by the ballot management system in use by
    Senigallia's municipality.
    """
    def __init__(self, mdb_root_dir):
        self.mdb_root_dir = mdb_root_dir
    
    def _is_valid_votation_mdb(self, fname):
        """
        Takes a file name ``fname``: if that string is a valid filename for a MDB file 
        containing votation data for a given sitting of the City Council, returns ``True``; 
        otherwise, returns ``False``.
        """
        pattern = re.compile(conf.MDB_FILENAME_PATTERN)
        if pattern.match(fname):
            return True
        else:
            return False
        
    def _get_sitting_id_from_mdb(self, fname):
        """
        Takes the name of a MDB file containing votation data for a given sitting 
        of the City Council; returns the corresponding sitting ID, as a string.
        """
        pattern = re.compile(conf.MDB_FILENAME_PATTERN)
        m = pattern.match(fname)
        return m.group('sitting_id')
        
    def _mdb_to_sqlite(self, mdb_fpath, sqlite_fpath):
        """
        Converts MDB files containing votation data to SQLite databases.
        
        Takes a path to a MDB file, ``mdb_fpath`` and creates an equivalent 
        SQLite DB file located at ``sqlite_fpath``.        
        """
        connection = sqlite3.connect(sqlite_fpath)
        cursor = connection.cursor()
        ## Re-create DB schema on target SQLite DBs
        # tables comprising the DB schema 
        tables = {}
        # sitting information
        tables['CostSed'] = {
                             'Legis': 'varchar(8)', 
                             'DataSeduta': 'date', 
                             'Convocazione': 'int', 
                             'IdPres': 'int', 
                             'NextVoto': 'int', 
                             'TempoParola': 'varchar(10)', 
                             'Plenum': 'int'
                             }
        # ballot subjects
        tables['Oggetti'] = {
                             'Sintetico': 'varchar(60)', 
                             'Esteso':  'varchar(400)',
                             'IdOgg': 'int', 
                             'Votato': 'int', 
                             }
        # ballots 
        tables['Votazioni'] = {
                               'NumVoto': 'int',              
                               'TipoVoto': 'varchar(2)', 
                               'Presenti': 'int', 
                               'Votanti': 'int', 
                               'Favorevoli': 'int', 
                               'Contrari': 'int', 
                               'Astenuti': 'int', 
                               'Plenum': 'int', 
                               'NumLegale': 'int', 
                               'Maggioranza': 'int', 
                               'TipoMagg': 'int', 
                               'Esito': 'int', 
                               'OggettoSint': 'varchar(60)', 
                               'OggettoEste': 'varchar(400)', 
                               'IdPres': 'int', 
                               'Data_Ora': 'date', 
                               'Tessere': 'int', 
                               'Convocazione': 'int', 
                               'PostiFissi': 'char', 
                               'Term_NR': 'int', 
                               'Term_ErrT': 'int', 
                               'Term_ErrL': 'int', 
                               'Dettaglio': 'text(255)', 
                               'DatiComp': 'text(255)'                            
                               } 
        
        for (table_name, table_schema) in tables.items():
            cursor.execute('DROP TABLE IF EXISTS %s;' % table_name)
            create_query = create_table_schema(table_name, table_schema)
            cursor.execute(create_query)
        ## Transcoding from MDBs to SQLite
        for table_name in tables:
            ## Export data records from MDBs
            export_command = "mdb-export -I %(fname)s %(table_name)s | sed -e 's/)$/)\;/'"
            export_output = os.popen(export_command % {'fname': mdb_fpath, 'table_name': table_name}).read()
            insert_queries = [line for line in export_output.split('\n') if line.startswith('INSERT')]
            for insert_query in insert_queries:
                ## Import data records into SQLite
                cursor.execute(insert_query)    
        ## close DB connection    
        connection.close()       
    
    def _get_sitting_seq_n(self, sitting_id):
        """
        Takes the internal ID for a sitting (as set by the ballot management system)
        and returns the sequential number since the beginning of the current year. 
        """
        # TODO: replace this dummy implementation
        return sitting_id

    def setup(self):
        # if the root dir holding SQLite files doesn't exist yet, create it
        if not os.path.exists(conf.SQLITE_ROOT_DIR):
            os.mkdir(conf.SQLITE_ROOT_DIR)
        # loop over (valid) MDB files and convert them to SQLite DBs
        for fname in os.listdir(self.mdb_root_dir):
            # sanity check
            if self._is_valid_votation_mdb(fname):
                sitting_id = self._get_sitting_id_from_mdb(fname)
                # create a SQLite DB containing the same votation data as the MDB file 
                mdb_fpath = os.path.join(self.mdb_root_dir, fname)
                sqlite_fpath = os.path.join(conf.SQLITE_ROOT_DIR, sitting_id + '.sqlite')
                self._mdb_to_sqlite(mdb_fpath, sqlite_fpath)
        
    def get_sittings(self):
        sittings = []
        # loop over the SQLite DBs containing votation data
        for fname in os.listdir(conf.SQLITE_ROOT_DIR):
            # sitting IDs are encoded within DB filenames
            sitting_id = fname.rstrip('.sqlite')
            sitting = Sitting()
            sitting.seq_n = self._get_sitting_seq_n(sitting_id)
            # TODO: retrieve sitting's ``call`` and ``date`` attributes, and set them
            sittings.append(sitting)  
    

class MdbVotationReader(BaseVotationReader):
    """
    Parse votation-related data from a set of MDB files. 
    """
    def get_data_source(self):
        """
        In this case, the data source is a filesystem directory containing MDB files
        """
        return MdbDataSource(conf.MDB_ROOT_DIR)