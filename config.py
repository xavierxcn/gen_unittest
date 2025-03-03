import os
import json
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 支持的模型列表
SUPPORTED_MODELS = [
    "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-3.5-turbo", 
    "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"
]

# API配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")

# 如果指定的模型不在支持列表中，使用默认模型
if OPENAI_MODEL not in SUPPORTED_MODELS:
    print(f"警告: 指定的模型 '{OPENAI_MODEL}' 不在支持列表中，将使用默认模型 'gpt-4'")
    OPENAI_MODEL = "gpt-4"

# 项目配置
PROJECT_ROOT = Path(__file__).parent
MAX_TOKENS = 4000
TEMPERATURE = 0.2

# 测试框架配置
DEFAULT_TEST_FRAMEWORK = "junit"  # 可选: junit (Android), pytest/unittest (Python)
DEFAULT_FOCUS = "android"  # 可选: android, python

# 默认排除目录
DEFAULT_EXCLUDE_DIRS = ['.git', 'build', '.gradle', '.idea', 'node_modules', 'dist', 'target']

# 检查必要的环境变量
def check_environment():
    """检查必要的环境变量是否设置"""
    if not OPENAI_API_KEY:
        raise EnvironmentError(
            "未设置OPENAI_API_KEY环境变量。请在.env文件中设置或通过命令行导出。"
            "\n例如：export OPENAI_API_KEY=your_api_key_here"
        )
    return True

# 加载用户配置（如果存在）
def load_user_config() -> Dict[str, Any]:
    """
    加载用户配置文件
    
    Returns:
        用户配置字典
    """
    config_path = PROJECT_ROOT / "user_config.json"
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载用户配置文件失败: {str(e)}")
    return {}

# 保存用户配置
def save_user_config(config: Dict[str, Any]):
    """
    保存用户配置到文件
    
    Args:
        config: 要保存的配置字典
    """
    config_path = PROJECT_ROOT / "user_config.json"
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"保存用户配置文件失败: {str(e)}")

# 获取完整配置（合并默认配置和用户配置）
def get_config() -> Dict[str, Any]:
    """
    获取完整配置
    
    Returns:
        合并后的配置字典
    """
    # 默认配置
    default_config = {
        "api": {
            "openai_api_base": OPENAI_API_BASE,
            "openai_model": OPENAI_MODEL,
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE
        },
        "test": {
            "framework": DEFAULT_TEST_FRAMEWORK,
            "focus": DEFAULT_FOCUS,
            "exclude_dirs": DEFAULT_EXCLUDE_DIRS
        }
    }
    
    # 加载用户配置
    user_config = load_user_config()
    
    # 合并配置
    merged_config = default_config.copy()
    
    # 递归合并字典
    def merge_dict(d1, d2):
        for k, v in d2.items():
            if k in d1 and isinstance(d1[k], dict) and isinstance(v, dict):
                merge_dict(d1[k], v)
            else:
                d1[k] = v
    
    merge_dict(merged_config, user_config)
    
    return merged_config
