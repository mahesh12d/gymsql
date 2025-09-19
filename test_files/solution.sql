-- Test question: Find customers with orders over $100
SELECT 
    customer_id,
    customer_name,
    total_spent
FROM dataset 
WHERE total_spent > 100
ORDER BY total_spent DESC;