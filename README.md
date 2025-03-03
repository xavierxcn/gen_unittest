# Android 单元测试生成工具 (优化版)

这个工具可以自动为 Android（Java/Kotlin）代码生成单元测试。它使用 AI 分析源代码，然后生成相应的测试代码，并且可以根据用户提供的测试示例来定制生成的测试风格。

## 功能特点

- 支持 Java 和 Kotlin 代码
- 可以为整个文件或特定方法生成测试
- 允许用户提供测试示例，生成的测试将严格遵循示例的风格和结构
- 自动验证生成的测试代码语法
- 生成详细的测试摘要报告
- 增强的错误处理和路径处理
- 灵活的配置系统，支持自定义配置文件
- 支持多种AI模型，包括OpenAI和Anthropic的模型

## 安装

### 前提条件

- Python 3.8 或更高版本
- pip（Python 包管理器）

### 安装步骤

1. 克隆仓库：

```bash
git clone <仓库URL>
cd gen_unittest
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 配置 API 密钥：

创建一个 `.env` 文件，并添加以下内容：

```
OPENAI_API_KEY=your_api_key_here
# 可选配置
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4
```

或者，您可以在运行程序前设置环境变量：

```bash
export OPENAI_API_KEY=your_api_key_here
```

## 使用方法

### 命令行使用

为单个文件生成测试：

```bash
python main.py /path/to/your/file.java
```

为整个目录生成测试：

```bash
python main.py /path/to/your/directory
```

### 高级选项

#### 为特定方法生成测试

```bash
# 为 Java 文件中的特定方法生成测试
python main.py /path/to/your/file.java --function methodName

# 为 Kotlin 文件中的特定方法生成测试
python main.py /path/to/your/file.kt --function functionName
```

#### 使用测试示例

您可以提供一个测试示例文件，生成的测试将遵循此示例的风格和结构：

```bash
python main.py /path/to/your/file.java --example /path/to/example_test.java
```

测试示例文件应该包含一个或多个测试方法，例如：

```java
@Test
public void testMultiply() {
    // 准备测试数据
    int a = 3;
    int b = 4;
    
    // 调用被测方法
    int result = testInstance.multiply(a, b);
    
    // 验证结果
    assertEquals(12, result);
    
    // 测试边界情况
    assertEquals(0, testInstance.multiply(0, 5));
    assertEquals(0, testInstance.multiply(5, 0));
}
```

工具会分析这个示例，并生成具有相似风格的测试，包括：
- 注释风格（标准或详细）
- 断言风格（单一或多个断言）
- 是否包含边界情况测试

#### 排除特定目录

```bash
python main.py /path/to/your/directory --exclude build .gradle .idea
```

#### 指定摘要文件路径

```bash
python main.py /path/to/your/file.java --summary my_test_summary.txt
```

#### 指定AI模型

```bash
python main.py /path/to/your/file.java --model gpt-4o
```

支持的模型包括：
- OpenAI: gpt-4, gpt-4-turbo, gpt-4o, gpt-3.5-turbo
- Anthropic: claude-3-opus-20240229, claude-3-sonnet-20240229, claude-3-haiku-20240307

#### 使用自定义配置文件

您可以创建一个JSON格式的配置文件，并通过`--config`参数指定：

```bash
python main.py /path/to/your/file.java --config my_config.json
```

配置文件示例：

```json
{
  "api": {
    "openai_model": "gpt-4o",
    "temperature": 0.3
  },
  "test": {
    "exclude_dirs": [".git", "build", ".gradle", ".idea", "node_modules"]
  }
}
```

### 完整命令示例

```bash
python main.py /path/to/android/project --function calculateTotal --example /path/to/example_test.java --exclude build .gradle --summary test_results.txt --model gpt-4o
```

## 作为 Python 包使用

您也可以在自己的 Python 代码中导入并使用这个工具：

```python
import asyncio
from agents.code_analyzer import CodeAnalyzer
from agents.test_generator import TestGenerator
from agents.test_validator import TestValidator
from config import check_environment, get_config
import os

