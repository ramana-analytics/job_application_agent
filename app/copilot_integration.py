import subprocess
from typing import Dict, Optional, List

# Simple catalog of supported models for the UI and metadata.
# Each entry provides: id (CLI model string), display name, level, and a price multiplier.
MODEL_CATALOG: List[Dict] = [
    {"id": "auto", "name": "Auto", "context_size": "", "capabilities": [], "multiplier": 1.0},
    {"id": "claude-haiku-4.5", "name": "Claude Haiku 4.5", "context_size": "160K", "capabilities": ["Tools", "Vision"], "multiplier": 0.33},
    {"id": "claude-sonnet-4.5", "name": "Claude Sonnet 4.5", "context_size": "160K", "capabilities": ["Tools", "Vision"], "multiplier": 1.0},
    {"id": "claude-sonnet-4.6", "name": "Claude Sonnet 4.6", "context_size": "160K", "capabilities": ["Tools", "Vision"], "multiplier": 1.0},
    {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "context_size": "173K", "capabilities": ["Tools", "Vision"], "multiplier": 1.0},
    {"id": "gemini-3-flash-preview", "name": "Gemini 3 Flash (Preview)", "context_size": "173K", "capabilities": ["Tools", "Vision"], "multiplier": 0.33},
    {"id": "gemini-3.1-pro-preview", "name": "Gemini 3.1 Pro (Preview)", "context_size": "173K", "capabilities": ["Tools", "Vision"], "multiplier": 1.0},
    {"id": "gemini-3.5-flash", "name": "Gemini 3.5 Flash", "context_size": "192K", "capabilities": ["Tools", "Vision"], "multiplier": 14.0},
    {"id": "gpt-4.1", "name": "GPT-4.1", "context_size": "128K", "capabilities": ["Tools", "Vision"], "multiplier": 0.0},
    {"id": "gpt-5-mini", "name": "GPT-5 mini", "context_size": "192K", "capabilities": ["Tools", "Vision"], "multiplier": 0.0},
    {"id": "gpt-5.2", "name": "GPT-5.2", "context_size": "192K", "capabilities": ["Tools", "Vision"], "multiplier": 1.0},
    {"id": "gpt-5.2-codex", "name": "GPT-5.2 Codex", "context_size": "400K", "capabilities": ["Tools", "Vision"], "multiplier": 1.0},
    {"id": "gpt-5.3-codex", "name": "GPT-5.3 Codex", "context_size": "400K", "capabilities": ["Tools", "Vision"], "multiplier": 1.0},
    {"id": "gpt-5.4", "name": "GPT-5.4", "context_size": "400K", "capabilities": ["Tools", "Vision"], "multiplier": 1.0},
    {"id": "gpt-5.4-mini", "name": "GPT-5.4 mini", "context_size": "400K", "capabilities": ["Tools", "Vision"], "multiplier": 0.33},
    {"id": "raptor-mini-preview", "name": "Raptor mini (Preview)", "context_size": "264K", "capabilities": ["Tools", "Vision"], "multiplier": 0.0},
]





def get_available_models() -> List[Dict]:
    """Return the model catalog (UI-friendly)."""
    return MODEL_CATALOG


def _find_model_info(model_id: str) -> Optional[Dict]:
    if not model_id:
        return None
    for m in MODEL_CATALOG:
        if m.get("id") == model_id:
            return m
    return None


COPILOT_CMD_BASE = ["copilot", "-p", "<PROMPT>", "--allow-all-tools", "-s"]


def gh_copilot_suggest_with_meta(prompt: str, max_retries: int = 2, model: str = "") -> Dict:
    """
    Execute Copilot CLI and return command metadata + output.
    Adds `model_info` to the returned metadata when available.
    """
    last_error = ""
    model = (model or "").strip()

    base_command = ["copilot", "-p", prompt, "--allow-all-tools", "-s"]
    model_command = base_command + (["--model", model] if model else [])
    command = model_command

    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=90,
            )

            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            success = result.returncode == 0 and bool(stdout)

            command_display = "copilot -p \"<prompt>\" --allow-all-tools -s"
            if model:
                command_display += f" --model {model}"

            model_info = _find_model_info(model) or {"id": model or "auto", "name": model or "auto", "level": "", "multiplier": 1.0}

            meta = {
                "command": command_display,
                "returncode": result.returncode,
                "stdout": stdout[:6000],
                "stderr": stderr[:2000],
                "attempt": attempt + 1,
                "success": success,
                "model": model or "auto",
                "model_info": model_info,
            }
            if success:
                return meta

            last_error = stderr or "Copilot returned no output"

            # Graceful fallback for older CLI versions that do not support --model
            if model and "--model" in command and (
                "unknown option" in (stderr or "").lower()
                or "unrecognized option" in (stderr or "").lower()
            ):
                command = base_command
                model = ""

        except subprocess.TimeoutExpired:
            last_error = "Copilot command timed out"
        except Exception as exc:
            last_error = str(exc)

    return {
        "command": "copilot -p \"<prompt>\" --allow-all-tools -s",
        "returncode": -1,
        "stdout": "",
        "stderr": last_error,
        "attempt": max_retries,
        "success": False,
        "model": model or "auto",
        "model_info": _find_model_info(model) or {"id": model or "auto", "name": model or "auto", "level": "", "multiplier": 1.0},
    }



def gh_copilot_suggest(prompt: str, max_retries: int = 2) -> Optional[str]:
    """
    Wrapper around Copilot CLI that returns only the generated text.
    """
    meta = gh_copilot_suggest_with_meta(prompt, max_retries=max_retries)
    if meta.get("success"):
        return meta.get("stdout", "")
    return None


def generate_resume_suggestions(job_description: str, current_resume: str) -> Optional[str]:
    """
    Generate resume improvement suggestions based on job description and resume.
    
    Args:
        job_description: The job posting text
        current_resume: The user's current resume text
    
    Returns:
        Suggested improvements or None if Copilot unavailable
    """
    prompt = f"""Analyze this job description and current resume, then suggest specific improvements to make the resume more competitive for this role:

JOB DESCRIPTION:
{job_description[:1500]}

CURRENT RESUME:
{current_resume[:1500]}

Provide 3-5 specific, actionable suggestions to improve the resume for this job. Format as a numbered list."""
    
    return gh_copilot_suggest(prompt)


def generate_cover_letter_draft(job_description: str, resume_text: str, company_name: str) -> Optional[str]:
    """
    Generate a cover letter draft based on job description and resume.
    
    Args:
        job_description: The job posting text
        resume_text: The user's resume text
        company_name: The company name
    
    Returns:
        A cover letter draft or None if Copilot unavailable
    """
    prompt = f"""Write a professional cover letter for this position at {company_name}:

JOB DESCRIPTION:
{job_description[:1500]}

CANDIDATE RESUME:
{resume_text[:1500]}

Create a 3-4 paragraph cover letter that is engaging, specific to the role, and highlights relevant experience."""
    
    return gh_copilot_suggest(prompt)
