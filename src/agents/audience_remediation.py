"""按受众（消费者 / 监管 / 商家）生成不同侧重的建议文案"""

from __future__ import annotations

from typing import Any, Dict, List

_AUDIENCES = frozenset({"consumer", "regulator", "merchant"})


def normalize_audience(role: str | None) -> str:
    r = (role or "consumer").strip().lower()
    return r if r in _AUDIENCES else "consumer"


def confidence_to_risk_rating(confidence: float | None) -> str:
    c = float(confidence or 0.5)
    if c >= 0.85:
        return "高"
    if c >= 0.65:
        return "中"
    return "低"


def _step(
    n: int,
    action: str,
    legal_basis: str = "",
    party: str = "",
    priority: str = "high",
) -> Dict[str, Any]:
    return {
        "step": n,
        "action": action,
        "legal_basis": legal_basis,
        "priority": priority,
        "responsible_party": party,
    }


def _template_key(violation_type: str) -> str:
    keys = [
        "不明码标价",
        "政府定价违规",
        "标价外加价",
        "误导性价格标示",
        "变相提高价格",
        "哄抬价格",
        "其他价格违法",
    ]
    return violation_type if violation_type in keys else "其他价格违法"


# ---------- 消费者：维权、证据、投诉渠道、政策认知 ----------
CONSUMER_STEPS: Dict[str, List[Dict[str, Any]]] = {
    "不明码标价": [
        _step(1, "对未标价、标价不清的商品拍摄照片或录屏，保留小票/电子订单。", "《价格法》第十三条", "您本人"),
        _step(2, "先向经营者或平台客服要求明码标价与收费说明，并留存沟通记录。", "", "您本人"),
        _step(3, "协商不成可向当地市场监管部门投诉举报（12315 平台/热线），说明时间、地点与商品信息。", "", "维权途径"),
    ],
    "政府定价违规": [
        _step(1, "保存收费票据、公示牌照片与政府定价文件查询结果（可截图政府网站）。", "《价格法》第十二条", "您本人"),
        _step(2, "向经营者索要收费依据；若超标准收费，要求其书面说明。", "", "您本人"),
        _step(3, "向价格主管部门或12315提交线索，附票据与现场照片。", "", "维权途径"),
    ],
    "标价外加价": [
        _step(1, "核对结算单与标价是否一致，对加收费用要求书面说明并拍照留存。", "《价格法》第十三条", "您本人"),
        _step(2, "拒绝支付未标明的费用或要求当场退费，并保存沟通记录。", "", "您本人"),
        _step(3, "必要时向市场监管部门举报「标价外加价」行为。", "", "维权途径"),
    ],
    "误导性价格标示": [
        _step(1, "保存商品页、促销规则、划线价/原价截图及成交记录，证明宣传内容。", "《禁止价格欺诈行为规定》第七条", "您本人"),
        _step(2, "向平台发起纠纷处理，主张虚假宣传或价格欺诈，提交证据材料。", "", "您本人"),
        _step(3, "可依法主张退货退款、赔偿损失；严重者可向市场监管部门举报。", "", "维权途径"),
    ],
    "变相提高价格": [
        _step(1, "保留商品实物、规格标签与称重/计量凭证，记录与标称不符之处。", "《价格法》第十四条", "您本人"),
        _step(2, "向经营者提出更换、补足或退费，并留存交涉记录。", "", "您本人"),
        _step(3, "涉及短斤少两、以次充好可向市场监管部门举报。", "", "维权途径"),
    ],
    "哄抬价格": [
        _step(1, "保存异常涨价页面、订单与时间节点，必要时公证或录屏。", "《价格法》第十四条", "您本人"),
        _step(2, "向平台与市场监管部门同步反映，提供囤积、散布涨价信息等线索。", "", "维权途径"),
        _step(3, "关注政府价格干预与投诉渠道，配合调查取证。", "", "维权途径"),
    ],
    "其他价格违法": [
        _step(1, "整理交易过程、价格承诺与实付金额相关证据（截图、录音、合同）。", "《价格法》", "您本人"),
        _step(2, "先与经营者协商解决；明确诉求与法律依据。", "", "您本人"),
        _step(3, "协商不成可通过12315、诉讼等途径维护权益。", "", "维权途径"),
    ],
}

