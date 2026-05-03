import logging
import sys

#创建logger
logger=logging.getLogger("backend")
logger.setLevel(logging.DEBUG)

#控制台输出（开发时看）
console_handler=logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)

#文件输出（生产时存）
file_handler=logging.FileHandler("app.log",encoding="utf-8")
file_handler.setLevel(logging.INFO)

#日志格式
formatter=logging.Formatter(
    "%(asctime)|%(levelname)-8s|%(name)s| %(message)s",
     datefmt="%Y-%m-%d %H:%M:%S"
     )

#设置格式
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

#添加输出渠道
logger.addHandler(console_handler)
logger.addHandler(file_handler)
