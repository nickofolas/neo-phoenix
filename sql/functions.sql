CREATE OR REPLACE FUNCTION get_column_description(
    _database_name TEXT,
    _table_name    TEXT,
    _column_name   TEXT
)
RETURNS TEXT AS $$
DECLARE
    result TEXT;
BEGIN
    SELECT (
        SELECT
            pg_catalog.col_description(
                c.oid,
                cols.ordinal_position::int
            )
        FROM pg_catalog.pg_class c
        WHERE
            c.oid     = (SELECT cols.table_name::regclass::oid) AND
            c.relname = cols.table_name
        ) as column_comment
    INTO result
    FROM information_schema.columns cols
    WHERE
        cols.table_catalog = _database_name AND
        cols.table_name    = _table_name    AND
        cols.column_name   = _column_name;
    RETURN result;
END;
$$ LANGUAGE plpgsql;