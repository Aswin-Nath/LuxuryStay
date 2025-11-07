-- CREATE OR REPLACE VIEW vw_customer_booking_summary AS
-- SELECT
--     b.booking_id,
--     u.user_id,
--     u.full_name AS customer_name,
--     STRING_AGG(DISTINCT rt.type_name, ', ') AS booked_room_types,
--     COUNT(brm.room_id) AS total_rooms,
--     b.check_in,
--     b.check_out,
--     b.total_price,
--     b.status,
--     b.created_at,
--     b.updated_at
-- FROM bookings b
-- LEFT JOIN users u ON b.user_id = u.user_id
-- LEFT JOIN booking_room_map brm ON brm.booking_id = b.booking_id
-- LEFT JOIN room_types rt ON rt.room_type_id = brm.room_type_id
-- WHERE b.is_deleted = FALSE
-- GROUP BY b.booking_id, u.user_id, u.full_name;


-- select * from vw_customer_booking_summary;


-- CREATE OR REPLACE VIEW vw_customer_payment_summary AS
-- SELECT
--     p.payment_id,
--     p.booking_id,
--     u.user_id,
--     u.full_name AS customer_name,
--     pmu.name AS payment_method,
--     p.amount,
--     p.status AS payment_status,
--     p.transaction_reference,
--     p.payment_date
-- FROM payments p
-- JOIN users u ON p.user_id = u.user_id
-- JOIN payment_method_utility pmu ON p.method_id = pmu.method_id
-- JOIN bookings b ON b.booking_id = p.booking_id
-- WHERE p.is_deleted = FALSE AND b.is_deleted = FALSE;

-- select * from vw_customer_payment_summary;

-- CREATE OR REPLACE VIEW vw_customer_refund_summary AS
-- SELECT
--     r.refund_id,
--     r.booking_id,
--     u.user_id,
--     u.full_name AS customer_name,
--     r.type AS refund_type,
--     r.status AS refund_status,
--     r.refund_amount,
--     r.initiated_at,
--     r.processed_at,
--     r.completed_at,
--     pmu.name AS transaction_method,
--     r.transaction_number,
--     r.remarks
-- FROM refunds r
-- JOIN users u ON r.user_id = u.user_id
-- LEFT JOIN payment_method_utility pmu ON r.transaction_method_id = pmu.method_id
-- WHERE r.is_deleted = FALSE;

-- select * from vw_customer_refund_summary; 

-- CREATE OR REPLACE VIEW vw_customer_refund_summary AS
-- SELECT
--     r.refund_id,
--     r.booking_id,
--     u.user_id,
--     u.full_name AS customer_name,
--     r.type AS refund_type,
--     r.status AS refund_status,
--     r.refund_amount,
--     r.initiated_at,
--     r.processed_at,
--     r.completed_at,
--     pmu.name AS transaction_method,
--     r.transaction_number,
--     r.remarks
-- FROM refunds r
-- JOIN users u ON r.user_id = u.user_id
-- LEFT JOIN payment_method_utility pmu ON r.transaction_method_id = pmu.method_id
-- WHERE r.is_deleted = FALSE;

-- select * from vw_customer_refund_summary;

-- CREATE OR REPLACE VIEW vw_admin_booking_performance AS
-- SELECT
--     rt.type_name AS room_type,
--     COUNT(DISTINCT b.booking_id) AS total_bookings,
--     SUM(b.total_price) AS total_revenue,
--     SUM(CASE WHEN b.status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled_bookings,
--     SUM(CASE WHEN b.status = 'CONFIRMED' THEN 1 ELSE 0 END) AS active_bookings,
--     SUM(CASE WHEN b.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_bookings,
--     DATE(b.created_at) AS booking_date
-- FROM bookings b
-- JOIN booking_room_map brm ON brm.booking_id = b.booking_id
-- JOIN room_types rt ON brm.room_type_id = rt.room_type_id
-- WHERE b.is_deleted = FALSE
-- GROUP BY rt.type_name, DATE(b.created_at)
-- ORDER BY booking_date DESC;

-- select * from vw_admin_booking_performance;

-- CREATE OR REPLACE VIEW vw_admin_revenue_summary AS
-- SELECT
--     DATE(p.payment_date) AS payment_date,
--     SUM(p.amount) AS total_collected,
--     COALESCE(SUM(r.refund_amount), 0) AS total_refunded,
--     SUM(p.amount) - COALESCE(SUM(r.refund_amount), 0) AS net_revenue
-- FROM payments p
-- LEFT JOIN refunds r ON p.booking_id = r.booking_id
-- WHERE p.is_deleted = FALSE
-- GROUP BY DATE(p.payment_date)
-- ORDER BY payment_date DESC;

-- select * from vw_admin_revenue_summary;

-- CREATE OR REPLACE VIEW vw_admin_refund_summary AS
-- SELECT
--     r.refund_id,
--     r.booking_id,
--     u.full_name AS customer_name,
--     r.refund_amount,
--     r.type AS refund_type,
--     r.status AS refund_status,
--     (r.completed_at - r.initiated_at) AS total_processing_time,
--     r.initiated_at,
--     r.completed_at
-- FROM refunds r
-- JOIN users u ON r.user_id = u.user_id
-- WHERE r.is_deleted = FALSE;

-- select * from vw_admin_refund_summary;

-- CREATE OR REPLACE VIEW vw_admin_payment_summary AS
-- SELECT
--     pmu.name AS payment_method,
--     COUNT(p.payment_id) AS total_transactions,
--     SUM(CASE WHEN p.status = 'SUCCESS' THEN 1 ELSE 0 END) AS successful,
--     SUM(CASE WHEN p.status = 'FAILED' THEN 1 ELSE 0 END) AS failed,
--     ROUND(
--         (SUM(CASE WHEN p.status = 'SUCCESS' THEN 1 ELSE 0 END)::NUMERIC / COUNT(p.payment_id)) * 100, 
--         2
--     ) AS success_rate
-- FROM payments p
-- JOIN payment_method_utility pmu ON p.method_id = pmu.method_id
-- WHERE p.is_deleted = FALSE
-- GROUP BY pmu.name;


-- select * from vw_admin_payment_summary;

-- CREATE OR REPLACE VIEW vw_admin_review_summary AS
-- SELECT
--     rt.type_name AS room_type,
--     COUNT(rv.review_id) AS total_reviews,
--     ROUND(AVG(rv.rating), 2) AS average_rating,
--     SUM(CASE WHEN rv.rating >= 4 THEN 1 ELSE 0 END) AS positive_reviews,
--     SUM(CASE WHEN rv.rating <= 2 THEN 1 ELSE 0 END) AS negative_reviews
-- FROM reviews rv
-- JOIN room_types rt ON rv.room_type_id = rt.room_type_id
-- GROUP BY rt.type_name;

-- select * from vw_admin_review_summary;