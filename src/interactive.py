"""双击 / run.bat / run.sh 使用的简易交互。"""

from __future__ import annotations

from types import SimpleNamespace

from src.domain_cache import DEFAULT_UNAVAILABLE_TTL_DAYS
from src.final_list_format import format_final_list_item
from src.pipeline import (
    print_pipeline_summary,
    run_full_pipeline,
    run_variants_on_result,
)


def _default_check_args(**overrides) -> SimpleNamespace:
    opts = {
        "no_cache": False,
        "cache_ttl_days": DEFAULT_UNAVAILABLE_TTL_DAYS,
        "dry_run": False,
        "lang": "zh",
        "quiet": False,
        "json": False,
        "limit": 0,
    }
    opts.update(overrides)
    return SimpleNamespace(**opts)


def _prompt_line(label: str) -> str:
    print(label, flush=True)
    return input("> ").strip()


def _yes_no(question: str) -> bool:
    while True:
        answer = input(f"{question} (Y/n): ").strip().lower()
        if answer in {"", "y", "yes", "是", "好", "要"}:
            return True
        if answer in {"n", "no", "否", "不要", "不"}:
            return False
        print("请输入 Y 或直接回车表示「是」，输入 n 表示「否」。")


def run_session() -> int:
    print("=" * 50)
    print("  domain_inquiry · 域名生成与可注册查询")
    print("=" * 50)
    print(
        "一条流水线：\n"
        "  ① LLM 生成 → ② LLM 自检 → ③ 阿里云\n"
        "  → ④ [可选] 修改建议+变体 → 阿里云 → 最终 list\n"
        "\n"
        "每次运行填写当次业务方向即可（如本次钣金加工，下次可换自动化设备配件等）。\n"
    )

    session_final: list[dict] = []
    check_args = _default_check_args()

    while True:
        business = _prompt_line(
            "\n请输入本次要生成域名的业务/行业方向：\n"
            "（例如：钣金加工、自动化设备配件）"
        )
        if not business:
            print("未输入内容，已跳过本轮。")
        else:
            try:
                result = run_full_pipeline(
                    business, check_args, save_output=True, run_variants=False
                )
                print_pipeline_summary(result)

                if result.available_rows() and _yes_no(
                    "\n[步骤4·可选] 是否根据上述可注册域名，"
                    "生成修改建议与变体并再查阿里云？"
                ):
                    result = run_variants_on_result(
                        result, check_args, save_output=True
                    )
                    print_pipeline_summary(result)

                if result.final_list:
                    session_final.extend(result.final_list)
            except (ValueError, OSError) as exc:
                print(f"\n错误: {exc}", flush=True)
            except Exception as exc:
                print(f"\n执行失败: {exc}", flush=True)

        # 无论是否执行步骤4，每轮结束后都询问是否继续
        print("\n" + "-" * 50, flush=True)
        if not _yes_no("还需要继续生成域名吗？"):
            break

    if session_final:
        print("\n" + "=" * 50)
        print("【本次会话 · 最终 list · 带释义】")
        for index, item in enumerate(session_final, start=1):
            print(format_final_list_item(item, index=index), flush=True)
        print("\nlist: " + ", ".join(i["domain"] for i in session_final))
        print("=" * 50)
    else:
        print("\n本次未得到可注册域名，可换一句业务方向再试。")

    print("\n按回车键退出…", flush=True)
    try:
        input()
    except EOFError:
        pass
    return 0
