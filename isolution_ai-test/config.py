import logging
from logging.handlers import TimedRotatingFileHandler
import os


def get_logger(name: str, log_dir: str = "./logs") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:  # 避免重复添加 handler
        # 控制台 handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # 错误日志文件 handler（每天一个文件）
        os.makedirs(log_dir, exist_ok=True)
        error_log_file = os.path.join(log_dir, "error.log")

        error_handler = TimedRotatingFileHandler(
            filename=error_log_file,
            when="midnight",  # 每天 0 点生成新文件
            interval=1,
            backupCount=7,    # 保留最近 7 天
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)  # 只记录 ERROR 及以上日志
        error_formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        error_handler.setFormatter(error_formatter)
        logger.addHandler(error_handler)

        # -----------------
        # 正常日志文件 handler（INFO 及以上）
        # -----------------
        info_log_file = os.path.join(log_dir, "info.log")
        info_handler = TimedRotatingFileHandler(
            filename=info_log_file,
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8"
        )
        info_handler.setLevel(logging.INFO)
        info_formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        info_handler.setFormatter(info_formatter)
        logger.addHandler(info_handler)

    return logger

# 配置日志
LOOGER = get_logger("road_agent")


# llm配置
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/"
API_KEY = "sk-fa8a2c8b696b45748485da5972ebcb68"

PARAM_MODEL_NAME = "qwen-turbo"
DEV_PORT = 9001
TEST_PORT = 9002
PROD_PORT = 9003
# Milvus / Zilliz 配置
MILVUS_HOST = os.getenv("MILVUS_HOST", "http://10.0.96.249:19530")
MILVUS_TOKEN = os.getenv("MILVUS_TOKEN", "")
MILVUS_DB_NAME = os.getenv("MILVUS_DB_NAME", "isolution_dev")
MILVUS_COLLECTION_NAME = os.getenv("MILVUS_COLLECTION_NAME", "products")
