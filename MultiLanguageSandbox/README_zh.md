<div align="center">


  {
      "exec_runtime": 0.113,              # 总执行时间(秒)
      "process_cpu_time": 0.01,           # CPU实际使用时间
      "process_cpu_util": 9.5,            # CPU使用率(%)
      "process_exec_time": 0.11,          # 进程执行时间
      "process_peak_memory": 0,           # 峰值内存使用(MB)
      "exit_code": 0,                     # 退出代码
      "timeout": false,                   # 是否超时
      "language": "python",               # 执行语言
      "cmd": ["python3", "test.py"],      # 执行命令
      "outcome": "PASSED",                # 执行结果
      "stdout": "...",                    # 标准输出
      "stderr": "..."                     # 错误输出
  }
# 多语言代码沙盒服务

**腾讯混元**

</div>

一个安全、高性能的多语言代码执行沙盒服务，支持30+种编程语言的代码编译和执行。

## 🚀 特性

- **多语言支持**：支持30+种编程语言，包括Python、JavaScript、Go、Java、C++、Rust等
- **安全隔离**：基于Docker容器和iptables防火墙规则，确保代码执行安全
- **智能代码拼接**：自动处理函数代码和测试代码的拼接，支持多种语言特定的语法
- **高性能**：基于Gunicorn多进程架构，支持并发执行
- **RESTful API**：提供简洁的HTTP API接口

## 📋 支持的编程语言

- **C** - 使用gcc编译
- **C#** - 使用.NET Core运行时
- **C++** - 使用g++编译
- **CoffeeScript** - 编译到JavaScript
- **Common Lisp** - 使用SBCL解释器
- **Dart** - 支持断言检查
- **Elixir** - 基于Erlang VM
- **Emacs Lisp** - 使用Emacs批处理模式
- **Erlang** - 使用erlc编译器
- **F#** - 基于.NET平台
- **Fortran** - 使用gfortran编译器
- **Go** - 使用go编译器
- **Groovy** - 使用groovy解释器
- **Haskell** - 使用GHC编译器
- **Java** - 集成JUnit测试框架
- **JavaScript** - 使用Node.js运行时
- **Julia** - 使用julia解释器
- **Kotlin** - 使用kotlinc脚本模式
- **Lua** - 使用lua解释器
- **Pascal** - 使用Free Pascal编译器
- **Perl** - 使用perl解释器
- **PHP** - 使用php解释器
- **PowerShell** - 使用pwsh执行
- **Python** - 使用python3解释器
- **R** - 使用Rscript执行
- **Racket** - 使用racket解释器
- **Ruby** - 使用ruby解释器
- **Rust** - 使用Cargo构建系统
- **Scala** - 使用Ammonite REPL
- **Scheme** - 使用Racket执行
- **Shell** - 使用bash执行
- **Swift** - 使用swift解释器
- **Tcl** - 使用tclsh执行
- **TypeScript** - 使用tsx执行
- **Vimscript** - 使用vim执行
- **Visual Basic** - 基于.NET平台

## 🏗️ 架构设计

### 整体架构

```
┌──────────────┐    ┌──────────────┐    ┌────────────────┐
│ HTTP Client  │───▶│  Flask Web   │───▶│    Executor    │
└──────────────┘    └──────────────┘    └────────────────┘
                           │                    │
                           │                    │
                           ▼                    ▼ 
                    ┌──────────────┐    ┌────────────────┐
                    │ Code Splicer │    │ Safe Subprocess│
                    └──────────────┘    └────────────────┘
                           │                     
                           ▼                     
                    ┌──────────────┐    
                    │  Code Store  │     
                    └──────────────┘    
                           │
                           ▼
                    ┌──────────────┐
                    │ Config File  │
                    └──────────────┘
```

### 核心组件

#### 1. Web服务层
- **Flask应用**：提供HTTP接口，处理代码执行和拼接请求
- **主要端点**：
  - `/submit` - 代码执行服务
- **功能**：请求验证、异常处理、响应格式化

#### 2. 代码处理层
- **代码拼接器**：智能合并函数代码和测试代码
  - 多语言语法适配（Go import合并、JS函数检测等）
  - 代码结构分析和优化
- **代码存储器**：管理临时执行环境
  - 文件创建和清理
  - 语法预检查
  - 权限控制

#### 3. 执行控制层
- **代码执行器**：统一的多语言执行管理
  - 编译器/解释器调度
  - 执行流程控制
  - 错误信息收集
- **安全子进程**：底层安全执行保障
  - 权限隔离
  - 资源限制
  - 超时控制

### 安全机制

