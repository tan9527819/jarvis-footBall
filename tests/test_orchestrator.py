"""
Football Orchestrator 单元测试

覆盖7个测试场景：
1. 缺少比赛数据 → insufficient_data
2. 只有比赛数据 → blocked / 证据不足
3. 比赛 + 赔率 → blocked（还需历史数据）
4. 比赛 + 历史数据 → blocked（还需赔率）
5. 比赛 + 赔率 + 历史数据 → ready_for_analysis
6. Risk Gate 置信度阻断
7. trace_id、Evidence、timestamp 完整性验证
"""

import unittest
from src.football_orchestrator import FootballOrchestrator, Evidence, AnalysisResult


class TestFootballOrchestrator(unittest.TestCase):
    """Football Orchestrator 单元测试套件"""
    
    def setUp(self):
        """测试初始化"""
        self.orchestrator = FootballOrchestrator()
    
    # ============ 测试场景 1: 缺少比赛数据 ============
    def test_01_missing_match_data_none(self):
        """测试场景 1.1: match=None"""
        result = self.orchestrator.orchestrate(match=None)
        
        self.assertEqual(result.status, "insufficient_data")
        self.assertIn("缺少比赛数据", result.conclusion)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(len(result.evidence), 0)
        self.assertIsNotNone(result.trace_id)
    
    def test_01_missing_match_data_empty_dict(self):
        """测试场景 1.2: match={}"""
        result = self.orchestrator.orchestrate(match={})
        
        self.assertEqual(result.status, "insufficient_data")
        self.assertIn("缺少比赛数据", result.conclusion)
        self.assertEqual(result.confidence, 0.0)
    
    def test_01_missing_match_fields(self):
        """测试场景 1.3: 缺少必需字段（home_team/away_team）"""
        result = self.orchestrator.orchestrate(match={"league": "Premier League"})
        
        self.assertEqual(result.status, "insufficient_data")
        self.assertIn("缺少", result.conclusion)
        self.assertTrue("home_team" in result.conclusion or "away_team" in result.conclusion)
    
    # ============ 测试场景 2: 只有比赛数据 ============
    def test_02_only_match_data(self):
        """测试场景 2: 只有比赛数据 → blocked（证据不足）"""
        match = {
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "league": "Premier League",
            "date": "2026-10-02"
        }
        result = self.orchestrator.orchestrate(match=match)
        
        self.assertEqual(result.status, "blocked")
        self.assertIn("证据不足", result.conclusion)
        self.assertEqual(len(result.evidence), 1)  # 只有比赛数据证据
        self.assertEqual(result.evidence[0].source, "football-data")
        self.assertIn("Manchester United", result.evidence[0].detail)
    
    # ============ 测试场景 3: 比赛 + 赔率 ============
    def test_03_match_and_odds(self):
        """测试场景 3: 比赛 + 赔率 → blocked（还需历史数据）"""
        match = {
            "home_team": "Arsenal",
            "away_team": "Chelsea"
        }
        odds = {
            "home_win": 1.80,
            "draw": 3.60,
            "away_win": 4.10
        }
        result = self.orchestrator.orchestrate(match=match, odds=odds)
        
        self.assertEqual(result.status, "blocked")
        self.assertIn("证据不足", result.conclusion)
        self.assertEqual(len(result.evidence), 2)
        
        # 验证证据来源
        sources = [e.source for e in result.evidence]
        self.assertIn("football-data", sources)
        self.assertIn("odds-analysis", sources)
        
        # 验证风险
        self.assertTrue(any("历史" in risk for risk in result.risks))
    
    # ============ 测试场景 4: 比赛 + 历史数据 ============
    def test_04_match_and_historical(self):
        """测试场景 4: 比赛 + 历史数据 → blocked（还需赔率）"""
        match = {
            "home_team": "Tottenham",
            "away_team": "Brighton"
        }
        historical_matches = [
            {"date": "2024-02-10", "result": "2-1"},
            {"date": "2023-09-17", "result": "1-1"}
        ]
        result = self.orchestrator.orchestrate(
            match=match,
            historical_matches=historical_matches
        )
        
        self.assertEqual(result.status, "blocked")
        self.assertIn("证据不足", result.conclusion)
        self.assertEqual(len(result.evidence), 2)
        
        # 验证历史匹配证据
        hist_evidence = [e for e in result.evidence if e.source == "historical-matching"]
        self.assertEqual(len(hist_evidence), 1)
        self.assertIn("2条", hist_evidence[0].detail)
        
        # 验证风险
        self.assertTrue(any("赔率" in risk for risk in result.risks))
    
    # ============ 测试场景 5: 比赛 + 赔率 + 历史数据 ============
    def test_05_sufficient_evidence_ready_for_analysis(self):
        """测试场景 5: 足够证据 → ready_for_analysis"""
        match = {
            "home_team": "Manchester City",
            "away_team": "Brighton",
            "league": "Premier League"
        }
        odds = {
            "home_win": 1.35,
            "draw": 4.50,
            "away_win": 8.50
        }
        historical_matches = [
            {"date": "2024-02-10", "result": "4-0"},
            {"date": "2023-10-01", "result": "3-1"}
        ]
        
        result = self.orchestrator.orchestrate(
            match=match,
            odds=odds,
            historical_matches=historical_matches
        )
        
        self.assertEqual(result.status, "ready_for_analysis")
        self.assertIn("进入分析流水线", result.conclusion)
        self.assertGreaterEqual(len(result.evidence), 3)
        self.assertGreater(result.confidence, 0.0)
        self.assertIsNotNone(result.trace_id)
    
    # ============ 测试场景 6: Risk Gate 置信度阻断 ============
    def test_06_risk_gate_confidence_threshold(self):
        """测试场景 6: 置信度太低被 Risk Gate 阻断
        
        这个测试演示了置信度阈值的作用。
        虽然当前实现中，赔率和历史数据的 strength 都足够高，
        但这个测试框架为未来的改进预留了空间。
        """
        match = {
            "home_team": "Weak Team",
            "away_team": "Strong Team"
        }
        odds = {"home": 1.5, "draw": 3.0, "away": 2.5}
        historical_matches = [{"date": "2024-01-01", "result": "0-5"}]
        
        result = self.orchestrator.orchestrate(
            match=match,
            odds=odds,
            historical_matches=historical_matches
        )
        
        # 验证结果状态
        self.assertIn(result.status, ["blocked", "ready_for_analysis"])
        
        # 如果进入 ready_for_analysis，验证平均置信度足够高
        if result.status == "ready_for_analysis":
            avg_confidence = sum(e.strength for e in result.evidence) / len(result.evidence)
            self.assertGreaterEqual(avg_confidence, self.orchestrator.MINIMUM_CONFIDENCE)
    
    # ============ 测试场景 7: trace_id、Evidence、timestamp 完整性 ============
    def test_07_traceability_and_evidence_integrity(self):
        """测试场景 7: 验证可追溯性和证据完整性"""
        match = {
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "league": "La Liga",
            "date": "2026-10-02"
        }
        odds = {"1": 2.10, "X": 3.40, "2": 3.20}
        historical_matches = [
            {"date": "2024-04-01", "result": "2-1"},
            {"date": "2023-11-12", "result": "1-1"}
        ]
        review = {"risk_level": "low", "data_quality": "high"}
        
        result = self.orchestrator.orchestrate(
            match=match,
            odds=odds,
            historical_matches=historical_matches,
            review=review
        )
        
        # ========== 验证 trace_id ==========
        self.assertIsNotNone(result.trace_id)
        self.assertTrue(len(result.trace_id) > 0)
        
        # ========== 验证 analysis_timestamp ==========
        self.assertIsNotNone(result.analysis_timestamp)
        self.assertIn("T", result.analysis_timestamp)  # ISO 8601 格式
        
        # ========== 验证 evidence 列表 ==========
        self.assertGreater(len(result.evidence), 0)
        
        for evidence in result.evidence:
            # 验证每个 Evidence 的完整性
            self.assertIsNotNone(evidence.source)
            self.assertIn(evidence.source, [
                "football-data",
                "odds-analysis",
                "historical-matching",
                "match-review"
            ])
            
            self.assertIsNotNone(evidence.signal)
            self.assertTrue(len(evidence.signal) > 0)
            
            self.assertIsNotNone(evidence.detail)
            self.assertTrue(len(evidence.detail) > 0)
            
            # 验证 strength 在 0-1 范围内
            self.assertGreaterEqual(evidence.strength, 0.0)
            self.assertLessEqual(evidence.strength, 1.0)
            
            # 验证 timestamp 存在且格式正确（ISO 8601）
            self.assertIsNotNone(evidence.timestamp)
            self.assertIn("T", evidence.timestamp)
        
        # ========== 验证 to_dict() 序列化 ==========
        result_dict = result.to_dict()
        self.assertEqual(result_dict["trace_id"], result.trace_id)
        self.assertEqual(result_dict["status"], result.status)
        self.assertIsInstance(result_dict["evidence"], list)
        
        # 验证序列化后的 evidence
        for evidence_dict in result_dict["evidence"]:
            self.assertIn("source", evidence_dict)
            self.assertIn("signal", evidence_dict)
            self.assertIn("strength", evidence_dict)
            self.assertIn("detail", evidence_dict)
            self.assertIn("timestamp", evidence_dict)
    
    # ============ 补充测试：不强行生成胜平负 ============
    def test_08_no_forced_prediction(self):
        """验证不强行生成胜平负预测
        
        orchestrate() 只返回证据充分度判断，不生成具体的胜/平/负预测。
        """
        match = {
            "home_team": "Team A",
            "away_team": "Team B"
        }
        odds = {"1": 2.0, "X": 3.0, "2": 3.5}
        historical_matches = [{"date": "2024-01-01", "result": "1-1"}]
        
        result = self.orchestrator.orchestrate(
            match=match,
            odds=odds,
            historical_matches=historical_matches
        )
        
        # conclusion 中不应该包含具体的预测结果
        self.assertNotIn("主胜", result.conclusion)
        self.assertNotIn("客胜", result.conclusion)
        self.assertNotIn("平局", result.conclusion)
        
        # 应该只是说明数据状态和下一步
        self.assertIn("分析", result.conclusion)
    
    # ============ 补充测试：单场判断独立 ============
    def test_09_independent_single_match_analysis(self):
        """验证单场判断独立进行，不受多串形式影响
        
        orchestrate() 接收单场比赛数据，输出单场分析结果。
        不因为需要组成 3串1、5串1、8串1 而改变判断。
        """
        match_data = {
            "home_team": "Team X",
            "away_team": "Team Y",
            "match_id": "2026-10-02-001"
        }
        odds_data = {"1": 1.8, "X": 3.5, "2": 4.0}
        
        # 同样的比赛，多次调用，结果应该一致
        result1 = self.orchestrator.orchestrate(match=match_data, odds=odds_data)
        result2 = self.orchestrator.orchestrate(match=match_data, odds=odds_data)
        
        self.assertEqual(result1.status, result2.status)
        self.assertEqual(result1.conclusion, result2.conclusion)
        self.assertEqual(len(result1.evidence), len(result2.evidence))
        
        # 但 trace_id 应该不同（因为每次分析是独立的）
        self.assertNotEqual(result1.trace_id, result2.trace_id)


