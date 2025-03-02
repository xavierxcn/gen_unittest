from typing import Dict, Any, List, Optional
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.actions import Action
import os

from ..utils.code_utils import (
    get_test_file_path, extract_module_name, extract_package_name, 
    extract_class_name, find_function_in_file
)
from ..config import DEFAULT_TEST_FRAMEWORK


class TestGenerationAction(Action):
    """生成单元测试代码的Action"""

    def __init__(self):
        super().__init__()
        self.desc = "根据代码分析结果生成单元测试"

    async def run(
        self, 
        code_analysis: Dict[str, Any], 
        framework: str = DEFAULT_TEST_FRAMEWORK,
        function_name: str = None,
        additional_info: str = None
    ) -> Dict[str, Any]:
        """
        根据代码分析结果生成单元测试

        Args:
            code_analysis: 代码分析结果
            framework: 测试框架，默认为pytest
            function_name: 要测试的特定函数名称，如果为None则测试整个文件
            additional_info: 用户提供的额外信息

        Returns:
            包含生成的测试代码的字典
        """
        file_path = code_analysis["file_path"]
        code_structure = code_analysis["structure"]
        test_priorities = code_analysis["test_priorities"]
        file_ext = os.path.splitext(file_path)[1].lower()

        # 生成测试文件路径
        test_file_path = get_test_file_path(file_path)
        
        # 根据文件类型选择不同的处理方式
        if file_ext == '.py':
            module_name = extract_module_name(file_path)
            package_name = None
            class_name = None
        else:  # Java/Kotlin
            module_name = None
            package_name = extract_package_name(file_path)
            class_name = extract_class_name(file_path)

        # 如果指定了函数名，只生成该函数的测试
        if function_name:
            test_code = self._generate_specific_function_test(
                file_path=file_path,
                function_name=function_name,
                code_structure=code_structure,
                framework=framework,
                module_name=module_name,
                package_name=package_name,
                class_name=class_name,
                additional_info=additional_info
            )
        else:
            # 生成整个文件的测试代码
            test_code = self._generate_test_code(
                file_path=file_path,
                code_structure=code_structure,
                test_priorities=test_priorities,
                framework=framework,
                module_name=module_name,
                package_name=package_name,
                class_name=class_name,
                additional_info=additional_info
            )

        return {
            "source_file": file_path,
            "test_file": test_file_path,
            "test_code": test_code,
            "framework": framework,
            "function_name": function_name
        }

    def _generate_test_code(
            self,
            file_path: str,
            code_structure: Dict[str, Any],
            test_priorities: List[Dict[str, Any]],
            framework: str,
            module_name: str = None,
            package_name: str = None,
            class_name: str = None,
            additional_info: str = None
    ) -> str:
        """
        生成测试代码

        Args:
            file_path: 源代码文件路径
            code_structure: 代码结构
            test_priorities: 测试优先级
            framework: 测试框架
            module_name: Python模块名称
            package_name: Java/Kotlin包名
            class_name: Java/Kotlin类名
            additional_info: 用户提供的额外信息

        Returns:
            生成的测试代码
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # 根据文件类型选择不同的测试生成方法
        if file_ext == '.py':
            return self._generate_python_test_code(
                module_name=module_name,
                code_structure=code_structure,
                test_priorities=test_priorities,
                framework=framework,
                additional_info=additional_info
            )
        elif file_ext == '.java':
            return self._generate_java_test_code(
                package_name=package_name,
                class_name=class_name,
                code_structure=code_structure,
                test_priorities=test_priorities,
                additional_info=additional_info
            )
        elif file_ext == '.kt':
            return self._generate_kotlin_test_code(
                package_name=package_name,
                class_name=class_name,
                code_structure=code_structure,
                test_priorities=test_priorities,
                additional_info=additional_info
            )
        else:
            raise ValueError(f"不支持的文件类型: {file_ext}")
    
    def _generate_python_test_code(
            self,
            module_name: str,
            code_structure: Dict[str, Any],
            test_priorities: List[Dict[str, Any]],
            framework: str,
            additional_info: str = None
    ) -> str:
        """
        生成Python测试代码

        Args:
            module_name: 模块名称
            code_structure: 代码结构
            test_priorities: 测试优先级
            framework: 测试框架
            additional_info: 用户提供的额外信息

        Returns:
            生成的测试代码
        """
        imports = []
        test_functions = []

        # 添加基本导入
        if framework == "pytest":
            imports.append("import pytest")
        else:  # unittest
            imports.append("import unittest")

        # 导入被测模块
        imports.append(f"import {module_name}")

        # 为每个优先级项生成测试
        for item in test_priorities:
            if item["type"] == "function":
                func_name = item["name"]
                # 查找对应的函数定义
                func_def = next((f for f in code_structure["functions"] if f["name"] == func_name), None)
                if func_def:
                    test_functions.append(self._generate_function_test(
                        func_name=func_name,
                        func_def=func_def,
                        module_name=module_name,
                        framework=framework,
                        additional_info=additional_info
                    ))

            elif item["type"] == "class":
                class_name = item["name"]
                # 查找对应的类定义
                class_def = next((c for c in code_structure["classes"] if c["name"] == class_name), None)
                if class_def:
                    test_functions.append(self._generate_class_test(
                        class_name=class_name,
                        class_def=class_def,
                        methods=item.get("methods", []),
                        module_name=module_name,
                        framework=framework,
                        additional_info=additional_info
                    ))

        # 组合测试代码
        test_code = "\n".join(imports) + "\n\n\n"

        if framework == "unittest":
            # 为unittest添加TestCase类
            test_code += f"class Test{module_name.capitalize()}(unittest.TestCase):\n"
            indented_tests = "\n".join(["    " + line for test in test_functions for line in test.split("\n")])
            test_code += indented_tests
            test_code += "\n\n\nif __name__ == '__main__':\n    unittest.main()\n"
        else:
            # pytest风格的测试
            test_code += "\n\n".join(test_functions)

        return test_code
    
    def _generate_java_test_code(
            self,
            package_name: str,
            class_name: str,
            code_structure: Dict[str, Any],
            test_priorities: List[Dict[str, Any]],
            additional_info: str = None
    ) -> str:
        """
        生成Java测试代码

        Args:
            package_name: 包名
            class_name: 类名
            code_structure: 代码结构
            test_priorities: 测试优先级
            additional_info: 用户提供的额外信息

        Returns:
            生成的测试代码
        """
        imports = []
        test_methods = []
        
        # 添加基本导入
        imports.append("import org.junit.Test;")
        imports.append("import org.junit.Before;")
        imports.append("import static org.junit.Assert.*;")
        
        # 导入被测类
        if package_name:
            imports.append(f"import {package_name}.{class_name};")
        
        # 添加Mockito导入（如果需要）
        imports.append("import org.mockito.Mock;")
        imports.append("import org.mockito.MockitoAnnotations;")
        imports.append("import static org.mockito.Mockito.*;")
        
        # 生成测试类
        test_class = []
        test_class.append(f"public class {class_name}Test {{")
        
        # 添加被测类的实例
        test_class.append(f"    private {class_name} testInstance;")
        test_class.append("")
        
        # 添加setUp方法
        test_class.append("    @Before")
        test_class.append("    public void setUp() {")
        test_class.append("        MockitoAnnotations.initMocks(this);")
        test_class.append(f"        testInstance = new {class_name}();  // TODO: 添加必要的初始化参数")
        test_class.append("    }")
        test_class.append("")
        
        # 为每个优先级项生成测试
        for item in test_priorities:
            if item["type"] == "class" and item["name"] == class_name:
                for method in item.get("methods", []):
                    method_name = method["name"]
                    # 查找对应的方法定义
                    method_def = next((m for m in code_structure["classes"][0]["methods"] 
                                      if m["name"] == method_name), None)
                    if method_def:
                        test_methods.append(self._generate_java_method_test(
                            method_name=method_name,
                            method_def=method_def,
                            class_name=class_name,
                            additional_info=additional_info
                        ))
        
        # 组合测试代码
        test_code = "\n".join(imports) + "\n\n"
        if package_name:
            test_code += f"package {package_name};\n\n"
        
        test_code += "\n".join(test_class) + "\n"
        test_code += "\n".join(["    " + line for method in test_methods for line in method.split("\n")]) + "\n"
        test_code += "}\n"
        
        return test_code
    
    def _generate_kotlin_test_code(
            self,
            package_name: str,
            class_name: str,
            code_structure: Dict[str, Any],
            test_priorities: List[Dict[str, Any]],
            additional_info: str = None
    ) -> str:
        """
        生成Kotlin测试代码

        Args:
            package_name: 包名
            class_name: 类名
            code_structure: 代码结构
            test_priorities: 测试优先级
            additional_info: 用户提供的额外信息

        Returns:
            生成的测试代码
        """
        imports = []
        test_methods = []
        
        # 添加基本导入
        imports.append("import org.junit.Test")
        imports.append("import org.junit.Before")
        imports.append("import org.junit.Assert.*")
        
        # 导入被测类
        if package_name:
            imports.append(f"import {package_name}.{class_name}")
        
        # 添加Mockito导入（如果需要）
        imports.append("import org.mockito.Mock")
        imports.append("import org.mockito.MockitoAnnotations")
        imports.append("import org.mockito.Mockito.*")
        
        # 生成测试类
        test_class = []
        test_class.append(f"class {class_name}Test {{")
        
        # 添加被测类的实例
        test_class.append(f"    private lateinit var testInstance: {class_name}")
        test_class.append("")
        
        # 添加setUp方法
        test_class.append("    @Before")
        test_class.append("    fun setUp() {")
        test_class.append("        MockitoAnnotations.initMocks(this)")
        test_class.append(f"        testInstance = {class_name}()  // TODO: 添加必要的初始化参数")
        test_class.append("    }")
        test_class.append("")
        
        # 为每个优先级项生成测试
        for item in test_priorities:
            if item["type"] == "class" and item["name"] == class_name:
                for method in item.get("methods", []):
                    method_name = method["name"]
                    # 查找对应的方法定义
                    method_def = next((m for m in code_structure["classes"][0]["methods"] 
                                      if m["name"] == method_name), None)
                    if method_def:
                        test_methods.append(self._generate_kotlin_method_test(
                            method_name=method_name,
                            method_def=method_def,
                            class_name=class_name,
                            additional_info=additional_info
                        ))
        
        # 组合测试代码
        test_code = ""
        if package_name:
            test_code += f"package {package_name}\n\n"
        
        test_code += "\n".join(imports) + "\n\n"
        test_code += "\n".join(test_class) + "\n"
        test_code += "\n".join(["    " + line for method in test_methods for line in method.split("\n")]) + "\n"
        test_code += "}\n"
        
        return test_code

    def _generate_function_test(
            self,
            func_name: str,
            func_def: Dict[str, Any],
            module_name: str,
            framework: str,
            additional_info: str = None
    ) -> str:
        """生成函数的测试代码"""
        args = func_def.get("args", [])
        # 移除self参数(如果存在)
        if args and args[0] == "self":
            args = args[1:]

        docstring = func_def.get("docstring", "")

        if framework == "pytest":
            test_func = f"def test_{func_name}():\n"
            test_func += f"    \"\"\"\n    测试 {module_name}.{func_name} 函数\n    \"\"\"\n"

            # 生成测试用例
            test_func += f"    # 准备测试数据\n"
            for arg in args:
                test_func += f"    {arg} = None  # TODO: 设置适当的测试值\n"

            if args:
                args_str = ", ".join(args)
                test_func += f"\n    # 调用被测函数\n"
                test_func += f"    result = {module_name}.{func_name}({args_str})\n\n"
            else:
                test_func += f"\n    # 调用被测函数\n"
                test_func += f"    result = {module_name}.{func_name}()\n\n"

            test_func += f"    # 断言\n"
            test_func += f"    assert result is not None  # TODO: 添加实际的断言\n"

        else:  # unittest
            test_func = f"def test_{func_name}(self):\n"
            test_func += f"    \"\"\"\n    测试 {module_name}.{func_name} 函数\n    \"\"\"\n"

            # 生成测试用例
            test_func += f"    # 准备测试数据\n"
            for arg in args:
                test_func += f"    {arg} = None  # TODO: 设置适当的测试值\n"

            if args:
                args_str = ", ".join(args)
                test_func += f"\n    # 调用被测函数\n"
                test_func += f"    result = {module_name}.{func_name}({args_str})\n\n"
            else:
                test_func += f"\n    # 调用被测函数\n"
                test_func += f"    result = {module_name}.{func_name}()\n\n"

            test_func += f"    # 断言\n"
            test_func += f"    self.assertIsNotNone(result)  # TODO: 添加实际的断言\n"

        return test_func

    def _generate_class_test(
            self,
            class_name: str,
            class_def: Dict[str, Any],
            methods: List[Dict[str, Any]],
            module_name: str,
            framework: str,
            additional_info: str = None
    ) -> str:
        """生成类的测试代码"""
        if framework == "pytest":
            test_class = f"# 测试 {module_name}.{class_name} 类\n\n"

            # 生成类实例化测试
            test_class += f"def test_{class_name}_initialization():\n"
            test_class += f"    \"\"\"\n    测试 {class_name} 类的初始化\n    \"\"\"\n"
            test_class += f"    # 创建实例\n"
            test_class += f"    instance = {module_name}.{class_name}()  # TODO: 添加必要的初始化参数\n\n"
            test_class += f"    # 断言\n"
            test_class += f"    assert instance is not None\n\n"

            # 为每个方法生成测试
            for method in methods:
                method_name = method["name"]
                if method_name != "__init__":  # 初始化方法已在上面测试
                    test_class += f"def test_{class_name}_{method_name}():\n"
                    test_class += f"    \"\"\"\n    测试 {class_name}.{method_name} 方法\n    \"\"\"\n"
                    test_class += f"    # 创建实例\n"
                    test_class += f"    instance = {module_name}.{class_name}()  # TODO: 添加必要的初始化参数\n\n"
                    test_class += f"    # 调用方法\n"
                    test_class += f"    result = instance.{method_name}()  # TODO: 添加必要的方法参数\n\n"
                    test_class += f"    # 断言\n"
                    test_class += f"    assert result is not None  # TODO: 添加实际的断言\n\n"

        else:  # unittest
            test_class = f"# 测试 {module_name}.{class_name} 类\n\n"

            # 生成类实例化测试
            test_class += f"def test_{class_name}_initialization(self):\n"
            test_class += f"    \"\"\"\n    测试 {class_name} 类的初始化\n    \"\"\"\n"
            test_class += f"    # 创建实例\n"
            test_class += f"    instance = {module_name}.{class_name}()  # TODO: 添加必要的初始化参数\n\n"
            test_class += f"    # 断言\n"
            test_class += f"    self.assertIsNotNone(instance)\n\n"

            # 为每个方法生成测试
            for method in methods:
                method_name = method["name"]
                if method_name != "__init__":  # 初始化方法已在上面测试
                    test_class += f"def test_{class_name}_{method_name}(self):\n"
                    test_class += f"    \"\"\"\n    测试 {class_name}.{method_name} 方法\n    \"\"\"\n"
                    test_class += f"    # 创建实例\n"
                    test_class += f"    instance = {module_name}.{class_name}()  # TODO: 添加必要的初始化参数\n\n"
                    test_class += f"    # 调用方法\n"
                    test_class += f"    result = instance.{method_name}()  # TODO: 添加必要的方法参数\n\n"
                    test_class += f"    # 断言\n"
                    test_class += f"    self.assertIsNotNone(result)  # TODO: 添加实际的断言\n\n"

        return test_class


    def _generate_java_method_test(
            self,
            method_name: str,
            method_def: Dict[str, Any],
            class_name: str,
            additional_info: str = None
    ) -> str:
        """
        生成Java方法的测试代码

        Args:
            method_name: 方法名
            method_def: 方法定义
            class_name: 类名
            additional_info: 用户提供的额外信息

        Returns:
            生成的测试代码
        """
        args = method_def.get("args", [])
        return_type = method_def.get("return_type", "void")
        
        # 生成测试方法
        test_method = []
        test_method.append(f"@Test")
        test_method.append(f"public void test{method_name.capitalize()}() {{")
        
        # 准备测试数据
        test_method.append("    // 准备测试数据")
        for arg in args:
            test_method.append(f"    // TODO: 为 {arg} 参数准备测试数据")
        
        # 如果有额外信息，添加注释
        if additional_info:
            test_method.append(f"    // 用户提供的额外信息: {additional_info}")
        
        # 调用被测方法
        test_method.append("    // 调用被测方法")
        if return_type != "void":
            test_method.append(f"    {return_type} result = testInstance.{method_name}();  // TODO: 添加必要的参数")
            test_method.append("")
            test_method.append("    // 验证结果")
            test_method.append("    assertNotNull(result);  // TODO: 添加更具体的断言")
        else:
            test_method.append(f"    testInstance.{method_name}();  // TODO: 添加必要的参数")
            test_method.append("")
            test_method.append("    // 验证行为")
            test_method.append("    // TODO: 验证方法的行为，例如是否调用了依赖的方法")
        
        test_method.append("}")
        
        return "\n".join(test_method)
    
    def _generate_kotlin_method_test(
            self,
            method_name: str,
            method_def: Dict[str, Any],
            class_name: str,
            additional_info: str = None
    ) -> str:
        """
        生成Kotlin方法的测试代码

        Args:
            method_name: 方法名
            method_def: 方法定义
            class_name: 类名
            additional_info: 用户提供的额外信息

        Returns:
            生成的测试代码
        """
        args = method_def.get("args", [])
        
        # 生成测试方法
        test_method = []
        test_method.append(f"@Test")
        test_method.append(f"fun test{method_name.capitalize()}() {{")
        
        # 准备测试数据
        test_method.append("    // 准备测试数据")
        for arg in args:
            test_method.append(f"    // TODO: 为 {arg} 参数准备测试数据")
        
        # 如果有额外信息，添加注释
        if additional_info:
            test_method.append(f"    // 用户提供的额外信息: {additional_info}")
        
        # 调用被测方法
        test_method.append("    // 调用被测方法")
        test_method.append(f"    val result = testInstance.{method_name}()  // TODO: 添加必要的参数")
        test_method.append("")
        test_method.append("    // 验证结果")
        test_method.append("    assertNotNull(result)  // TODO: 添加更具体的断言")
        
        test_method.append("}")
        
        return "\n".join(test_method)
    
    def _generate_specific_function_test(
            self,
            file_path: str,
            function_name: str,
            code_structure: Dict[str, Any],
            framework: str,
            module_name: str = None,
            package_name: str = None,
            class_name: str = None,
            additional_info: str = None
    ) -> str:
        """
        为特定函数生成测试代码

        Args:
            file_path: 源代码文件路径
            function_name: 要测试的函数名
            code_structure: 代码结构
            framework: 测试框架
            module_name: Python模块名称
            package_name: Java/Kotlin包名
            class_name: Java/Kotlin类名
            additional_info: 用户提供的额外信息

        Returns:
            生成的测试代码
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # 查找指定的函数或方法
        function_info = None
        
        # 在顶级函数中查找
        for func in code_structure.get("functions", []):
            if func["name"] == function_name:
                function_info = {
                    "type": "function",
                    "info": func
                }
                break
        
        # 如果没找到，在类方法中查找
        if not function_info:
            for cls in code_structure.get("classes", []):
                for method in cls.get("methods", []):
                    if method["name"] == function_name:
                        function_info = {
                            "type": "method",
                            "info": method,
                            "class_info": cls
                        }
                        break
                if function_info:
                    break
        
        if not function_info:
            return f"// 错误: 在文件 {file_path} 中未找到函数或方法 {function_name}"
        
        # 根据文件类型和函数类型生成测试
        if file_ext == '.py':
            if function_info["type"] == "function":
                # 生成Python函数测试
                imports = []
                if framework == "pytest":
                    imports.append("import pytest")
                else:  # unittest
                    imports.append("import unittest")
                imports.append(f"import {module_name}")
                
                test_code = "\n".join(imports) + "\n\n\n"
                
                func_test = self._generate_function_test(
                    func_name=function_name,
                    func_def=function_info["info"],
                    module_name=module_name,
                    framework=framework,
                    additional_info=additional_info
                )
                
                if framework == "unittest":
                    test_code += f"class Test{module_name.capitalize()}(unittest.TestCase):\n"
                    indented_test = "\n".join(["    " + line for line in func_test.split("\n")])
                    test_code += indented_test
                    test_code += "\n\n\nif __name__ == '__main__':\n    unittest.main()\n"
                else:
                    test_code += func_test
                
                return test_code
            else:  # method
                # 生成Python方法测试
                class_name = function_info["class_info"]["name"]
                
                imports = []
                if framework == "pytest":
                    imports.append("import pytest")
                else:  # unittest
                    imports.append("import unittest")
                imports.append(f"import {module_name}")
                
                test_code = "\n".join(imports) + "\n\n\n"
                
                # 创建一个只包含这个方法的methods列表
                methods = [{"name": function_name}]
                
                class_test = self._generate_class_test(
                    class_name=class_name,
                    class_def=function_info["class_info"],
                    methods=methods,
                    module_name=module_name,
                    framework=framework,
                    additional_info=additional_info
                )
                
                if framework == "unittest":
                    test_code += f"class Test{module_name.capitalize()}(unittest.TestCase):\n"
                    # 只保留特定方法的测试
                    method_lines = []
                    capture = False
                    for line in class_test.split("\n"):
                        if f"test_{class_name}_{function_name}" in line:
                            capture = True
                        if capture:
                            method_lines.append("    " + line)
                        if line.strip() == "" and capture:
                            capture = False
                    
                    test_code += "\n".join(method_lines)
                    test_code += "\n\n\nif __name__ == '__main__':\n    unittest.main()\n"
                else:
                    # 只保留特定方法的测试
                    method_lines = []
                    capture = False
                    for line in class_test.split("\n"):
                        if f"test_{class_name}_{function_name}" in line:
                            capture = True
                        if capture:
                            method_lines.append(line)
                        if line.strip() == "" and capture:
                            capture = False
                    
                    test_code += "\n".join(method_lines)
                
                return test_code
        
        elif file_ext == '.java':
            # 生成Java方法测试
            imports = []
            imports.append("import org.junit.Test;")
            imports.append("import org.junit.Before;")
            imports.append("import static org.junit.Assert.*;")
            
            if package_name:
                imports.append(f"import {package_name}.{class_name};")
            
            imports.append("import org.mockito.Mock;")
            imports.append("import org.mockito.MockitoAnnotations;")
            imports.append("import static org.mockito.Mockito.*;")
            
            test_code = "\n".join(imports) + "\n\n"
            if package_name:
                test_code += f"package {package_name};\n\n"
            
            test_code += f"public class {class_name}Test {{\n"
            test_code += f"    private {class_name} testInstance;\n\n"
            test_code += "    @Before\n"
            test_code += "    public void setUp() {\n"
            test_code += "        MockitoAnnotations.initMocks(this);\n"
            test_code += f"        testInstance = new {class_name}();  // TODO: 添加必要的初始化参数\n"
            test_code += "    }\n\n"
            
            method_test = self._generate_java_method_test(
                method_name=function_name,
                method_def=function_info["info"],
                class_name=class_name,
                additional_info=additional_info
            )
            
            test_code += "    " + "\n    ".join(method_test.split("\n")) + "\n"
            test_code += "}\n"
            
            return test_code
            
        elif file_ext == '.kt':
            # 生成Kotlin方法测试
            imports = []
            imports.append("import org.junit.Test")
            imports.append("import org.junit.Before")
            imports.append("import org.junit.Assert.*")
            
            if package_name:
                imports.append(f"import {package_name}.{class_name}")
            
            imports.append("import org.mockito.Mock")
            imports.append("import org.mockito.MockitoAnnotations")
            imports.append("import org.mockito.Mockito.*")
            
            test_code = ""
            if package_name:
                test_code += f"package {package_name}\n\n"
            
            test_code += "\n".join(imports) + "\n\n"
            test_code += f"class {class_name}Test {{\n"
            test_code += f"    private lateinit var testInstance: {class_name}\n\n"
            test_code += "    @Before\n"
            test_code += "    fun setUp() {\n"
            test_code += "        MockitoAnnotations.initMocks(this)\n"
            test_code += f"        testInstance = {class_name}()  // TODO: 添加必要的初始化参数\n"
            test_code += "    }\n\n"
            
            method_test = self._generate_kotlin_method_test(
                method_name=function_name,
                method_def=function_info["info"],
                class_name=class_name,
                additional_info=additional_info
            )
            
            test_code += "    " + "\n    ".join(method_test.split("\n")) + "\n"
            test_code += "}\n"
            
            return test_code
        
        else:
            return f"// 错误: 不支持的文件类型: {file_ext}"


class TestGenerator(Role):
    """测试生成角色，负责生成单元测试代码"""

    def __init__(self, name="TestGenerator"):
        super().__init__(name=name)
        self.description = "我根据代码分析结果生成高质量的单元测试。"
        self.add_action(TestGenerationAction())

    async def generate_tests(
        self, 
        code_analysis: Dict[str, Any],
        framework: str = DEFAULT_TEST_FRAMEWORK,
        function_name: str = None,
        additional_info: str = None
    ) -> Message:
        """
        生成单元测试代码

        Args:
            code_analysis: 代码分析结果
            framework: 测试框架
            function_name: 要测试的特定函数名称，如果为None则测试整个文件
            additional_info: 用户提供的额外信息

        Returns:
            包含生成的测试代码的消息
        """
        generation_action = self.get_action(TestGenerationAction)
        generation_result = await generation_action.run(
            code_analysis, 
            framework,
            function_name,
            additional_info
        )

        if function_name:
            content = f"为{generation_result['source_file']}中的{function_name}函数生成了测试代码"
        else:
            content = f"为{generation_result['source_file']}生成了测试代码"
            
        return Message(
            content=content,
            cause_by=generation_action,
            meta=generation_result
        )
