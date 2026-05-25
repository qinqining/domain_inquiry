import json
import time
from dataclasses import dataclass
from typing import Any

from aliyunsdkcore.client import AcsClient
from aliyunsdkdomain.request.v20180129.CheckDomainRequest import CheckDomainRequest

from src.config import get_aliyun_credentials

# CheckDomain 单账号约 10 QPS，保守间隔 0.12s
DEFAULT_QPS_INTERVAL = 0.12

AVAIL_LABELS = {
    "1": "可注册",
    "0": "不可注册",
    "3": "预登记",
    "4": "可删除预订",
    "-1": "异常",
    "-2": "暂停注册",
    "-3": "黑名单",
}


@dataclass
class DomainCheckResult:
    domain: str
    avail: str
    avail_label: str
    premium: bool | None
    price: int | None
    reason: str
    raw: dict[str, Any]
    from_cache: bool = False


def _to_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"true", "1", "yes"}


def _log(message: str, *, verbose: bool) -> None:
    if verbose:
        print(message, flush=True)


def format_result_line(result: DomainCheckResult) -> str:
    premium = "" if result.premium is None else ("溢价" if result.premium else "非溢价")
    price = "" if result.price is None else f"价格={result.price}"
    extra = ", ".join(x for x in (premium, price, result.reason) if x)
    suffix = f" ({extra})" if extra else ""
    return f"{result.domain} -> {result.avail_label} [Avail={result.avail}]{suffix}"


def create_client() -> AcsClient:
    access_key_id, access_key_secret, region = get_aliyun_credentials()
    return AcsClient(access_key_id, access_key_secret, region)


def check_one_domain(
    client: AcsClient,
    domain: str,
    *,
    lang: str = "zh",
    verbose: bool = True,
) -> DomainCheckResult:
    request = CheckDomainRequest()
    request.set_accept_format("json")
    request.set_DomainName(domain)
    request.set_FeeCommand("create")
    request.set_FeeCurrency("USD")
    request.set_FeePeriod(1)
    request.set_Lang(lang)

    response_bytes = client.do_action_with_exception(request)
    payload = json.loads(response_bytes.decode("utf-8"))
    avail = str(payload.get("Avail", ""))
    result = DomainCheckResult(
        domain=domain,
        avail=avail,
        avail_label=AVAIL_LABELS.get(avail, f"未知({avail})"),
        premium=_to_bool(payload.get("Premium")),
        price=payload.get("Price"),
        reason=str(payload.get("Reason") or ""),
        raw=payload,
    )
    _log(f"  [完成] {format_result_line(result)}", verbose=verbose)
    return result


def check_domains(
    domains: list[str],
    *,
    qps_interval: float = DEFAULT_QPS_INTERVAL,
    lang: str = "zh",
    verbose: bool = True,
) -> list[DomainCheckResult]:
    total = len(domains)
    _log(f"[阿里云] 开始 CheckDomain 查询，共 {total} 个域名", verbose=verbose)
    client = create_client()
    results: list[DomainCheckResult] = []

    for index, domain in enumerate(domains, start=1):
        if index > 1 and qps_interval > 0:
            _log(f"  [等待] 限流间隔 {qps_interval}s ...", verbose=verbose)
            time.sleep(qps_interval)

        _log(f"[{index}/{total}] 正在查询: {domain}", verbose=verbose)
        try:
            result = check_one_domain(client, domain, lang=lang, verbose=verbose)
        except Exception as exc:
            _log(f"  [失败] {domain} -> {exc}", verbose=verbose)
            raise

        results.append(result)

    available = sum(1 for r in results if r.avail == "1")
    _log(
        f"[阿里云] 全部查询结束: {total} 个已请求，可注册 {available} 个",
        verbose=verbose,
    )
    return results


def dry_run_check(
    domains: list[str],
    *,
    verbose: bool = True,
) -> list[DomainCheckResult]:
    """无阿里云凭证时用于验证解析与输出流程。"""
    total = len(domains)
    _log(f"[模拟] dry-run 模式，共 {total} 个域名（不调用 API）", verbose=verbose)
    results: list[DomainCheckResult] = []
    for index, domain in enumerate(domains, start=1):
        _log(f"[{index}/{total}] 模拟查询: {domain}", verbose=verbose)
        result = DomainCheckResult(
            domain=domain,
            avail="dry-run",
            avail_label="模拟（未调用 API）",
            premium=None,
            price=None,
            reason="",
            raw={},
        )
        _log(f"  [完成] {format_result_line(result)}", verbose=verbose)
        results.append(result)
    return results
