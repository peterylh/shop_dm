-- ADS 商品日销售排行TOP N表
-- table_id: 208649ff-2988-4a90-b1a6-1359c8334e18
DROP TABLE IF EXISTS shop_dm.ads_product_topn_daily;
CREATE TABLE IF NOT EXISTS shop_dm.ads_product_topn_daily (
    stat_date      DATE          NOT NULL COMMENT '统计日期',
    product_id     BIGINT        NOT NULL COMMENT '商品ID',
    product_name   VARCHAR(128)  NULL COMMENT '商品名称',
    category_name  VARCHAR(64)   NULL COMMENT '品类名称',
    sale_quantity  INT           NULL COMMENT '销售数量',
    sale_amount    DECIMAL(14,2) NULL COMMENT '销售金额',
    rank_num       INT           NULL COMMENT '排名',
    etl_time       DATETIME      NOT NULL COMMENT 'ETL处理时间'
) ENGINE=OLAP
UNIQUE KEY(stat_date, product_id)
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
DISTRIBUTED BY HASH(product_id) BUCKETS 10
PROPERTIES (
    "replication_num" = "1"
);
