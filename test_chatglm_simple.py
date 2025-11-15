"""
测试智谱AI ChatGLM API调用 - 简化版
"""
import os
from zhipuai import ZhipuAI

# 从环境变量加载配置
from dotenv import load_dotenv
load_dotenv()

def test_basic():
    """基础测试"""
    api_key = os.getenv('ZHIPU_API_KEY')

    if not api_key:
        print("错误: 未找到 ZHIPU_API_KEY 环境变量")
        return

    print("正在初始化智谱AI客户端...")
    print(f"API Key: {api_key[:20]}...")

    client = ZhipuAI(api_key=api_key)

    print("\n发送测试消息...")
    try:
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {"role": "user", "content": "你好，请用一句话介绍你自己"}
            ],
            stream=False,
            max_tokens=100,
            temperature=0.7
        )

        print("\n[成功] API调用成功！")
        print(f"模型: {response.model}")
        print(f"回复: {response.choices[0].message.content}")
        print(f"Token使用: 提示词={response.usage.prompt_tokens}, 完成={response.usage.completion_tokens}, 总计={response.usage.total_tokens}")

    except Exception as e:
        print(f"\n[失败] API调用失败: {str(e)}")
        import traceback
        traceback.print_exc()


def test_diary_analysis():
    """测试日记情绪分析 - 核心功能"""
    api_key = os.getenv('ZHIPU_API_KEY')

    if not api_key:
        print("错误: 未找到 ZHIPU_API_KEY")
        return

    print("\n" + "="*60)
    print("测试日记CBT分析")
    print("="*60)

    client = ZhipuAI(api_key=api_key)

    # 模拟日记数据
    test_diary = {
        "emotions": ["焦虑", "沮丧"],
        "trigger_event": "今天考试没考好，我觉得自己很失败。",
        "intensity": 7,
        "content": "今天数学考试只考了60分，我感觉自己太笨了。看到别人都考得很好，我更加难受。我一定是最差的那个。"
    }

    prompt = f"""
你是一位专业的认知行为治疗(CBT)分析师。请分析以下日记内容：

情绪标签：{', '.join(test_diary['emotions'])}
触发事件：{test_diary['trigger_event']}
情绪强度：{test_diary['intensity']}/10
日记内容：
{test_diary['content']}

请从CBT的角度进行全面分析，返回JSON格式的结果（不要markdown代码块，只返回纯JSON）：
{{
    "overall_emotion": "主要情绪名称",
    "emotion_intensity": 0.7,
    "cognitive_distortions": [
        {{"type": "认知扭曲类型", "description": "具体说明"}}
    ],
    "core_beliefs": ["核心信念1"],
    "automatic_thoughts": ["自动化思维1"],
    "suggestions": ["建议1", "建议2"],
    "recommended_game": "推荐的CBT游戏类型"
}}
"""

    print("\n发送日记分析请求...")
    print(f"日记内容: {test_diary['content'][:50]}...")

    try:
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {
                    "role": "system",
                    "content": "你是一位专业的CBT分析师，擅长识别认知扭曲并提供建设性建议。请始终以JSON格式返回分析结果。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            stream=False,
            max_tokens=2000,
            temperature=0.3
        )

        print("\n[成功] 日记分析完成！")
        print("\n分析结果:")
        print("-" * 60)
        content = response.choices[0].message.content
        print(content)
        print("-" * 60)

        # 尝试解析JSON
        import json
        import re

        # 移除可能的markdown代码块标记
        content_clean = re.sub(r'```json\s*|\s*```', '', content).strip()

        try:
            result = json.loads(content_clean)
            print("\n[成功] JSON解析成功！")
            print(f"  - 主要情绪: {result.get('overall_emotion')}")
            print(f"  - 情绪强度: {result.get('emotion_intensity')}")
            print(f"  - 认知扭曲: {len(result.get('cognitive_distortions', []))}个")
            if result.get('cognitive_distortions'):
                for dist in result.get('cognitive_distortions', []):
                    print(f"    * {dist.get('type')}: {dist.get('description')}")
            print(f"  - 核心信念: {result.get('core_beliefs')}")
            print(f"  - 建议数量: {len(result.get('suggestions', []))}条")
            if result.get('suggestions'):
                for i, sug in enumerate(result.get('suggestions', []), 1):
                    print(f"    {i}. {sug}")
            print(f"  - 推荐游戏: {result.get('recommended_game')}")

            return result

        except json.JSONDecodeError as je:
            print(f"\n[警告] JSON解析失败: {je}")
            print("返回的内容可能不是有效的JSON格式")
            return None

    except Exception as e:
        print(f"\n[失败] 日记分析失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_stream():
    """测试流式输出"""
    api_key = os.getenv('ZHIPU_API_KEY')

    if not api_key:
        print("错误: 未找到 ZHIPU_API_KEY")
        return

    print("\n" + "="*60)
    print("测试流式输出")
    print("="*60)

    client = ZhipuAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {"role": "user", "content": "写一首关于春天的五言绝句"}
            ],
            stream=True,
            max_tokens=200,
            temperature=0.9
        )

        print("\n流式输出开始:")
        print("-" * 60)

        for chunk in response:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end='', flush=True)

        print("\n" + "-" * 60)
        print("[成功] 流式输出完成！")

    except Exception as e:
        print(f"\n[失败] 流式调用失败: {str(e)}")


if __name__ == "__main__":
    print("="*60)
    print("智谱AI ChatGLM API 测试工具")
    print("="*60)

    # 测试1: 基础调用
    print("\n[测试1] 基础调用测试")
    print("-"*60)
    test_basic()

    # 测试2: 日记分析（核心功能）
    print("\n[测试2] 日记CBT分析测试（核心功能）")
    print("-"*60)
    result = test_diary_analysis()

    # 测试3: 流式输出
    print("\n[测试3] 流式输出测试")
    print("-"*60)
    test_stream()

    print("\n" + "="*60)
    print("所有测试完成！")
    print("="*60)

    if result:
        print("\n可以开始集成到后端了！")
