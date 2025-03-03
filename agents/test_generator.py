from typing import Dict, Any, List, Optional
import os
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.actions import Action

from utils.code_utils import (
    get_test_file_path, extract_module_name, extract_package_name, 
    extract_class_name, find_function_in_file
)
from config import DEFAULT_TEST_FRAMEWORK


class TestGenerationAction(Action):
    """生成单元测试代码的Action"""

    def __init__(self):
        super().__init__()
        self.desc = "根据代码分析结果生成Android单元测试"

    async def run(
        self, 
        code_analysis: Dict[str, Any], 
        framework: str = "junit",
        function_name: str = None,
        example_test: str = None
    ) -> Dict[str, Any]:
        """
        根据代码分析结果生成单元测试

        Args:
            code_analysis: 代码分析结果
            framework: 测试框架，固定为junit
            function_name: 要测试的特定函数名称，如果为None则测试整个文件
            example_test: 用户提供的测试示例，生成的测试将严格遵循此示例的风格和结构

        Returns:
            包含生成的测试代码的字典
        """
        file_path = code_analysis["file_path"]
        code_structure = code_analysis["structure"]
        test_priorities = code_analysis["test_priorities"]
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # 检查文件类型
        if file_ext not in ['.java', '.kt']:
            raise ValueError(f"不支持的文件类型: {file_ext}。只支持Java和Kotlin文件。")

        # 生成测试文件路径
        test_file_path = get_test_file_path(file_path)
        
        # 提取包名和类名
        package_name = extract_package_name(file_path)
        class_name = extract_class_name(file_path)

        # 如果指定了函数名，只生成该函数的测试
        if function_name:
            test_code = self._generate_specific_function_test(
                file_path=file_path,
                function_name=function_name,
                code_structure=code_structure,
                package_name=package_name,
                class_name=class_name,
                example_test=example_test
            )
        else:
            # 生成整个文件的测试代码
            if file_ext == '.java':
                test_code = self._generate_java_test_code(
                    package_name=package_name,
                    class_name=class_name,
                    code_structure=code_structure,
                    test_priorities=test_priorities,
                    example_test=example_test
                )
            else:  # .kt
                test_code = self._generate_kotlin_test_code(
                    package_name=package_name,
                    class_name=class_name,
                    code_structure=code_structure,
                    test_priorities=test_priorities,
                    example_test=example_test
                )

        return {
            "source_file": file_path,
            "test_file": test_file_path,
            "test_code": test_code,
            "framework": "junit",
            "function_name": function_name
        }
    
    def _generate_java_test_code(
            self,
            package_name: str,
            class_name: str,
            code_structure: Dict[str, Any],
            test_priorities: List[Dict[str, Any]],
            example_test: str = None
    ) -> str:
        """
        生成Java测试代码

        Args:
            package_name: 包名
            class_name: 类名
            code_structure: 代码结构
            test_priorities: 测试优先级
            example_test: 用户提供的测试示例

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
        
        # 分析用户提供的测试示例，提取风格和结构
        test_style = self._analyze_test_example(example_test) if example_test else {}
        
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
                            test_style=test_style
                        ))
        
        # 组合测试代码
        test_code = ""
        if package_name:
            test_code += f"package {package_name};\n\n"
        
        test_code += "\n".join(imports) + "\n\n"
        test_code += "\n".join(test_class) + "\n\n"
        
        # 添加测试方法
        for method in test_methods:
            test_code += method + "\n\n"
        
        # 关闭类定义
        test_code += "}\n"
        
        return test_code
    
    def _generate_kotlin_test_code(
            self,
            package_name: str,
            class_name: str,
            code_structure: Dict[str, Any],
            test_priorities: List[Dict[str, Any]],
            example_test: str = None
    ) -> str:
        """
        生成Kotlin测试代码

        Args:
            package_name: 包名
            class_name: 类名
            code_structure: 代码结构
            test_priorities: 测试优先级
            example_test: 用户提供的测试示例

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
        
        # 分析用户提供的测试示例，提取风格和结构
        test_style = self._analyze_test_example(example_test) if example_test else {}
        
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
                            test_style=test_style
                        ))
        
        # 组合测试代码
        test_code = ""
        if package_name:
            test_code += f"package {package_name}\n\n"
        
        test_code += "\n".join(imports) + "\n\n"
        test_code += "\n".join(test_class) + "\n\n"
        
        # 添加测试方法
        for method in test_methods:
            test_code += method + "\n\n"
        
        # 关闭类定义
        test_code += "}\n"
        
        return test_code

    def _generate_java_method_test(
            self,
            method_name: str,
            method_def: Dict[str, Any],
            class_name: str,
            test_style: Dict[str, Any] = None
    ) -> str:
        """
        生成Java方法的测试代码

        Args:
            method_name: 方法名
            method_def: 方法定义
            class_name: 类名
            test_style: 从用户示例中提取的测试风格

        Returns:
            生成的测试代码
        """
        args = method_def.get("args", [])
        return_type = method_def.get("return_type", "void")
        
        # 处理复杂的返回类型对象
        if isinstance(return_type, dict):
            if "name" in return_type:
                return_type = return_type["name"]
            elif "type" in return_type and "name" in return_type["type"]:
                return_type = return_type["type"]["name"]
            else:
                return_type = "Object"  # 默认为Object类型
        
        # 使用用户示例中的风格
        if test_style:
            comment_style = test_style.get("comment_style", "standard")
            assertion_style = test_style.get("assertion_style", "standard")
            test_boundary = test_style.get("test_boundary", False)
        else:
            comment_style = "standard"
            assertion_style = "standard"
            test_boundary = False
        
        # 生成测试方法
        test_method = []
        test_method.append(f"@Test")
        test_method.append(f"public void test{method_name.capitalize()}() {{")
        
        # 准备测试数据
        if comment_style == "detailed":
            test_method.append("    // 准备测试数据 - 为方法参数创建测试值")
        else:
            test_method.append("    // 准备测试数据")
            
        for arg in args:
            # 根据参数名和类型生成合适的测试值
            test_value = self._generate_test_value_for_arg(arg, method_def)
            test_method.append(f"    {test_value}")
        
        # 调用被测方法
        test_method.append("")
        if comment_style == "detailed":
            test_method.append("    // 调用被测方法 - 执行要测试的功能")
        else:
            test_method.append("    // 调用被测方法")
            
        if return_type != "void":
            # 更健壮的参数处理
            args_str = ""
            if args:
                arg_names = []
                for arg in args:
                    parts = arg.split(" ")
                    if len(parts) > 1:
                        arg_names.append(parts[-1])  # 取最后一部分作为参数名
                    else:
                        arg_names.append(arg)  # 如果没有空格，使用整个字符串
                args_str = ", ".join(arg_names)
                
            test_method.append(f"    {return_type} result = testInstance.{method_name}({args_str});")
            
            # 验证结果
            test_method.append("")
            if comment_style == "detailed":
                test_method.append("    // 验证结果 - 确保方法返回预期值")
            else:
                test_method.append("    // 验证结果")
                
            if assertion_style == "multiple":
                test_method.append("    assertNotNull(result);  // 确保结果不为空")
                test_method.append(f"    // TODO: 添加更多断言验证结果")
            else:
                test_method.append("    assertNotNull(result);  // TODO: 添加更具体的断言")
                
            # 添加边界测试
            if test_boundary:
                test_method.append("")
                test_method.append("    // 测试边界情况")
                test_method.append(f"    // TODO: 添加边界情况测试")
        else:
            args_str = ", ".join([arg.split(" ")[1] for arg in args]) if args else ""
            test_method.append(f"    testInstance.{method_name}({args_str});")
            
            # 验证行为
            test_method.append("")
            if comment_style == "detailed":
                test_method.append("    // 验证行为 - 确保方法执行了预期的操作")
            else:
                test_method.append("    // 验证行为")
                
            test_method.append("    // TODO: 验证方法的行为，例如是否调用了依赖的方法")
        
        test_method.append("}")
        
        return "\n".join(test_method)
    
    def _generate_kotlin_method_test(
            self,
            method_name: str,
            method_def: Dict[str, Any],
            class_name: str,
            test_style: Dict[str, Any] = None
    ) -> str:
        """
        生成Kotlin方法的测试代码

        Args:
            method_name: 方法名
            method_def: 方法定义
            class_name: 类名
            test_style: 从用户示例中提取的测试风格

        Returns:
            生成的测试代码
        """
        args = method_def.get("args", [])
        return_type = method_def.get("return_type", "Unit")
        
        # 处理复杂的返回类型对象
        if isinstance(return_type, dict):
            if "name" in return_type:
                return_type = return_type["name"]
            elif "type" in return_type and "name" in return_type["type"]:
                return_type = return_type["type"]["name"]
            else:
                return_type = "Any"  # Kotlin中默认为Any类型
        
        # 使用用户示例中的风格
        if test_style:
            comment_style = test_style.get("comment_style", "standard")
            assertion_style = test_style.get("assertion_style", "standard")
            test_boundary = test_style.get("test_boundary", False)
        else:
            comment_style = "standard"
            assertion_style = "standard"
            test_boundary = False
        
        # 生成测试方法
        test_method = []
        test_method.append(f"@Test")
        test_method.append(f"fun test{method_name.capitalize()}() {{")
        
        # 准备测试数据
        if comment_style == "detailed":
            test_method.append("    // 准备测试数据 - 为方法参数创建测试值")
        else:
            test_method.append("    // 准备测试数据")
            
        for arg in args:
            # 根据参数名和类型生成合适的测试值
            test_value = self._generate_kotlin_test_value_for_arg(arg, method_def)
            test_method.append(f"    {test_value}")
        
        # 调用被测方法
        test_method.append("")
        if comment_style == "detailed":
            test_method.append("    // 调用被测方法 - 执行要测试的功能")
        else:
            test_method.append("    // 调用被测方法")
            
        # 更健壮的参数处理
        args_str = ""
        if args:
            arg_names = []
            for arg in args:
                if ":" in arg:
                    # Kotlin参数格式: name: Type
                    arg_names.append(arg.split(":")[0].strip())
                else:
                    # 如果没有冒号，使用整个字符串
                    arg_names.append(arg.strip())
            args_str = ", ".join(arg_names)
            
        test_method.append(f"    val result = testInstance.{method_name}({args_str})")
        
        # 验证结果
        test_method.append("")
        if comment_style == "detailed":
            test_method.append("    // 验证结果 - 确保方法返回预期值")
        else:
            test_method.append("    // 验证结果")
            
        if assertion_style == "multiple":
            test_method.append("    assertNotNull(result)  // 确保结果不为空")
            test_method.append(f"    // TODO: 添加更多断言验证结果")
        else:
            test_method.append("    assertNotNull(result)  // TODO: 添加更具体的断言")
            
        # 添加边界测试
        if test_boundary:
            test_method.append("")
            test_method.append("    // 测试边界情况")
            test_method.append(f"    // TODO: 添加边界情况测试")
        
        test_method.append("}")
        
        return "\n".join(test_method)
    
    def _generate_test_value_for_arg(self, arg: str, method_def: Dict[str, Any]) -> str:
        """
        为Java方法参数生成测试值
        
        Args:
            arg: 参数定义，格式为"类型 名称"
            method_def: 方法定义
            
        Returns:
            生成的测试值代码
        """
        parts = arg.split(" ")
        if len(parts) < 2:
            return f"{arg} = null;  // TODO: 设置适当的测试值"
            
        arg_type = parts[0]
        arg_name = parts[1]
        
        if arg_type == "int" or arg_type == "Integer":
            return f"int {arg_name} = 5;  // 示例整数值"
        elif arg_type == "long" or arg_type == "Long":
            return f"long {arg_name} = 1000L;  // 示例长整数值"
        elif arg_type == "double" or arg_type == "Double":
            return f"double {arg_name} = 5.0;  // 示例浮点数值"
        elif arg_type == "float" or arg_type == "Float":
            return f"float {arg_name} = 5.0f;  // 示例浮点数值"
        elif arg_type == "boolean" or arg_type == "Boolean":
            return f"boolean {arg_name} = true;  // 示例布尔值"
        elif arg_type == "String":
            return f"String {arg_name} = \"test\";  // 示例字符串值"
        elif arg_type == "List":
            return f"List<Object> {arg_name} = new ArrayList<>();  // 示例列表"
        elif arg_type == "Map":
            return f"Map<String, Object> {arg_name} = new HashMap<>();  // 示例映射"
        else:
            return f"{arg_type} {arg_name} = null;  // TODO: 设置适当的测试值"
    
    def _generate_kotlin_test_value_for_arg(self, arg: str, method_def: Dict[str, Any]) -> str:
        """
        为Kotlin方法参数生成测试值
        
        Args:
            arg: 参数定义，格式为"名称: 类型"
            method_def: 方法定义
            
        Returns:
            生成的测试值代码
        """
        if ":" not in arg:
            return f"val {arg} = null  // TODO: 设置适当的测试值"
            
        parts = arg.split(":")
        arg_name = parts[0].strip()
        arg_type = parts[1].strip()
        
        if arg_type == "Int" or arg_type == "Integer":
            return f"val {arg_name} = 5  // 示例整数值"
        elif arg_type == "Long":
            return f"val {arg_name} = 1000L  // 示例长整数值"
        elif arg_type == "Double":
            return f"val {arg_name} = 5.0  // 示例浮点数值"
        elif arg_type == "Float":
            return f"val {arg_name} = 5.0f  // 示例浮点数值"
        elif arg_type == "Boolean":
            return f"val {arg_name} = true  // 示例布尔值"
        elif arg_type == "String":
            return f"val {arg_name} = \"test\"  // 示例字符串值"
        elif arg_type == "List<*>" or arg_type.startswith("List<"):
            return f"val {arg_name} = listOf<Any>()  // 示例列表"
        elif arg_type == "Map<*,*>" or arg_type.startswith("Map<"):
            return f"val {arg_name} = mapOf<String, Any>()  // 示例映射"
        else:
            return f"val {arg_name}: {arg_type}? = null  // TODO: 设置适当的测试值"
    
    def _analyze_test_example(self, example_test: str) -> Dict[str, Any]:
        """
        分析用户提供的测试示例，提取测试风格和结构
        
        Args:
            example_test: 用户提供的测试示例
            
        Returns:
            测试风格和结构信息
        """
        if not example_test:
            return {}
            
        test_style = {}
        
        # 检查注释风格
        if "// 准备测试数据 -" in example_test or "// 调用被测方法 -" in example_test:
            test_style["comment_style"] = "detailed"
        else:
            test_style["comment_style"] = "standard"
        
        # 检查断言风格
        assertion_count = example_test.count("assert")
        if assertion_count > 2:
            test_style["assertion_style"] = "multiple"
        else:
            test_style["assertion_style"] = "standard"
        
        # 检查是否测试边界情况
        if "边界情况" in example_test or "boundary" in example_test.lower():
            test_style["test_boundary"] = True
        else:
            test_style["test_boundary"] = False
        
        return test_style
    
    def _generate_specific_function_test(
            self,
            file_path: str,
            function_name: str,
            code_structure: Dict[str, Any],
            package_name: str = None,
            class_name: str = None,
            example_test: str = None
    ) -> str:
        """
        为特定函数生成测试代码
        
        Args:
            file_path: 源代码文件路径
            function_name: 要测试的函数名
            code_structure: 代码结构
            package_name: 包名（Java/Kotlin）
            class_name: 类名（Java/Kotlin）
            example_test: 用户提供的测试示例
            
        Returns:
            生成的测试代码
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # 查找指定的函数或方法
        function_info = None
        
        # 在类方法中查找
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
            return f"// 错误: 在文件 {file_path} 中未找到方法 {function_name}"
        
        # 分析用户提供的测试示例
        test_style = self._analyze_test_example(example_test) if example_test else {}
        
        # 生成Java/Kotlin测试
        if file_ext == '.java':
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
                test_style=test_style
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
                test_style=test_style
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
        self.description = "我根据代码分析结果生成高质量的Android单元测试。"
        self.generation_action = TestGenerationAction()
        self.set_action(self.generation_action)

    async def generate_tests(
        self, 
        code_analysis: Dict[str, Any],
        framework: str = "junit",
        function_name: str = None,
        example_test: str = None
    ) -> Dict[str, Any]:
        """
        生成单元测试代码

        Args:
            code_analysis: 代码分析结果
            framework: 测试框架，固定为junit
            function_name: 要测试的特定函数名称，如果为None则测试整个文件
            example_test: 用户提供的测试示例，生成的测试将严格遵循此示例的风格和结构

        Returns:
            包含生成的测试代码的字典
        """
        # 直接使用保存的action实例，而不是通过get_action获取
        generation_result = await self.generation_action.run(
            code_analysis, 
            framework,
            function_name,
            example_test
        )

        # 直接返回生成结果
        return generation_result
