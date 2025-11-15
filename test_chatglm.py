"""
测试智谱AI ChatGLM API调用
"""
import os
from zhipuai import ZhipuAI

def test_chatglm_basic():
    """基础测试：验证API是否能正常调用"""
    # 从环境变量获取API Key，或者直接填写
    api_key = os.getenv('ZHIPU_API_KEY') or "your-api-key-here"

    if api_key == "your-api-key-here":
        print("⚠️  请先设置环境变量 ZHIPU_API_KEY 或修改代码中的 api_key")
        print("   export ZHIPU_API_KEY='你的API密钥'  # Linux/Mac")
        print("   set ZHIPU_API_KEY=你的API密钥      # Windows")
        return

    print("🔄 正在初始化智谱AI客户端...")
    client = ZhipuAI(api_key=api_key)

    print("📝 发送测试消息...")
    try:
        response = client.chat.completions.create(
            model="glm-4-flash",  # 使用免费的flash模型进行测试
            messages=[
                {"role": "user", "content": "你好，请用一句话介绍你自己"}
            ],
            stream=False,  # 先用非流式测试
            max_tokens=100,
            temperature=0.7
        )

        print("\n✅ API调用成功！")
        print(f"📊 模型: {response.model}")
        print(f"💬 回复: {response.choices[0].message.content}")
        print(f"📈 Token使用: {response.usage}")

    except Exception as e:
        print(f"\n❌ API调用失败: {str(e)}")
        print(f"   错误类型: {type(e).__name__}")


def test_chatglm_stream():
    """流式输出测试"""
    api_key = os.getenv('ZHIPU_API_KEY') or "your-api-key-here"

    if api_key == "your-api-key-here":
        print("⚠️  请先设置 ZHIPU_API_KEY 环境变量")
        return

    print("🔄 测试流式输出...")
    client = ZhipuAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {"role": "user", "content": "写一首关于春天的五言绝句"}
            ],
            stream=True,  # 启用流式输出
            max_tokens=200,
            temperature=0.9
        )

        print("\n✅ 流式输出开始：")
        print("💬 ", end='', flush=True)

        for chunk in response:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end='', flush=True)

        print("\n\n✅ 流式输出完成！")

    except Exception as e:
        print(f"\n❌ 流式调用失败: {str(e)}")


def test_chatglm_thinking():
    """深度思考模式测试（仅GLM-4支持）"""
    api_key = os.getenv('ZHIPU_API_KEY') or "your-api-key-here"

    if api_key == "your-api-key-here":
        print("⚠️  请先设置 ZHIPU_API_KEY 环境变量")
        return

    print("🔄 测试深度思考模式...")
    client = ZhipuAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model="glm-4-plus",  # 深度思考需要plus版本
            messages=[
                {"role": "user", "content": "请分析：为什么有些人容易陷入焦虑？"}
            ],
            thinking={
                "type": "enabled",  # 启用深度思考
            },
            stream=True,
            max_tokens=1000,
            temperature=0.7
        )

        print("\n✅ 深度思考模式启动：")
        print("🧠 思考过程：", end='', flush=True)

        for chunk in response:
            # 输出思考过程
            if chunk.choices[0].delta.reasoning_content:
                print(chunk.choices[0].delta.reasoning_content, end='', flush=True)

            # 输出最终回答
            if chunk.choices[0].delta.content:
                if not hasattr(test_chatglm_thinking, 'content_started'):
                    print("\n\n💬 回答内容：", end='', flush=True)
                    test_chatglm_thinking.content_started = True
                print(chunk.choices[0].delta.content, end='', flush=True)

        # 重置标志
        if hasattr(test_chatglm_thinking, 'content_started'):
            delattr(test_chatglm_thinking, 'content_started')

        print("\n\n✅ 深度思考完成！")

    except Exception as e:
        print(f"\n❌ 深度思考模式调用失败: {str(e)}")
        print("   注意：深度思考模式需要 glm-4-plus 或更高版本")


