import logging
from enum import Enum
import boto3
from botocore.config import Config

from shared import log

config = Config(
    retries=dict(
        max_attempts=3,
        mode='adaptive'
    )
)
bedrock = boto3.client("bedrock-runtime", config=config)


class Model(Enum):
    """Bedrock models"""
    NOVA_PRO_V1 = "us.amazon.nova-pro-v1:0"
    CLAUDE_3_5_HAIKU_v1 = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    CLAUDE_3_5_SONNET_V2 = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    CLAUDE_3_7_SONNET_V1 = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"


def generate_message(
    messages,
    model_id=Model.CLAUDE_3_5_HAIKU_v1.value,
    max_tokens=4096,
    temperature=0.0,
    top_p=0.999,
    system_prompt="",
):
    """Generates a message using Bedrock"""

    response = converse(
        messages,
        model_id,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        system_prompt=system_prompt,
    )

    stop_reason = response["stopReason"]
    if stop_reason != "end_turn":
        raise Exception(
            f"invalid stopReason returned from model: {stop_reason}")

    return response["output"]["message"]["content"][0]["text"]


def converse(
    messages,
    model_id,
    max_tokens=4096,
    temperature=0.0,
    top_p=0.999,
    system_prompt="",
    tool_config=None,
):
    """Invoke the bedrock converse API"""

    logging.info(f"bedrock.converse() using {model_id}")

    request = {
        "modelId": model_id,
        "messages": messages,
        "inferenceConfig": {
            "maxTokens": max_tokens,
            "temperature": temperature,
            "topP": top_p,
        },
    }
    if system_prompt != "":
        request["system"] = [{'text': system_prompt}]

    if tool_config is not None:
        request["toolConfig"] = tool_config

    response = bedrock.converse(**request)

    log.llm(request, response)

    return response
