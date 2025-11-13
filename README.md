# 论文分析多代理系统

<div align="center">

**基于 LangGraph 的智能论文分析系统，支持自动问答、用户对话和智能恢复**

[快速开始](QUICKSTART.md) | [环境配置](ENVIRONMENT.md)

</div>

---

## ✨ 核心特性

### 🤖 多代理协作
- **分析者（Analyzer）**: 强大的深度模型，负责理解论文和回答问题
- **审核者（Reviewer）**: 快速模型，负责选择问题、核实答案和整合报告
- **智能工作流**: 自动化的问答循环，每个问题可追问多轮

### 💾 智能检查点系统
- **自动保存**: 每个关键阶段自动保存进度
- **智能恢复**: 中断后自动检测检查点，可选择恢复点
- **arXiv ID 分类**: 自动识别 arXiv 论文，按论文 ID 组织检查点
- **完成标识**: 自动标注已完成的分析，方便后续提问
- **清晰命名**: `checkpoint_q1a0_时间戳.json` 格式，一目了然

### 💬 用户对话模式
- **交互式提问**: 自动分析完成后，可以就笔记内容自由提问
- **上下文感知**: 分析者能看到已生成的笔记，回答更准确
- **动态整合**: 用户对话可以自动整合进最终报告

### 📊 优化的报告质量
- **精准提问**: 强调只有 3 次机会，避免无意义问题（如"如何复现"）
- **规范格式**: 自动按结构生成报告
  - 研究背景 & 主要贡献
  - 主要内容详解（根据贡献重要性灵活组织）
  - 总结

### 🧹 自动清理管理
- **大小限制**: 默认总大小超过 100MB 时自动清理
- **灵活配置**: 支持按文件数、天数、每篇论文保留数等策略
- **手动清理**: `--reset` 参数一键清空所有缓存

### 🔄 API 重试机制
- **自动重试**: API 返回空结果时自动重试（默认 5 次）
- **指数退避**: 重试间隔递增，避免频繁请求
- **稳定可靠**: 大幅降低 API 临时故障导致的失败

---

## 🚀 快速开始

### 1. 环境安装

选择一种方式安装依赖：

```bash
# 方式1: Conda（推荐，完整复制环境）
conda env create -f environment.yml
conda activate paper-reading

# 方式2: uv（最快，30秒安装）
pip install uv
uv pip install -r requirements.txt

# 方式3: pip（传统方式）
pip install -r requirements.txt
```

详细说明请参考 [ENVIRONMENT.md](ENVIRONMENT.md)

### 2. 配置 API

复制配置示例文件并填写 API 信息：

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`:
```yaml
api:
  base_url: "https://your-api.com/v1"
  api_key: "your-api-key-here"

models:
  analyzer: "gpt-4"  # 或其他强模型
  reviewer: "gpt-3.5-turbo"  # 或其他快速模型
```

### 3. 运行分析

```bash
# 基础用法
python main.py paper.pdf

# 从检查点恢复
python main.py paper.pdf --resume

# 使用强模型整合报告（更高质量）
# 修改 config.yaml: final_integration_model: "analyzer"
python main.py paper.pdf
```

完整使用指南请参考 [QUICKSTART.md](QUICKSTART.md)

---

## 📖 使用示例

### 场景1: 首次分析论文

```bash
python main.py 2510.19555v1.pdf
```

**工作流程:**
1. 📄 解析 PDF 内容
2. 🔍 分析论文结构
3. ❓ 审核者选择 3 个核心问题
4. 💬 分析者逐个回答并追问
5. ✅ 生成初版报告
6. 💾 自动保存完成状态检查点
7. 💬 询问是否进入对话模式
8. 📝 如有对话，自动重新整合笔记

**输出文件:**
- `output/paper_analysis_时间戳.md` - 分析报告
- `checkpoints/2510.19555v1/checkpoint_final_时间戳.json` - 完成状态检查点
- `checkpoints/2510.19555v1/readable_final_时间戳.md` - 可读版本

### 场景2: 中断后恢复

```bash
# 自动检测并选择检查点
python main.py 2510.19555v1.pdf

# 输出示例：
📁 发现以下检查点:

编号     保存时间                 进度                对话数    状态
----------------------------------------------------------------------
1      2025-11-13 14:30:25    已完成               15       ✅ 已完成
2      2025-11-13 14:25:10    2/3 问题             10
3      2025-11-13 14:20:05    1/3 问题              5

请选择检查点 (1-3) 或 0 重新开始: 1
```

### 场景3: 用户对话模式

```bash
python main.py paper.pdf
```

**对话示例:**
```
📄 初版报告已生成，请先阅读:
   output/paper_analysis_20251113_143025.md

==================================================
是否需要进入对话模式向分析者提问? (y/n): y

💬 用户对话模式
==================================================
您可以就论文内容向分析者提问。
输入 '结束' 或 'exit' 退出对话模式。

👤 您的问题: 这篇论文的核心创新点是什么？

🤖 分析者正在思考...

🤖 分析者: 根据已生成的分析报告，这篇论文的核心创新点有三个...

👤 您的问题: exit

✅ 退出对话模式

🔄 重新整合笔记（包含您的对话内容）...
✅ 笔记重新整合完成!
```

### 场景4: 清理缓存

```bash
# 清空所有输出和检查点
python main.py --reset

# 输出：
⚠️  警告: 即将清空所有输出和检查点目录！
这将删除:
  - output/ 目录下的所有分析报告
  - checkpoints/ 目录下的所有检查点文件

确认清空? (yes/no): yes

✅ 清空完成!
   删除文件: 156 个
   释放空间: 3.45 MB
