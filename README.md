# Android 单元测试生成工具

这个工具可以自动为 Android（Java/Kotlin）和 Python 代码生成单元测试。它使用 AI 分析源代码，然后生成相应的测试代码。

## 功能特点

- 支持 Android（Java/Kotlin）和 Python 代码
- 可以为整个文件或特定函数生成测试
- 允许用户提供额外信息以改进测试生成
- 自动验证生成的测试代码语法
- 生成详细的测试摘要报告

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

3. 配置 OpenAI API 密钥：

创建一个 `.env` 文件，并添加以下内容：

```
OPENAI_API_KEY=your_api_key_here
```

或者，您可以在运行程序前设置环境变量：

```bash
export OPENAI_API_KEY=your_api_key_here
```

## 使用方法

### 基本用法

为单个文件生成测试：

```bash
python main.py /path/to/your/file.java
```

为整个目录生成测试：

```bash
python main.py /path/to/your/directory
```

### 高级选项

#### 指定测试框架

```bash
# 使用 JUnit 为 Android 代码生成测试（默认）
python main.py /path/to/your/file.java --framework junit

# 使用 pytest 为 Python 代码生成测试
python main.py /path/to/your/file.py --framework pytest --focus python

# 使用 unittest 为 Python 代码生成测试
python main.py /path/to/your/file.py --framework unittest --focus python
```

#### 为特定函数生成测试

```bash
# 为 Java 文件中的特定方法生成测试
python main.py /path/to/your/file.java --function methodName

# 为 Kotlin 文件中的特定函数生成测试
python main.py /path/to/your/file.kt --function functionName

# 为 Python 文件中的特定函数生成测试
python main.py /path/to/your/file.py --function function_name --focus python
```

#### 提供额外信息

```bash
python main.py /path/to/your/file.java --function methodName --info "这个方法应该处理空输入并返回默认值"
```

#### 排除特定目录

```bash
python main.py /path/to/your/directory --exclude build .gradle .idea
```

#### 指定摘要文件路径

```bash
python main.py /path/to/your/file.java --summary my_test_summary.txt
```

### 完整命令示例

```bash
python main.py /path/to/android/project --framework junit --function calculateTotal --info "这个方法计算购物车中所有商品的总价，应该处理折扣和税费" --exclude build .gradle --summary test_results.txt
```

## 输出

程序会生成以下输出：

1. 测试文件：对于每个源文件，会生成一个对应的测试文件。
   - 对于 Java 文件 `ClassName.java`，会生成 `ClassNameTest.java`
   - 对于 Kotlin 文件 `ClassName.kt`，会生成 `ClassNameTest.kt`
   - 对于 Python 文件 `module_name.py`，会生成 `test_module_name.py`

2. 测试摘要：包含测试生成结果的摘要文件，默认为 `test_generation_summary.txt`。

## 配置

您可以在 `config.py` 文件中修改默认配置：

- `DEFAULT_TEST_FRAMEWORK`：默认测试框架（"junit"、"pytest" 或 "unittest"）
- `DEFAULT_FOCUS`：默认测试重点（"android" 或 "python"）
- `OPENAI_MODEL`：使用的 OpenAI 模型
- `MAX_TOKENS`：生成测试时使用的最大令牌数
- `TEMPERATURE`：生成测试时使用的温度参数

## 故障排除

### 常见问题

1. **API 密钥错误**：确保您已正确设置 `OPENAI_API_KEY` 环境变量或在 `.env` 文件中提供了有效的 API 密钥。

2. **依赖问题**：如果遇到导入错误，请确保已安装所有必要的依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. **语法验证失败**：生成的测试代码可能包含语法错误。查看测试摘要文件中的错误信息，并手动修复测试文件。

4. **执行验证失败**：对于 Python 测试，程序会尝试执行生成的测试。如果执行失败，查看测试摘要文件中的错误信息。对于 Android 测试，程序只会验证语法，不会执行测试。

### 获取帮助

如果您遇到其他问题，请查看命令行帮助：

```bash
python main.py --help
```

## 限制

