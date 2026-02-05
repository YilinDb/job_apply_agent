import asyncio
import json
import os
import platform
from pathlib import Path
from typing import Any

from browser_use import Agent, Browser, BrowserProfile, ChatAnthropic, ChatBrowserUse, ChatGoogle, ChatOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    value = _env(name)
    try:
        return int(value) if value else default
    except ValueError:
        return default


def _format_value(value) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=True, indent=2)
    return str(value)


class Settings(BaseModel):
    resume_pdf_path: Path = Field(alias="RESUME_PDF_PATH")
    apply_number: int = Field(default=1, alias="APPLY_NUMBER")
    chrome_executable_path: str | None = Field(default=None, alias="CHROME_EXECUTABLE_PATH")
    chrome_user_data_dir: str | None = Field(default=None, alias="CHROME_USER_DATA_DIR")
    chrome_profile_dir: str = Field(default="Default", alias="CHROME_PROFILE_DIR")
    llm_provider: str = Field(default="google", alias="LLM_PROVIDER")
    llm_model: str = Field(default="gemini-3-flash-preview", alias="LLM_MODEL")
    cdp_url: str | None = Field(default=None, alias="CDP_URL")

    @field_validator("resume_pdf_path")
    @classmethod
    def _resume_exists(cls, value: Path) -> Path:
        path = value.expanduser()
        if not path.exists() or not path.is_file() or path.suffix.lower() != ".pdf":
            raise FileNotFoundError(
                "RESUME_PDF_PATH is required and must point to an existing PDF file."
            )
        return path

    @field_validator("apply_number")
    @classmethod
    def _apply_min(cls, value: int) -> int:
        return max(1, value)


class ApplyInfo(BaseModel):
    LINKEDIN_PASSWORD: str = ""
    FIRST_NAME: str = ""
    LAST_NAME: str = ""
    PREFERRED_NAME: str = ""
    EMAIL: str = ""
    DATE_OF_BIRTH: str = ""
    PHONE: str = ""
    PHONE_AREA: str = ""
    LOCATION: str = ""
    ADDRESS_LINE1: str = ""
    ADDRESS_LINE2: str = ""
    ADDRESS_LINE3: str = ""
    POSTAL_CODE: str = ""
    ETHNICITY: str = ""
    WORK_AUTH_US: str = ""
    WORK_AUTH_CANADA: str = ""
    WORK_AUTH_UK: str = ""
    NEED_VISA_SPONSORSHIP: str = ""
    HAS_DISABILITY: str = ""
    IDENTIFIES_LGBTQ: str = ""
    GENDER: str = ""
    VETERAN: str = ""
    WORK_EXPERIENCE: list[Any] | dict[str, Any] | None = None
    EDUCATION: list[Any] | dict[str, Any] | None = None
    PROJECTS: list[Any] | dict[str, Any] | None = None
    LINKS: list[Any] | dict[str, Any] | None = None
    SKILLS: list[Any] | dict[str, Any] | None = None
    LANGUAGES: list[Any] | dict[str, Any] | None = None


def _build_task(apply_info: ApplyInfo, resume_path: str, apply_limit: int) -> str:
    info_lines = "\n".join(
        f"- {k}: {_format_value(v)}"
        for k, v in apply_info.model_dump(exclude_none=True).items()
    )
    return f"""
    Getting Started:
    1. Go to LinkedIn https://www.linkedin.com/jobs/collections/recommended
    2. Log in if needed and confirm you are on the jobs list page. Wait after logging in.
    3. Apply to up to {apply_limit} jobs from this collection.
    Rules:
    - Use only the provided resume and info block; do not change existing answers unless they conflict.
    - Apply to at most {apply_limit} jobs total, then stop and report how many were completed.
    - Skip any job that requires security clearance.
    - If redirected to an external site, proceed only if it is a simple form; otherwise abandon that job.
    - After clicking "Apply", wait for the modal; if it never appears, go back and try the next job.
    - If the application form is still not visible after two scrolls, go back and try the next job.
    - If an element index becomes invalid, refresh your goal and re-locate it before clicking.
    - Always clear text fields before typing.
    - For years-of-experience questions: match the job description; if unsure, use personal info; if still unsure, answer 1 year.

    Resume path: {resume_path or "[MISSING]"}

    Applicant info:
    {info_lines}
    """


