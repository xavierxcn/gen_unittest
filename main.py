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
from utils.code_utils import find_python_files, find_android_files
from config import OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_MODEL


class TestGenerationTeam:
    """自动测试生成团队，协调多个Agent完成测试生成任务"""

    def __init__(self, framework: str = "junit", focus: str = "android"):
        """
        初始化测试生成团队

        Args:
            framework: 测试框架，默认为junit (Android)
            focus: 测试重点，可选 "android" 或 "python"
        """
        self.framework = framework
        self.focus = focus

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
        additional_info: str = None
    ) -> Dict[str, Any]:
        """
        为单个文件生成测试

        Args:
            file_path: 源代码文件路径
            function_name: 要测试的特定函数名称，如果为None则测试整个文件
            additional_info: 用户提供的额外信息

        Returns:
            测试生成结果
        """
        if function_name:
            logger.info(f"为文件 {file_path} 中的函数 {function_name} 生成测试")
        else:
            logger.info(f"为文件生成测试: {file_path}")

        # 1. 分析代码
        analysis_msg = await self.code_analyzer.analyze_code(file_path, function_name)
        code_analysis = analysis_msg.meta

        # 2. 生成测试
        test_msg = await self.test_generator.generate_tests(
            code_analysis, 
            self.framework,
            function_name,
            additional_info
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
            "execution_valid": validation_result["execution_valid"],
            "execution_result": validation_result["execution_result"]
        }

    async def generate_tests_for_directory(
        self, 
        directory: str, 
        exclude_dirs: List[str] = None,
        function_name: str = None,
        additional_info: str = None
    ) -> List[Dict[str, Any]]:
        """
        为目录中的所有源代码文件生成测试

        Args:
            directory: 源代码目录
            exclude_dirs: 要排除的目录列表
            function_name: 要测试的特定函数名称，如果为None则测试整个文件
            additional_info: 用户提供的额外信息

        Returns:
            所有文件的测试生成结果
        """
        logger.info(f"为目录生成测试: {directory}")

        # 根据重点选择要处理的文件类型
        if self.focus == "android":
            source_files = find_android_files(directory, exclude_dirs)
            logger.info(f"找到 {len(source_files)} 个Android源代码文件")
        else:  # python
            source_files = find_python_files(directory, exclude_dirs)
            logger.info(f"找到 {len(source_files)} 个Python文件")

        # 为每个文件生成测试
        results = []
        for file_path in source_files:
            try:
                result = await self.generate_tests_for_file(
                    file_path, 
                    function_name,
                    additional_info
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
            f.write("# 自动测试生成摘要\n\n")

            total = len(results)
            success = sum(1 for r in results if r.get("syntax_valid", False))
            executable = sum(1 for r in results if r.get("execution_valid", False))

            f.write(f"总文件数: {total}\n")
            f.write(f"语法有效的测试: {success} ({success / total * 100:.1f}%)\n")
            f.write(f"可执行的测试: {executable} ({executable / total * 100:.1f}%)\n\n")

            f.write("## 详细结果\n\n")
            for result in results:
                source_file = result.get("source_file", "未知")
                function_name = result.get("function_name", "整个文件")
                
                if function_name:
                    f.write(f"### {os.path.basename(source_file)} - 函数: {function_name}\n")
                else:
                    f.write(f"### {os.path.basename(source_file)}\n")

                if "error" in result:
                    f.write(f"错误: {result['error']}\n\n")
                    continue

                test_file = result.get("test_file", "未知")
                syntax_valid = "是" if result.get("syntax_valid", False) else "否"
                execution_valid = "是" if result.get("execution_valid", False) else "否"

                f.write(f"- 源文件: {source_file}\n")
                if function_name:
                    f.write(f"- 测试函数: {function_name}\n")
                f.write(f"- 测试文件: {test_file}\n")
                f.write(f"- 语法有效: {syntax_valid}\n")
                f.write(f"- 可执行: {execution_valid}\n\n")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="自动生成单元测试")
    parser.add_argument("path", help="源代码文件或目录路径")
    parser.add_argument("--framework", choices=["junit", "pytest", "unittest"], default="junit", 
                        help="测试框架 (junit用于Android, pytest/unittest用于Python)")
    parser.add_argument("--focus", choices=["android", "python"], default="android", 
                        help="测试重点，默认为Android")
    parser.add_argument("--function", help="要测试的特定函数名称")
    parser.add_argument("--info", help="额外的测试信息")
    parser.add_argument("--exclude", nargs="+", default=[], help="排除的目录")
    parser.add_argument("--summary", default="test_generation_summary.txt", help="摘要输出文件")

    args = parser.parse_args()

    # 检查API密钥
    if not OPENAI_API_KEY:
        raise ValueError("未设置OPENAI_API_KEY环境变量")

    # 创建测试生成团队
    team = TestGenerationTeam(framework=args.framework, focus=args.focus)

    # 生成测试
    path = args.path
    file_ext = os.path.splitext(path)[1].lower()
    
    # 检查文件类型是否与focus匹配
    is_android_file = file_ext in ['.java', '.kt']
    is_python_file = file_ext == '.py'
    
    if os.path.isfile(path):
        if (args.focus == "android" and not is_android_file) or (args.focus == "python" and not is_python_file):
            logger.warning(f"文件类型 {file_ext} 与测试重点 {args.focus} 不匹配，但仍将尝试生成测试")
            
        results = [await team.generate_tests_for_file(path, args.function, args.info)]
    elif os.path.isdir(path):
        results = await team.generate_tests_for_directory(path, args.exclude, args.function, args.info)
    else:
        raise ValueError(f"无效的路径: {path}")

    # 保存摘要
    team.save_results_summary(results, args.summary)
    logger.info(f"测试生成完成，摘要已保存到 {args.summary}")


if __name__ == "__main__":
    # 设置环境变量
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    os.environ["OPENAI_API_BASE"] = OPENAI_API_BASE
    os.environ["OPENAI_MODEL"] = OPENAI_MODEL

    # 运行主程序
    asyncio.run(main())
