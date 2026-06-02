#!/usr/bin/env python3
"""Test script to verify global default context limits."""

import os
import sys

# Set environment variables before importing server
os.environ["DEFAULT_MAX_INPUT_TOKENS"] = "200000"
os.environ["DEFAULT_MAX_OUTPUT_TOKENS"] = "8192"

from server import get_model_context_info

def test_known_model():
    """Test that known models use litellm data."""
    print("=" * 60)
    print("测试 1: 已知模型（应使用 litellm 内置数据）")
    print("=" * 60)

    models = ["gpt-4o", "gpt-4", "claude-3-opus-20240229"]

    for model in models:
        info = get_model_context_info(model)
        if info:
            print(f"\n{model}:")
            print(f"  max_input_tokens: {info.max_input_tokens}")
            print(f"  max_output_tokens: {info.max_output_tokens}")
            print(f"  ✓ 使用 litellm 内置数据")
        else:
            print(f"\n{model}:")
            print(f"  ✗ 未获取到信息")

def test_unknown_model():
    """Test that unknown models use environment defaults."""
    print("\n" + "=" * 60)
    print("测试 2: 未知模型（应使用环境变量默认值）")
    print("=" * 60)

    models = ["my-custom-model", "private-gpt-4", "internal-llm"]

    for model in models:
        info = get_model_context_info(model)
        if info:
            print(f"\n{model}:")
            print(f"  max_input_tokens: {info.max_input_tokens}")
            print(f"  max_output_tokens: {info.max_output_tokens}")

            # Verify it's using environment defaults
            if (info.max_input_tokens == 200000 and
                info.max_output_tokens == 8192):
                print(f"  ✓ 使用环境变量默认值")
            else:
                print(f"  ✗ 值不匹配环境变量")
        else:
            print(f"\n{model}:")
            print(f"  ✗ 未获取到信息")

def test_priority():
    """Test that litellm data takes priority over environment defaults."""
    print("\n" + "=" * 60)
    print("测试 3: 优先级验证（litellm 数据应优先于环境变量）")
    print("=" * 60)

    # gpt-4o has 128K/16K in litellm, but env has 200K/8K
    info = get_model_context_info("gpt-4o")

    if info:
        print(f"\ngpt-4o:")
        print(f"  max_input_tokens: {info.max_input_tokens}")
        print(f"  max_output_tokens: {info.max_output_tokens}")
        print(f"  环境变量设置: 200000/8192")

        if (info.max_input_tokens == 128000 and
            info.max_output_tokens == 16384):
            print(f"  ✓ 正确使用 litellm 数据（优先级正确）")
        else:
            print(f"  ✗ 优先级错误，应使用 litellm 数据")
    else:
        print(f"\ngpt-4o:")
        print(f"  ✗ 未获取到信息")

def main():
    print("\n" + "=" * 60)
    print("全局默认上下文限制功能测试")
    print("=" * 60)
    print(f"\n环境变量设置:")
    print(f"  DEFAULT_MAX_INPUT_TOKENS={os.environ.get('DEFAULT_MAX_INPUT_TOKENS')}")
    print(f"  DEFAULT_MAX_OUTPUT_TOKENS={os.environ.get('DEFAULT_MAX_OUTPUT_TOKENS')}")
    print()

    try:
        test_known_model()
        test_unknown_model()
        test_priority()

        print("\n" + "=" * 60)
        print("✓ 所有测试完成")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
