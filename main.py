"""
Multi-Agent Paper Analysis System - Main Entry Point
"""

import os
import sys
import yaml
import logging
import argparse
from datetime import datetime
from graph.workflow import run_workflow, resume_workflow
from utils.checkpoint import (
    list_checkpoints,
    load_checkpoint,
    find_latest_checkpoint,
    verify_checkpoint_consistency,
    cleanup_checkpoints,
    save_checkpoint,
    save_readable_checkpoint
)
from utils.llm_client import LLMClient
from agents.analyzer import answer_user_question


def setup_logging(config: dict):
    """设置日志"""
    log_config = config.get('logging', {})
    level = log_config.get('level', 'INFO')
    log_file = log_config.get('file', 'paper_analysis.log')

    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def load_config(config_path: str = 'config.yaml') -> dict:
    """加载配置文件"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


def save_report(final_state: dict, output_dir: str):
    """保存报告"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(output_dir, f"paper_analysis_{timestamp}.md")

    # 保存最终报告
    final_report = final_state.get('final_report', '')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(final_report)

    print(f"\n✅ 报告已保存至: {report_file}")

    # 如果配置了保存中间结果
    if final_state['config']['output'].get('save_intermediate', False):
        intermediate_file = os.path.join(output_dir, f"intermediate_{timestamp}.txt")
        with open(intermediate_file, 'w', encoding='utf-8') as f:
            f.write("=" * 50 + "\n")
            f.write("论文架构\n")
            f.write("=" * 50 + "\n\n")
            f.write(final_state.get('paper_structure', ''))
            f.write("\n\n")

            f.write("=" * 50 + "\n")
            f.write("对话记录\n")
            f.write("=" * 50 + "\n\n")

            for msg in final_state.get('messages', []):
                f.write(f"[{msg['role'].upper()}] Round {msg['round']}, Q{msg['question_id']}\n")
                f.write(f"{msg['content']}\n")
                f.write("-" * 50 + "\n\n")

        print(f"📄 中间结果已保存至: {intermediate_file}")

    return report_file


def print_statistics(final_state: dict):
    """打印统计信息"""
    start_time = final_state.get('start_time', 0)
    end_time = final_state.get('end_time', 0)
    duration = end_time - start_time if end_time > 0 else 0

    print("\n" + "=" * 50)
    print("📊 统计信息")
    print("=" * 50)
    print(f"论文路径: {final_state['paper_path']}")
    print(f"总问题数: {final_state['total_questions']}")
    print(f"对话轮次: {len(final_state['messages'])}")
    print(f"总耗时: {duration:.2f} 秒")
    print("=" * 50)


def select_checkpoint_interactive(checkpoints: list) -> str:
    """交互式选择检查点"""
    print("\n📁 发现以下检查点:\n")
    print(f"{'编号':<6} {'保存时间':<22} {'进度':<18} {'对话数':<8} {'状态':<8}")
    print("-" * 70)

    for i, cp in enumerate(checkpoints, 1):
        saved_at = cp['saved_at'][:19] if cp['saved_at'] else '未知'
        progress = cp['progress_text']
        num_msg = cp['num_messages']
        status = "✅ 已完成" if cp.get('is_completed', False) else ""
        print(f"{i:<6} {saved_at:<22} {progress:<18} {num_msg:<8} {status:<8}")

    print()
    while True:
        try:
            choice = input(f"请选择检查点 (1-{len(checkpoints)}) 或 0 重新开始: ")
            choice_num = int(choice)
            if choice_num == 0:
                return None
            if 1 <= choice_num <= len(checkpoints):
                return checkpoints[choice_num - 1]['file']
            else:
                print(f"❌ 无效选择，请输入 0-{len(checkpoints)} 之间的数字")
        except ValueError:
            print("❌ 请输入数字")
        except KeyboardInterrupt:
            print("\n⚠️ 已取消")
            sys.exit(0)


def handle_checkpoint_consistency(checkpoint_file: str, paper_path: str, config: dict) -> bool:
    """处理检查点一致性检查，返回是否继续使用检查点"""
    is_consistent, differences = verify_checkpoint_consistency(checkpoint_file, paper_path, config)

    if is_consistent:
        print("✅ 检查点一致性验证通过")
        return True

    # 显示差异
    print("\n⚠️  检查点一致性检查发现以下差异:\n")
    for i, diff in enumerate(differences, 1):
        print(f"  {i}. {diff}")

    print()
    while True:
        try:
            choice = input("是否仍要使用此检查点继续? (y/n): ").strip().lower()
            if choice in ['y', 'yes', '是']:
                print("⚠️  将使用现有检查点继续，但可能产生不一致的结果")
                return True
            elif choice in ['n', 'no', '否']:
                print("✅ 将从头开始新的分析")
                return False
            else:
                print("❌ 请输入 y 或 n")
        except KeyboardInterrupt:
            print("\n⚠️ 已取消")
            sys.exit(0)


