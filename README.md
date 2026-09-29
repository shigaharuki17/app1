# Codegen：DeepSeek 代码生成 Agent

输入中文需求，生成一个 Python 脚本。模型会调用本机工具检查代码语法，收到错误后继续修改，最后保存通过检查的源码。支持网页交互、命令行使用及基于最近结果继续修改。

## 对应作业要求

| 要求 | 本项目实现 |
| --- | --- |
| 代码生成方向 | 根据自然语言生成 Python 函数或脚本 |
| 输入、推理、工具调用、输出 | `agent.py` 中有明确的多轮工具调用循环 |
| 至少一种工具 | `check_python` 语法检查、`submit_code` 检查后保存 |
| 命令行或 Web 界面 | Streamlit 网页和 `cli.py` 命令行 |
| 上下文记忆 | 网页保留最近 3 次成功结果，支持后续修改 |
| 错误处理与重试 | 语法错误反馈、参数校验、超时、网络错误及限流重试 |
| 文档 | 本 README、`DESIGN.md` 设计说明、`DEMO.md` 演示脚本 |

## 环境

- Windows，Python 3.14（开发验证版本为 3.14.2）
- DeepSeek API Key，API 按平台规则计费
- 依赖：`openai`、`streamlit`、`python-dotenv`，版本见 `requirements.txt`
- 推荐 VS Code。项目使用 DeepSeek 官方 API，`openai` 仅作为兼容客户端。

## 本机启动

当前部署目录为 `D:\codegen-agent`。双击 `run.bat`，浏览器会打开本地网页。

也可在 PowerShell 执行：

```powershell
Set-Location -LiteralPath "D:\codegen-agent"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

默认访问地址：`http://127.0.0.1:8501`。在终端按 Ctrl+C 停止服务。

## 从源码包重新安装

解压源码后安装 Python 3.14，双击 `setup.bat`。或执行：

```powershell
Set-Location -LiteralPath "D:\codegen-agent"
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `.env`。选择下面一种密钥配置方法：

```dotenv
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_MODEL=deepseek-flash
AGENT_MAX_ROUNDS=8
API_TIMEOUT_SECONDS=60
```

也可以读取一个只含一行密钥的本机文本文件。使用此方法时，移除 `DEEPSEEK_API_KEY` 那一行：

```dotenv
DEEPSEEK_API_KEY_FILE=D:/deepseek/api.txt
DEEPSEEK_MODEL=deepseek-flash
AGENT_MAX_ROUNDS=8
API_TIMEOUT_SECONDS=60
```

现有部署使用第二种方法。程序只在请求 DeepSeek 官方接口时使用密钥，不把密钥放入模型提示词。`.env`、密钥文件和虚拟环境不属于提交物。

配置优先级：同名系统环境变量高于 `.env`；直接密钥高于密钥文件。接口地址固定为 `https://api.deepseek.com`。

## 使用方法

1. 在页面选择示例，或输入功能、输入格式、输出格式及异常处理要求。
2. 点击“生成并检查”，页面展示模型调用和工具检查进度。
3. 在“代码”查看结果并下载 `.py` 文件。
4. 在“运行说明”查看用法，在“工具记录”查看检查过程、轮数和 Token 用量。
5. 输入“在上一次代码中增加……”可继续修改。
6. “开始新对话”清空当前会话上下文，不删除已经生成的文件。

页面保存最近 6 个成功结果供查看，模型只接收最近 3 个作为上下文。会话记忆保存在当前浏览器连接中，不是永久聊天记录。源码单独保存在 `generated/<本次唯一目录>/<文件名>.py`。

### 命令行

```powershell
.\.venv\Scripts\python.exe cli.py --check-api
.\.venv\Scripts\python.exe cli.py "写一个统计成绩平均值、最大值和及格人数的 Python 函数，处理空列表和非法成绩"
```

第一条命令读取可用模型列表，用来确认密钥和模型是否可访问。第二条命令开始生成代码。命令行每次运行是独立任务，上下文续写通过网页使用。

## 验证与限制

- 当前范围是一个 Python 文件，源码上限 30000 字符，需求上限 6000 字符。
- 检查器调用 Python 标准库 `ast.parse` 和 `compile`，不调用 `exec`、`eval` 或子进程来运行生成代码。
- 语法通过仅说明代码可以编译，不保证功能正确、第三方依赖已安装、文件和网络操作安全。按照生成的说明手动验证具体功能。
- 最多 8 轮模型调用（可设为 2–12）。网络故障、429 和部分服务端故障最多重试 2 次，间隔 1 秒和 2 秒。鉴权和余额错误不重试。
- 当前关闭模型的思考模式，使用原生 `tool_calls`；界面展示工具动作及结果，不展示模型内部推理内容。
- 默认只监听本机地址，不作为公网多用户服务部署。

## 运行测试

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

自动测试不需要真实 API 密钥、不产生模型调用费用。覆盖语法错误后修复、工具参数错误、未验证代码拒绝保存、路径限制、重试、上下文、配置及网页交互。

## 作业打包

```powershell
.\.venv\Scripts\python.exe package_submission.py
```

输出 `submission/codegen-agent.zip`。打包脚本使用明确文件清单，只包含项目源码、测试、配置模板与文档，排除真实密钥、`.env`、`.venv` 和生成结果。

按作业要求将压缩包重命名为“学号姓名.zip”，例如 `10086张三.zip`，确认小于 200 MB，提交至“001Homework1”。演示视频可选，时长在 1 分钟以内。课件截止时间：2026 年 10 月 7 日 24 点。

## 常见问题

| 现象 | 处理方式 |
| --- | --- |
| 密钥文件无法读取 | 检查 `.env` 中的文件路径，文件应仅包含 API Key |
| HTTP 401 | 检查 DeepSeek 密钥是否有效 |
| HTTP 402 | 在 DeepSeek 开放平台检查 API 余额 |
| HTTP 429 | 等待限流恢复后再试 |
| 模型不存在 | 运行 `cli.py --check-api`，按账户可用模型调整 `.env` |
| 超时 | 缩短需求，或适当提高 `API_TIMEOUT_SECONDS` |
| 端口被占用 | 先停止旧服务，或启动时加 `--server.port 8502` |
| 达到轮数上限 | 拆分复杂任务，再针对一个脚本提出需求 |

## 项目结构

```text
app.py                  网页界面和当前会话状态
agent.py                DeepSeek 工具调用循环、重试和上下文
code_tools.py           语法检查及受限文件交付
config.py               本机配置读取
cli.py                  命令行入口
requirements.txt        依赖版本
.env.example            无真实密钥的配置模板
.streamlit/config.toml  本机服务和主题配置
tests/                  自动测试
generated/              生成的源码，不提交
package_submission.py   按明确清单打包
DESIGN.md               设计说明
DEMO.md                 一分钟演示流程
```

## 官方参考

- [DeepSeek 工具调用](https://api-docs.deepseek.com/guides/tool_calls/)
- [DeepSeek 思考模式参数](https://api-docs.deepseek.com/guides/thinking_mode/)
- [DeepSeek Python 示例](https://api-docs.deepseek.com/api_samples/chat_python/)
- [Streamlit 文档](https://docs.streamlit.io/)
