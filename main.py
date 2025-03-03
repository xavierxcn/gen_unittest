import os
import asyncio
import argparse
from typing import List, Dict, Any, Optional
from pathlib import Path

from metagpt.logs import logger
from metagpt.team import Team

from agents.code_analyzer import CodeAnalyzer
from agents.test_generator import TestGenerator
from agents.test_validator import TestValidator
from utils.code_utils import find_android_files
from config import (
    OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_MODEL, 
    check_environment, get_config, DEFAULT_EXCLUDE_DIRS
)


class TestGenerationTeam:
    """自动测试生成团队，协调多个Agent完成测试生成任务"""

    def __init__(self):
        """初始化测试生成团队"""
        # 创建团队成员
        self.code_analyzer = CodeAnalyzer()
        self.test_generator = TestGenerator()
        self.test_validator = TestValidator()

        # 创建MetaGPT团队
        self.team = Team()
        self.team.hire([self.code_analyzer, self.test_generator, self.test_validator])

    async def generate_tests_for_file(
        self, 
        file_path: str, 
        function_name: str = None,
        example_test: str = None
    ) -> Dict[str, Any]:
        """
        为单个文件生成测试

        Args:
            file_path: 源代码文件路径
            function_name: 要测试的特定函数名称，如果为None则测试整个文件
            example_test: 用户提供的测试示例，生成的测试将严格遵循此示例的风格和结构

        Returns:
            测试生成结果
        """
        if function_name:
            logger.info(f"为文件 {file_path} 中的方法 {function_name} 生成测试")
        else:
            logger.info(f"为文件生成测试: {file_path}")

        # 1. 分析代码
        analysis_msg = await self.code_analyzer.analyze_code(file_path, function_name)
        code_analysis = analysis_msg.meta

        # 2. 生成测试
        test_msg = await self.test_generator.generate_tests(
            code_analysis, 
            "junit",  # 固定使用JUnit框架
            function_name,
            example_test
        )
        test_info = test_msg.meta

        # 3. 验证测试
        validation_msg = await self.test_validator.validate_tests(test_info)
        validation_result = validation_msg.meta

        return {
            "source_file": file_path,
            "function_name": function_name,
            "test_file": validation_result["test_file"],
            "test_code": validation_result["test_code"],
            "syntax_valid": validation_result["syntax_valid"],
            "execution_valid": validation_result.get("execution_valid", False),
            "execution_result": validation_result.get("execution_result", "Android测试需要在Android环境中执行")
        }

    async def generate_tests_for_directory(
        self, 
        directory: str, 
        exclude_dirs: List[str] = None,
        function_name: str = None,
        example_test: str = None
    ) -> List[Dict[str, Any]]:
        """
        为目录中的所有Android源代码文件生成测试

        Args:
            directory: 源代码目录
            exclude_dirs: 要排除的目录列表
            function_name: 要测试的特定函数名称，如果为None则测试整个文件
            example_test: 用户提供的测试示例

        Returns:
            所有文件的测试生成结果
        """
        logger.info(f"为目录生成测试: {directory}")

        # 查找所有Android文件
        source_files = find_android_files(directory, exclude_dirs)
        logger.info(f"找到 {len(source_files)} 个Android源代码文件")

        # 为每个文件生成测试
        results = []
        for file_path in source_files:
            try:
                result = await self.generate_tests_for_file(
                    file_path, 
                    function_name,
                    example_test
                )
                results.append(result)
                logger.info(f"成功为 {file_path} 生成测试")
            except Exception as e:
                logger.error(f"为 {file_path} 生成测试失败: {str(e)}")
                results.append({
                    "source_file": file_path,
                    "function_name": function_name,
                    "error": str(e)
                })

        return results

    def save_results_summary(self, results: List[Dict[str, Any]], output_file: str = "test_generation_summary.txt"):
        """
        保存测试生成结果摘要

        Args:
            results: 测试生成结果列表
            output_file: 输出文件路径
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Android单元测试生成摘要\n\n")

            total = len(results)
            success = sum(1 for r in results if r.get("syntax_valid", False))

            f.write(f"总文件数: {total}\n")
            percentage = success / total * 100 if total > 0 else 0
            f.write(f"语法有效的测试: {success} ({percentage:.1f}%)\n\n")

            f.write("## 详细结果\n\n")
            for result in results:
                source_file = result.get("source_file", "未知")
                function_name = result.get("function_name", "整个文件")
                
                if function_name:
                    f.write(f"### {os.path.basename(source_file)} - 方法: {function_name}\n")
                else:
                    f.write(f"### {os.path.basename(source_file)}\n")

                if "error" in result:
                    f.write(f"错误: {result['error']}\n\n")
                    continue

                test_file = result.get("test_file", "未知")
                syntax_valid = "是" if result.get("syntax_valid", False) else "否"

                f.write(f"- 源文件: {source_file}\n")
                if function_name:
                    f.write(f"- 测试方法: {function_name}\n")
                f.write(f"- 测试文件: {test_file}\n")
                f.write(f"- 语法有效: {syntax_valid}\n\n")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="自动生成Android单元测试")
    parser.add_argument("path", help="Android源代码文件或目录路径")
    parser.add_argument("--function", help="要测试的特定方法名称")
    parser.add_argument("--example", help="测试示例文件路径，生成的测试将遵循此示例的风格")
    parser.add_argument("--exclude", nargs="+", default=None, help="排除的目录")
    parser.add_argument("--summary", default="test_generation_summary.txt", help="摘要输出文件")
    parser.add_argument("--model", help="要使用的OpenAI模型名称，覆盖环境变量设置")
    parser.add_argument("--config", help="自定义配置文件路径")

    args = parser.parse_args()

    try:
        # 检查环境变量
        check_environment()
        
        # 加载配置
        config = get_config()
        if args.config and os.path.isfile(args.config):
            try:
                import json
                with open(args.config, 'r', encoding='utf-8') as f:
                    custom_config = json.load(f)
                    # 更新配置
                    for key, value in custom_config.items():
                        if isinstance(value, dict) and key in config and isinstance(config[key], dict):
                            config[key].update(value)
                        else:
                            config[key] = value
                logger.info(f"已加载自定义配置: {args.config}")
            except Exception as e:
                logger.error(f"加载自定义配置失败: {str(e)}")
        
        # 如果命令行指定了模型，则使用命令行参数
        model = args.model or config["api"]["openai_model"]
        
        # 设置环境变量
        os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
        os.environ["OPENAI_API_BASE"] = config["api"]["openai_api_base"]
        os.environ["OPENAI_MODEL"] = model
        
        # 获取排除目录
        exclude_dirs = args.exclude if args.exclude is not None else config["test"]["exclude_dirs"]
        
        # 创建测试生成团队
        team = TestGenerationTeam()

        # 读取测试示例（如果提供）
        example_test = None
        if args.example:
            if not os.path.isfile(args.example):
                logger.warning(f"测试示例文件不存在: {args.example}")
            else:
                with open(args.example, 'r', encoding='utf-8') as f:
                    example_test = f.read()
                logger.info(f"已加载测试示例: {args.example}")

        # 生成测试
        path = args.path
        
        if not os.path.exists(path):
            raise ValueError(f"路径不存在: {path}")
            
        if os.path.isfile(path):
            file_ext = os.path.splitext(path)[1].lower()
            if file_ext not in ['.java', '.kt']:
                raise ValueError(f"不支持的文件类型: {file_ext}。只支持Java和Kotlin文件。")
                
            results = [await team.generate_tests_for_file(path, args.function, example_test)]
        elif os.path.isdir(path):
            results = await team.generate_tests_for_directory(path, exclude_dirs, args.function, example_test)
        else:
            raise ValueError(f"无效的路径: {path}")

        # 保存摘要
        team.save_results_summary(results, args.summary)
        logger.info(f"测试生成完成，摘要已保存到 {args.summary}")
        
    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        return 1
    
    return 0


if __name__ == "__main__":
    # 运行主程序
    exit_code = asyncio.run(main())
    exit(exit_code)
