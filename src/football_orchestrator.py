from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class Evidence:
    source: str
    signal: str
    strength: float
    detail: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        self.strength = max(0.0, min(1.0, float(self.strength)))


@dataclass
class AnalysisResult:
    status: str
    conclusion: str
    confidence: float
    evidence: List[Evidence] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    trace_id: str = field(default_factory=lambda: uuid4().hex)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "evidence": [
                {
                    "source": item.source,
                    "signal": item.signal,
                    "strength": item.strength,
                    "detail": item.detail,
                    "timestamp": item.timestamp,
                }
                for item in self.evidence
            ],
            "risks": list(self.risks),
            "trace_id": self.trace_id,
        }


class FootballOrchestrator:
    """
    足球分析总控器。

    当前阶段职责：
    1. 接收比赛基础数据
    2. 收集赔率证据
    3. 收集历史相似盘证据
    4. 建立 Evidence Ledger
    5. 执行 Risk Gate
    6. 在核心证据完整后进入 ready_for_analysis

    注意：
    当前版本不负责直接预测胜平负，也不虚构外部数据。
    """

    MINIMUM_CONFIDENCE = 0.65

    REQUIRED_SOURCES = {
        "football-data",
        "odds-analysis",
        "historical-matching",
    }

    def __init__(self) -> None:
        self.evidence_ledger: List[Evidence] = []

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _add_evidence(
        self,
        source: str,
        signal: str,
        strength: float,
        detail: str = "",
    ) -> Evidence:
        evidence = Evidence(
            source=source,
            signal=signal,
            strength=strength,
            detail=detail,
            timestamp=self._timestamp(),
        )
        self.evidence_ledger.append(evidence)
        return evidence

    @staticmethod
    def _normalise_historical_matches(
        historical_matches: Optional[List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        if not historical_matches:
            return []
        return historical_matches

    def _calculate_confidence(
        self,
        evidence: List[Evidence],
    ) -> float:
        if not evidence:
            return 0.0

        core_evidence = [
            item
            for item in evidence
            if item.source in self.REQUIRED_SOURCES
        ]

        if not core_evidence:
            return 0.0

        confidence = sum(
            item.strength for item in core_evidence
        ) / len(core_evidence)

        return round(confidence, 4)

    def _risk_gate(
        self,
        evidence: List[Evidence],
        risks: List[str],
    ) -> Optional[AnalysisResult]:
        sources = {item.source for item in evidence}

        missing_sources = self.REQUIRED_SOURCES - sources

        if missing_sources:
            source_names = {
                "football-data": "比赛数据",
                "odds-analysis": "赔率数据",
                "historical-matching": "历史相似盘",
            }

            missing_text = "、".join(
                source_names.get(source, source)
                for source in sorted(missing_sources)
            )

            return AnalysisResult(
                status="blocked",
                conclusion=f"暂不推荐：证据不足，缺少{missing_text}",
                confidence=0.0,
                evidence=list(evidence),
                risks=list(risks),
            )

        confidence = self._calculate_confidence(evidence)

        if confidence < self.MINIMUM_CONFIDENCE:
            risks.append(
                f"核心证据平均强度 {confidence:.2f} "
                f"低于阈值 {self.MINIMUM_CONFIDENCE:.2f}"
            )

            return AnalysisResult(
                status="blocked",
                conclusion="暂不推荐：核心证据可信度不足",
                confidence=confidence,
                evidence=list(evidence),
                risks=list(risks),
            )

        return None

    def analyze(
        self,
        match: Optional[Dict[str, Any]],
        odds: Optional[Dict[str, Any]] = None,
        historical_matches: Optional[List[Dict[str, Any]]] = None,
        review: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        """
        执行一次完整的最小分析编排。

        核心证据：
        - football-data
        - odds-analysis
        - historical-matching

        review 为可选证据，不作为 Risk Gate 的必要条件。
        """

        # 每次分析建立新的 Evidence Ledger
        self.evidence_ledger = []

        risks: List[str] = []

        # ---------------------------------------------------------
        # 1. 比赛基础数据
        # ---------------------------------------------------------
        if not match:
            return AnalysisResult(
                status="insufficient_data",
                conclusion="暂不推荐：缺少比赛数据",
                confidence=0.0,
                evidence=[],
                risks=["缺少比赛基础数据"],
            )

        self._add_evidence(
            source="football-data",
            signal="match_data_available",
            strength=1.0,
            detail="比赛基础数据已提供",
        )

        # ---------------------------------------------------------
        # 2. 赔率数据
        # ---------------------------------------------------------
        if odds:
            self._add_evidence(
                source="odds-analysis",
                signal="odds_data_available",
                strength=0.85,
                detail="赔率数据已提供，等待进一步分析",
            )
        else:
            risks.append("缺少赔率数据")

        # ---------------------------------------------------------
        # 3. 历史相似盘
        # ---------------------------------------------------------
        historical_matches = self._normalise_historical_matches(
            historical_matches
        )

        if historical_matches:
            self._add_evidence(
                source="historical-matching",
                signal="historical_matches_available",
                strength=0.85,
                detail=(
                    f"发现 {len(historical_matches)} "
                    "条历史相似比赛记录"
                ),
            )
        else:
            risks.append("缺少历史相似盘匹配结果")

        # ---------------------------------------------------------
        # 4. 赛后复盘（可选）
        # ---------------------------------------------------------
        if review:
            self._add_evidence(
                source="match-review",
                signal="review_available",
                strength=0.75,
                detail="赛后复盘数据已提供",
            )

        # ---------------------------------------------------------
        # 5. Risk Gate
        # ---------------------------------------------------------
        blocked_result = self._risk_gate(
            evidence=list(self.evidence_ledger),
            risks=risks,
        )

        if blocked_result is not None:
            return blocked_result

        # ---------------------------------------------------------
        # 6. 核心证据完整
        # ---------------------------------------------------------
        confidence = self._calculate_confidence(
            self.evidence_ledger
        )

        return AnalysisResult(
            status="ready_for_analysis",
            conclusion=(
                "核心证据完整，允许进入下一阶段分析；"
                "当前不直接生成胜平负结论"
            ),
            confidence=confidence,
            evidence=list(self.evidence_ledger),
            risks=risks,
        )

    def orchestrate(
        self,
        match: Optional[Dict[str, Any]],
        odds: Optional[Dict[str, Any]] = None,
        historical_matches: Optional[List[Dict[str, Any]]] = None,
        review: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        """
        analyze() 的统一入口。
        """

        return self.analyze(
            match=match,
            odds=odds,
            historical_matches=historical_matches,
            review=review,
        )


def analyze_match(
    match: Optional[Dict[str, Any]],
    odds: Optional[Dict[str, Any]] = None,
    historical_matches: Optional[List[Dict[str, Any]]] = None,
    review: Optional[Dict[str, Any]] = None,
) -> AnalysisResult:
    """
    便捷函数，供其他模块调用。
    """

    orchestrator = FootballOrchestrator()

    return orchestrator.analyze(
        match=match,
        odds=odds,
        historical_matches=historical_matches,
        review=review,
    )


if __name__ == "__main__":
    orchestrator = FootballOrchestrator()

    result = orchestrator.analyze(
        match={
            "home": "Home",
            "away": "Away",
        },
        odds={
            "available": True,
        },
        historical_matches=[
            {
                "home": "Historical Home",
                "away": "Historical Away",
            }
        ],
    )

    print(result.to_dict())