"""
Football Orchestrator - 足球分析总控系统

功能：
- 编排数据流：比赛 → 赔率 → 历史 → AI → 复盘
- 建立 Evidence Ledger（证据账本），记录每条证据来源
- 实现 Risk Gate（风险门控），拦截不足证据
- 输出可追溯的分析结果
- 防止为了凑推荐而制造证据

核心原则：
- 缺少核心证据 → blocked（暂不推荐）
- 每条结论都要有证据支撑
- 单场判断独立进行，不受其他因素影响
"""

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class Evidence:
    """证据数据结构"""
    source: str              # 数据来源 (match/odds/historical_matching/football-ai/match-review)
    signal: str              # 信号类型 (e.g., match_data_available, odds_available)
    strength: float          # 证据强度 (0.0-1.0)
    detail: str              # 详细说明
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source": self.source,
            "signal": self.signal,
            "strength": self.strength,
            "detail": self.detail,
            "timestamp": self.timestamp,
        }


@dataclass
class AnalysisResult:
    """分析结果数据结构"""
    status: str              # 状态: insufficient_data, blocked, ready_for_analysis, completed
    conclusion: str          # 最终结论
    confidence: float        # 置信度 (0.0-1.0)
    evidence: List[Evidence] = field(default_factory=list)
    risks: List[str]         = field(default_factory=list)
    trace_id: str            = field(default_factory=lambda: str(uuid.uuid4()))
    analysis_timestamp: str  = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "status": self.status,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "evidence": [e.to_dict() for e in self.evidence],
            "risks": self.risks,
            "trace_id": self.trace_id,
            "analysis_timestamp": self.analysis_timestamp,
        }


