"""
Checkpoint - 保存和恢复中间结果，支持自动分类和清理
"""

import os
import json
import hashlib
import logging
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


logger = logging.getLogger(__name__)


# ==================== arXiv ID 提取 ====================

# arXiv ID 正则表达式：YYMM.NNNNN 或 YYMM.NNNNNvX
ARXIV_ID_PATTERN = r'\b(\d{4}\.\d{4,5})(v\d+)?\b'


def extract_arxiv_id_from_filename(paper_path: str) -> Optional[str]:
    """
    从文件名中提取 arXiv ID

    Args:
        paper_path: 论文文件路径

    Returns:
        str: arXiv ID (如 "2510.19555v1") 或 None
    """
    filename = os.path.basename(paper_path)

    # 匹配 arXiv ID
    match = re.search(ARXIV_ID_PATTERN, filename)
    if match:
        arxiv_id = match.group(1)  # 主ID（如 2510.19555）
        version = match.group(2)    # 版本号（如 v1）

        if version:
            return f"{arxiv_id}{version}"
        else:
            # 如果没有版本号，默认补 v1
            return f"{arxiv_id}v1"

    return None


def extract_arxiv_id_from_content(paper_content: str) -> Optional[str]:
    """
    从 PDF 内容中提取 arXiv ID

    Args:
        paper_content: 论文文本内容

    Returns:
        str: arXiv ID 或 None
    """
    # 只检查前 3000 字符（通常在第一页）
    content_head = paper_content[:3000] if paper_content else ""

    # 尝试多种模式
    patterns = [
        r'arXiv:(\d{4}\.\d{4,5}(?:v\d+)?)',  # arXiv:2510.19555v1
        r'arxiv\.org/abs/(\d{4}\.\d{4,5})',   # arxiv.org/abs/2510.19555
    ]

    for pattern in patterns:
        match = re.search(pattern, content_head, re.IGNORECASE)
        if match:
            arxiv_id = match.group(1)
            # 补充版本号（如果没有）
            if not re.search(r'v\d+$', arxiv_id):
                arxiv_id += 'v1'
            return arxiv_id

    return None


def get_next_custom_id(checkpoint_base_dir: str) -> str:
    """
    获取下一个可用的 custom_N 编号

    Args:
        checkpoint_base_dir: 检查点基础目录

    Returns:
        str: 如 "custom_1", "custom_2", ...
    """
    if not os.path.exists(checkpoint_base_dir):
        return "custom_1"

    # 查找现有的 custom_N 目录
    existing_nums = []
    for dirname in os.listdir(checkpoint_base_dir):
        if dirname.startswith('custom_'):
            try:
                num = int(dirname.split('_')[1])
                existing_nums.append(num)
            except:
                pass

    # 返回下一个编号
    next_num = max(existing_nums) + 1 if existing_nums else 1
    return f"custom_{next_num}"


def get_paper_identifier(paper_path: str, paper_content: str = "", checkpoint_base_dir: str = "checkpoints") -> str:
    """
    获取论文的唯一标识符（arXiv ID 或 custom_N）

    优先级：
    1. 从文件名提取 arXiv ID
    2. 从内容提取 arXiv ID
    3. 查找现有的 custom_N（基于论文路径）
    4. 分配新的 custom_N

    Args:
        paper_path: 论文文件路径
        paper_content: 论文文本内容
        checkpoint_base_dir: 检查点基础目录

    Returns:
        str: 论文标识符
    """
    # 1. 尝试从文件名提取
    arxiv_id = extract_arxiv_id_from_filename(paper_path)
    if arxiv_id:
        logger.info(f"Extracted arXiv ID from filename: {arxiv_id}")
        return arxiv_id

    # 2. 尝试从内容提取
    if paper_content:
        arxiv_id = extract_arxiv_id_from_content(paper_content)
        if arxiv_id:
            logger.info(f"Extracted arXiv ID from content: {arxiv_id}")
            return arxiv_id

    # 3. 查找是否已经为这篇论文分配了 custom_N
    # 通过检查所有 custom_N 目录中的第一个检查点文件的 paper_path
    if os.path.exists(checkpoint_base_dir):
        abs_paper_path = os.path.abspath(paper_path)

        for dirname in os.listdir(checkpoint_base_dir):
            if dirname.startswith('custom_'):
                dir_path = os.path.join(checkpoint_base_dir, dirname)
                if not os.path.isdir(dir_path):
                    continue

                # 检查这个目录中的任一检查点文件
                for filename in os.listdir(dir_path):
                    if filename.endswith('.json') and filename.startswith('checkpoint_'):
                        checkpoint_file = os.path.join(dir_path, filename)
                        try:
                            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                saved_path = data.get('paper_path', '')
                                if os.path.abspath(saved_path) == abs_paper_path:
                                    logger.info(f"Found existing custom ID: {dirname}")
                                    return dirname
                        except:
                            pass
                        break  # 只需要检查一个文件即可

    # 4. 分配新的 custom_N
    custom_id = get_next_custom_id(checkpoint_base_dir)
    logger.info(f"Assigned custom ID: {custom_id}")
    return custom_id