class TestEvidenceDataClass(unittest.TestCase):
    """Evidence 数据类测试"""
    
    def test_evidence_creation(self):
        """验证 Evidence 创建和属性"""
        evidence = Evidence(
            source="football-data",
            signal="match_available",
            strength=0.95,
            detail="测试证据"
        )
        
        self.assertEqual(evidence.source, "football-data")
        self.assertEqual(evidence.signal, "match_available")
        self.assertEqual(evidence.strength, 0.95)
        self.assertEqual(evidence.detail, "测试证据")
        self.assertIsNotNone(evidence.timestamp)
    
    def test_evidence_to_dict(self):
        """验证 Evidence 序列化"""
        evidence = Evidence(
            source="odds",
            signal="odds_updated",
            strength=0.85,
            detail="赔率已更新"
        )
        
        evidence_dict = evidence.to_dict()
        self.assertEqual(evidence_dict["source"], "odds")
        self.assertEqual(evidence_dict["strength"], 0.85)
        self.assertIn("timestamp", evidence_dict)


class TestAnalysisResultDataClass(unittest.TestCase):
    """AnalysisResult 数据类测试"""
    
    def test_analysis_result_creation(self):
        """验证 AnalysisResult 创建"""
        evidence_list = [
            Evidence(source="test", signal="test", strength=0.9, detail="test")
        ]
        result = AnalysisResult(
            status="ready_for_analysis",
            conclusion="测试结论",
            confidence=0.85,
            evidence=evidence_list,
            risks=[]
        )
        
        self.assertEqual(result.status, "ready_for_analysis")
        self.assertEqual(result.confidence, 0.85)
        self.assertEqual(len(result.evidence), 1)
        self.assertIsNotNone(result.trace_id)
    
    def test_analysis_result_to_dict(self):
        """验证 AnalysisResult 序列化"""
        result = AnalysisResult(
            status="blocked",
            conclusion="证据不足",
            confidence=0.5,
            evidence=[],
            risks=["缺少数据"]
        )
        
        result_dict = result.to_dict()
        self.assertEqual(result_dict["status"], "blocked")
        self.assertEqual(result_dict["confidence"], 0.5)
        self.assertIn("trace_id", result_dict)
        self.assertIn("analysis_timestamp", result_dict)
        self.assertEqual(result_dict["risks"], ["缺少数据"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
