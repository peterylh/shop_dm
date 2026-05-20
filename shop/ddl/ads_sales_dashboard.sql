-- ADS 销售驾驶舱汇总表
-- table_id: cd82b3a9-ec2f-4269-8cd0-d4e8d5476a01
DROP TABLE IF EXISTS shop_dm.ads_sales_dashboard;
CREATE TABLE IF NOT EXISTS shop_dm.ads_sales_dashboard (
    stat_date          DATE          NOT NULL COMMENT '统计日期',
    total_orders       INT           NULL COMMENT '总订单数',
    total_customers    INT           NULL COMMENT '总客户数(去重)',
    total_amount       DECIMAL(14,2) NULL COMMENT '总销售额',
    total_discount     DECIMAL(14,2) NULL COMMENT '总折扣金额',
    avg_order_amount   DECIMAL(10,2) NULL COMMENT '平均客单价',
    order_growth_rate  DECIMAL(5,2)  NULL COMMENT '订单环比增长率(%)',
    amount_growth_rate DECIMAL(5,2)  NULL COMMENT '销售额环比增长率(%)',
    etl_time           DATETIME      NOT NULL COMMENT 'ETL处理时间'
) ENGINE=OLAP
UNIQUE KEY(stat_date)
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
DISTRIBUTED BY HASH(stat_date) BUCKETS 10
PROPERTIES (
    "replication_num" = "1"
);
