# -*- coding: utf-8 -*-
"""
Integration test for dual ChatGLM call flow
"""
import sys
import json
from routes.analysis import EmotionAnalysisService

def test_dual_call():
    print("=" * 60)
    print("Testing ChatGLM Dual Call Integration")
    print("=" * 60)

    analyzer = EmotionAnalysisService()

    if not analyzer.zhipu_client:
        print("\nWARNING: ChatGLM client not initialized")
        print("Please check ZHIPU_API_KEY in .env file")
        return False

    # Test data
    test_data = {
        "emotions": ["anxious", "frustrated"],
        "trigger_event": "Got criticized at work today",
        "intensity": 7,
        "content": "My proposal was rejected in the meeting. I feel terrible."
    }

    print(f"\nTest data:")
    print(f"  Emotions: {', '.join(test_data['emotions'])}")
    print(f"  Trigger: {test_data['trigger_event']}")
    print(f"  Intensity: {test_data['intensity']}/10")

    print("\n\nCalling analyze_with_chatglm_dual()...")
    print("-" * 60)

    try:
        user_message, game_data = analyzer.analyze_with_chatglm_dual(
            emotions=test_data['emotions'],
            trigger_event=test_data['trigger_event'],
            intensity=test_data['intensity'],
            content=test_data['content']
        )

        print("\nSUCCESS: Dual call completed!")

        # Validate results
        print("\n" + "=" * 60)
        print("Part 1: User-Friendly Message")
        print("=" * 60)
        if user_message:
            print(user_message[:200] + "..." if len(user_message) > 200 else user_message)
        else:
            print("ERROR: No user message received")
            return False

        print("\n" + "=" * 60)
        print("Part 2: Game Data")
        print("=" * 60)
        if game_data:
            # Validate required fields
            if 'game_values' not in game_data:
                print("ERROR: Missing game_values field")
                return False

            game_values = game_data['game_values']
            required_fields = [
                'mental_health_score',
                'stress_level',
                'energy_level',
                'daily_income_base',
                'income_multiplier'
            ]

            missing = [f for f in required_fields if f not in game_values]
            if missing:
                print(f"ERROR: Missing fields: {missing}")
                return False

            print("\nGame Values:")
            print(f"  Mental Health: {game_values['mental_health_score']}")
            print(f"  Stress Level: {game_values['stress_level']}")
            print(f"  Energy Level: {game_values['energy_level']}")
            print(f"  Daily Income: {game_values['daily_income_base']}")
            print(f"  Income Multiplier: {game_values['income_multiplier']}")
            print(f"  Mood Bonus: {game_values.get('mood_bonus', 0)}")
            print(f"  Growth Potential: {game_values.get('growth_potential', 0)}")

            print("\nSUCCESS: All required fields validated!")
            return True
        else:
            print("ERROR: No game data received")
            return False

    except Exception as e:
        print(f"\nERROR: Test failed - {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_fallback():
    print("\n\n" + "=" * 60)
    print("Testing Fallback Mechanism")
    print("=" * 60)

    analyzer = EmotionAnalysisService()
    original_client = analyzer.zhipu_client
    analyzer.zhipu_client = None  # Disable to test fallback

    test_data = {
        "emotions": ["happy", "satisfied"],
        "trigger_event": "Completed important project",
        "intensity": 3,
        "content": "Finally finished the project. Feeling accomplished."
    }

    print("\nUsing fallback mechanism...")

    try:
        user_message, game_data = analyzer.analyze_with_chatglm_dual(
            emotions=test_data['emotions'],
            trigger_event=test_data['trigger_event'],
            intensity=test_data['intensity'],
            content=test_data['content']
        )

        print("\nSUCCESS: Fallback mechanism works!")
        print(f"User message length: {len(user_message)} chars")
        print(f"Game values: {list(game_data.get('game_values', {}).keys())}")

        analyzer.zhipu_client = original_client
        return True

    except Exception as e:
        print(f"\nERROR: Fallback test failed - {str(e)}")
        analyzer.zhipu_client = original_client
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("CBT Diary - ChatGLM Integration Test")
    print("=" * 60)

    success1 = test_dual_call()
    success2 = test_fallback()

    print("\n\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"  Dual Call Test: {'PASS' if success1 else 'FAIL'}")
    print(f"  Fallback Test: {'PASS' if success2 else 'FAIL'}")

    if success1 and success2:
        print("\nAll tests passed! System is ready.")
        print("\nNext steps:")
        print("  1. Visit http://127.0.0.1:5000/diary/new")
        print("  2. Write and save a diary")
        print("  3. Check AI analysis and game values")
        print("  4. Click game button to view game page")
        sys.exit(0)
    else:
        print("\nSome tests failed.")
        sys.exit(1)
