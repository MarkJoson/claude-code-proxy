#!/usr/bin/env python3
"""Regression tests for forwarding MCP tool-result images to the main model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server import (
    MessagesRequest,
    _normalize_openai_multimodal_blocks,
    convert_anthropic_to_litellm,
    parse_tool_result_content,
)


def test_nested_tool_result_images():
    request = MessagesRequest.model_validate({
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 1024,
        "messages": [
            {
                "role": "assistant",
                "content": [{
                    "type": "tool_use",
                    "id": "toolu_view_pdf",
                    "name": "view_pdf_page",
                    "input": {"page": 1, "mode": "compare"},
                }],
            },
            {
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": "toolu_view_pdf",
                    "content": [
                        {"type": "text", "text": "IMAGE A then IMAGE B"},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": "SOURCE_IMAGE_DATA",
                            },
                        },
                        {
                            "type": "image",
                            "mimeType": "image/jpeg",
                            "data": "OUTPUT_IMAGE_DATA",
                        },
                    ],
                }],
            },
        ],
    })

    converted = convert_anthropic_to_litellm(request)
    assert [message["role"] for message in converted["messages"]] == [
        "assistant", "tool", "user",
    ]

    tool_content = converted["messages"][1]["content"]
    assert "IMAGE A then IMAGE B" in tool_content
    assert tool_content.count("[image returned directly to the model]") == 2
    assert "SOURCE_IMAGE_DATA" not in tool_content
    assert "OUTPUT_IMAGE_DATA" not in tool_content

    user_content = converted["messages"][2]["content"]
    assert [block["type"] for block in user_content] == [
        "text", "image_url", "image_url",
    ]
    assert user_content[1]["image_url"]["url"] == (
        "data:image/png;base64,SOURCE_IMAGE_DATA"
    )
    assert user_content[2]["image_url"]["url"] == (
        "data:image/jpeg;base64,OUTPUT_IMAGE_DATA"
    )


def test_openai_sanitizer_preserves_multimodal_lists():
    content = [
        {"type": "text", "text": "inspect this image"},
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/webp",
                "data": "WEBP_DATA",
            },
        },
    ]
    normalized = _normalize_openai_multimodal_blocks(content)
    assert normalized == [
        {"type": "text", "text": "inspect this image"},
        {
            "type": "image_url",
            "image_url": {"url": "data:image/webp;base64,WEBP_DATA"},
        },
    ]
    assert parse_tool_result_content(content[1]) == (
        "[image returned directly to the model]"
    )


def main():
    test_nested_tool_result_images()
    test_openai_sanitizer_preserves_multimodal_lists()
    print("TOOL_RESULT_IMAGE_FORWARD_OK")


if __name__ == "__main__":
    main()
