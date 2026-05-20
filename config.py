"""
全局配置文件
"""
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent

# 项目配置映射
# 每个数据集市项目拥有两个库:
#   db     - 生产库 (ETL 读写, verify 时作为源)
#   qa_db  - 验证库 (verify 时写入, 用于重构对比)
PROJECT_CONFIG = {
    "shop": {
        "dir": "shop",
        "db": "shop_dm",
        "qa_db": "shop_dm_qa",
        "lineage_db": "shop_lineage",
    },
    "olist": {
        "dir": "olist",
        "db": "olist_dm",
        "qa_db": "olist_dm_qa",
        "lineage_db": "olist_lineage",
    },
}

# 兼容旧的命名
PROJECT_MAP = PROJECT_CONFIG

# 数据库环境配置 (MySQL 协议)
# 环境 = 物理集群, 不同的 host/port 组合
# qa_user = 操作验证库 (qa_db) 的专用用户, 权限仅限 qa_db
DB_ENV_CONFIG = {
    "prod": {"host": "172.16.0.90", "port": 9030, "user": "root", "qa_user": "qa"},
    "test": {"host": "172.16.0.90", "port": 9034, "user": "root", "qa_user": "qa"},
}

# Doris HTTP 协议配置 (Stream Load 使用)
DORIS_HTTP_PORT = 8030

# 默认提供 prod 环境的快捷访问
DORIS_HOST = DB_ENV_CONFIG["prod"]["host"]
DORIS_PORT = DB_ENV_CONFIG["prod"]["port"]
DORIS_USER = DB_ENV_CONFIG["prod"]["user"]
DORIS_QA_USER = DB_ENV_CONFIG["prod"]["qa_user"]

def get_mysql_cmd(env: str = "prod", qa: bool = False) -> list[str]:
    """获取 mysql 命令行参数数组.

    Args:
        env: 物理环境 (prod / test)
        qa: True 时使用 qa_user 连接, 用于操作验证库
    """
    cfg = DB_ENV_CONFIG[env]
    user = cfg["qa_user"] if qa else cfg["user"]
    return ["mysql", f"-h{cfg['host']}", f"-P{cfg['port']}", f"-u{user}"]