```

---

## ⚙️ 配置说明

### 关键配置项

```yaml
# API 配置
api:
  base_url: "https://api.openai.com/v1"
  api_key: "your-key"
  max_retries: 5  # API 重试次数

# 模型配置
models:
  analyzer: "gpt-4"  # 强模型用于分析
  reviewer: "gpt-3.5-turbo"  # 快速模型用于审核

# 工作流配置
workflow:
  num_questions: 3  # 提问数量
  final_integration_model: "reviewer"  # 可选 "analyzer" 提高质量
  enable_user_qa: true  # 启用用户对话模式

# 检查点清理
checkpoint_management:
  auto_cleanup: true
  max_checkpoint_size_mb: 100  # 超过此大小自动清理
```

### 高级配置

详细配置说明请参考 `config.example.yaml` 中的注释。

---

## 🔧 命令行参数

```bash
python main.py <paper_path> [OPTIONS]

必需参数:
  paper_path              PDF 文件路径

可选参数:
  --config PATH           配置文件路径 (默认: config.yaml)
  --output-dir PATH       输出目录 (覆盖配置文件)
  --resume                从最新检查点恢复
  --checkpoint PATH       从指定检查点恢复
  --reset                 清空所有输出和检查点

示例:
  python main.py paper.pdf                        # 基础用法
  python main.py paper.pdf --resume              # 恢复最新检查点
  python main.py paper.pdf --checkpoint xxx.json # 恢复指定检查点
  python main.py --reset                         # 清空缓存
```

---

## 📁 项目结构

```
paper-analysis-multiagent/
├── agents/              # 代理实现
│   ├── analyzer.py      # 分析者代理
│   ├── reviewer.py      # 审核者代理
│   └── prompts.py       # Prompt 模板
├── graph/               # 工作流定义
│   ├── workflow.py      # LangGraph 工作流
│   └── state.py         # 状态定义
├── utils/               # 工具函数
│   ├── checkpoint.py    # 检查点管理（arXiv ID识别、清理）
│   ├── llm_client.py    # LLM 客户端（重试机制）
│   └── pdf_parser.py    # PDF 解析
├── main.py              # 主程序入口
├── config.yaml          # 配置文件
├── requirements.txt     # Python 依赖（pip）
├── environment.yml      # Conda 环境配置
├── pyproject.toml       # 项目配置（uv支持）
└── README.md            # 本文档
```

---

## ❓ 常见问题

### Q1: httpx 版本冲突错误

**错误信息:**
```
Client.__init__() got an unexpected keyword argument 'proxies'
```

**解决方法:**
```bash
pip install httpx==0.27.0 --force-reinstall
```

**原因:** httpx 0.28.x 与 openai 1.40.0 不兼容，必须使用 0.27.0。

### Q2: 检查点保存在哪里？

检查点按论文组织：
- arXiv 论文: `checkpoints/2510.19555v1/`
- 其他论文: `checkpoints/custom_1/`, `checkpoints/custom_2/`, ...

文件命名格式:
- `checkpoint_q0a0_时间戳.json` - 结构分析阶段
- `checkpoint_q1a0_时间戳.json` - 问题1首次回答
- `checkpoint_q1a1_时间戳.json` - 问题1追问后
- `checkpoint_final_时间戳.json` - 分析完成

### Q3: 如何提高报告质量？

1. **使用强模型整合**:
```yaml
workflow:
  final_integration_model: "analyzer"  # 改为 analyzer
```

2. **增加提问数量**:
```yaml
workflow:
  num_questions: 5  # 从 3 增加到 5
```

3. **使用用户对话模式**: 在自动分析后进入对话模式，针对性补充提问

### Q4: 检查点太多如何清理？

**方法1: 自动清理（推荐）**
```yaml
checkpoint_management:
  auto_cleanup: true
  max_checkpoint_size_mb: 50  # 降低阈值
  max_checkpoint_age_days: 7  # 启用天数限制
  keep_per_paper: 2  # 每篇论文只保留最新2个
```

**方法2: 手动清理**
```bash
python main.py --reset
```

### Q5: 如何从完成的检查点继续提问？

```bash
# 运行时会自动显示检查点列表
python main.py paper.pdf

# 选择标记为"✅ 已完成"的检查点
# 恢复后会自动进入用户对话模式
```

---

## 📝 更新日志

### v2.0.0 (2025-11-13)

**新功能:**
- ✨ 用户对话模式：分析完成后可以自由提问
- ✨ 完成状态检查点：自动保存并标识已完成的分析
- ✨ 优化检查点命名：`q0a0`, `q1a1` 等清晰格式
- ✨ --reset 参数：一键清空所有缓存

**改进:**
- 🎯 优化提问质量：强调 3 次机会，避免无意义问题
- 📊 规范报告格式：统一结构，避免模型凑字数
- 🔄 优化对话流程：先保存报告再询问是否对话
- 💾 修复检查点 bug：保存完整累积状态而非增量

**文档:**
- 📖 重写 README：突出新功能
- 📘 新增 QUICKSTART：快速入门指南
- 🌍 新增 ENVIRONMENT：详细环境配置说明

### v1.0.0 (2025-11-12)

**初始版本:**
- 🤖 多代理协作系统
- 💾 检查点保存与恢复
- 📊 arXiv ID 自动分类
- 🧹 自动清理管理
- 🔄 API 自动重试

---

## 📄 许可证

MIT License

---

## 🙏 致谢

本项目基于以下优秀开源项目：

- [LangGraph](https://github.com/langchain-ai/langgraph) - 多代理工作流编排
- [LangChain](https://github.com/langchain-ai/langchain) - LLM 应用框架
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) - PDF 处理
- [OpenAI API](https://openai.com) - LLM 接口

---

<div align="center">

**如果这个项目对您有帮助，欢迎 ⭐Star 支持！**

</div>