def test_diary_analysis():
    """测试日记情绪分析"""
    api_key = os.getenv('ZHIPU_API_KEY') or "your-api-key-here"

    if api_key == "your-api-key-here":
        print("⚠️  请先设置 ZHIPU_API_KEY 环境变量")
        return

    print("🔄 测试日记情绪分析...")
    client = ZhipuAI(api_key=api_key)

    # 模拟日记数据
    test_diary = {
        "emotions": ["焦虑", "沮丧"],
        "trigger_event": "今天考试没考好，我觉得自己很失败，可能永远都学不会这门课了。",
        "intensity": 7,
        "content": "今天数学考试只考了60分，我感觉自己太笨了。看到别人都考得很好，我更加难受。我一定是最差的那个，以后肯定考不上好大学。妈妈会很失望的，我让所有人失望了。"
    }

    prompt = f"""
你是一位专业的认知行为治疗(CBT)分析师。请分析以下日记内容：

**情绪标签**：{', '.join(test_diary['emotions'])}
**触发事件**：{test_diary['trigger_event']}
**情绪强度**：{test_diary['intensity']}/10
**日记内容**：
{test_diary['content']}

请从CBT的角度进行全面分析，返回JSON格式的结果（不要markdown代码块，只返回纯JSON）：
{{
    "overall_emotion": "主要情绪名称",
    "emotion_intensity": 0.7,
    "cognitive_distortions": [
        {{"type": "认知扭曲类型", "description": "具体说明"}}
    ],
    "core_beliefs": ["核心信念1", "核心信念2"],
    "automatic_thoughts": ["自动化思维1", "自动化思维2"],
    "suggestions": ["建议1", "建议2", "建议3"],
    "recommended_game": "推荐的CBT游戏类型"
}}
"""

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
            temperature=0.3  # 降低温度提高准确性
        )

        print("\n✅ 日记分析完成！")
        print("\n📊 分析结果：")
        print(response.choices[0].message.content)

        # 尝试解析JSON
        import json
        import re
        content = response.choices[0].message.content

        # 移除可能的markdown代码块标记
        content = re.sub(r'```json\s*|\s*```', '', content)

        try:
            result = json.loads(content)
            print("\n✅ JSON解析成功！")
            print(f"   主要情绪: {result.get('overall_emotion')}")
            print(f"   情绪强度: {result.get('emotion_intensity')}")
            print(f"   认知扭曲: {len(result.get('cognitive_distortions', []))}个")
            print(f"   建议数量: {len(result.get('suggestions', []))}条")
        except json.JSONDecodeError as je:
            print(f"\n⚠️  JSON解析失败: {je}")
            print("   返回的内容可能不是有效的JSON格式")

    except Exception as e:
        print(f"\n❌ 日记分析失败: {str(e)}")


if __name__ == "__main__":
    print("=" * 60)
    print("智谱AI ChatGLM API 测试工具")
    print("=" * 60)

    # 检查API Key
    api_key = os.getenv('ZHIPU_API_KEY')
    if not api_key:
        print("\n⚠️  未检测到 ZHIPU_API_KEY 环境变量")
        print("请先设置API Key：")
        print("  Windows: set ZHIPU_API_KEY=你的密钥")
        print("  Linux/Mac: export ZHIPU_API_KEY=你的密钥")
        print("\n或者直接在代码中修改 api_key 变量\n")

    # 运行测试
    print("\n" + "=" * 60)
    print("测试1: 基础调用测试")
    print("=" * 60)
    test_chatglm_basic()

    print("\n" + "=" * 60)
    print("测试2: 流式输出测试")
    print("=" * 60)
    test_chatglm_stream()

    print("\n" + "=" * 60)
    print("测试3: 日记情绪分析测试（核心功能）")
    print("=" * 60)
    test_diary_analysis()

    # 深度思考模式测试（可选，需要plus版本）
    # print("\n" + "=" * 60)
    # print("测试4: 深度思考模式测试（需要GLM-4-Plus）")
    # print("=" * 60)
    # test_chatglm_thinking()

    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)
