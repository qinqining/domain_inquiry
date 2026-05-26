from src.config import ROOT_DIR
from src.deepseek_client import chat_completion
from src.domain_cache import collect_avoid_domains, format_avoid_domains_for_prompt
from src.domain_parser import parse_domain_list

PROMPT_PATH = ROOT_DIR / "prompts" / "domain_generator.txt"
COMPANY_PATH = ROOT_DIR / "context" / "company.md"
NAMING_PREFS_PATH = ROOT_DIR / "context" / "naming_prefs.md"


def load_prompt_template() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def load_company_context() -> str:
    paths = [COMPANY_PATH, ROOT_DIR / "company.md"]
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8").strip()
        if text.startswith("公司上下文已移至"):
            continue
        if text:
            return text
    return ""


def load_naming_prefs() -> str:
    if NAMING_PREFS_PATH.exists():
        return NAMING_PREFS_PATH.read_text(encoding="utf-8").strip()
    return ""


def render_prompt(business: str) -> str:
    template = load_prompt_template()
    avoid = format_avoid_domains_for_prompt()
    company = load_company_context()
    prefs = load_naming_prefs()
    company_block = company if company else "（未配置 context/company.md）"
    prefs_block = f"\n\n{prefs}" if prefs else ""
    return (
        template.replace("{{business}}", business.strip())
        .replace("{{avoid_domains}}", avoid)
        .replace("{{company_context}}", company_block + prefs_block)
    )


def generate_domains(business: str) -> list[str]:
    prompt = render_prompt(business)
    avoid_n = len(collect_avoid_domains())
    if avoid_n:
        print(
            f"[LLM-1] 避让列表 {avoid_n} 个（blocked + 缓存）",
            flush=True,
        )
    print(f"[LLM-1] 业务描述: {business.strip()}", flush=True)
    content = chat_completion(prompt, temperature=0.8, label="DeepSeek·生成")
    domains = parse_domain_list(content)
    print(f"[LLM-1] 生成完成，共 {len(domains)} 个域名", flush=True)
    return domains
