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
    注意：由于没有完整的Kotlin解析器，我们使用正则表达式进行基本解析
    """
    # 提取类定义
    class_pattern = r'(?:open\s+|abstract\s+|sealed\s+|data\s+)?class\s+(\w+)(?:<[^>]+>)?(?:\s*:\s*[^{]+)?'
    class_matches = re.finditer(class_pattern, content)
    
    classes = []
    for match in class_matches:
        class_name = match.group(1)
        class_start = match.start()
        
        # 找到类的开始和结束位置
        open_braces = 0
        class_end = -1
        for i in range(match.end(), len(content)):
            if content[i] == '{':
                open_braces += 1
            elif content[i] == '}':
                open_braces -= 1
                if open_braces == 0:
                    class_end = i + 1
                    break
        
        if class_end == -1:
            continue  # 无法确定类的结束位置
        
        class_content = content[class_start:class_end]
        
        # 提取方法
        method_pattern = r'(?:fun|override fun)\s+(\w+)\s*\(([^)]*)\)[^{]*\{'
        method_matches = re.finditer(method_pattern, class_content)
        
        methods = []
        for method_match in method_matches:
            method_name = method_match.group(1)
            params_str = method_match.group(2).strip()
            
            # 解析参数
            params = []
            if params_str:
                for param in params_str.split(','):
                    param = param.strip()
                    if ':' in param:
                        param_name = param.split(':')[0].strip()
                        params.append(param_name)
            
            # 提取方法源代码
            method_start = method_match.start()
            open_braces = 0
            method_end = -1
            
            for i in range(method_match.end(), len(class_content)):
                if class_content[i] == '{':
                    open_braces += 1
                elif class_content[i] == '}':
                    open_braces -= 1
                    if open_braces == 0:
                        method_end = i + 1
                        break
            
            if method_end == -1:
                continue  # 无法确定方法的结束位置
            
            method_source = class_content[method_start:method_end]
            
            methods.append({
                'name': method_name,
                'lineno': content[:class_start + method_start].count('\n') + 1,
                'args': params,
                'docstring': "",  # Kotlin注释解析需要更复杂的逻辑
                'source': method_source
            })
        
        classes.append({
            'name': class_name,
            'lineno': content[:class_start].count('\n') + 1,
            'methods': methods,
            'docstring': "",  # Kotlin注释解析需要更复杂的逻辑
            'source': class_content
        })
    
    # 提取顶级函数
    functions = []
    func_pattern = r'(?:^|\n)fun\s+(\w+)\s*\(([^)]*)\)[^{]*\{'
    func_matches = re.finditer(func_pattern, content)
    
    for match in func_matches:
        func_name = match.group(1)
        params_str = match.group(2).strip()
        
        # 解析参数
        params = []
        if params_str:
            for param in params_str.split(','):
                param = param.strip()
                if ':' in param:
                    param_name = param.split(':')[0].strip()
                    params.append(param_name)
        
        # 提取函数源代码
        func_start = match.start()
        open_braces = 0
        func_end = -1
        
        for i in range(match.end(), len(content)):
            if content[i] == '{':
                open_braces += 1
            elif content[i] == '}':
                open_braces -= 1
                if open_braces == 0:
                    func_end = i + 1
                    break
        
        if func_end == -1:
            continue  # 无法确定函数的结束位置
        
        func_source = content[func_start:func_end]
        
        functions.append({
            'name': func_name,
            'lineno': content[:func_start].count('\n') + 1,
            'args': params,
            'docstring': "",  # Kotlin注释解析需要更复杂的逻辑
            'source': func_source
        })
    
    return {
        'functions': functions,
        'classes': classes,
        'imports': extract_android_imports(content, '.kt'),
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
    在指定目录中查找所有Java/Kotlin文件
    """
    if exclude_dirs is None:
        exclude_dirs = ['.git', 'build', '.gradle', '.idea']

    android_files = []

    for root, dirs, files in os.walk(directory):
        # 排除指定目录
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith('.java') or file.endswith('.kt'):
                android_files.append(os.path.join(root, file))

    return android_files


def get_test_file_path(source_file: str, test_dir: str = None) -> str:
    """
    根据源文件路径生成测试文件路径
    """
    file_path = Path(source_file)
    file_name = file_path.name
    file_ext = file_path.suffix

    if test_dir:
        if file_ext == '.py':
            test_path = Path(test_dir) / f"test_{file_name}"
        else:  # Java/Kotlin
            test_path = Path(test_dir) / f"{file_path.stem}Test{file_ext}"
    else:
        # 在同一目录下创建测试文件
        if file_ext == '.py':
            test_path = file_path.parent / f"test_{file_name}"
        else:  # Java/Kotlin
            test_path = file_path.parent / f"{file_path.stem}Test{file_ext}"

    return str(test_path)


def extract_module_name(file_path: str) -> str:
    """
    从文件路径中提取模块名
    """
    file_name = os.path.basename(file_path)
    module_name = os.path.splitext(file_name)[0]
    return module_name


def extract_package_name(file_path: str) -> str:
    """
    从Java/Kotlin文件中提取包名
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找package语句
    package_match = re.search(r'package\s+([a-zA-Z0-9_.]+)', content)
    if package_match:
        return package_match.group(1)
    return ""


def extract_class_name(file_path: str) -> str:
    """
    从Java/Kotlin文件路径中提取类名
    """
    file_name = os.path.basename(file_path)
    class_name = os.path.splitext(file_name)[0]
    return class_name


def find_function_in_file(file_path: str, function_name: str) -> Optional[Dict[str, Any]]:
    """
    在文件中查找指定的函数或方法
    
    Args:
        file_path: 源代码文件路径
        function_name: 要查找的函数或方法名
        
    Returns:
        找到的函数信息，如果未找到则返回None
    """
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
    
    return None
