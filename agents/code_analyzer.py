from typing import Dict, Any, List, Optional
import os
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.actions import Action

from ..utils.code_utils import extract_functions_and_classes, find_function_in_file


class CodeAnalysisAction(Action):
    """分析代码结构和功能的Action"""

    def __init__(self):
        super().__init__()
        self.desc = "分析源代码，提取函数、类和依赖关系"

    async def run(
        self, 
        code_file: str, 
        function_name: str = None
    ) -> Dict[str, Any]:
        """
        分析给定的代码文件

        Args:
            code_file: 要分析的代码文件路径
            function_name: 要分析的特定函数名称，如果为None则分析整个文件

        Returns:
            包含代码结构信息的字典
        """
        # 提取代码结构
        code_structure = extract_functions_and_classes(code_file)
        file_ext = os.path.splitext(code_file)[1].lower()

        # 如果指定了函数名，只分析该函数
        if function_name:
            function_info = find_function_in_file(code_file, function_name)
            if not function_info:
                raise ValueError(f"在文件 {code_file} 中未找到函数或方法 {function_name}")
            
            # 创建一个只包含指定函数的代码结构
            if function_info["type"] == "function":
                filtered_structure = {
                    "functions": [function_info["info"]],
                    "classes": [],
                    "imports": code_structure["imports"],
                    "full_content": code_structure["full_content"]
                }
            else:  # method
                filtered_structure = {
                    "functions": [],
                    "classes": [function_info["class_info"]],
                    "imports": code_structure["imports"],
                    "full_content": code_structure["full_content"]
                }
                
            code_structure = filtered_structure

        # 分析代码复杂度和测试需求
        analysis_result = {
            "file_path": code_file,
            "structure": code_structure,
            "test_priorities": self._determine_test_priorities(code_structure, file_ext, function_name),
            "dependencies": code_structure["imports"],
            "function_name": function_name
        }

        return analysis_result

    def _determine_test_priorities(
        self, 
        code_structure: Dict[str, Any], 
        file_ext: str,
        function_name: str = None
    ) -> List[Dict[str, Any]]:
        """
        确定需要优先测试的函数和类

        Args:
            code_structure: 代码结构信息
            file_ext: 文件扩展名
            function_name: 要分析的特定函数名称

        Returns:
            优先测试项列表
        """
        priorities = []

        # 如果是Java/Kotlin文件，使用不同的优先级确定逻辑
        if file_ext in ['.java', '.kt']:
            return self._determine_android_test_priorities(code_structure, function_name)

        # 处理Python函数
        for func in code_structure.get("functions", []):
            # 如果指定了函数名，只处理该函数
            if function_name and func["name"] != function_name:
                continue
                
            # 公共函数优先级高
            if not func["name"].startswith("_"):
                priorities.append({
                    "type": "function",
                    "name": func["name"],
                    "priority": "high" if len(func["args"]) > 0 else "medium"
                })

        # 处理Python类
        for cls in code_structure.get("classes", []):
            class_priority = {
                "type": "class",
                "name": cls["name"],
                "priority": "high",
                "methods": []
            }

            # 分析类方法
            for method in cls.get("methods", []):
                # 如果指定了函数名，只处理该方法
                if function_name and method["name"] != function_name:
                    continue
                    
                if not method["name"].startswith("_") or method["name"] == "__init__":
                    class_priority["methods"].append({
                        "name": method["name"],
                        "priority": "high" if method["name"] == "__init__" else "medium"
                    })

            # 只有当类有方法需要测试时才添加
            if class_priority["methods"]:
                priorities.append(class_priority)

        return priorities
        
    def _determine_android_test_priorities(
        self, 
        code_structure: Dict[str, Any],
        function_name: str = None
    ) -> List[Dict[str, Any]]:
        """
        确定需要优先测试的Android函数和类

        Args:
            code_structure: 代码结构信息
            function_name: 要分析的特定函数名称

        Returns:
            优先测试项列表
        """
        priorities = []

        # 处理Java/Kotlin顶级函数（通常很少）
        for func in code_structure.get("functions", []):
            # 如果指定了函数名，只处理该函数
            if function_name and func["name"] != function_name:
                continue
                
            priorities.append({
                "type": "function",
                "name": func["name"],
                "priority": "high"
            })

        # 处理Java/Kotlin类
        for cls in code_structure.get("classes", []):
            class_priority = {
                "type": "class",
                "name": cls["name"],
                "priority": "high",
                "methods": []
            }

            # 分析类方法
            for method in cls.get("methods", []):
                # 如果指定了函数名，只处理该方法
                if function_name and method["name"] != function_name:
                    continue
                
                # 检查方法修饰符
                modifiers = method.get("modifiers", [])
                
                # 跳过私有方法，除非是指定要测试的函数
                if "private" in modifiers and not (function_name and method["name"] == function_name):
                    continue
                    
                # 确定优先级
                priority = "medium"
                if "public" in modifiers:
                    priority = "high"
                if method["name"].startswith("test") or method["name"].endswith("Test"):
                    priority = "low"  # 测试方法本身不需要测试
                
                class_priority["methods"].append({
                    "name": method["name"],
                    "priority": priority
                })

            # 只有当类有方法需要测试时才添加
            if class_priority["methods"]:
                priorities.append(class_priority)

        return priorities


class CodeAnalyzer(Role):
    """代码分析角色，负责分析源代码并提供结构化信息"""

    def __init__(self, name="CodeAnalyzer"):
        super().__init__(name=name)
        self.description = "我分析源代码并提取关键信息，为测试生成提供基础。"
        self.add_action(CodeAnalysisAction())

    async def analyze_code(
        self, 
        code_file: str,
        function_name: str = None
    ) -> Message:
        """
        分析指定的代码文件

        Args:
            code_file: 要分析的代码文件路径
            function_name: 要分析的特定函数名称，如果为None则分析整个文件

        Returns:
            包含分析结果的消息
        """
        analysis_action = self.get_action(CodeAnalysisAction)
        analysis_result = await analysis_action.run(code_file, function_name)

        if function_name:
            content = f"完成对{code_file}中{function_name}函数的分析"
        else:
            content = f"完成对{code_file}的分析"
            
        return Message(
            content=content,
            cause_by=analysis_action,
            meta=analysis_result
        )