class FootballOrchestrator:
    """足球分析流程总控器"""
    
    # Risk Gate 阈值
    MINIMUM_EVIDENCE_COUNT = 2           # 最少证据数
    MINIMUM_CONFIDENCE = 0.65            # 最小置信度阈值
    
    def orchestrate(
        self,
        match: Optional[Dict[str, Any]] = None,
        odds: Optional[Dict[str, Any]] = None,
        historical_matches: Optional[List[Dict[str, Any]]] = None,
        review: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        """
        编排足球分析流程
        
        Args:
            match: 比赛基本数据 {home_team, away_team, match_date, league, ...}
            odds: 赔率数据 {open_odds, current_odds, ...}
            historical_matches: 历史相似比赛列表
            review: 复盘数据 {risk_flags, ...}
        
        Returns:
            AnalysisResult: 分析结果，包含证据链和风险评估
        """
        evidence: List[Evidence] = []
        risks: List[str] = []
        
        # ============ 步骤 1: 比赛数据验证 ============
        if not match or not isinstance(match, dict) or not match:
            return AnalysisResult(
                status="insufficient_data",
                conclusion="暂不推荐：缺少比赛数据",
                confidence=0.0,
                evidence=evidence,
                risks=["缺少比赛基础数据"],
            )
        
        # 验证比赛必需字段
        required_match_fields = ["home_team", "away_team"]
        missing_fields = [f for f in required_match_fields if f not in match]
        
        if missing_fields:
            return AnalysisResult(
                status="insufficient_data",
                conclusion=f"暂不推荐：比赛数据不完整，缺少 {missing_fields}",
                confidence=0.0,
                evidence=evidence,
                risks=[f"比赛数据不完整：{missing_fields}"],
            )
        
        # 记录比赛数据证据
        evidence.append(
            Evidence(
                source="football-data",
                signal="match_data_available",
                strength=1.0,
                detail=f"比赛数据已提供：{match.get('home_team')} vs {match.get('away_team')}",
            )
        )
        
        # ============ 步骤 2: 赔率数据分析 ============
        if odds and isinstance(odds, dict) and odds:
            evidence.append(
                Evidence(
                    source="odds-analysis",
                    signal="odds_available",
                    strength=0.8,
                    detail=f"赔率数据已提供：{list(odds.keys())}",
                )
            )
        else:
            risks.append("缺少赔率数据：无法进行赔率分析")
        
        # ============ 步骤 3: 历史相似盘匹配 ============
        if historical_matches and isinstance(historical_matches, list) and len(historical_matches) > 0:
            evidence.append(
                Evidence(
                    source="historical-matching",
                    signal="historical_matches_found",
                    strength=0.75,
                    detail=f"发现 {len(historical_matches)} 条历史相似记录",
                )
            )
        else:
            risks.append("暂无历史相似盘匹配结果")
        
        # ============ 步骤 4: 复盘数据检查 ============
        if review and isinstance(review, dict) and review:
            evidence.append(
                Evidence(
                    source="match-review",
                    signal="review_data_available",
                    strength=0.7,
                    detail=f"复盘数据已提供：{list(review.keys())}",
                )
            )
        
        # ============ 步骤 5: Risk Gate - 风险门控 ============
        # 门槛 1: 最小证据数
        if len(evidence) < self.MINIMUM_EVIDENCE_COUNT:
            return AnalysisResult(
                status="blocked",
                conclusion="暂不推荐：证据不足",
                confidence=0.0,
                evidence=evidence,
                risks=risks + ["证据数 < 最低要求（2条）"],
            )
        
        # 门槛 2: 平均置信度
        avg_confidence = sum(e.strength for e in evidence) / len(evidence) if evidence else 0.0
        if avg_confidence < self.MINIMUM_CONFIDENCE:
            return AnalysisResult(
                status="blocked",
                conclusion="暂不推荐：证据不足",
                confidence=avg_confidence,
                evidence=evidence,
                risks=risks + [f"平均置信度 {avg_confidence:.2f} < {self.MINIMUM_CONFIDENCE}"],
            )
        
        # ============ 步骤 6: 输出可进行后续分析的状态 ============
        return AnalysisResult(
            status="ready_for_analysis",
            conclusion="数据已进入分析流水线，等待进一步计算（赔率变化、历史趋势、AI 预测、风险复盘）",
            confidence=avg_confidence,
            evidence=evidence,
            risks=risks,
        )


def main():
    """命令行测试入口"""
    orchestrator = FootballOrchestrator()
    
    # 测试 1: 空数据
    print("=" * 60)
    print("测试 1: 空数据")
    result = orchestrator.orchestrate()
    print(f"Status: {result.status}")
    print(f"Conclusion: {result.conclusion}")
    print()
    
    # 测试 2: 只有比赛数据
    print("=" * 60)
    print("测试 2: 只有比赛数据")
    result = orchestrator.orchestrate(
        match={"home_team": "Home", "away_team": "Away"}
    )
    print(f"Status: {result.status}")
    print(f"Conclusion: {result.conclusion}")
    print(f"Evidence count: {len(result.evidence)}")
    print()
    
    # 测试 3: 比赛 + 赔率
    print("=" * 60)
    print("测试 3: 比赛 + 赔率")
    result = orchestrator.orchestrate(
        match={"home_team": "Home", "away_team": "Away"},
        odds={"open": 1.5, "current": 1.45}
    )
    print(f"Status: {result.status}")
    print(f"Conclusion: {result.conclusion}")
    print(f"Evidence count: {len(result.evidence)}")
    print()
    
    # 测试 4: 比赛 + 赔率 + 历史
    print("=" * 60)
    print("测试 4: 比赛 + 赔率 + 历史数据")
    result = orchestrator.orchestrate(
        match={"home_team": "Home", "away_team": "Away"},
        odds={"open": 1.5, "current": 1.45},
        historical_matches=[{"date": "2024-01-01", "result": "1-0"}]
    )
    print(f"Status: {result.status}")
    print(f"Conclusion: {result.conclusion}")
    print(f"Evidence count: {len(result.evidence)}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Risks: {result.risks}")
    print(f"Trace ID: {result.trace_id}")


if __name__ == "__main__":
    main()
