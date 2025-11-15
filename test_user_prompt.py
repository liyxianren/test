# -*- coding: utf-8 -*-
"""测试用户友好版Prompt"""
import os
from dotenv import load_dotenv
from zhipuai import ZhipuAI
from prompts.chatglm_prompts import get_user_friendly_prompt, get_game_data_prompt

load_dotenv()

def test_user_friendly():
    """测试用户友好版"""
    api_key = os.getenv('ZHIPU_API_KEY')
    client = ZhipuAI(api_key=api_key)

    # 测试数据
    emotions = ["开心", "兴奋"]
    trigger_event = "今天完成了一个重要项目"
    intensity = 3
    content = "今天终于完成了这个困扰我很久的项目，感觉非常有成就感！"

    prompt = get_user_friendly_prompt(emotions, trigger_event, intensity, content)

    print("=" * 60)
    print("测试用户友好版Prompt")
    print("=" * 60)
    print(f"\nPrompt长度: {len(prompt)} 字符")
    print(f"\nPrompt内容:\n{prompt}\n")

    print("\n发送到ChatGLM...")
    try:
        response = client.chat.completions.create(
            model="glm-4.6",
            messages=[
                {"role": "system", "content": "你是一位专业的CBT分析师。"},
                {"role": "user", "content": prompt}
            ],
            stream=False,
            max_tokens=1500,
            temperature=0.8
        )

        content = response.choices[0].message.content
        print(f"\n响应长度: {len(content) if content else 0} 字符")
        print(f"\n响应内容:\n{content}\n")

        if not content or len(content) == 0:
            print("\n❌ 错误: 返回空响应!")
            return False
        else:
            print("\n✅ 成功: 用户友好版工作正常")
            return True

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_game_data():
    """测试游戏数据版"""
    api_key = os.getenv('ZHIPU_API_KEY')
    client = ZhipuAI(api_key=api_key)

    # 测试数据
    emotions = ["开心", "兴奋"]
    trigger_event = "今天完成了一个重要项目"
    intensity = 3
    content = "今天终于完成了这个困扰我很久的项目，感觉非常有成就感！"

    prompt = get_game_data_prompt(emotions, trigger_event, intensity, content)

    print("\n" + "=" * 60)
    print("测试游戏数据版Prompt")
    print("=" * 60)
    print(f"\nPrompt长度: {len(prompt)} 字符")

    print("\n发送到ChatGLM...")
    try:
        response = client.chat.completions.create(
            model="glm-4.6",
            messages=[
                {"role": "system", "content": "你是一位专业的CBT分析师。"},
                {"role": "user", "content": prompt}
            ],
            stream=False,
            max_tokens=2000,
            temperature=0.3
        )

        content = response.choices[0].message.content
        print(f"\n响应长度: {len(content) if content else 0} 字符")
        print(f"\n响应前200字符:\n{content[:200] if content else 'None'}...\n")

        if not content or len(content) == 0:
            print("\n❌ 错误: 返回空响应!")
            return False
        else:
            print("\n✅ 成功: 游戏数据版工作正常")
            return True

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ChatGLM双Prompt测试")
    print("=" * 60)

    test1 = test_user_friendly()
    test2 = test_game_data()

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"  用户友好版: {'✅ 通过' if test1 else '❌ 失败'}")
    print(f"  游戏数据版: {'✅ 通过' if test2 else '❌ 失败'}")

    if test1 and test2:
        print("\n✅ 所有测试通过!")
    else:
        print("\n❌ 有测试失败，请检查。")
