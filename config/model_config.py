import os
import time
import re
from typing import Type, TypeVar, Optional, Any, Dict, List, Tuple
from dotenv import load_dotenv
load_dotenv()
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

T = TypeVar("T", bound=BaseModel)

def get_phase_model(phase: int = 1) -> str:
    """Returns the configured model name for a given phase."""
    load_dotenv(override=True)
    provider = os.getenv("LLM_PROVIDER", "openrouter").lower().strip()
    default_model = "gpt-4o" if provider == "openai" else "deepseek/deepseek-chat"
    if phase == 1:
        val = os.getenv("LLM_PHASE_1", default_model)
    elif phase == 3:
        val = os.getenv("LLM_PHASE_3", default_model)
    elif phase == 4:
        val = os.getenv("LLM_PHASE_4", default_model)
    else:
        val = os.getenv(f"LLM_PHASE_{phase}", default_model)
    return str(val).strip().strip('"').strip("'")

LLM_MODEL_PHASE_1_ELICITATION = get_phase_model(1)
LLM_MODEL_PHASE_3_REPAIR = get_phase_model(3)
LLM_MODEL_PHASE_4_MAINTENANCE = get_phase_model(4)

import json

def extract_and_parse_json(schema: Type[T], raw_text: str) -> T:
    """Extracts JSON object substring from raw LLM output text and validates against Pydantic schema."""
    text = str(raw_text).strip() if raw_text is not None else ""
    
    if not text:
        raise ValueError(
            "The model returned an empty response. "
            "This usually happens when the model times out, exhausts output tokens during internal reasoning, "
            "or the upstream free-tier endpoint is temporarily congested."
        )
    
    # Strip markdown code fences
    text = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```$", "", text, flags=re.MULTILINE).strip()
    
    # Extract outermost JSON object { ... }
    json_match = re.search(r"(\{.*\})", text, re.DOTALL)
    json_str = json_match.group(1).strip() if json_match else text

    # Direct validation attempt
    try:
        return schema.model_validate_json(json_str)
    except Exception:
        pass

    # Helper function to normalize domain schema keys
    def _normalize_and_validate(raw_data):
        if not isinstance(raw_data, dict):
            return None
        # Handle $defs, definitions, or outer "domain" wrappers if emitted by an LLM
        if "$defs" in raw_data and "domain_name" not in raw_data:
            defs = raw_data["$defs"]
            dom = defs.get("DomainRepresentation") or defs.get("DomainBlueprint") or defs.get("domain")
            if isinstance(dom, dict):
                raw_data = dom
        elif "definitions" in raw_data and "domain_name" not in raw_data:
            defs = raw_data["definitions"]
            dom = defs.get("DomainRepresentation") or defs.get("DomainBlueprint") or defs.get("domain")
            if isinstance(dom, dict):
                raw_data = dom
        elif "domain" in raw_data and isinstance(raw_data["domain"], dict) and "domain_name" not in raw_data:
            raw_data = raw_data["domain"]
        return schema.model_validate(raw_data)

    # 1. Fast Path: Standard Python json.loads
    try:
        data = json.loads(json_str)
        validated = _normalize_and_validate(data)
        if validated:
            return validated
    except Exception:
        pass

    # 2. Resilient Path: Professional json_repair
    # Automatically fixes unquoted keys, unclosed brackets, and trailing commas
    try:
        import json_repair
        data = json_repair.repair_json(json_str, return_objects=True)
        if isinstance(data, dict):
            validated = _normalize_and_validate(data)
            if validated:
                return validated
    except Exception:
        pass

    # 3. If both fail, raise clear diagnostic error
    snippet = text[:200] if len(text) > 200 else text
    raise ValueError(
        f"Failed to parse LLM output into schema {getattr(schema, '__name__', str(schema))}.\n"
        f"Received: {repr(snippet)}"
    )

def get_pricing_per_m() -> tuple[float, float]:
    """Returns (price_prompt_per_m, price_completion_per_m) configured directly via .env."""
    prompt_raw = os.getenv("PRICE_PROMPT_PER_M")
    comp_raw = os.getenv("PRICE_COMPLETION_PER_M")
    if prompt_raw is None or str(prompt_raw).strip() == "":
        raise RuntimeError("[ALERT] PRICE_PROMPT_PER_M is missing from your .env file! Please set it directly.")
    if comp_raw is None or str(comp_raw).strip() == "":
        raise RuntimeError("[ALERT] PRICE_COMPLETION_PER_M is missing from your .env file! Please set it directly.")
    return float(str(prompt_raw).strip()), float(str(comp_raw).strip())


PRICE_PROMPT_PER_M, PRICE_COMPLETION_PER_M = get_pricing_per_m()


def extract_telemetry_from_response(raw_resp) -> dict:
    """Extracts prompt_tokens, completion_tokens, total_tokens and estimates USD cost."""
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0

    if hasattr(raw_resp, "usage_metadata") and raw_resp.usage_metadata:
        um = raw_resp.usage_metadata
        prompt_tokens = um.get("input_tokens", 0) or um.get("prompt_tokens", 0) or 0
        completion_tokens = um.get("output_tokens", 0) or um.get("completion_tokens", 0) or 0
        total_tokens = um.get("total_tokens", 0) or (prompt_tokens + completion_tokens)
    elif hasattr(raw_resp, "response_metadata") and raw_resp.response_metadata:
        rm = raw_resp.response_metadata
        tu = rm.get("token_usage") or rm.get("usage") or {}
        if isinstance(tu, dict):
            prompt_tokens = tu.get("prompt_tokens", 0) or tu.get("input_tokens", 0) or 0
            completion_tokens = tu.get("completion_tokens", 0) or tu.get("output_tokens", 0) or 0
            total_tokens = tu.get("total_tokens", 0) or (prompt_tokens + completion_tokens)

    if total_tokens == 0:
        raw_text = str(raw_resp.content if hasattr(raw_resp, "content") else raw_resp)
        prompt_tokens = max(100, len(raw_text) // 4)
        completion_tokens = max(50, len(raw_text) // 4)
        total_tokens = prompt_tokens + completion_tokens

    # Dynamic pricing read from .env (PRICE_PROMPT_PER_M, PRICE_COMPLETION_PER_M)
    p_in, p_out = get_pricing_per_m()
    cost = (prompt_tokens * p_in / 1_000_000) + (completion_tokens * p_out / 1_000_000)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": round(cost, 6)
    }

def _get_llm_client_config(target_model: str = None) -> tuple[str, str, str, Optional[str], int]:
    """Resolves provider, model name, api_key, api_base, and max_tokens from environment."""
    load_dotenv(override=True)
    provider = os.getenv("LLM_PROVIDER", "openrouter").lower().strip()
    
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("[ALERT] OPENAI_API_KEY is missing from your .env file!")
        api_base = os.getenv("OPENAI_API_BASE", None)
        model_name = target_model or get_phase_model(1)
        max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", os.getenv("OPENROUTER_MAX_TOKENS", "8192")))
        provider_label = "OpenAI"
    else:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("[ALERT] OPENROUTER_API_KEY is missing from your .env file!")
        api_base = os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")
        model_name = target_model or get_phase_model(1)
        max_tokens = int(os.getenv("OPENROUTER_MAX_TOKENS", "8192"))
        provider_label = "OpenRouter"

    if model_name and model_name.endswith(":batch"):
        model_name = model_name[:-6]

    return provider_label, model_name, api_key, api_base, max_tokens

def invoke_structured_llm(schema: Type[T], prompt: str, target_model: str = None) -> T:
    """Invokes LLM with structured Pydantic schema validation."""
    result, _ = invoke_structured_llm_with_telemetry(schema, prompt, target_model=target_model)
    return result

def invoke_structured_llm_with_telemetry(schema: Type[T], prompt: str, target_model: str = None) -> tuple[T, dict]:
    """
    Invokes LLM (OpenAI or OpenRouter) with structured Pydantic output AND returns usage telemetry dict (tokens & estimated cost).
    Strictly invokes only the requested model without switching or falling back to other models.
    """
    provider_label, model_name, api_key, api_base, max_tokens = _get_llm_client_config(target_model)

    schema_json_hint = ""
    if hasattr(schema, "model_json_schema"):
        schema_json_hint = f"\n\nCRITICAL REQUIREMENT: Respond ONLY with a valid JSON object strictly matching this schema. Do not write markdown explanations or conversational text outside the JSON:\n{json.dumps(schema.model_json_schema())}"
    json_prompt = (prompt or "") + schema_json_hint

    max_api_retries = 5
    for attempt in range(max_api_retries):
        try:
            print(f"[LLM Provider]: Invoking {provider_label} Model '{model_name}' (max_tokens={max_tokens})...")
            llm_kwargs = {
                "model_name": model_name,
                "openai_api_key": api_key,
                "temperature": 0.0,
                "max_tokens": max_tokens,
                "timeout": 120.0,
                "max_retries": 1
            }
            if api_base:
                llm_kwargs["openai_api_base"] = api_base

            llm = ChatOpenAI(**llm_kwargs)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except Exception:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            raw_resp = llm.invoke(json_prompt)
            telemetry = extract_telemetry_from_response(raw_resp)
            raw_text = raw_resp.content if hasattr(raw_resp, "content") else str(raw_resp)

            # If content is empty, check reasoning_content, response_metadata or refusal
            if not raw_text or not raw_text.strip():
                ak = getattr(raw_resp, "additional_kwargs", {}) or {}
                rm = getattr(raw_resp, "response_metadata", {}) or {}
                finish_reason = rm.get("finish_reason")
                if ak.get("reasoning_content"):
                    raw_text = ak.get("reasoning_content")
                elif ak.get("refusal"):
                    raise RuntimeError(f"{provider_label} model '{model_name}' refused the request: {ak.get('refusal')}")
                elif finish_reason == "length":
                    raise RuntimeError(
                        f"{provider_label} model '{model_name}' exhausted max_tokens ({max_tokens}) during internal reasoning. "
                        f"Please set OPENAI_MAX_TOKENS=16384 (or OPENROUTER_MAX_TOKENS) in your .env file or choose a non-reasoning chat model."
                    )

            result = extract_and_parse_json(schema, raw_text)
            print(f"[LLM Provider]: Successfully obtained response from {provider_label} ('{model_name}').")
            return result, telemetry
        except Exception as e:
            err_msg = str(e)
            is_rate_limit = any(k in err_msg.lower() for k in ["429", "rate limit", "rate_limit", "quota"])
            is_conn_error = any(k in err_msg.lower() for k in ["connection error", "timeout", "timed out", "connection reset", "remote end closed"])
            is_parse_error = any(k in err_msg.lower() for k in ["failed to parse", "validationerror", "jsondecodeerror", "unterminated string"])
            if (is_rate_limit or is_conn_error or is_parse_error) and attempt < max_api_retries - 1:
                backoff_time = (attempt + 1) * 6
                print(f"[LLM Provider WARNING]: Transient API / parse issue ({err_msg[:70]}...). Backoff retry {attempt + 1}/{max_api_retries} in {backoff_time}s...")
                time.sleep(backoff_time)
                continue
            if is_rate_limit:
                raise RuntimeError(
                    f"[ALERT] RATE / QUOTA LIMIT REACHED for model '{model_name}' on {provider_label}! Execution aborted.\n\n"
                    f"Details: {err_msg}\n"
                    f"[FIX]: Check your {provider_label} account credits, quota or rate limits, or switch provider in your .env file!"
                )
            else:
                raise RuntimeError(f"[ALERT] {provider_label} LLM API Error for Model '{model_name}': {err_msg}")

def invoke_raw_llm_with_telemetry(prompt: str, target_model: str = None) -> tuple[str, dict]:
    """
    Invokes LLM (OpenAI or OpenRouter) for unstructured/raw string output (used by Zero-Shot, No-AST, and Unstructured-Retry baselines)
    and returns (raw_text, telemetry_dict).
    Strictly invokes only the requested model without switching or falling back to other models,
    applying the same transient network/rate-limit backoff as invoke_structured_llm_with_telemetry.
    """
    provider_label, model_name, api_key, api_base, max_tokens = _get_llm_client_config(target_model)

    max_api_retries = 5
    for attempt in range(max_api_retries):
        try:
            print(f"[LLM Provider]: Invoking {provider_label} Model '{model_name}' (max_tokens={max_tokens})...")
            llm_kwargs = {
                "model_name": model_name,
                "openai_api_key": api_key,
                "temperature": 0.0,
                "max_tokens": max_tokens,
                "timeout": 120.0,
                "max_retries": 1,
            }
            if api_base:
                llm_kwargs["openai_api_base"] = api_base

            llm = ChatOpenAI(**llm_kwargs)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except Exception:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            raw_resp = llm.invoke(prompt)
            telemetry = extract_telemetry_from_response(raw_resp)
            raw_text = raw_resp.content if hasattr(raw_resp, "content") else str(raw_resp)
            if not raw_text or not raw_text.strip():
                ak = getattr(raw_resp, "additional_kwargs", {}) or {}
                if ak.get("reasoning_content"):
                    raw_text = ak.get("reasoning_content")
                else:
                    raise ValueError("Empty response returned by upstream endpoint.")
            print(f"[LLM Provider]: Successfully obtained raw response from {provider_label} ('{model_name}').")
            return raw_text, telemetry
        except Exception as e:
            err_msg = str(e)
            is_rate_limit = any(k in err_msg.lower() for k in ["429", "rate limit", "rate_limit", "quota"])
            is_conn_error = any(k in err_msg.lower() for k in ["connection error", "timeout", "timed out", "connection reset", "remote end closed", "empty response", "peer closed", "incomplete chunked"])
            if (is_rate_limit or is_conn_error) and attempt < max_api_retries - 1:
                backoff_time = (attempt + 1) * 6
                print(f"[LLM Provider WARNING]: Transient raw API issue ({err_msg[:70]}...). Backoff retry {attempt + 1}/{max_api_retries} in {backoff_time}s...")
                time.sleep(backoff_time)
                continue
            raise RuntimeError(f"[ALERT] {provider_label} (Raw) LLM API Error for Model '{model_name}': {err_msg}")


