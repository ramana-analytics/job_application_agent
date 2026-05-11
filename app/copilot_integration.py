import subprocess
from typing import Dict, Optional

COPILOT_CMD_BASE = ["copilot", "-p", "<PROMPT>", "--allow-all-tools", "-s"]


def gh_copilot_suggest_with_meta(prompt: str, max_retries: int = 2, model: str = "") -> Dict:
    """
    Execute Copilot CLI and return command metadata + output.
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

            meta = {
                "command": command_display,
                "returncode": result.returncode,
                "stdout": stdout[:6000],
                "stderr": stderr[:2000],
                "attempt": attempt + 1,
                "success": success,
                "model": model or "auto",
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
    Generate resume improvement suggestions based on job description.
    
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