def _default_chrome_paths() -> list[Path]:
    system = platform.system().lower()
    paths: list[Path] = []
    if system == "windows":
        program_files = os.environ.get("ProgramFiles", "")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", "")
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            Path(program_files) / "Google/Chrome/Application/chrome.exe",
            Path(program_files_x86) / "Google/Chrome/Application/chrome.exe",
            Path(local_app_data) / "Google/Chrome/Application/chrome.exe",
        ]
        paths.extend(candidates)
    elif system == "darwin":
        paths.extend(
            [
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                Path("/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta"),
                Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
            ]
        )
    else:
        paths.extend(
            [
                Path("/usr/bin/google-chrome"),
                Path("/usr/bin/google-chrome-stable"),
                Path("/usr/bin/chromium"),
                Path("/usr/bin/chromium-browser"),
                Path("/snap/bin/chromium"),
            ]
        )
    return paths


def _default_user_data_dir() -> Path | None:
    system = platform.system().lower()
    if system == "windows":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        return Path(local_app_data) / "Google/Chrome/User Data"
    if system == "darwin":
        return Path.home() / "Library/Application Support/Google/Chrome"
    return Path.home() / ".config/google-chrome"


def _resolve_chrome_executable(explicit_path: str | None) -> str | None:
    if explicit_path:
        path = Path(explicit_path).expanduser()
        return str(path) if path.exists() else None
    for candidate in _default_chrome_paths():
        if candidate.exists():
            return str(candidate)
    return None


def _resolve_user_data_dir(explicit_path: str | None) -> str | None:
    if explicit_path:
        path = Path(explicit_path).expanduser()
        return str(path) if path.exists() else None
    path = _default_user_data_dir()
    if path and path.exists():
        return str(path)
    return None


def _build_llm(provider: str, model: str):
    normalized = provider.strip().lower()
    if normalized in {"browser_use", "browseruse", "chatbrowseruse"}:
        return ChatBrowserUse()
    if normalized in {"google", "gemini"}:
        return ChatGoogle(model=model)
    if normalized in {"openai"}:
        return ChatOpenAI(model=model)
    if normalized in {"anthropic"}:
        return ChatAnthropic(model=model)
    raise ValueError(f"Unsupported LLM_PROVIDER '{provider}'.")


def _load_profile(path: Path) -> ApplyInfo:
    if not path.exists():
        raise FileNotFoundError(f"Profile JSON not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return ApplyInfo.model_validate(data)


async def main() -> None:
    load_dotenv()

    settings = Settings.model_validate(
        {
            "RESUME_PDF_PATH": _env("RESUME_PDF_PATH"),
            "APPLY_NUMBER": _env_int("APPLY_NUMBER", 1),
            "CHROME_EXECUTABLE_PATH": _env("CHROME_EXECUTABLE_PATH") or None,
            "CHROME_USER_DATA_DIR": _env("CHROME_USER_DATA_DIR") or None,
            "CHROME_PROFILE_DIR": _env("CHROME_PROFILE_DIR", "Default"),
            "LLM_PROVIDER": _env("LLM_PROVIDER", "google"),
            "LLM_MODEL": _env("LLM_MODEL", "gemini-3-flash-preview"),
            "CDP_URL": _env("CDP_URL") or None,
        }
    )

    profile_path = Path(_env("PROFILE_JSON_PATH", "private/profile.json")).expanduser()
    apply_info = _load_profile(profile_path)

    resume_file = settings.resume_pdf_path
    available_files = [str(resume_file)]

    chrome_exe = _resolve_chrome_executable(settings.chrome_executable_path)
    user_data_dir = _resolve_user_data_dir(settings.chrome_user_data_dir)
    profile_dir = settings.chrome_profile_dir if user_data_dir else None

    profile_kwargs: dict[str, Any] = {"headless": False, "copy_profile_to_temp": False}
    if chrome_exe:
        profile_kwargs["executable_path"] = chrome_exe
    if user_data_dir:
        profile_kwargs["user_data_dir"] = user_data_dir
    if profile_dir:
        profile_kwargs["profile_directory"] = profile_dir

    browser_profile = BrowserProfile(**profile_kwargs)
    if settings.cdp_url:
        browser = Browser(cdp_url=settings.cdp_url)
    else:
        browser = Browser(browser_profile=browser_profile)

    llm = _build_llm(settings.llm_provider, settings.llm_model)
    task = _build_task(apply_info, str(resume_file), settings.apply_number)
    agent = Agent(task=task, llm=llm, browser=browser, available_file_paths=available_files)
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