def user_interactive_qa(state: dict, config: dict) -> list:
    """
    用户自由对话模式

    Args:
        state: 当前状态
        config: 配置

    Returns:
        list: 用户对话记录
    """
    # 检查是否启用用户对话模式
    enable_user_qa = config.get('workflow', {}).get('enable_user_qa', True)
    if not enable_user_qa:
        return []

    print("\n" + "=" * 50)
    print("💬 用户对话模式")
    print("=" * 50)
    print("您可以就论文内容向分析者提问。")
    print("输入 '结束' 或 'exit' 退出对话模式。\n")

    # 创建 LLM 客户端
    llm_client = LLMClient(config)

    user_qa_history = []

    while True:
        try:
            user_question = input("👤 您的问题: ").strip()

            # 检查退出命令
            if user_question.lower() in ['结束', 'exit', 'quit', 'q']:
                print("\n✅ 退出对话模式")
                break

            if not user_question:
                print("⚠️  问题不能为空，请重新输入")
                continue

            # 调用分析者回答
            print("\n🤖 分析者正在思考...\n")
            answer = answer_user_question(state, llm_client, user_question)

            print(f"🤖 分析者: {answer}\n")
            print("-" * 50 + "\n")

            # 记录对话
            user_qa_history.append({
                'question': user_question,
                'answer': answer
            })

        except KeyboardInterrupt:
            print("\n\n⚠️ 对话被中断")
            break
        except Exception as e:
            print(f"\n❌ 回答问题时出错: {str(e)}")
            logging.exception("Error in user QA")

    return user_qa_history


