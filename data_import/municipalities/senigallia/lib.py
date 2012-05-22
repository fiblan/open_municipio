from data_import.utils import create_table_schema, get_row_dicts
from data_import.votations.lib import Ballot, Sitting, Vote, BaseVotationReader, VotationDataSource
from data_import.municipalities.senigallia import conf

import re, os, sqlite3, datetime, logging, struct



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
            cursor.execute('DROP TABLE IF EXISTS %s' % table_name)
            create_query = create_table_schema(table_name, table_schema)
            cursor.execute(create_query)
        ## Transcoding from MDBs to SQLite
        for table_name in tables:
            ## Export data records from MDBs
            export_command = "mdb-export -I %(fname)s %(table_name)s"
            export_output = os.popen(export_command % {'fname': mdb_fpath, 'table_name': table_name}).read()
            insert_queries = [line for line in export_output.split('\n') if line.startswith('INSERT')]
            for insert_query in insert_queries:
                ## Import data records into SQLite
                cursor.execute(insert_query)
        ## commit DB changes
        connection.commit()
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
            logging.info("Processing %s" % os.path.join(conf.SQLITE_ROOT_DIR, fname))
            # sitting IDs are encoded within DB filenames
            sitting_id = fname.rstrip('.sqlite')
            sitting = Sitting()
            sitting._id = sitting_id # internal use only
            sitting.seq_n = self._get_sitting_seq_n(sitting_id)
            # make a connection to the SQLite DB
            db_file_path = os.path.join(conf.SQLITE_ROOT_DIR, fname)
            connection = sqlite3.connect(db_file_path)
            cursor = connection.cursor()
            ## Retrieve sitting info
            query = 'SELECT DataSeduta, Convocazione FROM CostSed'
            cursor.execute(query)
            results = cursor.fetchall()
            connection.close()
            # sanity check
            if len(results) != 1:
                logging.error("Corrupted table `CostSed` for sitting #%s" % sitting_id)
            row = results[0]
            # sitting's date, as returned by the DB (i.e. a string)
            date_string = row[0]
            # convert to a Python ``Date`` object
            sitting.date =  datetime.datetime.strptime(date_string, '%m/%d/%y %H:%M:%S').date()
            sitting.call = row[1]
            sittings.append(sitting)           
        return sittings  
        
    def get_ballots(self, sitting):
        BALLOT_TYPES = {
                        1: 'Palese Semplice',
                        2: 'Palese Nominale',
                        3: 'Numero Legale',
                        4: 'Segreta',                            
                        }
        OUTCOMES = {
                    0: 'No Esito',
                    1: 'Approvato',
                    2: 'Respinto',
                    3: 'SI Numero Legale',
                    4: 'NO Numero Legale',
                    5: 'Annullata',                                                                
                    }
        ballots = []
        # DB to query against
        db_file_path = os.path.join(conf.SQLITE_ROOT_DIR, sitting._id + '.sqlite')            
        connection = sqlite3.connect(db_file_path)
        cursor = connection.cursor()
        query = 'SELECT * FROM Votazioni'
        row_dicts = get_row_dicts(cursor, query)
        for row_dict in row_dicts:
            # TODO: filter out irrelevant ballots
            ballot = Ballot(
                sitting = sitting,
                seq_n = row_dict['NumVoto'],
                timestamp = datetime.datetime.strptime(row_dict['Data_Ora '], '%m/%d/%y %H:%M:%S'),
                ballot_type = BALLOT_TYPES[row_dict['TipoVoto']],
                n_presents = row_dict['Presenti'],
                n_partecipants = row_dict['Votanti'],
                n_yes = row_dict['Favorevoli'],
                n_no = row_dict['Contrari'],
                n_abst = row_dict['Astenuti'],
                n_legal = row_dict['NumLegale '],
                outcome = OUTCOMES[row_dict['Esito']],
                )
            ballots.append(ballot)
        return ballots
                     
    def get_votes(self, ballot):
        VOTE_OUTCOME = {
                      'FAV': 'Favorevole',
                      'CON': 'Contrario',
                      'AST': 'Astenuto', 
                      'VOT': 'Votante (Vot. Segreta)',
                      'NVT': 'Non Votante (4 Tasto)',
                      'PRE': 'Presente(Vot N.L.)',
                      '...': 'Tessera Presente Non Votante (Se presente un numero di tessera)',
                      '___': 'Terminale NON INSTALLATO',
                      'ECP': 'Tessera Capovolta',
                      'ETP': 'Errore tipo Tessera',
                      'ELE': 'Errore lettura Tessera',
                      'ELG': 'Errata Legislatura',
                      'EFW': 'Errore Release firmware', 
                      'ENR': 'Errore Non Risponde',
                      'BDO': 'Errore BDO',
                      'EAB': 'Errore Tessera non abilitata',
                      'EPO': 'Errore Posto (posti fissi)',
                      }           
        votes = []
        db_file_path = os.path.join(conf.SQLITE_ROOT_DIR, ballot.sitting._id + '.sqlite')
        connection = sqlite3.connect(db_file_path)
        cursor = connection.cursor()
        ## retrieve individual counselors' votes for the given ballot
        query = 'SELECT Dettaglio FROM Votazioni WHERE NumVoto = ?'
        cursor.execute(query, [ballot.seq_n])
        results = cursor.fetchall()
        connection.close()
        # sanity check
        if len(results) != 1:
            logging.error("Corrupted table `Votazioni` for sitting #%s" % ballot.sitting._id)
        # individual votes are encoded within a binary (but ASCII-only) string
        ballot_detail_str = results[0][0]
        # sanity check: string encoding votes detail must be a multiple of 14
        # (since it's made of 14-bytes records)
        if len(ballot_detail_str) % 14 != 0:
            logging.error("Corrupted table `Votazioni` for sitting #%s" % ballot.sitting._id)
        records = [ballot_detail_str[i:i+14] for i in range(0, len(ballot_detail_str), 14)]
        for record in records:
            ## record format: ``CCCCGGGGTTTXXX``, where:
            ## ``CCCC``: component ID
            ## ``GGGG``: group ID
            ## ``TTT``: card ID
            ## ``XXX``: issued vote
            componentID, groupID, cardID, vote_code = struct.unpack('4s4s3s3s', record)
            vote = Vote(
                        ballot = ballot,
                        cardID = cardID, 
                        componentID = componentID, 
                        groupID = groupID, 
                        choice = VOTE_OUTCOME[vote_code]
                        )           
            # TODO: filter out irrelevant votes               
            votes.append(vote)
        return votes


class MdbVotationReader(BaseVotationReader):
    """
    Parse votation-related data from a set of MDB files. 
    """
    def get_data_source(self):
        """
        In this case, the data source is a filesystem directory containing MDB files
        """
        return MdbDataSource(conf.MDB_ROOT_DIR)