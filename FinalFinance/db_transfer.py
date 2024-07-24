from sqlalchemy import create_engine, MetaData, Table, select, VARCHAR
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.sql.sqltypes import String

# SQLAlchemy engine for SQLite and PostgreSQL
sqlite_engine = create_engine('sqlite:///C:\\Users\\UP\\PycharmProjects\\codeacademy\\FinalFinance\\instance\\f_finance.db')
postgres_engine = create_engine('postgresql://postgres:Lietuva09@localhost:5432/final_finance')

# Create MetaData objects
sqlite_meta = MetaData()
postgres_meta = MetaData()

# Reflect SQLite database schema
sqlite_meta.reflect(bind=sqlite_engine)

# Reflect PostgreSQL database schema
postgres_meta.reflect(bind=postgres_engine)

# Iterate over tables in SQLite and PostgreSQL
for table_name in sqlite_meta.tables:
    if table_name in postgres_meta.tables:
        # Retrieve SQLite table
        sqlite_table = Table(table_name, sqlite_meta, autoload_with=sqlite_engine)

        # Retrieve PostgreSQL table
        postgres_table = Table(table_name, postgres_meta, autoload_with=postgres_engine)

        # Construct a SELECT statement for all columns in SQLite table
        stmt = select(sqlite_table.columns)

        # Get a connection from SQLite engine
        with sqlite_engine.connect() as conn_sqlite:
            # Execute SELECT statement
            results = conn_sqlite.execute(stmt)

            # Get a connection from PostgreSQL engine
            with postgres_engine.connect() as conn_postgres:
                # Begin a transaction
                with conn_postgres.begin() as trans:
                    try:
                        # Iterate through results and insert into PostgreSQL
                        for row in results:
                            # Prepare data dictionary for PostgreSQL insert
                            data = {}
                            for index, column in enumerate(sqlite_table.columns):
                                # Check if column exists in PostgreSQL table
                                if column.name in postgres_table.columns:
                                    # If it's a string column and exceeds length, truncate
                                    if isinstance(column.type, String) and len(str(row[index])) > column.type.length:
                                        data[column.name] = str(row[index])[:column.type.length]
                                    else:
                                        data[column.name] = row[index]

                            conn_postgres.execute(postgres_table.insert().values(**data))
                    except (IntegrityError, DataError) as e:
                        # Handle integrity or data errors
                        print(f"Skipping row due to error: {e}")
                        trans.rollback()  # Rollback the transaction on error
                    else:
                        trans.commit()  # Commit the transaction if successful

print("Data migration completed.")
