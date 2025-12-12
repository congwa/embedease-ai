"""models.dev API 集成

在应用启动时拉取 https://models.dev/api.json，
将模型能力数据转换为 LangChain profile 格式，并与 .env 手动配置合并。

数据结构（以 siliconflow 为例）：
{
  "siliconflow": {
    "models": {
      "moonshotai-kimi-k2-instruct": {
        "name": "moonshotai/Kimi-K2-Instruct",
        "reasoning": false,
        "tool_call": true,
        "structured_output": true,
        "limit": {"context": 131000, "output": 131000},
        "modalities": {"input": ["text"], "output": ["text"]}
      }
    }
  }
}

合并规则：models.dev 作为基础，.env JSON 作为强覆盖（env 优先）。
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger("models_dev")

# 模块级缓存
_cached_profiles: dict[str, dict[str, Any]] | None = None
_cache_timestamp: float = 0.0


def _convert_model_data_to_profile(model_data: dict[str, Any]) -> dict[str, Any]:
    """将 models.dev 的模型数据转换为 LangChain profile 格式。

    映射关系：
    - reasoning -> reasoning_output
    - tool_call -> tool_calling
    - structured_output -> structured_output
    - limit.context -> max_input_tokens
    - limit.output -> max_output_tokens
    - modalities.input 包含 "image" -> image_inputs
    - modalities.input 包含 "audio" -> audio_inputs
    - modalities.input 包含 "video" -> video_inputs
    - modalities.output 包含 "image" -> image_outputs
    """
    limit = model_data.get("limit") or {}
    modalities = model_data.get("modalities") or {}
    input_modalities = modalities.get("input") or []
    output_modalities = modalities.get("output") or []

    profile: dict[str, Any] = {}

    # Token 限制
    if limit.get("context") is not None:
        profile["max_input_tokens"] = limit["context"]
    if limit.get("output") is not None:
        profile["max_output_tokens"] = limit["output"]

    # 能力标志
    if model_data.get("reasoning") is not None:
        profile["reasoning_output"] = bool(model_data["reasoning"])
    if model_data.get("tool_call") is not None:
        profile["tool_calling"] = bool(model_data["tool_call"])
    if model_data.get("structured_output") is not None:
        profile["structured_output"] = bool(model_data["structured_output"])

    # 输入模态
    profile["image_inputs"] = "image" in input_modalities
    profile["audio_inputs"] = "audio" in input_modalities
    profile["video_inputs"] = "video" in input_modalities

    # 输出模态
    profile["image_outputs"] = "image" in output_modalities
    profile["audio_outputs"] = "audio" in output_modalities
    profile["video_outputs"] = "video" in output_modalities

    return profile


def fetch_models_dev_profiles(
    api_url: str,
    provider_id: str,
    timeout_seconds: float = 10.0,
) -> dict[str, dict[str, Any]]:
    """从 models.dev API 拉取指定 provider 的模型 profiles。

    Args:
        api_url: API URL，默认 https://models.dev/api.json
        provider_id: provider ID，如 "siliconflow"
        timeout_seconds: 请求超时时间

    Returns:
        dict: key 为模型 name（如 "moonshotai/Kimi-K2-Instruct"），value 为 profile dict
              失败时返回空 dict
    """
    logger.info(
        "开始拉取 models.dev 配置",
        api_url=api_url,
        provider_id=provider_id,
    )

    try:
        response = httpx.get(api_url, timeout=timeout_seconds)
        response.raise_for_status()
    except httpx.TimeoutException:
        logger.warning("models.dev 请求超时", api_url=api_url, timeout=timeout_seconds)
        return {}
    except httpx.HTTPStatusError as e:
        logger.warning(
            "models.dev 请求失败",
            api_url=api_url,
            status_code=e.response.status_code,
        )
        return {}
    except httpx.RequestError as e:
        logger.warning("models.dev 网络错误", api_url=api_url, error=str(e))
        return {}

    try:
        all_data = response.json()
    except Exception as e:
        logger.warning("models.dev 响应解析失败", error=str(e))
        return {}

    if not isinstance(all_data, dict):
        logger.warning("models.dev 响应格式错误：期望 dict")
        return {}

    # 提取指定 provider 的数据
    provider_data = all_data.get(provider_id)
    if not isinstance(provider_data, dict):
        logger.warning(
            "models.dev 未找到 provider",
            provider_id=provider_id,
            available_providers=list(all_data.keys())[:10],
        )
        return {}

    models = provider_data.get("models")
    if not isinstance(models, dict):
        logger.warning("models.dev provider 下无 models 字段", provider_id=provider_id)
        return {}

    # 转换为 profiles，以 model.name 为 key（小写）
    profiles: dict[str, dict[str, Any]] = {}
    for model_id, model_data in models.items():
        if not isinstance(model_data, dict):
            continue
        model_name = model_data.get("name")
        if not isinstance(model_name, str) or not model_name.strip():
            continue

        profile = _convert_model_data_to_profile(model_data)
        # 用 name 字段作为 key，并转小写（与 SILICONFLOW_CHAT_MODEL 匹配时统一小写）
        profiles[model_name.strip().lower()] = profile

    logger.info(
        "models.dev 配置拉取成功",
        provider_id=provider_id,
        model_count=len(profiles),
    )

    return profiles


def get_model_profile(
    model_name: str,
    *,
    api_url: str = "https://models.dev/api.json",
    provider_id: str = "siliconflow",
    timeout_seconds: float = 10.0,
    cache_ttl_seconds: float = 86400.0,
    env_profiles: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """获取指定模型的最终 profile（models.dev + .env 合并）。

    合并规则：models.dev 作为基础，env_profiles 作为强覆盖（env 优先）。

    Args:
        model_name: 模型名称，如 "moonshotai/Kimi-K2-Instruct"
        api_url: models.dev API URL
        provider_id: provider ID
        timeout_seconds: 请求超时
        cache_ttl_seconds: 缓存 TTL（秒），0 表示不缓存
        env_profiles: 从 .env 解析的 profiles（会覆盖 models.dev）

    Returns:
        dict: 最终合并后的 profile，可能为空 dict
    """
    global _cached_profiles, _cache_timestamp

    model_key = model_name.strip().lower()
    env_profiles = env_profiles or {}

    # 检查缓存
    now = time.time()
    if (
        _cached_profiles is not None
        and cache_ttl_seconds > 0
        and (now - _cache_timestamp) < cache_ttl_seconds
    ):
        logger.debug("使用缓存的 models.dev 配置")
    else:
        # 拉取并缓存
        _cached_profiles = fetch_models_dev_profiles(
            api_url=api_url,
            provider_id=provider_id,
            timeout_seconds=timeout_seconds,
        )
        _cache_timestamp = now

    # 从 models.dev 获取基础 profile
    base_profile = (_cached_profiles or {}).get(model_key, {})

    # 从 .env 获取覆盖 profile
    env_override = env_profiles.get(model_key, {})

    # 合并：env 覆盖 models.dev
    final_profile = {**base_profile, **env_override}

    # 打印最终 profile 到日志
    logger.info(
        "模型 profile 解析完成",
        model_name=model_name,
        from_models_dev=bool(base_profile),
        from_env=bool(env_override),
        final_profile=final_profile,
    )

    return final_profile

