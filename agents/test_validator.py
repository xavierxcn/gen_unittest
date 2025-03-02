import os
import tempfile
import subprocess
import re
from typing import Dict, Any, Tuple
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.actions import Action


class TestValidationAction(Action):
    """验证生成的测试代码的Action"""

    def __init__(self):
        super().__init__()
        self.desc = "验证生成的测试代码的语法和执行情况"

    async def run(self, test_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证生成的测试代码

        Args:
            test_info: 测试信息，包含测试代码和相关元数据

        Returns:
            验证结果
        """
        test_code = test_info["test_code"]
        test_file = test_info["test_file"]
        framework = test_info.get("framework", "junit")
        file_ext = os.path.splitext(test_file)[1].lower()

        # 根据文件类型选择不同的验证方法
        if file_ext == '.py':
            # Python测试验证
            syntax_valid, syntax_error = self._validate_python_syntax(test_code)
            
            # 如果语法有效，尝试执行测试
            execution_valid = False
            execution_result = ""
            if syntax_valid:
                execution_valid, execution_result = self._validate_python_execution(test_code, framework)
        else:  # Java/Kotlin
            # Android测试验证
            syntax_valid, syntax_error = self._validate_android_syntax(test_code, file_ext)
            
            # 对于Android测试，我们不执行实际测试，因为需要Android环境
            execution_valid = False
            execution_result = "Android测试需要在Android环境中执行，此处仅验证语法。"

        return {
            "test_file": test_file,
            "test_code": test_code,
            "syntax_valid": syntax_valid,
            "syntax_error": syntax_error if not syntax_valid else "",
            "execution_valid": execution_valid,
            "execution_result": execution_result
        }

    def _validate_python_syntax(self, test_code: str) -> Tuple[bool, str]:
        """
        验证Python测试代码的语法

        Args:
            test_code: 测试代码

        Returns:
            (语法是否有效, 错误信息)
        """
        try:
            # 使用Python的ast模块验证语法
            import ast
            ast.parse(test_code)
            return True, ""
        except SyntaxError as e:
            return False, str(e)

    def _validate_android_syntax(self, test_code: str, file_ext: str) -> Tuple[bool, str]:
        """
        验证Android测试代码的语法

        Args:
            test_code: 测试代码
            file_ext: 文件扩展名

        Returns:
            (语法是否有效, 错误信息)
        """
        # 简单的语法检查
        if file_ext == '.java':
            return self._validate_java_syntax(test_code)
        elif file_ext == '.kt':
            return self._validate_kotlin_syntax(test_code)
        else:
            return False, f"不支持的文件类型: {file_ext}"

    def _validate_java_syntax(self, test_code: str) -> Tuple[bool, str]:
        """
        验证Java测试代码的语法

        Args:
            test_code: 测试代码

        Returns:
            (语法是否有效, 错误信息)
        """
        # 简单的语法检查
        # 检查括号是否匹配
        if test_code.count('{') != test_code.count('}'):
            return False, "Java语法错误: 花括号不匹配"
        
        # 检查分号
        lines = test_code.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if line and not line.startswith('//') and not line.startswith('/*') and not line.startswith('*') and not line.endswith('{') and not line.endswith('}') and not line.endswith(';') and not line.startswith('@') and not line.startswith('package') and not line.startswith('import'):
                return False, f"Java语法错误: 第{i+1}行缺少分号: {line}"
        
        return True, ""

    def _validate_kotlin_syntax(self, test_code: str) -> Tuple[bool, str]:
        """
        验证Kotlin测试代码的语法

        Args:
            test_code: 测试代码

        Returns:
            (语法是否有效, 错误信息)
        """
        # 简单的语法检查
        # 检查括号是否匹配
        if test_code.count('{') != test_code.count('}'):
            return False, "Kotlin语法错误: 花括号不匹配"
        
        return True, ""

    def _validate_python_execution(self, test_code: str, framework: str) -> Tuple[bool, str]:
        """
        验证Python测试代码的执行情况

        Args:
            test_code: 测试代码
            framework: 测试框架

        Returns:
            (执行是否成功, 执行结果)
        """
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(test_code.encode('utf-8'))

        try:
            # 执行测试
            if framework == "pytest":
                cmd = ["pytest", "-xvs", temp_file_path]
            else:  # unittest
                cmd = ["python", temp_file_path]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10  # 设置超时时间
            )

            # 检查执行结果
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, f"退出代码: {result.returncode}\n标准输出: {result.stdout}\n标准错误: {result.stderr}"
        except Exception as e:
            return False, f"执行测试时出错: {str(e)}"
        finally:
            # 删除临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)


class TestValidator(Role):
    """测试验证角色，负责验证生成的测试代码"""

    def __init__(self, name="TestValidator"):
        super().__init__(name=name)
        self.description = "我验证生成的测试代码的语法和执行情况。"
        self.add_action(TestValidationAction())

    async def validate_tests(self, test_info: Dict[str, Any]) -> Message:
        """
        验证测试代码

        Args:
            test_info: 测试信息，包含测试代码和相关元数据

        Returns:
            包含验证结果的消息
        """
        validation_action = self.get_action(TestValidationAction)
        validation_result = await validation_action.run(test_info)

        return Message(
            content=f"完成对测试代码的验证",
            cause_by=validation_action,
            meta=validation_result
        )