- Android 测试仅验证语法，不会执行测试，因为这需要 Android 环境。
- 生成的测试可能需要手动调整以适应特定的项目结构和依赖关系。
- 对于复杂的代码，生成的测试可能不够全面，需要手动补充。

## 示例

### Java 示例

源文件 `Calculator.java`：

```java
package com.example.calculator;

public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
    
    public int subtract(int a, int b) {
        return a - b;
    }
}
```

生成测试命令：

```bash
python main.py Calculator.java --function add
```

生成的测试文件 `CalculatorTest.java`：

```java
package com.example.calculator;

import org.junit.Test;
import org.junit.Before;
import static org.junit.Assert.*;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import static org.mockito.Mockito.*;

public class CalculatorTest {
    private Calculator testInstance;

    @Before
    public void setUp() {
        MockitoAnnotations.initMocks(this);
        testInstance = new Calculator();
    }

    @Test
    public void testAdd() {
        // 准备测试数据
        int a = 5;
        int b = 3;
        
        // 调用被测方法
        int result = testInstance.add(a, b);
        
        // 验证结果
        assertEquals(8, result);
    }
}
```

### Kotlin 示例

源文件 `StringUtils.kt`：

```kotlin
package com.example.utils

class StringUtils {
    fun concatenate(a: String, b: String): String {
        return a + b
    }
    
    fun reverse(input: String): String {
        return input.reversed()
    }
}
```

生成测试命令：

```bash
python main.py StringUtils.kt
```

生成的测试文件 `StringUtilsTest.kt`：

```kotlin
package com.example.utils

import org.junit.Test
import org.junit.Before
import org.junit.Assert.*
import org.mockito.Mock
import org.mockito.MockitoAnnotations
import org.mockito.Mockito.*

class StringUtilsTest {
    private lateinit var testInstance: StringUtils

    @Before
    fun setUp() {
        MockitoAnnotations.initMocks(this)
        testInstance = StringUtils()
    }

    @Test
    fun testConcatenate() {
        // 准备测试数据
        val a = "Hello, "
        val b = "World!"
        
        // 调用被测方法
        val result = testInstance.concatenate(a, b)
        
        // 验证结果
        assertEquals("Hello, World!", result)
    }

    @Test
    fun testReverse() {
        // 准备测试数据
        val input = "Hello"
        
        // 调用被测方法
        val result = testInstance.reverse(input)
        
        // 验证结果
        assertEquals("olleH", result)
    }
}
```

### Python 示例

源文件 `math_utils.py`：

```python
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

class Calculator:
    def __init__(self, initial_value=0):
        self.value = initial_value
    
    def add(self, x):
        self.value += x
        return self.value
    
    def subtract(self, x):
        self.value -= x
        return self.value
```

生成测试命令：

```bash
python main.py math_utils.py --focus python --framework pytest
```

生成的测试文件 `test_math_utils.py`：

```python
import pytest
import math_utils


def test_add():
    """
    测试 math_utils.add 函数
    """
    # 准备测试数据
    a = 5
    b = 3

    # 调用被测函数
    result = math_utils.add(a, b)

    # 断言
    assert result == 8


def test_multiply():
    """
    测试 math_utils.multiply 函数
    """
    # 准备测试数据
    a = 4
    b = 5

    # 调用被测函数
    result = math_utils.multiply(a, b)

    # 断言
    assert result == 20


# 测试 math_utils.Calculator 类

def test_Calculator_initialization():
    """
    测试 Calculator 类的初始化
    """
    # 创建实例
    instance = math_utils.Calculator()

    # 断言
    assert instance is not None
    assert instance.value == 0

    # 测试带初始值的初始化
    instance_with_value = math_utils.Calculator(10)
    assert instance_with_value.value == 10


def test_Calculator_add():
    """
    测试 Calculator.add 方法
    """
    # 创建实例
    instance = math_utils.Calculator(5)

    # 调用方法
    result = instance.add(3)

    # 断言
    assert result == 8
    assert instance.value == 8


def test_Calculator_subtract():
    """
    测试 Calculator.subtract 方法
    """
    # 创建实例
    instance = math_utils.Calculator(10)

    # 调用方法
    result = instance.subtract(4)

    # 断言
    assert result == 6
    assert instance.value == 6
