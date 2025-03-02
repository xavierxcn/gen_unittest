import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# API配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")

# 项目配置
PROJECT_ROOT = Path(__file__).parent.parent
MAX_TOKENS = 4000
TEMPERATURE = 0.2

# 测试框架配置
DEFAULT_TEST_FRAMEWORK = "junit"  # 可选: junit (Android), pytest/unittest (Python)
DEFAULT_FOCUS = "android"  # 可选: android, python