#### 1. 容器隔离
- 基于Docker容器运行，与宿主机完全隔离
- 使用非特权用户执行代码
- 限制文件系统访问权限

#### 2. 网络安全
- iptables防火墙规则严格控制网络访问
- 仅允许必要的出站连接（DNS、镜像源、日志服务）
- 默认拒绝所有其他网络流量

#### 3. 资源限制
- CPU和内存使用限制
- 执行时间超时控制
- 文件系统写入限制

## 🚀 快速开始

### 1. 拉取镜像

```bash
docker pull hunyuansandbox/multi-language-sandbox:v1
```

### 2. 启动服务
```bash
docker run -d \
  --name sandbox-service \
  -p 8080:8080 \
  --cap-add=NET_ADMIN \
  hunyuansandbox/multi-language-sandbox:v1
```

### 3. 验证服务

服务启动后，可以通过以下方式验证是否正常运行：

```bash
# 检查容器状态
docker ps | grep sandbox

# 测试服务健康状态
curl -X POST http://localhost:8080/submit \
  -H "Content-Type: application/json" \
  -d '{"src_uid": "test-001", "lang": "python", "source_code": "print(\"Hello World\")"}'
```

如果返回包含 `"exec_outcome": "PASSED"` 的JSON响应，说明服务运行正常。

## 📡 API接口

### 1. 代码执行接口

**端点**：`POST /submit` （使用source_code）

**请求参数**：
```json
{
  "src_uid": "unique-request-id",
  "lang": "python",
  "source_code": "def hello():\n    print('Hello World')\nhello()",
  "request_extensions": {
    "timeout": 10,
    "debug": false
  },
  "show_log": true
}
```

**响应示例**：
```json
{
  "src_uid": "unique-request-id",
  "all_code": "",
  "exec_cout": "Hello World\n",
  "exec_outcome": "PASSED",
  "exec_compile_message": "",
  "exec_runtime_message": "",
  "response_extensions": {
    "server_ip": "172.17.0.2",
    "exec_runtime": 0.123,
    "outcome": "PASSED",
    "stdout": "Hello World\n",
    "stderr": ""
  }
}
```

### 2. 代码拼接后执行接口

**端点**：`POST /submit`（使用func_code和main_code）

**请求参数**：
```json
{
  "src_uid": "unique-request-id",
  "lang": "go",
  "func_code": "package main\n\nfunc add(a, b int) int {\n    return a + b\n}",
  "main_code": "package main\nimport \"fmt\"\n\nfunc main() {\n    fmt.Println(add(1, 2))\n}",
  "request_extensions": {
    "timeout": 5
  }
}
```

## 🔧 使用示例

### Python代码执行
```bash
curl -X POST http://localhost:8080/submit \
  -H "Content-Type: application/json" \
  -d '{
    "src_uid": "python-test-001",
    "lang": "python",
    "source_code": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)\n\nprint(fibonacci(10))"
  }'
```

### JavaScript代码拼接后执行
```bash
curl -X POST http://localhost:8080/submit \
  -H "Content-Type: application/json" \
  -d '{
    "src_uid": "js-test-001",
    "lang": "javascript",
    "func_code": "\n// Function to calculate the number of structurally unique BSTs for a given n\nconst countUniqueBSTs = (n) => {\n    // Handle edge cases\n    if (n <= 0) return 0;\n    if (n === 1) return 1;\n    \n    // Create a DP array to store results of subproblems\n    const dp = new Array(n + 1).fill(0);\n    dp[0] = 1; // Base case: empty tree\n    dp[1] = 1; // Base case: single node\n    \n    // Fill the DP array in bottom-up manner\n    for (let i = 2; i <= n; i++) {\n        for (let j = 0; j < i; j++) {\n            // The number of trees when j is the root\n            dp[i] += dp[j] * dp[i - j - 1];\n        }\n    }\n    \n    return dp[n];\n};\n",
    "main_code": "\nconst assert = require(\"assert\");\n\nconst demoTesting = () => {\n    assert.strictEqual(countUniqueBSTs(2), 2);\n    assert.strictEqual(countUniqueBSTs(3), 5);\n};\n"
  }'
```

### Go代码拼接后执行
```bash
curl -X POST http://localhost:8080/submit \
  -H "Content-Type: application/json" \
  -d '{
    "src_uid": "go-test-001",
    "lang": "go",
    "func_code": "package main\n\nfunc isPrime(n int) bool {\n    if n < 2 { return false }\n    for i := 2; i*i <= n; i++ {\n        if n%i == 0 { return false }\n    }\n    return true\n}",
    "main_code": "package main\nimport \"fmt\"\n\nfunc main() {\n    for i := 2; i <= 20; i++ {\n        if isPrime(i) {\n            fmt.Printf(\"%d \", i)\n        }\n    }\n    fmt.Println()\n}"
  }'
```