# ==================== 目录管理 ====================

def get_checkpoint_dir_for_paper(paper_path: str, paper_content: str = "", checkpoint_base_dir: str = "checkpoints") -> Tuple[str, str]:
    """
    获取论文的专属检查点目录

    Args:
        paper_path: 论文文件路径
        paper_content: 论文文本内容（用于提取 arXiv ID）
        checkpoint_base_dir: 检查点基础目录

    Returns:
        Tuple[str, str]: (检查点目录路径, 论文标识符)
    """
    # 获取论文标识符（arXiv ID 或 custom_N）
    identifier = get_paper_identifier(paper_path, paper_content, checkpoint_base_dir)

    # 构建目录路径
    paper_checkpoint_dir = os.path.join(checkpoint_base_dir, identifier)

    # 创建目录（如果不存在）
    if not os.path.exists(paper_checkpoint_dir):
        os.makedirs(paper_checkpoint_dir)
        logger.info(f"Created checkpoint directory: {paper_checkpoint_dir}")

    return paper_checkpoint_dir, identifier


def get_dir_size(directory: str) -> int:
    """计算目录总大小（字节）"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
    except Exception as e:
        logger.warning(f"Failed to calculate directory size: {e}")
    return total_size


def get_checkpoint_stats(checkpoint_base_dir: str = "checkpoints") -> Dict:
    """
    获取检查点统计信息

    Returns:
        Dict: 包含总数、总大小、每篇论文统计等信息
    """
    stats = {
        'total_files': 0,
        'total_size_mb': 0.0,
        'papers': {},  # {paper_name: {'count': N, 'latest': timestamp, 'completed': N}}
        'oldest_timestamp': None,
        'newest_timestamp': None
    }

    if not os.path.exists(checkpoint_base_dir):
        return stats

    try:
        total_size_bytes = get_dir_size(checkpoint_base_dir)
        stats['total_size_mb'] = total_size_bytes / (1024 * 1024)

        oldest_mtime = None
        newest_mtime = None

        # 遍历所有子目录（论文目录）
        for paper_dir in os.listdir(checkpoint_base_dir):
            paper_path = os.path.join(checkpoint_base_dir, paper_dir)

            if not os.path.isdir(paper_path):
                continue

            paper_stats = {
                'count': 0,
                'latest': None,
                'completed_count': 0
            }

            # 统计该论文的检查点
            for filename in os.listdir(paper_path):
                if filename.endswith('.json') and filename.startswith('checkpoint_'):
                    filepath = os.path.join(paper_path, filename)
                    stats['total_files'] += 1
                    paper_stats['count'] += 1

                    mtime = os.path.getmtime(filepath)

                    if oldest_mtime is None or mtime < oldest_mtime:
                        oldest_mtime = mtime
                    if newest_mtime is None or mtime > newest_mtime:
                        newest_mtime = mtime

                    if paper_stats['latest'] is None or mtime > paper_stats['latest']:
                        paper_stats['latest'] = mtime

                    # 检查是否完成
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            current_q = data.get('current_question_id', 0)
                            total_q = data.get('total_questions', 3)
                            if current_q >= total_q:
                                paper_stats['completed_count'] += 1
                    except:
                        pass

            if paper_stats['count'] > 0:
                stats['papers'][paper_dir] = paper_stats

        if oldest_mtime:
            stats['oldest_timestamp'] = oldest_mtime
        if newest_mtime:
            stats['newest_timestamp'] = newest_mtime

    except Exception as e:
        logger.error(f"Failed to get checkpoint stats: {e}")

    return stats


def _get_file_hash(filepath: str) -> str:
    """计算文件的 MD5 哈希值"""
    try:
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.warning(f"Failed to compute hash for {filepath}: {e}")
        return ""


def _get_pdf_metadata(paper_path: str) -> Dict:
    """获取PDF文件元数据"""
    try:
        if os.path.exists(paper_path):
            stat = os.stat(paper_path)
            return {
                'path': paper_path,
                'size': stat.st_size,
                'mtime': stat.st_mtime,
                'hash': _get_file_hash(paper_path)
            }
    except Exception as e:
        logger.warning(f"Failed to get PDF metadata: {e}")
    return {}


def get_checkpoint_stage(state: Dict) -> str:
    """
    根据状态生成检查点阶段标识

    Args:
        state: 当前状态字典

    Returns:
        str: 阶段标识，如 'q0a0', 'q1a0', 'q1a1', 'final'
    """
    # 获取当前问题ID和轮次
    current_q = state.get('current_question_id', 0)
    current_round = state.get('current_round', 0)
    total_q = state.get('total_questions', 3)

    # 判断是否有结构
    has_structure = bool(state.get('paper_structure', ''))

    # 判断是否有选中的问题
    has_questions = bool(state.get('selected_questions', []))

    # 判断是否有最终报告
    has_final_report = bool(state.get('final_report', ''))

    # 根据状态判断阶段
    if has_final_report:
        return 'final'
    elif not has_structure:
        return 'q0a0'  # 结构分析阶段
    elif not has_questions:
        return 'q0a1'  # 问题选择阶段
    elif current_q < total_q:
        # 根据当前问题的消息数判断是第几次回答
        messages = state.get('messages', [])
        # 计算该问题相关的回答次数
        answer_count = sum(1 for msg in messages
                          if msg.get('question_id') == current_q and msg.get('role') == 'analyzer')
        return f'q{current_q + 1}a{answer_count}'  # 问题从1开始计数，回答次数从0开始
    else:
        return f'q{total_q}a1'  # 所有问题完成


def save_checkpoint(state: Dict, checkpoint_base_dir: str = "checkpoints"):
    """
    保存当前状态到检查点文件（使用 arXiv ID 分类目录）

    Args:
        state: 当前状态字典
        checkpoint_base_dir: 检查点基础目录
    """
    try:
        paper_path = state.get('paper_path', 'unknown')
        paper_content = state.get('paper_content', '')  # 用于提取 arXiv ID

        # 获取状态变量（用于序列化）
        current_q = state.get('current_question_id', 0)
        total_q = state.get('total_questions', 3)

        # 获取论文专属目录和标识符
        paper_checkpoint_dir, identifier = get_checkpoint_dir_for_paper(
            paper_path, paper_content, checkpoint_base_dir
        )

        # 生成检查点阶段标识和文件名
        stage = get_checkpoint_stage(state)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_file = os.path.join(paper_checkpoint_dir, f"checkpoint_{stage}_{timestamp}.json")

        # 获取PDF元数据
        pdf_metadata = _get_pdf_metadata(paper_path)

        # 获取配置快照（关键配置项）
        config = state.get('config', {})
        config_snapshot = {
            'models': config.get('models', {}),
            'workflow': config.get('workflow', {}),
            'api': {
                'base_url': config.get('api', {}).get('base_url', ''),
                'timeout': config.get('api', {}).get('timeout', 120),
            }
        }

        # 准备可序列化的状态（排除不可序列化的对象）
        serializable_state = {
            # 元数据
            'checkpoint_version': '2.0',  # 新版本（使用 arXiv ID 目录）
            'saved_at': datetime.now().isoformat(),
            'paper_identifier': identifier,  # 保存标识符
            'pdf_metadata': pdf_metadata,
            'config_snapshot': config_snapshot,

            # 状态数据
            'paper_path': paper_path,
            'paper_structure': state.get('paper_structure', ''),
            'selected_questions': state.get('selected_questions', []),
            'messages': list(state.get('messages', [])),
            'qa_pairs': state.get('qa_pairs', []),
            'verification_results': state.get('verification_results', []),
            'current_question_id': current_q,
            'current_round': state.get('current_round', 0),
            'total_questions': total_q,
            'final_report': state.get('final_report', ''),
            'start_time': state.get('start_time', 0.0),
        }

        # 保存到文件
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_state, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 Checkpoint saved: {checkpoint_file} (ID: {identifier})")
        return checkpoint_file

    except Exception as e:
        logger.error(f"Failed to save checkpoint: {str(e)}")
        return None


def save_readable_checkpoint(state: Dict, checkpoint_base_dir: str = "checkpoints"):
    """
    保存人类可读的检查点（Markdown格式）

    Args:
        state: 当前状态字典
        checkpoint_base_dir: 检查点基础目录
    """
    try:
        paper_path = state.get('paper_path', 'unknown')
        paper_content = state.get('paper_content', '')

        # 获取论文专属目录和标识符
        paper_checkpoint_dir, identifier = get_checkpoint_dir_for_paper(
            paper_path, paper_content, checkpoint_base_dir
        )

        # 生成文件名（使用阶段标识）
        stage = get_checkpoint_stage(state)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        readable_file = os.path.join(paper_checkpoint_dir, f"readable_{stage}_{timestamp}.md")

        # 生成可读内容
        content = []
        content.append(f"# 论文分析检查点\n")
        content.append(f"**论文**: {state.get('paper_path', 'N/A')}\n")
        content.append(f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        content.append(f"**当前轮次**: {state.get('current_round', 0)}\n")
        content.append(f"**当前问题**: {state.get('current_question_id', 0)}/{state.get('total_questions', 3)}\n")
        content.append("\n---\n\n")

        # 论文架构
        if state.get('paper_structure'):
            content.append("## 📋 论文架构\n\n")
            content.append(state['paper_structure'])
            content.append("\n\n---\n\n")

        # 选择的问题
        if state.get('selected_questions'):
            content.append("## ❓ 选择的问题\n\n")
            for i, q in enumerate(state['selected_questions'], 1):
                content.append(f"{i}. {q}\n")
            content.append("\n---\n\n")

        # 对话历史
        if state.get('messages'):
            content.append("## 💬 对话历史\n\n")
            for msg in state['messages']:
                role = msg.get('role', 'unknown')
                round_num = msg.get('round', 0)
                q_id = msg.get('question_id', 0)
                msg_content = msg.get('content', '')

                role_icon = "🔍" if role == "analyzer" else "✅"
                content.append(f"### {role_icon} {role.upper()} - Round {round_num}, Q{q_id}\n\n")
                content.append(f"{msg_content}\n\n")
                content.append("---\n\n")

        # 保存文件
        with open(readable_file, 'w', encoding='utf-8') as f:
            f.write(''.join(content))

        logger.info(f"📖 Readable checkpoint saved: {readable_file}")
        return readable_file

    except Exception as e:
        logger.error(f"Failed to save readable checkpoint: {str(e)}")
        return None


def find_latest_checkpoint(paper_path: str, checkpoint_base_dir: str = "checkpoints") -> str:
    """
    查找指定论文的最新检查点（支持新的 arXiv ID 目录结构）

    Args:
        paper_path: 论文路径
        checkpoint_base_dir: 检查点基础目录

    Returns:
        str: 最新检查点文件路径，如果没有则返回 None
    """
    try:
        # 获取论文标识符（不需要 paper_content，因为只是查找）
        identifier = get_paper_identifier(paper_path, "", checkpoint_base_dir)

        # 构建论文专属目录
        paper_checkpoint_dir = os.path.join(checkpoint_base_dir, identifier)

        if not os.path.exists(paper_checkpoint_dir):
            logger.info(f"No checkpoint directory found for: {identifier}")
            return None

        checkpoints = []
        for filename in os.listdir(paper_checkpoint_dir):
            if filename.startswith("checkpoint_") and filename.endswith('.json'):
                filepath = os.path.join(paper_checkpoint_dir, filename)
                checkpoints.append((os.path.getmtime(filepath), filepath))

        if checkpoints:
            checkpoints.sort(reverse=True)
            latest = checkpoints[0][1]
            logger.info(f"Found latest checkpoint: {latest}")
            return latest

        return None

    except Exception as e:
        logger.error(f"Failed to find checkpoint: {str(e)}")
        return None


def load_checkpoint(checkpoint_file: str) -> Optional[Dict]:
    """
    从检查点文件加载状态

    Args:
        checkpoint_file: 检查点文件路径

    Returns:
        Dict: 恢复的状态字典，如果失败则返回 None
    """
    try:
        if not os.path.exists(checkpoint_file):
            logger.error(f"Checkpoint file not found: {checkpoint_file}")
            return None

        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            state = json.load(f)

        logger.info(f"✅ Checkpoint loaded: {checkpoint_file}")
        return state

    except Exception as e:
        logger.error(f"Failed to load checkpoint: {str(e)}")
        return None


def list_checkpoints(paper_path: str, checkpoint_base_dir: str = "checkpoints") -> List[Dict]:
    """
    列出指定论文的所有检查点（支持新的 arXiv ID 目录结构）

    Args:
        paper_path: 论文路径
        checkpoint_base_dir: 检查点基础目录

    Returns:
        List[Dict]: 检查点信息列表
    """
    try:
        # 获取论文标识符
        identifier = get_paper_identifier(paper_path, "", checkpoint_base_dir)

        # 构建论文专属目录
        paper_checkpoint_dir = os.path.join(checkpoint_base_dir, identifier)

        if not os.path.exists(paper_checkpoint_dir):
            return []

        checkpoints = []
        for filename in os.listdir(paper_checkpoint_dir):
            if filename.startswith("checkpoint_") and filename.endswith('.json'):
                filepath = os.path.join(paper_checkpoint_dir, filename)

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    stat = os.stat(filepath)
                    saved_at = data.get('saved_at', '')
                    current_q = data.get('current_question_id', 0)
                    total_q = data.get('total_questions', 3)
                    has_final_report = bool(data.get('final_report', '').strip())

                    # 判断是否已完成：有最终报告
                    is_completed = has_final_report

                    checkpoints.append({
                        'file': filepath,
                        'filename': filename,
                        'mtime': stat.st_mtime,
                        'size': stat.st_size,
                        'saved_at': saved_at,
                        'current_question': current_q,
                        'total_questions': total_q,
                        'progress_text': f"{current_q}/{total_q} 问题" if not is_completed else "已完成",
                        'has_structure': bool(data.get('paper_structure')),
                        'num_messages': len(data.get('messages', [])),
                        'is_completed': is_completed,
                    })
                except Exception as e:
                    logger.warning(f"Failed to read checkpoint {filename}: {e}")
                    continue

        # 按时间降序排序
        checkpoints.sort(key=lambda x: x['mtime'], reverse=True)
        return checkpoints

    except Exception as e:
        logger.error(f"Failed to list checkpoints: {str(e)}")
        return []


def verify_checkpoint_consistency(checkpoint_file: str, current_paper_path: str, current_config: Dict) -> Tuple[bool, List[str]]:
    """
    验证检查点的一致性（论文是否修改、配置是否变化）

    Args:
        checkpoint_file: 检查点文件路径
        current_paper_path: 当前的论文文件路径
        current_config: 当前的配置字典

    Returns:
        Tuple[bool, List[str]]: (是否一致, 差异列表)
    """
    differences = []

    try:
        # 加载检查点
        checkpoint = load_checkpoint(checkpoint_file)
        if not checkpoint:
            return False, ["无法加载检查点文件"]

        # 1. 检查论文路径是否一致
        saved_paper_path = checkpoint.get('paper_path', '')
        if os.path.abspath(saved_paper_path) != os.path.abspath(current_paper_path):
            differences.append(f"论文路径不同: 检查点={saved_paper_path}, 当前={current_paper_path}")

        # 2. 检查PDF文件是否被修改
        saved_pdf_meta = checkpoint.get('pdf_metadata', {})
        current_pdf_meta = _get_pdf_metadata(current_paper_path)

        if saved_pdf_meta and current_pdf_meta:
            # 比较文件大小
            if saved_pdf_meta.get('size') != current_pdf_meta.get('size'):
                differences.append(f"PDF文件大小不同: 检查点={saved_pdf_meta.get('size')}, 当前={current_pdf_meta.get('size')}")

            # 比较文件哈希
            saved_hash = saved_pdf_meta.get('hash', '')
            current_hash = current_pdf_meta.get('hash', '')
            if saved_hash and current_hash and saved_hash != current_hash:
                differences.append(f"PDF文件内容已修改 (哈希值不同)")

        # 3. 检查关键配置是否变化
        saved_config = checkpoint.get('config_snapshot', {})

        # 比较模型配置
        saved_models = saved_config.get('models', {})
        current_models = current_config.get('models', {})
        if saved_models != current_models:
            differences.append(f"模型配置已变化")

        # 比较工作流配置
        saved_workflow = saved_config.get('workflow', {})
        current_workflow = current_config.get('workflow', {})
        if saved_workflow.get('num_questions') != current_workflow.get('num_questions'):
            differences.append(f"问题数量配置已变化: {saved_workflow.get('num_questions')} → {current_workflow.get('num_questions')}")

        # 比较 API 配置
        saved_api = saved_config.get('api', {})
        current_api = current_config.get('api', {})
        if saved_api.get('base_url') != current_api.get('base_url'):
            differences.append(f"API base_url 已变化")

        is_consistent = len(differences) == 0
        return is_consistent, differences

    except Exception as e:
        logger.error(f"Failed to verify checkpoint consistency: {str(e)}")
        return False, [f"验证失败: {str(e)}"]


# ==================== 自动清理 ====================

def cleanup_checkpoints(checkpoint_base_dir: str = "checkpoints", config: Dict = None) -> Dict:
    """
    根据配置自动清理检查点

    Args:
        checkpoint_base_dir: 检查点基础目录
        config: 配置字典

    Returns:
        Dict: 清理统计信息 {'deleted_files': N, 'freed_mb': X, 'details': [...]}
    """
    if config is None:
        config = {}

    cleanup_config = config.get('checkpoint_management', {})

    # 如果未启用自动清理，直接返回
    if not cleanup_config.get('auto_cleanup', False):
        return {'deleted_files': 0, 'freed_mb': 0.0, 'details': []}

    # 读取配置项
    max_size_mb = cleanup_config.get('max_checkpoint_size_mb', None)
    max_files = cleanup_config.get('max_checkpoint_files', None)
    max_age_days = cleanup_config.get('max_checkpoint_age_days', None)
    keep_per_paper = cleanup_config.get('keep_per_paper', None)
    keep_completed = cleanup_config.get('keep_completed', True)

    # 检查是否存在检查点目录
    if not os.path.exists(checkpoint_base_dir):
        return {'deleted_files': 0, 'freed_mb': 0.0, 'details': []}

    logger.info("🧹 Starting checkpoint cleanup...")

    # 统计当前状态
    stats = get_checkpoint_stats(checkpoint_base_dir)
    current_size_mb = stats['total_size_mb']
    current_files = stats['total_files']

    logger.info(f"Current checkpoint status: {current_files} files, {current_size_mb:.2f} MB")

    deleted_files = 0
    freed_bytes = 0
    details = []

    # 收集所有检查点文件（包含完整路径和元数据）
    all_checkpoints = []

    for paper_dir in os.listdir(checkpoint_base_dir):
        paper_path = os.path.join(checkpoint_base_dir, paper_dir)
        if not os.path.isdir(paper_path):
            continue

        for filename in os.listdir(paper_path):
            if filename.endswith('.json') and filename.startswith('checkpoint_'):
                filepath = os.path.join(paper_path, filename)

                try:
                    stat = os.stat(filepath)
                    mtime = stat.st_mtime
                    size = stat.st_size

                    # 读取检查点判断是否完成
                    is_completed = False
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            current_q = data.get('current_question_id', 0)
                            total_q = data.get('total_questions', 3)
                            is_completed = (current_q >= total_q)
                    except:
                        pass

                    all_checkpoints.append({
                        'path': filepath,
                        'paper_dir': paper_dir,
                        'filename': filename,
                        'mtime': mtime,
                        'size': size,
                        'is_completed': is_completed,
                        'age_days': (time.time() - mtime) / 86400
                    })
                except Exception as e:
                    logger.warning(f"Failed to stat checkpoint {filepath}: {e}")

    # 按时间排序（最旧的在前）
    all_checkpoints.sort(key=lambda x: x['mtime'])

    files_to_delete = []

    # 策略1: 按年龄清理
    if max_age_days is not None:
        for cp in all_checkpoints:
            if cp['age_days'] > max_age_days:
                # 如果设置了保留已完成的，且这是已完成的检查点，则跳过
                if keep_completed and cp['is_completed']:
                    continue
                files_to_delete.append(cp)

        if files_to_delete:
            details.append(f"Removed {len(files_to_delete)} checkpoints older than {max_age_days} days")

    # 策略2: 按每篇论文保留数量清理
    if keep_per_paper is not None:
        paper_checkpoints = {}
        for cp in all_checkpoints:
            paper_dir = cp['paper_dir']
            if paper_dir not in paper_checkpoints:
                paper_checkpoints[paper_dir] = []
            paper_checkpoints[paper_dir].append(cp)

        for paper_dir, cps in paper_checkpoints.items():
            # 按时间排序（最新的在前）
            cps.sort(key=lambda x: x['mtime'], reverse=True)

            # 保留最新的 keep_per_paper 个（如果设置了 keep_completed，已完成的不计入）
            kept_count = 0
            for cp in cps:
                if kept_count >= keep_per_paper:
                    # 超出限制，标记为删除
                    if keep_completed and cp['is_completed']:
                        continue  # 保留已完成的
                    if cp not in files_to_delete:
                        files_to_delete.append(cp)
                else:
                    # 如果这是已完成的，不计入保留数量
                    if not (keep_completed and cp['is_completed']):
                        kept_count += 1

        if keep_per_paper:
            details.append(f"Applied keep_per_paper={keep_per_paper} policy")

    # 策略3: 按总文件数清理
    if max_files is not None and current_files > max_files:
        excess = current_files - max_files
        # 删除最旧的文件（但如果已在删除列表中则不重复）
        for cp in all_checkpoints:
            if excess <= 0:
                break
            if keep_completed and cp['is_completed']:
                continue
            if cp not in files_to_delete:
                files_to_delete.append(cp)
                excess -= 1

        details.append(f"Reduced file count to max {max_files}")

    # 策略4: 按总大小清理（最重要，最后执行）
    if max_size_mb is not None and current_size_mb > max_size_mb:
        # 需要释放的空间
        need_free_mb = current_size_mb - max_size_mb
        need_free_bytes = need_free_mb * 1024 * 1024

        # 按时间删除最旧的检查点，直到满足大小要求
        freed_so_far = sum(cp['size'] for cp in files_to_delete)

        for cp in all_checkpoints:
            if freed_so_far >= need_free_bytes:
                break
            if keep_completed and cp['is_completed']:
                continue
            if cp not in files_to_delete:
                files_to_delete.append(cp)
                freed_so_far += cp['size']

        details.append(f"Reduced total size to max {max_size_mb} MB")

    # 执行删除
    for cp in files_to_delete:
        try:
            # 删除 JSON 检查点文件
            os.remove(cp['path'])
            deleted_files += 1
            freed_bytes += cp['size']
            logger.debug(f"Deleted checkpoint: {cp['path']}")

            # 同时删除对应的 readable markdown 文件（如果存在）
            readable_file = cp['path'].replace('checkpoint_', 'readable_').replace('.json', '.md')
            if os.path.exists(readable_file):
                try:
                    readable_size = os.path.getsize(readable_file)
                    os.remove(readable_file)
                    freed_bytes += readable_size
                    logger.debug(f"Deleted readable file: {readable_file}")
                except Exception as e:
                    logger.warning(f"Failed to delete readable file {readable_file}: {e}")

        except Exception as e:
            logger.warning(f"Failed to delete {cp['path']}: {e}")

    freed_mb = freed_bytes / (1024 * 1024)

    if deleted_files > 0:
        logger.info(f"✅ Cleanup complete: deleted {deleted_files} files, freed {freed_mb:.2f} MB")
    else:
        logger.info("✅ No cleanup needed")

    return {
        'deleted_files': deleted_files,
        'freed_mb': freed_mb,
        'details': details
    }

