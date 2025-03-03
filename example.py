import asyncio
import os
import sys
from pathlib import Path
import json

# 添加项目根目录到Python路径，确保可以正确导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 导入本地模块
from agents.code_analyzer import CodeAnalyzer
from agents.test_generator import TestGenerator
from agents.test_validator import TestValidator
from config import check_environment, get_config


async def generate_android_test(
    file_path: str, 
    function_name: str = None, 
    example_test: str = None,
    model: str = None,
    verbose: bool = True
):
    """
    为Android代码（Java/Kotlin）生成单元测试
    
    Args:
        file_path: 源代码文件路径（.java或.kt文件）
        function_name: 要测试的方法名称，如果为None则测试整个文件
        example_test: 用户提供的测试示例，生成的测试将严格遵循此示例的风格和结构
        model: 要使用的AI模型名称
        verbose: 是否打印详细日志
        
    Returns:
        生成的测试代码信息
    """
    # 检查文件类型
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext not in ['.java', '.kt']:
        raise ValueError(f"不支持的文件类型: {file_ext}。只支持Java和Kotlin文件。")
    
    # 检查环境变量
    check_environment()
    
    # 加载配置
    config = get_config()
    
    # 设置环境变量
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    os.environ["OPENAI_API_BASE"] = config["api"]["openai_api_base"]
    os.environ["OPENAI_MODEL"] = model or config["api"]["openai_model"]
    
    # 创建代理
    code_analyzer = CodeAnalyzer()
    test_generator = TestGenerator()
    test_validator = TestValidator()
    
    if verbose:
        print("\n" + "="*80)
        print(f"🤖 多代理协作流程开始")
        print(f"📄 源文件: {file_path}")
        if function_name:
            print(f"🔍 目标方法: {function_name}")
        else:
            print(f"🔍 目标: 整个类")
        print("="*80)
    
    try:
        # 1. 代理1: 代码分析器分析代码
        if verbose:
            print("\n🔎 [代理1: 代码分析器] 开始分析源代码...")
            
        code_analysis = await code_analyzer.analyze_code(file_path, function_name)
        
        if verbose:
            print(f"✅ [代理1: 代码分析器] 分析完成")
            print(f"   - 文件路径: {code_analysis.get('file_path')}")
            print(f"   - 包名: {code_analysis.get('package_name')}")
            print(f"   - 类名: {code_analysis.get('class_name')}")
            if 'methods' in code_analysis:
                print(f"   - 分析了 {len(code_analysis['methods'])} 个方法")
                if function_name and function_name in code_analysis['methods']:
                    method_info = code_analysis['methods'][function_name]
                    print(f"   - 方法 '{function_name}' 信息:")
                    print(f"     - 返回类型: {method_info.get('return_type')}")
                    print(f"     - 参数数量: {len(method_info.get('args', []))}")
            print(f"   - 测试优先级: {len(code_analysis.get('test_priorities', []))} 项")
        
        # 2. 代理2: 测试生成器生成测试
        if verbose:
            print("\n🧪 [代理2: 测试生成器] 开始生成单元测试...")
            
        test_info = await test_generator.generate_tests(
            code_analysis, 
            "junit",  # 固定使用JUnit框架
            function_name,
            example_test  # 传入用户提供的测试示例
        )
        
        if verbose:
            print(f"✅ [代理2: 测试生成器] 测试生成完成")
            print(f"   - 测试文件: {test_info.get('test_file')}")
            print(f"   - 测试代码长度: {len(test_info.get('test_code', ''))} 字符")
            
        # 3. 代理3: 测试验证器验证测试
        if verbose:
            print("\n🔍 [代理3: 测试验证器] 开始验证测试代码...")
            
        validation_result = await test_validator.validate_tests(test_info)
        
        if verbose:
            print(f"✅ [代理3: 测试验证器] 验证完成")
            print(f"   - 语法有效: {'是' if validation_result.get('syntax_valid') else '否'}")
            if not validation_result.get('syntax_valid'):
                print(f"   - 语法错误: {validation_result.get('syntax_error', '未知错误')}")
        
        # 4. 保存测试文件
        test_file_path = validation_result["test_file"]
        test_code = validation_result["test_code"]
        
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(test_file_path)), exist_ok=True)
        
        # 写入测试文件
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_code)
        
        if verbose:
            print("\n📝 [结果] 测试文件已生成")
            print(f"   - 路径: {test_file_path}")
            print(f"   - 语法有效: {'是' if validation_result.get('syntax_valid') else '否'}")
            print("\n📄 测试代码预览:")
            print("-"*80)
            preview_lines = test_code.split('\n')[:15]  # 显示前15行
            print('\n'.join(preview_lines))
            if len(preview_lines) < test_code.count('\n'):
                print("...")
            print("-"*80)
            print(f"\n🎉 多代理协作流程结束")
        
        return {
            "test_file_path": test_file_path,
            "test_code": test_code,
            "syntax_valid": validation_result["syntax_valid"],
            "syntax_error": validation_result.get("syntax_error", "")
        }
    except Exception as e:
        print(f"❌ 生成测试时出错: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise


# 使用示例
if __name__ == "__main__":
    # 设置示例文件路径
    example_dir = os.path.join(current_dir, "example_files")
    os.makedirs(example_dir, exist_ok=True)
    
    # 使用UserManager.java作为示例文件
    user_manager_file = os.path.join(example_dir, "UserManager.java")
    
    # 读取测试示例
    example_test_file = os.path.join(example_dir, "UserManagerTest_example.java")
    with open(example_test_file, 'r', encoding='utf-8') as f:
        example_test = f.read()
    
    # 异步调用
    try:
        # 为registerUser方法生成测试
        print("\n为registerUser方法生成测试:")
        result1 = asyncio.run(generate_android_test(
            user_manager_file, 
            "registerUser",  # 测试registerUser方法
            example_test,
            "gpt-4"
        ))
        
        # 为updateUserEmail方法生成测试
        print("\n为updateUserEmail方法生成测试:")
        result2 = asyncio.run(generate_android_test(
            user_manager_file, 
            "updateUserEmail",  # 测试updateUserEmail方法
            example_test,
            "gpt-4"
        ))
        
    except Exception as e:
        print(f"执行示例时出错: {str(e)}")