### Java代码拼接后执行
```bash
curl -X POST http://localhost:8080/submit \
  -H "Content-Type: application/json" \
  -d '{
    "src_uid": "java-test-001",
    "lang": "java",
    "func_code": "import java.util.List;\n\nclass WineGlassMaximizer {\n    /**\n     * Calculates the maximum amount of wine that can be consumed without drinking\n     * three glasses in a row, using dynamic programming.\n     * \n     * @param glasses List of wine glass amounts\n     * @return Maximum amount that can be consumed following the rules\n     */\n    public int maxWineConsumption(List<Integer> glasses) {\n        if (glasses.isEmpty()) return 0;\n        if (glasses.size() == 1) return glasses.get(0);\n        if (glasses.size() == 2) return glasses.get(0) + glasses.get(1);\n        \n        int n = glasses.size();\n        int[] dp = new int[n];\n        \n        dp[0] = glasses.get(0);\n        dp[1] = glasses.get(0) + glasses.get(1);\n        dp[2] = Math.max(Math.max(glasses.get(0) + glasses.get(2), glasses.get(1) + glasses.get(2)), dp[1]);\n        \n        for (int i = 3; i < n; i++) {\n            dp[i] = Math.max(\n                Math.max(\n                    dp[i-3] + glasses.get(i-1) + glasses.get(i), // skip two, then take two\n                    dp[i-2] + glasses.get(i)                     // skip one, then take one\n                ),\n                dp[i-1]                                         // skip current glass\n            );\n        }\n        \n        return dp[n-1];\n    }\n}",
    "main_code": "import static org.junit.jupiter.api.Assertions.assertEquals;\nimport org.junit.jupiter.api.Test;\nimport java.util.Arrays;\nimport java.util.List;\n\nclass TestWineGlassMaximizer {\n    @Test\n    public void test() {\n        WineGlassMaximizer maximizer = new WineGlassMaximizer();\n        \n        List<Integer> input1 = Arrays.asList(1, 2, 3, 4, 5);\n        assertEquals(12, maximizer.maxWineConsumption(input1));\n        \n        List<Integer> input2 = Arrays.asList(5, 5, 5, 5);\n        assertEquals(15, maximizer.maxWineConsumption(input2));\n    }\n}"
  }'
```

## 📊 执行结果状态

| 状态 | 说明 |
|------|------|
| `PASSED` | 代码执行成功 |
| `COMPILATION_ERROR` | 编译错误 |
| `RUNTIME_ERROR` | 运行时错误 |
| `TIMEOUT` | 执行超时 |
| `SYNTAX_ERROR` | 语法错误 |
| `ARGUMENT_ERROR` | 参数错误 |
| `INTERNAL_ERROR` | 服务器内部错误 |

## 🔍 监控和日志

### 日志文件
- **位置**：`/data/logs/`
- **格式**：JSON格式，包含请求ID、执行时间、结果状态等
- **轮转**：自动按日期轮转

### 性能监控
- **请求追踪**：每个请求都有唯一的src_uid进行追踪
- **资源使用**：CPU、内存、执行时间统计

## 🛡️ 安全注意事项

1. **网络隔离**：确保容器网络配置正确，避免访问内网资源
2. **资源限制**：根据实际需求调整CPU和内存限制
3. **权限控制**：不要以root用户运行容器
4. **定期更新**：及时更新基础镜像和依赖包
5. **监控告警**：建议配置异常执行的监控告警

## 💬 反馈与支持

如果在使用过程中遇到问题或有改进建议，欢迎：

- 提交Issue报告问题
- 分享使用经验和最佳实践
- 建议新的语言支持需求


## 🆘 故障排除

### 常见问题

**Q: 容器启动失败，提示权限错误**
A: 确保Docker有足够权限，并添加`--cap-add=NET_ADMIN`参数

**Q: 代码执行超时**
A: 检查timeout参数设置，复杂算法可能需要更长时间

**Q: 某些语言编译失败**
A: 检查语言环境是否正确安装，查看编译错误信息

**Q: 网络连接问题**
A: 检查iptables规则，确保必要的网络访问被允许

### 调试模式

启用调试模式保留临时文件：
```json
{
  "request_extensions": {
    "debug": true
  }
}
```

### 日志查看

```bash
# 查看容器日志
docker logs sandbox-service

# 查看应用日志
docker exec sandbox-service tail -f /data/logs/sandbox.log
```

