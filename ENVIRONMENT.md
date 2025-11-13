# 环境配置说明

本项目提供多种环境配置方式，可根据您的工具选择合适的方法。

## 快速开始

### 方法1: 使用 Conda（推荐）

Conda 可以完整复制包括 Python 版本在内的整个环境。

```bash
# 创建环境
conda env create -f environment.yml

# 激活环境
conda activate paper-reading

# 验证安装
python -c "import langgraph; print('Environment ready!')"
```

### 方法2: 使用 uv（最快）

[uv](https://github.com/astral-sh/uv) 是 Rust 编写的超快速 Python 包管理器。

```bash
# 安装 uv
pip install uv

# 使用 pyproject.toml 安装
uv pip install -e .

# 或使用 requirements.txt
uv pip install -r requirements.txt
```

### 方法3: 使用 pip（传统方式）

```bash
# 创建虚拟环境
python -m venv venv

# 激活环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 环境要求

- **Python**: 3.10.19 （推荐）或 3.10.x
- **操作系统**: Windows / Linux / macOS
- **内存**: 建议 8GB 以上

## 关键依赖说明

### 核心框架
- **langgraph==0.2.16**: 多代理工作流编排
- **langchain==0.2.16**: LLM 应用框架
- **openai==1.40.0**: OpenAI API 客户端

### ⚠️ 重要版本限制
- **httpx==0.27.0**: 必须使用 0.27.0 版本
  - httpx 0.28.x 与 openai 1.40.0 不兼容
  - 会导致 `Client.__init__() got an unexpected keyword argument 'proxies'` 错误

### PDF 处理
- **PyMuPDF**: 高性能 PDF 解析
- **pdfplumber**: 表格和布局提取
- **pymupdf4llm**: LLM 友好的文本提取

## 可选依赖

### NLP 增强（可选）
```bash
pip install spacy
python -m spacy download en_core_web_sm
```

## 导出当前环境

如果您在现有环境中做了修改，可以重新导出：

### 导出 requirements.txt
```bash
pip freeze > requirements-freeze.txt
```

### 导出 conda environment
```bash
conda env export > environment-export.yml
```

### 导出完整的 conda 列表
```bash
conda list --export > conda-list.txt
```

## 环境验证

安装完成后，运行以下命令验证环境：

```bash
python -c "
import langgraph
import langchain
import openai
import httpx
import pymupdf
print('✅ All core dependencies installed successfully!')
print(f'httpx version: {httpx.__version__} (should be 0.27.0)')
print(f'openai version: {openai.__version__}')
"
```

## 常见问题

### Q1: httpx 版本冲突
**问题**: 安装后 httpx 版本不是 0.27.0
**解决**: 强制重装 `pip install httpx==0.27.0 --force-reinstall`

### Q2: PDF 解析失败
**问题**: 无法解析某些 PDF 文件
**解决**: 确保安装了 PyMuPDF: `pip install PyMuPDF==1.26.6`

### Q3: LangGraph 导入错误
**问题**: `ImportError: cannot import name 'StateGraph'`
**解决**: 检查版本 `pip install langgraph==0.2.16 --force-reinstall`

## 更新依赖

定期更新依赖以获取安全补丁和新功能：

```bash
# 使用 pip
pip install --upgrade -r requirements.txt

# 使用 conda
conda env update -f environment.yml --prune

# 使用 uv（最快）
uv pip install --upgrade -r requirements.txt
```

## 环境清理

如果需要完全重建环境：

```bash
# Conda
conda deactivate
conda env remove -n paper-reading
conda env create -f environment.yml

# pip/venv
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate  # 或 venv\Scripts\activate (Windows)
pip install -r requirements.txt
```

## 性能对比

各工具安装速度对比（仅供参考）：

| 工具 | 首次安装 | 更新依赖 | 优点 |
|------|---------|---------|------|
| uv | ~30秒 | ~5秒 | 最快，并行下载 |
| pip | ~2分钟 | ~30秒 | 兼容性好 |
| conda | ~5分钟 | ~1分钟 | 完整环境管理 |

## 技术支持

遇到环境问题？
1. 查看 [GitHub Issues](https://github.com/your-repo/issues)
2. 运行诊断脚本: `python -m utils.check_env`
3. 提供完整的错误日志
