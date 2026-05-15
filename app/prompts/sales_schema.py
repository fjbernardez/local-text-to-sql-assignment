SALES_SCHEMA_CONTEXT = """
PostgreSQL sales CSV schema.

Allowed table:

sales
- Each row represents a sold product line inside a ticket/order.
- Columns:
  - date: sale date
  - week_day: weekday name, for example Friday
  - hour: hour of the sale
  - ticket_number: ticket/order identifier
  - waiter: internal waiter, seller, or cashier identifier
  - product_name: sold item name
  - quantity: number of units sold in the line
  - unitary_price: unit price for the product line
  - total: line total revenue

Business interpretation:
- Product revenue: SUM(total) grouped by product_name.
- Product quantity sold: SUM(quantity) grouped by product_name.
- Ticket count: COUNT(DISTINCT ticket_number).
- Average ticket value: SUM(total) / COUNT(DISTINCT ticket_number).
- Revenue by waiter: SUM(total) grouped by waiter.
- Quantity by waiter: SUM(quantity) grouped by waiter.
- Ticket count by waiter: COUNT(DISTINCT ticket_number) grouped by waiter.
- Revenue by date, weekday, or hour: SUM(total) grouped by date, week_day, or hour.
- Quantity by date, weekday, or hour: SUM(quantity) grouped by date, week_day, or hour.

Ambiguity rules:
- "best product" is ambiguous unless the question says revenue, quantity sold, tickets, average, maximum, or another explicit metric.
- "busiest hour" is ambiguous unless the question says ticket count, quantity sold, revenue, or another explicit metric.
- "top waiter" is ambiguous unless the question says revenue, quantity sold, ticket count, average ticket value, or another explicit metric.
- Causal, subjective, predictive, recommendation-based, or external-knowledge questions are unsupported by this schema.
""".strip()


ALLOWED_SALES_TABLES = {"sales"}
