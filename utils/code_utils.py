import ast
import os
import re
import javalang
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional


def extract_functions_and_classes(file_path: str) -> Dict[str, Any]:
    """
    从源代码文件中提取函数和类的定义
    支持Python和Java/Kotlin
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # 根据文件扩展名选择解析方法
    if file_ext == '.py':
        return extract_python_code(file_path)
    elif file_ext in ['.java', '.kt']:
        return extract_android_code(file_path)
    else:
        raise ValueError(f"不支持的文件类型: {file_ext}")


def extract_python_code(file_path: str) -> Dict[str, Any]:
    """
    从Python文件中提取函数和类的定义
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    try:
        tree = ast.parse(content)

        functions = []
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    'name': node.name,
                    'lineno': node.lineno,
                    'args': [arg.arg for arg in node.args.args],
                    'docstring': ast.get_docstring(node) or "",
                    'source': ast.unparse(node)
                })
            elif isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.append({
                            'name': item.name,
                            'lineno': item.lineno,
                            'args': [arg.arg for arg in item.args.args],
                            'docstring': ast.get_docstring(item) or "",
                            'source': ast.unparse(item)
                        })

                classes.append({
                    'name': node.name,
                    'lineno': node.lineno,
                    'methods': methods,
                    'docstring': ast.get_docstring(node) or "",
                    'source': ast.unparse(node)
                })

        return {
            'functions': functions,
            'classes': classes,
            'imports': extract_imports(content),
            'full_content': content
        }
    except SyntaxError:
        # 如果解析失败，返回原始内容
        return {
            'functions': [],
            'classes': [],
            'imports': extract_imports(content),
            'full_content': content
        }


