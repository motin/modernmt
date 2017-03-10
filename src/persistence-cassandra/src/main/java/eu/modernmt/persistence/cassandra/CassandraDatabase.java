package eu.modernmt.persistence.cassandra;

import com.datastax.driver.core.Cluster;
import com.datastax.driver.core.Session;
import com.datastax.driver.core.schemabuilder.DropKeyspace;
import com.datastax.driver.core.schemabuilder.SchemaBuilder;
import eu.modernmt.persistence.*;
import org.apache.commons.io.IOUtils;

import java.io.IOException;

/**
 * Created by andrearossi on 08/03/17.
 */
public class CassandraDatabase extends Database {
    public static final String DEFAULT_KEY_SPACE = "default";
    public static final String DOMAINS_TABLE = "domains";
    public static final String IMPORT_JOBS_TABLE = "import_jobs";
    public static final String COUNTERS_TABLE = "table_counters";

    private String keyspace;
    private String host;
    private int port;
    private Cluster cluster;
    /*username? password?*/

    public CassandraDatabase(String host, int port, String keyspace) {
        this.host = host;
        this.port = port;
        this.keyspace = keyspace;
        this.cluster = Cluster.builder().withPort(port).addContactPoint(host).build();
    }

    public CassandraDatabase(String host, int port) {
        this(host, port, DEFAULT_KEY_SPACE);
    }

    @Override
    public Connection getConnection(boolean cached) throws PersistenceException {
        return new CassandraConnection(this.cluster, this.keyspace);
    }

    @Override
    public DomainDAO getDomainDAO(Connection connection) {
        return new CassandraDomainDAO((CassandraConnection) connection);
    }

    @Override
    public ImportJobDAO getImportJobDAO(Connection connection) {
        return new CassandraImportJobDAO((CassandraConnection) connection);
    }

    @Override
    public void drop() throws PersistenceException {
        CassandraConnection connection = null;

        try {
            connection = new CassandraConnection(this.cluster, this.keyspace);
            Session session = connection.session;

            DropKeyspace dropKeyspace = SchemaBuilder.dropKeyspace("\"" + this.keyspace + "\"").ifExists();

            CassandraUtils.checkedExecute(session, dropKeyspace);

        } catch (KeyspaceNotFoundException e) {

        } finally {
            IOUtils.closeQuietly(connection);
        }

    }

    @Override
    public void create() throws PersistenceException {
        CassandraConnection connection = null;

        try {
            connection = new CassandraConnection(this.cluster, null);
            Session session = connection.session;
            String currentKeyspace = session.getLoggedKeyspace();


            String createKeyspace =
                    "CREATE KEYSPACE \"" + DEFAULT_KEY_SPACE + "\" WITH replication = " +
                            "{'class':'SimpleStrategy', 'replication_factor':1};";

            //CreateKeyspace createKeyspace = SchemaBuilder.createKeyspace(keyspace).ifNotExists();

            String createCountersTable =
                    "CREATE TABLE IF NOT EXISTS \"" + DEFAULT_KEY_SPACE + "\"." + COUNTERS_TABLE +
                            " (table_id int PRIMARY KEY, table_counter bigint );";

            String putDomainsTableEntry =
                    "INSERT INTO \"" + DEFAULT_KEY_SPACE + "\"." + COUNTERS_TABLE +
                            " (table_id, table_counter) VALUES (1, 0);";

            String putImportJobsTableEntry =
                    "INSERT INTO \"" + DEFAULT_KEY_SPACE + "\"." + COUNTERS_TABLE +
                            " (table_id, table_counter) VALUES (2, 0);";

            String createDomainsTable =
                    "CREATE TABLE \"" + DEFAULT_KEY_SPACE + "\"." + DOMAINS_TABLE +
                            " (id int PRIMARY KEY, name varchar);";

            String createImportJobsTable =
                    "CREATE TABLE \"" + DEFAULT_KEY_SPACE + "\"." + IMPORT_JOBS_TABLE +
                            " (id bigint PRIMARY KEY, domain int, size int, \"begin\" bigint, end bigint, data_channel smallint);";


            if (currentKeyspace == null) {
                CassandraUtils.checkedExecute(session, createKeyspace);
                this.keyspace = DEFAULT_KEY_SPACE;
            }

            CassandraUtils.checkedExecute(session, createCountersTable);
            CassandraUtils.checkedExecute(session, putDomainsTableEntry);
            CassandraUtils.checkedExecute(session, putImportJobsTableEntry);
            CassandraUtils.checkedExecute(session, createDomainsTable);
            CassandraUtils.checkedExecute(session, createImportJobsTable);

        } finally {
            IOUtils.closeQuietly(connection);
        }
    }

    @Override
    public void close() throws IOException {
        this.cluster.close();
    }
}