async def generate_android_test(
    file_path: str, 
    function_name: str = None, 
    example_test: str = None,
    model: str = None
):
    """
    为Android代码（Java/Kotlin）生成单元测试
    
    Args:
        file_path: 源代码文件路径（.java或.kt文件）
        function_name: 要测试的方法名称，如果为None则测试整个文件
        example_test: 用户提供的测试示例，生成的测试将严格遵循此示例的风格和结构
        model: 要使用的AI模型名称
        
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
    
    # 1. 分析代码
    analysis_msg = await code_analyzer.analyze_code(file_path, function_name)
    code_analysis = analysis_msg.meta
    
    # 2. 生成测试
    test_msg = await test_generator.generate_tests(
        code_analysis, 
        "junit",  # 固定使用JUnit框架
        function_name,
        example_test  # 传入用户提供的测试示例
    )
    test_info = test_msg.meta
    
    # 3. 验证测试
    validation_msg = await test_validator.validate_tests(test_info)
    validation_result = validation_msg.meta
    
    # 4. 保存测试文件
    test_file_path = validation_result["test_file"]
    test_code = validation_result["test_code"]
    
    # 确保目录存在
    os.makedirs(os.path.dirname(os.path.abspath(test_file_path)), exist_ok=True)
    
    # 写入测试文件
    with open(test_file_path, 'w', encoding='utf-8') as f:
        f.write(test_code)
    
    print(f"测试文件已生成: {test_file_path}")
    print(f"语法有效: {'是' if validation_result['syntax_valid'] else '否'}")
    
    if not validation_result['syntax_valid']:
        print(f"语法错误: {validation_result.get('syntax_error', '未知错误')}")
    
    return {
        "test_file_path": test_file_path,
        "test_code": test_code,
        "syntax_valid": validation_result["syntax_valid"],
        "syntax_error": validation_result.get("syntax_error", "")
    }

# 使用示例
if __name__ == "__main__":
    # 为Java文件中的特定方法生成测试，提供测试示例
    java_file = "path/to/your/Calculator.java"
    java_method = "add"
    
    # 用户提供的测试示例
    example_test = """
    @Test
    public void testMultiply() {
        // 准备测试数据
        int a = 3;
        int b = 4;
        
        // 调用被测方法
        int result = testInstance.multiply(a, b);
        
        // 验证结果
        assertEquals(12, result);
        
        // 测试边界情况
        assertEquals(0, testInstance.multiply(0, 5));
        assertEquals(0, testInstance.multiply(5, 0));
    }
    """
    
    # 异步调用
    result = asyncio.run(generate_android_test(
        java_file, 
        java_method,
        example_test,
        "gpt-4"
    ))
```

## 优化特性

与原始版本相比，优化版本包含以下改进：

1. **增强的安全性**：
   - 移除了硬编码的API密钥
   - 更安全的配置管理

2. **改进的代码解析**：
   - 更可靠的Kotlin代码解析
   - 更准确的类名提取

3. **增强的语法验证**：
   - 使用javac和kotlinc进行实际编译验证（如果可用）
   - 更全面的基本语法检查作为后备方案

4. **健壮的错误处理**：
   - 详细的错误日志
   - 优雅的失败处理和回退机制

5. **灵活的配置系统**：
   - 支持用户配置文件
   - 命令行参数覆盖
   - 多种AI模型支持

6. **改进的路径处理**：
   - 更好的跨平台兼容性
   - 更可靠的文件路径处理

7. **模糊匹配功能**：
   - 当找不到精确匹配的函数时，提供相似函数的建议

## 输出

程序会生成以下输出：

1. 测试文件：对于每个源文件，会生成一个对应的测试文件。
   - 对于 Java 文件 `ClassName.java`，会生成 `ClassNameTest.java`
   - 对于 Kotlin 文件 `ClassName.kt`，会生成 `ClassNameTest.kt`

2. 测试摘要：包含所有生成的测试的详细信息，包括：
   - 源文件路径
   - 测试文件路径
   - 语法验证结果
   - 错误信息（如果有）

## 故障排除

如果遇到问题，请检查以下几点：

1. 确保已正确设置API密钥
2. 检查生成的测试摘要文件中的错误信息
3. 确保源代码文件是有效的Java或Kotlin文件
4. 如果指定了函数名，确保该函数在源文件中存在

## 贡献

欢迎贡献代码、报告问题或提出改进建议。请遵循以下步骤：

1. Fork 仓库
2. 创建您的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开一个 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详情请参阅 LICENSE 文件。
