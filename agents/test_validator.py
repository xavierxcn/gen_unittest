import os
import tempfile
import subprocess
import re
import json
from typing import Dict, Any, Tuple, Optional
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.actions import Action
from metagpt.logs import logger


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
        # 根据文件类型选择验证方法
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
        # 使用临时文件和javac进行语法检查
        with tempfile.NamedTemporaryFile(suffix='.java', delete=False) as temp_file:
            temp_file_path = temp_file.name
            try:
                # 写入测试代码到临时文件
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    f.write(test_code)
                
                # 尝试使用javac编译
                if self._is_command_available('javac'):
                    result = subprocess.run(
                        ['javac', '-Xlint:all', temp_file_path],
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        return True, ""
                    else:
                        return False, result.stderr
                else:
                    # 如果javac不可用，回退到基本语法检查
                    return self._basic_java_syntax_check(test_code)
            except Exception as e:
                return False, f"验证Java语法时出错: {str(e)}"
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
    
    def _basic_java_syntax_check(self, test_code: str) -> Tuple[bool, str]:
        """基本的Java语法检查，当javac不可用时使用"""
        errors = []
        
        # 检查括号是否匹配
        if test_code.count('{') != test_code.count('}'):
            errors.append("花括号不匹配")
        
        if test_code.count('(') != test_code.count(')'):
            errors.append("圆括号不匹配")
        
        if test_code.count('[') != test_code.count(']'):
            errors.append("方括号不匹配")
        
        # 检查分号
        lines = test_code.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if line and not line.startswith('//') and not line.startswith('/*') and not line.startswith('*') and not line.endswith('{') and not line.endswith('}') and not line.endswith(';') and not line.startswith('@') and not line.startswith('package') and not line.startswith('import'):
                errors.append(f"第{i+1}行可能缺少分号: {line}")
        
        # 检查类定义
        if not re.search(r'class\s+\w+', test_code):
            errors.append("缺少类定义")
        
        if errors:
            return False, "Java语法错误: " + "; ".join(errors)
        return True, ""

    def _validate_kotlin_syntax(self, test_code: str) -> Tuple[bool, str]:
        """
        验证Kotlin测试代码的语法

        Args:
            test_code: 测试代码

        Returns:
            (语法是否有效, 错误信息)
        """
        # 使用临时文件和kotlinc进行语法检查
        with tempfile.NamedTemporaryFile(suffix='.kt', delete=False) as temp_file:
            temp_file_path = temp_file.name
            try:
                # 写入测试代码到临时文件
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    f.write(test_code)
                
                # 尝试使用kotlinc编译
                if self._is_command_available('kotlinc'):
                    result = subprocess.run(
                        ['kotlinc', temp_file_path],
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        return True, ""
                    else:
                        return False, result.stderr
                else:
                    # 如果kotlinc不可用，回退到基本语法检查
                    return self._basic_kotlin_syntax_check(test_code)
            except Exception as e:
                return False, f"验证Kotlin语法时出错: {str(e)}"
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
    
    def _basic_kotlin_syntax_check(self, test_code: str) -> Tuple[bool, str]:
        """基本的Kotlin语法检查，当kotlinc不可用时使用"""
        errors = []
        
        # 检查括号是否匹配
        if test_code.count('{') != test_code.count('}'):
            errors.append("花括号不匹配")
        
        if test_code.count('(') != test_code.count(')'):
            errors.append("圆括号不匹配")
        
        if test_code.count('[') != test_code.count(']'):
            errors.append("方括号不匹配")
        
        # 检查类定义或函数定义
        if not re.search(r'class\s+\w+', test_code) and not re.search(r'fun\s+\w+', test_code):
            errors.append("缺少类或函数定义")
        
        if errors:
            return False, "Kotlin语法错误: " + "; ".join(errors)
        return True, ""
    
    def _is_command_available(self, command: str) -> bool:
        """检查命令是否可用"""
        try:
            subprocess.run(
                [command, '--version'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            return True
        except:
            return False

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
            try:
                # 写入测试代码到临时文件
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    f.write(test_code)
                
                # 根据测试框架选择执行命令
                if framework == 'pytest':
                    cmd = ['pytest', temp_file_path, '-v']
                else:  # unittest
                    cmd = ['python', '-m', 'unittest', temp_file_path]
                
                # 执行测试
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                # 返回执行结果
                return result.returncode == 0, result.stdout + '\n' + result.stderr
            except Exception as e:
                return False, f"执行测试时出错: {str(e)}"
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_file_path)
                except:
                    pass


class TestValidator(Role):
    """测试验证角色，负责验证生成的测试代码"""

    def __init__(self, name="TestValidator"):
        super().__init__(name=name)
        self.description = "我验证生成的测试代码的语法和执行情况。"
        self.validation_action = TestValidationAction()
        self.set_action(self.validation_action)

    async def validate_tests(self, test_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证测试代码

        Args:
            test_info: 测试信息，包含测试代码和相关元数据

        Returns:
            包含验证结果的字典
        """
        # 直接使用保存的action实例，而不是通过get_action获取
        validation_result = await self.validation_action.run(test_info)

        # 直接返回验证结果
        return validation_result