def ask_user_for_interactive_qa() -> bool:
    """询问用户是否需要进入对话模式"""
    print("\n" + "=" * 50)
    while True:
        try:
            choice = input("是否需要进入对话模式向分析者提问? (y/n): ").strip().lower()
            if choice in ['y', 'yes', '是']:
                return True
            elif choice in ['n', 'no', '否']:
                print("✅ 跳过对话模式")
                return False
            else:
                print("❌ 请输入 y 或 n")
        except KeyboardInterrupt:
            print("\n⚠️ 已取消")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Multi-Agent Paper Analysis System')
    parser.add_argument('paper_path', nargs='?', help='Path to the PDF paper')
    parser.add_argument('--config', default='config.yaml', help='Path to config file')
    parser.add_argument('--output-dir', help='Output directory (overrides config)')
    parser.add_argument('--resume', action='store_true', help='Resume from latest checkpoint')
    parser.add_argument('--checkpoint', help='Resume from specific checkpoint file')
    parser.add_argument('--reset', action='store_true', help='Clear all output, checkpoint directories and log files')

    args = parser.parse_args()

    # ==================== 处理 --reset ====================
    if args.reset:
        # 尝试加载配置以获取 log 文件路径
        log_file = 'paper_analysis.log'  # 默认值
        try:
            config = load_config(args.config)
            log_file = config.get('logging', {}).get('file', 'paper_analysis.log')
        except:
            pass  # 如果加载失败，使用默认值

        print("\n⚠️  警告: 即将清空所有输出、检查点和日志文件！")
        print("这将删除:")
        print("  - output/ 目录下的所有分析报告")
        print("  - checkpoints/ 目录下的所有检查点文件")
        print(f"  - {log_file} (日志文件)")
        print()

        try:
            confirm = input("确认清空? (yes/no): ").strip().lower()
            if confirm not in ['yes', 'y', '是']:
                print("✅ 已取消清空操作")
                sys.exit(0)
        except KeyboardInterrupt:
            print("\n✅ 已取消清空操作")
            sys.exit(0)

        # 清空目录
        import shutil
        deleted_files = 0
        freed_bytes = 0

        # 清空 output 目录
        if os.path.exists('output'):
            for item in os.listdir('output'):
                item_path = os.path.join('output', item)
                try:
                    if os.path.isfile(item_path):
                        size = os.path.getsize(item_path)
                        os.remove(item_path)
                        deleted_files += 1
                        freed_bytes += size
                    elif os.path.isdir(item_path):
                        # 计算目录大小
                        for root, dirs, files in os.walk(item_path):
                            for f in files:
                                freed_bytes += os.path.getsize(os.path.join(root, f))
                                deleted_files += 1
                        shutil.rmtree(item_path)
                except Exception as e:
                    print(f"⚠️  无法删除 {item_path}: {e}")

        # 清空 checkpoints 目录
        if os.path.exists('checkpoints'):
            for item in os.listdir('checkpoints'):
                item_path = os.path.join('checkpoints', item)
                try:
                    if os.path.isfile(item_path):
                        size = os.path.getsize(item_path)
                        os.remove(item_path)
                        deleted_files += 1
                        freed_bytes += size
                    elif os.path.isdir(item_path):
                        # 计算目录大小
                        for root, dirs, files in os.walk(item_path):
                            for f in files:
                                freed_bytes += os.path.getsize(os.path.join(root, f))
                                deleted_files += 1
                        shutil.rmtree(item_path)
                except Exception as e:
                    print(f"⚠️  无法删除 {item_path}: {e}")

        # 清空 log 文件
        if os.path.exists(log_file):
            try:
                size = os.path.getsize(log_file)
                os.remove(log_file)
                deleted_files += 1
                freed_bytes += size
                print(f"🗑️  已删除日志文件: {log_file}")
            except Exception as e:
                print(f"⚠️  无法删除日志文件 {log_file}: {e}")

        freed_mb = freed_bytes / (1024 * 1024)
        print(f"\n✅ 清空完成!")
        print(f"   删除文件: {deleted_files} 个")
        print(f"   释放空间: {freed_mb:.2f} MB")
        sys.exit(0)

    # ==================== 正常运行模式 ====================
    # 检查PDF文件
    if not args.paper_path:
        parser.print_help()
        print("\n❌ 错误: 需要指定论文PDF文件路径")
        sys.exit(1)

    if not os.path.exists(args.paper_path):
        print(f"❌ 错误: 找不到PDF文件: {args.paper_path}")
        sys.exit(1)

    try:
        # 加载配置
        print("📝 加载配置...")
        config = load_config(args.config)

        # 设置日志
        setup_logging(config)
        logger = logging.getLogger(__name__)

        # 确定输出目录
        output_dir = args.output_dir or config['output']['output_dir']
        checkpoint_dir = config.get('output', {}).get('checkpoint_dir', 'checkpoints')

        # ==================== 自动清理检查点 ====================
        cleanup_result = cleanup_checkpoints(checkpoint_dir, config)
        if cleanup_result['deleted_files'] > 0:
            print(f"🧹 自动清理: 删除了 {cleanup_result['deleted_files']} 个检查点文件，释放 {cleanup_result['freed_mb']:.2f} MB")

        # ==================== 检查是否需要恢复 ====================
        checkpoint_file = None
        should_resume = False

        # 1. 命令行指定了具体检查点文件
        if args.checkpoint:
            if os.path.exists(args.checkpoint):
                checkpoint_file = args.checkpoint
                print(f"📦 使用指定的检查点: {checkpoint_file}")
                should_resume = True
            else:
                print(f"❌ 错误: 检查点文件不存在: {args.checkpoint}")
                sys.exit(1)

        # 2. 命令行指定了 --resume
        elif args.resume:
            checkpoint_file = find_latest_checkpoint(args.paper_path, checkpoint_dir)
            if checkpoint_file:
                print(f"📦 找到最新检查点: {checkpoint_file}")
                should_resume = True
            else:
                print("⚠️  没有找到检查点，将从头开始")
                should_resume = False

        # 3. 自动检测（没有指定 --resume 或 --checkpoint）
        else:
            checkpoints = list_checkpoints(args.paper_path, checkpoint_dir)
            if checkpoints:
                print(f"\n💡 发现 {len(checkpoints)} 个检查点")
                checkpoint_file = select_checkpoint_interactive(checkpoints)
                if checkpoint_file:
                    should_resume = True
                else:
                    print("✅ 将从头开始新的分析")
                    should_resume = False

        # ==================== 如果需要恢复，进行一致性检查 ====================
        if should_resume and checkpoint_file:
            if not handle_checkpoint_consistency(checkpoint_file, args.paper_path, config):
                should_resume = False
                checkpoint_file = None

        # ==================== 执行分析 ====================
        if should_resume and checkpoint_file:
            # 从检查点恢复
            print("\n🔄 从检查点恢复...")
            print("-" * 50)

            checkpoint_state = load_checkpoint(checkpoint_file)
            if not checkpoint_state:
                print("❌ 错误: 无法加载检查点")
                sys.exit(1)

            final_state = resume_workflow(checkpoint_state, config)

        else:
            # 从头开始
            print(f"\n🚀 开始分析论文: {args.paper_path}")
            print("-" * 50)

            final_state = run_workflow(args.paper_path, config)

        print("-" * 50)
        print("✅ 分析完成!")

        # 打印统计
        print_statistics(final_state)

        # ==================== 保存初版报告 ====================
        print("\n📝 保存初版报告...")
        initial_report_file = save_report(final_state, output_dir)

        # 保存完成后的检查点（方便用户后续恢复并提问）
        if config.get('output', {}).get('enable_checkpoints', True):
            print("💾 保存完成状态检查点...")
            save_checkpoint(final_state, checkpoint_dir)
            save_readable_checkpoint(final_state, checkpoint_dir)

        print(f"\n📄 初版报告已生成，请先阅读:")
        print(f"   {initial_report_file}")

        # ==================== 用户对话模式 ====================
        # 检查是否启用用户对话模式
        enable_user_qa = config.get('workflow', {}).get('enable_user_qa', True)

        if enable_user_qa:
            # 询问用户是否需要进入对话模式
            if ask_user_for_interactive_qa():
                user_qa_history = user_interactive_qa(final_state, config)

                # 如果有用户对话，询问是否需要重新整合
                if user_qa_history:
                    print("\n" + "=" * 50)
                    print("💡 您在对话模式中提出了新的问题")
                    print("   重新整合笔记可以将您的对话内容整合进最终报告中")
                    print("=" * 50)

                    # 询问用户是否需要重新整合
                    while True:
                        response = input("是否需要重新整合笔记? (y/n，默认 y): ").strip().lower()
                        if response == '' or response in ['y', 'yes', '是']:
                            should_reintegrate = True
                            break
                        elif response in ['n', 'no', '否']:
                            should_reintegrate = False
                            break
                        else:
                            print("❌ 无效输入，请输入 y 或 n")

                    if should_reintegrate:
                        print("\n🔄 重新整合笔记（包含您的对话内容）...")

                        # 将用户对话添加到 messages 中
                        for qa in user_qa_history:
                            final_state['messages'].append({
                                'role': 'user',
                                'content': qa['question'],
                                'round': -1,  # 用户对话标记为特殊轮次
                                'question_id': -1
                            })
                            final_state['messages'].append({
                                'role': 'analyzer',
                                'content': qa['answer'],
                                'round': -1,
                                'question_id': -1
                            })

                        # 重新生成最终报告
                        from agents.reviewer import integrate_final_report
                        llm_client = LLMClient(config)

                        # 构建包含用户对话的 QA 历史
                        qa_pairs = []
                        messages = final_state.get('messages', [])

                        # 遍历消息，配对问题和回答
                        i = 0
                        while i < len(messages):
                            msg = messages[i]
                            # 如果是问题（reviewer 或 user）
                            if msg['role'] in ['reviewer', 'user']:
                                question = msg['content']
                                # 查找紧跟的回答
                                if i + 1 < len(messages) and messages[i + 1]['role'] == 'analyzer':
                                    answer = messages[i + 1]['content']
                                    qa_pairs.append(f"**问题**: {question}\n**回答**: {answer}")
                                    i += 2  # 跳过已处理的问答对
                                else:
                                    i += 1
                            else:
                                i += 1

                        qa_history_text = "\n\n".join(qa_pairs)

                        final_state['qa_history'] = qa_history_text
                        integration_result = integrate_final_report(final_state, llm_client)
                        final_state.update(integration_result)

                        print("✅ 笔记重新整合完成!")

                        # 保存新版本报告
                        final_report_file = save_report(final_state, output_dir)
                        print(f"\n🎉 完成！最终报告已生成: {final_report_file}")

                        # 保存更新后的检查点
                        if config.get('output', {}).get('enable_checkpoints', True):
                            print("💾 保存更新后的检查点...")
                            save_checkpoint(final_state, checkpoint_dir)
                            save_readable_checkpoint(final_state, checkpoint_dir)
                    else:
                        print("\n⏭️  跳过笔记重新整合")
                        print(f"💡 您的对话记录已保存，初版报告仍然有效: {initial_report_file}")
                        print(f"\n🎉 完成！报告已生成: {initial_report_file}")
                else:
                    print(f"\n🎉 完成！报告已生成: {initial_report_file}")
            else:
                print(f"\n🎉 完成！报告已生成: {initial_report_file}")
        else:
            print(f"\n🎉 完成！报告已生成: {initial_report_file}")

    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        logging.exception("Workflow failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
