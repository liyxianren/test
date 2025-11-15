"""
集成测试：测试完整的双调用流程
"""
import sys
import json
from routes.analysis import EmotionAnalysisService

def test_dual_call_integration():
    """测试ChatGLM双调用集成"""
    print("=" * 60)
    print("集成测试：ChatGLM双调用流程")
    print("=" * 60)

    # 初始化分析器
    analyzer = EmotionAnalysisService()

    if not analyzer.zhipu_client:
        print("\n⚠️  警告: ChatGLM客户端未初始化")
        print("请检查 .env 文件中的 ZHIPU_API_KEY")
        return False

    # 模拟日记数据
    test_data = {
        "emotions": ["焦虑", "沮丧"],
        "trigger_event": "今天工作被批评了，觉得很挫败",
        "intensity": 7,
        "content": "今天在会议上提出的方案被领导批评了，说我准备不充分。我觉得很难过，也很焦虑。同事们都看着我，我感觉自己很丢人。可能我真的不适合这份工作。"
    }

    print(f"\n测试数据:")
    print(f"  情绪: {', '.join(test_data['emotions'])}")
    print(f"  触发事件: {test_data['trigger_event']}")
    print(f"  情绪强度: {test_data['intensity']}/10")
    print(f"  日记内容: {test_data['content'][:50]}...")

    print("\n\n开始调用 analyze_with_chatglm_dual()...")
    print("-" * 60)

    try:
        # 调用双调用方法
        user_message, game_data = analyzer.analyze_with_chatglm_dual(
            emotions=test_data['emotions'],
            trigger_event=test_data['trigger_event'],
            intensity=test_data['intensity'],
            content=test_data['content']
        )

        print("\n✅ 双调用成功！")

        # 验证返回结果
        print("\n" + "=" * 60)
        print("Part 1: 用户友好消息")
        print("=" * 60)
        if user_message:
            print(user_message[:300] + "..." if len(user_message) > 300 else user_message)
        else:
            print("❌ 未获取到用户消息")
            return False

        print("\n" + "=" * 60)
        print("Part 2: 游戏数值数据")
        print("=" * 60)
        if game_data:
            print(json.dumps(game_data, ensure_ascii=False, indent=2))

            # 验证必要字段
            required_fields = ['emotion_analysis', 'game_values']
            missing_fields = [f for f in required_fields if f not in game_data]

            if missing_fields:
                print(f"\n⚠️  警告: 缺少必要字段: {missing_fields}")
                return False

            # 验证游戏数值字段
            game_values = game_data.get('game_values', {})
            required_game_fields = [
                'mental_health_score',
                'stress_level',
                'energy_level',
                'daily_income_base',
                'income_multiplier'
            ]

            missing_game_fields = [f for f in required_game_fields if f not in game_values]
            if missing_game_fields:
                print(f"\n⚠️  警告: 游戏数值缺少字段: {missing_game_fields}")
                return False

            print("\n" + "-" * 60)
            print("游戏数值验证:")
            print(f"  ✓ 心理健康: {game_values.get('mental_health_score')}")
            print(f"  ✓ 压力值: {game_values.get('stress_level')}")
            print(f"  ✓ 精力值: {game_values.get('energy_level')}")
            print(f"  ✓ 今日收入: {game_values.get('daily_income_base')} × {game_values.get('income_multiplier')}")
            print(f"  ✓ 心情加成: {game_values.get('mood_bonus', 0)}")
            print(f"  ✓ 成长潜力: {game_values.get('growth_potential', 0)}")

            print("\n✅ 所有必要字段验证通过！")
            return True
        else:
            print("❌ 未获取到游戏数据")
            return False

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_fallback_mechanism():
    """测试降级机制"""
    print("\n\n" + "=" * 60)
    print("测试降级机制（模拟API失败）")
    print("=" * 60)

    analyzer = EmotionAnalysisService()

    # 临时禁用ChatGLM客户端来测试降级
    original_client = analyzer.zhipu_client
    analyzer.zhipu_client = None

    test_data = {
        "emotions": ["开心", "满足"],
        "trigger_event": "今天完成了一个重要项目",
        "intensity": 3,
        "content": "今天终于完成了这个项目，感觉很有成就感。"
    }

    print("\n使用降级机制生成数据...")

    try:
        user_message, game_data = analyzer.analyze_with_chatglm_dual(
            emotions=test_data['emotions'],
            trigger_event=test_data['trigger_event'],
            intensity=test_data['intensity'],
            content=test_data['content']
        )

        print("\n✅ 降级机制工作正常！")
        print(f"\n用户消息长度: {len(user_message)} 字符")
        print(f"游戏数值字段: {list(game_data.get('game_values', {}).keys())}")

        # 恢复客户端
        analyzer.zhipu_client = original_client

        return True

    except Exception as e:
        print(f"\n❌ 降级机制测试失败: {str(e)}")
        analyzer.zhipu_client = original_client
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("CBT情绪日记 - ChatGLM集成测试")
    print("=" * 60)

    # 测试1: 双调用集成测试
    success1 = test_dual_call_integration()

    # 测试2: 降级机制测试
    success2 = test_fallback_mechanism()

    # 总结
    print("\n\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"  双调用集成测试: {'✅ 通过' if success1 else '❌ 失败'}")
    print(f"  降级机制测试: {'✅ 通过' if success2 else '❌ 失败'}")

    if success1 and success2:
        print("\nAll tests passed! System is ready.")
        print("\nNext steps:")
        print("  1. Visit http://127.0.0.1:5000/diary/new")
        print("  2. Write a diary and save it")
        print("  3. Check AI analysis and game values")
        print("  4. Click the game button to view the game page")
        sys.exit(0)
    else:
        print("\nSome tests failed. Please check the error messages.")
        sys.exit(1)
