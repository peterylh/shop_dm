-- DWS 客户订单汇总表
-- table_id: 674c2c22-95c3-47f2-92f0-2d9fcd34b4f0
DROP TABLE IF EXISTS shop_dm.dws_customer_order_summary;
CREATE TABLE IF NOT EXISTS shop_dm.dws_customer_order_summary (
    customer_id      BIGINT        NOT NULL COMMENT '客户ID',
    stat_date        DATE          NOT NULL COMMENT '统计日期',
    order_count      INT           NOT NULL DEFAULT 0 COMMENT '订单数',
    total_amount     DECIMAL(14,2) NOT NULL DEFAULT 0.00 COMMENT '订单总额',
    total_discount   DECIMAL(14,2) NOT NULL DEFAULT 0.00 COMMENT '折扣总额',
    payment_amount   DECIMAL(14,2) NOT NULL DEFAULT 0.00 COMMENT '实付总额',
    avg_order_amount DECIMAL(10,2) NULL COMMENT '平均客单价',
    etl_time         DATETIME      NOT NULL COMMENT 'ETL处理时间'
) ENGINE=OLAP
UNIQUE KEY(customer_id, stat_date)
PARTITION BY RANGE(stat_date) (
    PARTITION p202406 VALUES LESS THAN ("2024-07-01"),
    PARTITION p202407 VALUES LESS THAN ("2024-08-01"),
    PARTITION p202408 VALUES LESS THAN ("2024-09-01"),
    PARTITION p202409 VALUES LESS THAN ("2024-10-01"),
    PARTITION p202410 VALUES LESS THAN ("2024-11-01"),
    PARTITION p202411 VALUES LESS THAN ("2024-12-01"),
    PARTITION p202412 VALUES LESS THAN ("2025-01-01"),
    PARTITION p202501 VALUES LESS THAN ("2025-02-01")
)
DISTRIBUTED BY HASH(customer_id) BUCKETS 10
PROPERTIES (
    "replication_num" = "1"
);