def extract_android_code(file_path: str) -> Dict[str, Any]:
    """
    从Java/Kotlin文件中提取函数和类的定义
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    file_ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if file_ext == '.java':
            return extract_java_code(content)
        elif file_ext == '.kt':
            return extract_kotlin_code(content)
        else:
            raise ValueError(f"不支持的Android文件类型: {file_ext}")
    except Exception as e:
        # 如果解析失败，返回原始内容
        return {
            'functions': [],
            'classes': [],
            'imports': extract_android_imports(content, file_ext),
            'full_content': content,
            'error': str(e)
        }


def extract_java_code(content: str) -> Dict[str, Any]:
    """
    使用javalang解析Java代码
    """
    try:
        tree = javalang.parse.parse(content)
        
        functions = []  # Java中的静态方法或全局函数
        classes = []
        
        for path, node in tree.filter(javalang.tree.ClassDeclaration):
            methods = []
            
            # 处理类中的方法
            for method_node in node.methods:
                params = []
                if method_node.parameters:
                    for param in method_node.parameters:
                        params.append(param.name)
                
                # 提取方法源代码
                method_source = extract_method_source(content, method_node)
                
                methods.append({
                    'name': method_node.name,
                    'lineno': method_node.position.line if method_node.position else 0,
                    'args': params,
                    'docstring': extract_javadoc(method_node),
                    'source': method_source,
                    'return_type': str(method_node.return_type) if method_node.return_type else "void",
                    'modifiers': method_node.modifiers
                })
            
            # 提取类源代码
            class_source = extract_class_source(content, node)
            
            classes.append({
                'name': node.name,
                'lineno': node.position.line if node.position else 0,
                'methods': methods,
                'docstring': extract_javadoc(node),
                'source': class_source,
                'modifiers': node.modifiers
            })
        
        return {
            'functions': functions,  # Java通常没有顶级函数
            'classes': classes,
            'imports': extract_android_imports(content, '.java'),
            'full_content': content
        }
    except Exception as e:
        # 解析失败时返回基本信息
        return {
            'functions': [],
            'classes': [],
            'imports': extract_android_imports(content, '.java'),
            'full_content': content,
            'error': str(e)
        }


def extract_kotlin_code(content: str) -> Dict[str, Any]:
    """
    解析Kotlin代码
    使用更可靠的方法解析Kotlin代码结构
    """
    # 提取导入语句
    imports = extract_android_imports(content, '.kt')
    
    # 提取类定义
    classes = []
    class_pattern = r'(?:open\s+|abstract\s+|sealed\s+|data\s+)?class\s+(\w+)(?:<[^>]+>)?(?:\s*:\s*[^{]+)?'
    class_matches = re.finditer(class_pattern, content)
    
    for match in class_matches:
        class_name = match.group(1)
        class_start = match.start()
        
        # 找到类的开始和结束位置
        open_braces = 0
        class_end = -1
        found_open_brace = False
        
        for i in range(match.end(), len(content)):
            if content[i] == '{':
                if not found_open_brace:
                    found_open_brace = True
                open_braces += 1
            elif content[i] == '}':
                open_braces -= 1
                if open_braces == 0 and found_open_brace:
                    class_end = i + 1
                    break
        
        if class_end == -1:
            continue  # 无法确定类的结束位置
        
        # 提取类的源代码
        class_source = content[class_start:class_end].strip()
        
        # 提取类的文档字符串
        docstring = ""
        doc_match = re.search(r'/\*\*(.*?)\*/', content[:class_start], re.DOTALL)
        if doc_match:
            docstring = doc_match.group(1).strip()
        
        # 提取类中的方法
        methods = []
        method_pattern = r'fun\s+(\w+)\s*\(([^)]*)\)'
        method_matches = re.finditer(method_pattern, class_source)
        
        for method_match in method_matches:
            method_name = method_match.group(1)
            method_params_str = method_match.group(2)
            
            # 解析方法参数
            params = []
            if method_params_str.strip():
                param_parts = method_params_str.split(',')
                for part in param_parts:
                    part = part.strip()
                    if part:
                        # 提取参数名（忽略类型）
                        param_name = part.split(':')[0].strip()
                        params.append(param_name)
            
            # 找到方法的开始和结束位置
            method_start = class_source.find(method_match.group(0))
            if method_start == -1:
                continue
            
            # 从方法声明开始查找方法体
            method_body_start = class_source.find('{', method_start)
            if method_body_start == -1:
                continue
            
            # 找到方法体的结束位置
            open_braces = 1
            method_end = -1
            
            for i in range(method_body_start + 1, len(class_source)):
                if class_source[i] == '{':
                    open_braces += 1
                elif class_source[i] == '}':
                    open_braces -= 1
                    if open_braces == 0:
                        method_end = i + 1
                        break
            
            if method_end == -1:
                continue  # 无法确定方法的结束位置
            
            # 提取方法的源代码
            method_source = class_source[method_start:method_end].strip()
            
            # 提取方法的文档字符串
            method_docstring = ""
            method_doc_match = re.search(r'/\*\*(.*?)\*/', class_source[:method_start], re.DOTALL)
            if method_doc_match:
                method_docstring = method_doc_match.group(1).strip()
            
            # 计算方法在原始内容中的行号
            method_lineno = content[:class_start].count('\n') + class_source[:method_start].count('\n') + 1
            
            methods.append({
                'name': method_name,
                'lineno': method_lineno,
                'args': params,
                'docstring': method_docstring,
                'source': method_source
            })
        
        # 计算类在原始内容中的行号
        class_lineno = content[:class_start].count('\n') + 1
        
        classes.append({
            'name': class_name,
            'lineno': class_lineno,
            'methods': methods,
            'docstring': docstring,
            'source': class_source
        })
    
    # 提取顶级函数
    functions = []
    function_pattern = r'fun\s+(\w+)\s*\(([^)]*)\)'
    
    # 排除类中的函数
    for match in re.finditer(function_pattern, content):
        # 检查这个函数是否在任何类中
        is_in_class = False
        for cls in classes:
            cls_start = content.find(cls['source'])
            cls_end = cls_start + len(cls['source'])
            if cls_start <= match.start() <= cls_end:
                is_in_class = True
                break
        
        if is_in_class:
            continue
        
        function_name = match.group(1)
        function_params_str = match.group(2)
        
        # 解析函数参数
        params = []
        if function_params_str.strip():
            param_parts = function_params_str.split(',')
            for part in param_parts:
                part = part.strip()
                if part:
                    # 提取参数名（忽略类型）
                    param_name = part.split(':')[0].strip()
                    params.append(param_name)
        
        # 找到函数的开始和结束位置
        function_start = match.start()
        
        # 从函数声明开始查找函数体
        function_body_start = content.find('{', function_start)
        if function_body_start == -1:
            continue
        
        # 找到函数体的结束位置
        open_braces = 1
        function_end = -1
        
        for i in range(function_body_start + 1, len(content)):
            if content[i] == '{':
                open_braces += 1
            elif content[i] == '}':
                open_braces -= 1
                if open_braces == 0:
                    function_end = i + 1
                    break
        
        if function_end == -1:
            continue  # 无法确定函数的结束位置
        
        # 提取函数的源代码
        function_source = content[function_start:function_end].strip()
        
        # 提取函数的文档字符串
        function_docstring = ""
        function_doc_match = re.search(r'/\*\*(.*?)\*/', content[:function_start], re.DOTALL)
        if function_doc_match:
            function_docstring = function_doc_match.group(1).strip()
        
        # 计算函数在原始内容中的行号
        function_lineno = content[:function_start].count('\n') + 1
        
        functions.append({
            'name': function_name,
            'lineno': function_lineno,
            'args': params,
            'docstring': function_docstring,
            'source': function_source
        })
    
    return {
        'functions': functions,
        'classes': classes,
        'imports': imports,
        'full_content': content
    }


def extract_method_source(content: str, method_node) -> str:
    """
    从Java源代码中提取方法的源代码
    """
    if not hasattr(method_node, 'position') or not method_node.position:
        return ""
    
    start_line = method_node.position.line
    lines = content.split('\n')
    
    # 找到方法的开始行
    method_start = start_line - 1  # 行号从1开始，索引从0开始
    
    # 找到方法的结束行
    open_braces = 0
    method_end = method_start
    
    for i in range(method_start, len(lines)):
        line = lines[i]
        open_braces += line.count('{')
        open_braces -= line.count('}')
        
        if open_braces == 0 and '{' in line:
            method_end = i
            break
        
        if open_braces == 0 and i > method_start:
            method_end = i
            break
    
    # 提取方法源代码
    return '\n'.join(lines[method_start:method_end+1])


def extract_class_source(content: str, class_node) -> str:
    """
    从Java源代码中提取类的源代码
    """
    if not hasattr(class_node, 'position') or not class_node.position:
        return ""
    
    start_line = class_node.position.line
    lines = content.split('\n')
    
    # 找到类的开始行
    class_start = start_line - 1  # 行号从1开始，索引从0开始
    
    # 找到类的结束行
    open_braces = 0
    class_end = class_start
    
    for i in range(class_start, len(lines)):
        line = lines[i]
        open_braces += line.count('{')
        open_braces -= line.count('}')
        
        if open_braces == 0 and i > class_start:
            class_end = i
            break
    
    # 提取类源代码
    return '\n'.join(lines[class_start:class_end+1])


def extract_javadoc(node) -> str:
    """
    提取Java节点的JavaDoc注释
    """
    if hasattr(node, 'documentation') and node.documentation:
        return node.documentation
    return ""


def extract_imports(content: str) -> List[str]:
    """
    从Python代码内容中提取import语句
    """
    import_lines = []
    for line in content.split('\n'):
        if line.strip().startswith(('import ', 'from ')):
            import_lines.append(line.strip())
    return import_lines


def extract_android_imports(content: str, file_ext: str) -> List[str]:
    """
    从Java/Kotlin代码内容中提取import语句
    """
    import_lines = []
    for line in content.split('\n'):
        if line.strip().startswith('import '):
            import_lines.append(line.strip())
    return import_lines


def find_python_files(directory: str, exclude_dirs: List[str] = None) -> List[str]:
    """
    在指定目录中查找所有Python文件
    """
    if exclude_dirs is None:
        exclude_dirs = ['venv', '.venv', 'env', '.env', '.git', '__pycache__', 'tests', 'test']

    python_files = []

    for root, dirs, files in os.walk(directory):
        # 排除指定目录
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    return python_files


def find_android_files(directory: str, exclude_dirs: List[str] = None) -> List[str]:
    """
    在目录中查找所有Android源代码文件（Java和Kotlin）
    
    Args:
        directory: 要搜索的目录
        exclude_dirs: 要排除的目录列表
        
    Returns:
        找到的Android源代码文件路径列表
    """
    if exclude_dirs is None:
        exclude_dirs = []
    
    # 将排除目录转换为绝对路径
    exclude_paths = []
    for exclude_dir in exclude_dirs:
        if os.path.isabs(exclude_dir):
            exclude_paths.append(exclude_dir)
        else:
            # 如果是相对路径，转换为相对于搜索目录的绝对路径
            exclude_paths.append(os.path.abspath(os.path.join(directory, exclude_dir)))
    
    android_files = []
    
    try:
        for root, dirs, files in os.walk(directory):
            # 检查当前目录是否应该被排除
            if any(os.path.abspath(root).startswith(exclude_path) for exclude_path in exclude_paths):
                continue
            
            # 过滤掉要排除的目录
            dirs[:] = [d for d in dirs if not any(os.path.abspath(os.path.join(root, d)).startswith(exclude_path) for exclude_path in exclude_paths)]
            
            for file in files:
                if file.endswith('.java') or file.endswith('.kt'):
                    android_files.append(os.path.join(root, file))
    except Exception as e:
        from metagpt.logs import logger
        logger.error(f"查找Android文件时出错: {str(e)}")
    
    return android_files


def get_test_file_path(source_file: str, test_dir: str = None) -> str:
    """
    根据源文件路径生成测试文件路径
    
    Args:
        source_file: 源代码文件路径
        test_dir: 测试目录，如果为None则在同一目录下创建测试文件
        
    Returns:
        测试文件路径
    """
    try:
        file_path = Path(source_file)
        file_name = file_path.name
        file_ext = file_path.suffix

        if test_dir:
            test_dir_path = Path(test_dir)
            # 确保测试目录存在
            os.makedirs(test_dir_path, exist_ok=True)
            
            if file_ext == '.py':
                test_path = test_dir_path / f"test_{file_name}"
            else:  # Java/Kotlin
                test_path = test_dir_path / f"{file_path.stem}Test{file_ext}"
        else:
            # 在同一目录下创建测试文件
            if file_ext == '.py':
                test_path = file_path.parent / f"test_{file_name}"
            else:  # Java/Kotlin
                test_path = file_path.parent / f"{file_path.stem}Test{file_ext}"

        return str(test_path)
    except Exception as e:
        # 如果出现异常，记录错误并返回一个基于原始文件名的测试文件路径
        from metagpt.logs import logger
        logger.error(f"生成测试文件路径时出错: {str(e)}")
        
        # 尝试使用基本方法生成测试文件路径
        try:
            base_name = os.path.basename(source_file)
            dir_name = os.path.dirname(source_file)
            name, ext = os.path.splitext(base_name)
            
            if ext == '.py':
                test_file = f"test_{base_name}"
            else:  # Java/Kotlin
                test_file = f"{name}Test{ext}"
                
            if test_dir:
                return os.path.join(test_dir, test_file)
            else:
                return os.path.join(dir_name, test_file)
        except:
            # 如果还是失败，返回一个默认值
            return f"{source_file}.test"


def extract_module_name(file_path: str) -> str:
    """
    从文件路径中提取模块名
    
    Args:
        file_path: 文件路径
        
    Returns:
        模块名
    """
    try:
        file_name = os.path.basename(file_path)
        module_name = os.path.splitext(file_name)[0]
        return module_name
    except Exception as e:
        from metagpt.logs import logger
        logger.error(f"提取模块名时出错: {str(e)}")
        
        # 返回一个基于文件路径的安全模块名
        safe_name = "".join(c if c.isalnum() else "_" for c in file_path)
        return f"module_{safe_name}"


def extract_package_name(file_path: str) -> str:
    """
    从Java/Kotlin文件中提取包名
    
    Args:
        file_path: 文件路径
        
    Returns:
        包名，如果未找到则返回空字符串
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找package语句
        package_match = re.search(r'package\s+([a-zA-Z0-9_.]+)', content)
        if package_match:
            return package_match.group(1)
    except Exception as e:
        from metagpt.logs import logger
        logger.error(f"提取包名时出错: {str(e)}")
    
    return ""