# ---------- 监管：执法、取证、裁量、风险评级、下一步 ----------
REGULATOR_STEPS: Dict[str, List[Dict[str, Any]]] = {
    "不明码标价": [
        _step(1, "现场检查标价签要素（品名、规格、计价单位、价格），制作检查笔录与拍照取证。", "《价格法》第十三条", "执法人员"),
        _step(2, "责令限期改正，逾期可依法处罚；对典型问题可曝光警示。", "《行政处罚法》", "办案机构"),
        _step(3, "将同类主体纳入双随机抽查或提醒告诫名单。", "", "监管部门"),
    ],
    "政府定价违规": [
        _step(1, "比对收费与政府定价文件，调取票据与公示材料，固定超标收费证据。", "《价格法》第十二条", "执法人员"),
        _step(2, "责令退还多收价款，依法处罚并督促整改。", "", "办案机构"),
        _step(3, "对行业性、系统性问题可开展专项整治或联合检查。", "", "监管部门"),
    ],
    "标价外加价": [
        _step(1, "核查标价与结算系统，确认是否存在未标明的加收项目。", "《价格法》第十三条", "执法人员"),
        _step(2, "责令退还多收费用，依法处罚并复查整改落实情况。", "", "办案机构"),
        _step(3, "对投诉高发主体提高检查频次。", "", "监管部门"),
    ],
    "误导性价格标示": [
        _step(1, "调取成交价与「原价」依据，核查前七日或合理期间交易记录。", "《禁止价格欺诈行为规定》第七条", "执法人员"),
        _step(2, "构成欺诈的依法处罚；可采取约谈、责令改正等措施。", "", "办案机构"),
        _step(3, "对平台内经营者可同步通报平台履行管理责任。", "", "监管部门"),
    ],
    "变相提高价格": [
        _step(1, "抽样检验商品等级、计量，与标价及宣传比对。", "《价格法》第十四条", "执法人员"),
        _step(2, "违法成立的，没收违法所得并处罚款；涉嫌犯罪的移送。", "", "办案机构"),
        _step(3, "加强集贸市场、商超等重点场所巡查。", "", "监管部门"),
    ],
    "哄抬价格": [
        _step(1, "核查进销价、库存与宣传信息，排查囤积居奇、散布涨价信息等行为。", "《价格法》第十四条", "执法人员"),
        _step(2, "依法从重处罚并责令纠正；特殊时期启动应急监测。", "", "办案机构"),
        _step(3, "与发改、商务等部门建立信息共享。", "", "监管部门"),
    ],
    "其他价格违法": [
        _step(1, "根据案情固定电子与现场证据，完善证据链。", "《价格法》", "执法人员"),
        _step(2, "对照裁量基准提出处罚建议，履行告知与听证程序。", "", "办案机构"),
        _step(3, "结案后归档，必要时开展回头看。", "", "监管部门"),
    ],
}


def build_consumer_violation_advice(
    violation_type: str,
    reasoning_result: Dict[str, Any],
) -> Dict[str, Any]:
    key = _template_key(violation_type)
    steps = [dict(s) for s in CONSUMER_STEPS[key]]
    lb = reasoning_result.get("legal_basis") or ""
    if lb:
        for s in steps:
            if not s.get("legal_basis"):
                s["legal_basis"] = lb
    return {
        "has_violation": True,
        "audience": "consumer",
        "panel_title": "维权与法律指引",
        "violation_type": violation_type,
        "remediation_steps": steps,
        "generation_mode": "audience_rule_based",
        "message": "",
    }


def build_regulator_violation_advice(
    violation_type: str,
    reasoning_result: Dict[str, Any],
) -> Dict[str, Any]:
    key = _template_key(violation_type)
    steps = [dict(s) for s in REGULATOR_STEPS[key]]
    lb = reasoning_result.get("legal_basis") or ""
    if lb:
        for s in steps:
            if not s.get("legal_basis"):
                s["legal_basis"] = lb
    conf = reasoning_result.get("confidence")
    risk_rating = confidence_to_risk_rating(float(conf) if conf is not None else None)
    return {
        "has_violation": True,
        "audience": "regulator",
        "panel_title": "监管处置与下一步",
        "violation_type": violation_type,
        "remediation_steps": steps,
        "risk_rating": risk_rating,
        "supervision_focus": "建议结合本案违法事实固定证据，依法履行告知程序并视情开展行政指导或处罚。",
        "generation_mode": "audience_rule_based",
        "message": "",
    }


def build_risk_remediation(audience: str, final_result: Dict[str, Any]) -> Dict[str, Any]:
    """未构成违法但存在风险标记"""
    audience = normalize_audience(audience)
    risk_level = final_result.get("risk_level", "low")
    cats = final_result.get("risk_categories") or []
    sug = final_result.get("risk_suggestions") or []
    conf = final_result.get("confidence")
    risk_rating = confidence_to_risk_rating(float(conf) if conf is not None else None)

    base = {
        "has_violation": False,
        "has_risk_flag": True,
        "risk_level": risk_level,
        "risk_categories": cats,
        "risk_suggestions": sug,
        "audience": audience,
        "risk_rating": risk_rating,
    }

    if audience == "consumer":
        base["panel_title"] = "风险提示与自我保护"
        base["message"] = (
            "案情尚未明确构成价格违法，但存在合规瑕疵。建议您保留交易与宣传证据，关注经营者整改；"
            "若权益受损可向平台或12315咨询。"
        )
    elif audience == "regulator":
        base["panel_title"] = "监管关注与行政指导"
        base["message"] = (
            f"本案风险等级（模型）：{risk_rating}。建议采取行政指导、约谈或重点监测，并留存线索备查。"
        )
    else:
        base["panel_title"] = "合规风险提示"
        base["message"] = "未构成违规，但存在合规风险，建议关注内部标价与宣传审核。"

    return base


def build_compliant_remediation(audience: str) -> Dict[str, Any]:
    """认定合规且无风险标记"""
    audience = normalize_audience(audience)
    out: Dict[str, Any] = {
        "has_violation": False,
        "has_risk_flag": False,
        "audience": audience,
    }
    if audience == "consumer":
        out["panel_title"] = "说明"
        out["message"] = "根据当前案情描述，未发现明确的价格违法行为。若仍有疑虑，可补充事实后再次咨询或向监管部门求证。"
    elif audience == "regulator":
        out["panel_title"] = "监管意见"
        out["message"] = "未发现明显违法线索，可结案存档或作线索留存；若出现新证据可重启核查。"
        out["risk_rating"] = "低"
    else:
        out["panel_title"] = "说明"
        out["message"] = "该案例未构成违规，暂无整改要求；建议保持明码标价与宣传合规。"
    return out
