"""
PDF解析工具 - 复用gpt_academic的成熟方案
"""

import os
import sys

# 添加gpt_academic到路径（如果需要直接复用）
GPT_ACADEMIC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../OneKeyInstallerForWindowsAndMacOS/gpt_academic'))
if os.path.exists(GPT_ACADEMIC_PATH):
    sys.path.insert(0, GPT_ACADEMIC_PATH)


def parse_pdf_simple(pdf_path: str) -> str:
    """
    简化版PDF解析 - 直接返回纯文本
    复用gpt_academic的TextContentLoader

    Args:
        pdf_path: PDF文件路径

    Returns:
        str: 论文全文（纯文本）
    """
    try:
        # 方案1：直接使用gpt_academic的TextContentLoader
        from crazy_functions.doc_fns.text_content_loader import TextContentLoader

        # 创建一个简单的加载器
        loader = TextContentLoader(chatbot=None, history=[])

        # 读取文件
        # 注意：TextContentLoader.execute_single_file 需要chatbot和history，这里简化处理
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)
        text = ""
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text()
            # 添加页码标记
            text += f"\n\n===== Page {page_num} =====\n\n"
            text += page_text

        doc.close()
        return text

    except ImportError:
        # 方案2：如果无法导入gpt_academic，使用PyMuPDF
        import fitz

        doc = fitz.open(pdf_path)
        text = ""
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text()
            text += f"\n\n===== Page {page_num} =====\n\n"
            text += page_text

        doc.close()
        return text


def parse_pdf_with_structure(pdf_path: str) -> dict:
    """
    带结构的PDF解析（可选）

    Returns:
        dict: {
            'text': 全文,
            'pages': [{page_num, text}, ...],
            'metadata': {title, author, ...}
        }
    """
    import fitz

    doc = fitz.open(pdf_path)

    # 提取元数据
    metadata = doc.metadata

    # 按页提取
    pages = []
    full_text = ""

    for page_num, page in enumerate(doc, start=1):
        page_text = page.get_text()
        pages.append({
            'page_num': page_num,
            'text': page_text
        })
        full_text += f"\n\n===== Page {page_num} =====\n\n{page_text}"

    doc.close()

    return {
        'text': full_text,
        'pages': pages,
        'metadata': metadata
    }


# 默认使用简化版
parse_pdf = parse_pdf_simple