def extract_class_name(file_path: str) -> str:
    """
    从Java/Kotlin文件中提取类名
    
    不再简单地使用文件名，而是尝试从文件内容中提取主类名
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # 如果不是Java或Kotlin文件，直接使用文件名
    if file_ext not in ['.java', '.kt']:
        file_name = os.path.basename(file_path)
        return os.path.splitext(file_name)[0]
    
    # 读取文件内容
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取类定义
        if file_ext == '.java':
            # 使用正则表达式查找Java类定义
            class_match = re.search(r'(?:public\s+|private\s+|protected\s+)?(?:abstract\s+|final\s+)?class\s+(\w+)', content)
            if class_match:
                return class_match.group(1)
        else:  # .kt
            # 使用正则表达式查找Kotlin类定义
            class_match = re.search(r'(?:open\s+|abstract\s+|sealed\s+|data\s+)?class\s+(\w+)', content)
            if class_match:
                return class_match.group(1)
    except Exception:
        pass  # 如果读取或解析失败，回退到使用文件名
    
    # 如果无法从内容中提取类名，回退到使用文件名
    file_name = os.path.basename(file_path)
    return os.path.splitext(file_name)[0]


def find_function_in_file(file_path: str, function_name: str) -> Optional[Dict[str, Any]]:
    """
    在文件中查找指定的函数或方法
    
    Args:
        file_path: 源代码文件路径
        function_name: 要查找的函数或方法名
        
    Returns:
        找到的函数信息，如果未找到则返回None
    """
    try:
        code_structure = extract_functions_and_classes(file_path)
        
        # 检查顶级函数
        for func in code_structure.get('functions', []):
            if func['name'] == function_name:
                return {
                    'type': 'function',
                    'info': func,
                    'file_path': file_path,
                    'structure': code_structure
                }
        
        # 检查类方法
        for cls in code_structure.get('classes', []):
            for method in cls.get('methods', []):
                if method['name'] == function_name:
                    return {
                        'type': 'method',
                        'info': method,
                        'class_info': cls,
                        'file_path': file_path,
                        'structure': code_structure
                    }
        
        # 如果没有找到精确匹配，尝试模糊匹配
        # 检查是否有名称相似的函数或方法
        similar_functions = []
        
        # 检查顶级函数
        for func in code_structure.get('functions', []):
            if function_name.lower() in func['name'].lower():
                similar_functions.append({
                    'type': 'function',
                    'name': func['name'],
                    'similarity': 'partial_match'
                })
        
        # 检查类方法
        for cls in code_structure.get('classes', []):
            for method in cls.get('methods', []):
                if function_name.lower() in method['name'].lower():
                    similar_functions.append({
                        'type': 'method',
                        'name': method['name'],
                        'class': cls['name'],
                        'similarity': 'partial_match'
                    })
        
        if similar_functions:
            from metagpt.logs import logger
            logger.warning(f"未找到名为 '{function_name}' 的函数或方法，但找到了类似的: {similar_functions}")
        
        return None
    except Exception as e:
        from metagpt.logs import logger
        logger.error(f"查找函数时出错: {str(e)}")
        return None
