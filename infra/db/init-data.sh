set -eu

CSV_PATH="${CSV_PATH:-/data/data.csv}"

echo "Loading sales CSV from ${CSV_PATH}..."

psql -v ON_ERROR_STOP=1 <<SQL
SET datestyle = 'ISO, MDY';

DROP TABLE IF EXISTS sales;

CREATE TABLE sales (
  date date,
  week_day text,
  hour time,
  ticket_number text,
  waiter text,
  product_name text,
  quantity numeric,
  unitary_price numeric,
  total numeric
);

\copy sales (date, week_day, hour, ticket_number, waiter, product_name, quantity, unitary_price, total) FROM '${CSV_PATH}' WITH (FORMAT csv, HEADER true);
SQL

echo "Sales CSV loaded successfully."