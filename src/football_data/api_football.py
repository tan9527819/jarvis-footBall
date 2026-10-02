"""
API-Football 数据接口模块

功能：
- 获取当天和次日的足球赛事
- 处理原始 JSON 数据
- 生成标准化 CSV 数据
- 支持本地缓存和离线模式
"""

import os
import json
import csv
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pytz
from pathlib import Path


class APIFootballClient:
    """API-Football 客户端"""
    
    BASE_URL = "https://api-football-v3.p.rapidapi.com"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化客户端
        
        Args:
            api_key: API Key，如果为 None 则从环境变量 API_FOOTBALL_KEY 读取
        """
        self.api_key = api_key or os.getenv("API_FOOTBALL_KEY")
        if not self.api_key:
            raise ValueError(
                "API_FOOTBALL_KEY 未设置。请通过参数或环境变量提供。"
            )
        
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "api-football-v3.p.rapidapi.com"
        }
        self.timezone = pytz.timezone("Asia/Singapore")
    
    def _get_singapore_date(self, days_offset: int = 0) -> str:
        """
        获取新加坡时区的日期
        
        Args:
            days_offset: 天数偏移（0=今天，1=明天，-1=昨天）
        
        Returns:
            YYYY-MM-DD 格式的日期字符串
        """
        sg_time = datetime.now(self.timezone)
        target_date = sg_time + timedelta(days=days_offset)
        return target_date.strftime("%Y-%m-%d")
    
    def get_fixtures_by_date(self, date: str, league_ids: Optional[List[int]] = None) -> List[Dict]:
        """
        获取指定日期的赛事
        
        Args:
            date: YYYY-MM-DD 格式的日期
            league_ids: 联赛 ID 列表（可选），None 表示获取全部
        
        Returns:
            赛事列表
        
        Example:
            >>> client = APIFootballClient()
            >>> fixtures = client.get_fixtures_by_date("2024-01-15")
            >>> len(fixtures)
            24
        """
        params = {"date": date}
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/fixtures",
                headers=self.headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            fixtures = data.get("response", [])
            
            # 按联赛 ID 过滤
            if league_ids:
                fixtures = [
                    f for f in fixtures 
                    if f.get("league", {}).get("id") in league_ids
                ]
            
            return fixtures
            
        except requests.RequestException as e:
            print(f"❌ 获取 {date} 赛事失败: {str(e)}")
            return []
    
    def get_fixtures_today_and_tomorrow(
        self, 
        league_ids: Optional[List[int]] = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        获取当天和次日的赛事
        
        Args:
            league_ids: 联赛 ID 列表（可选）
        
        Returns:
            (今天赛事, 明天赛事)
        """
        today_date = self._get_singapore_date(0)
        tomorrow_date = self._get_singapore_date(1)
        
        print(f"📅 正在获取 {today_date} 和 {tomorrow_date} 的赛事...")
        
        today_fixtures = self.get_fixtures_by_date(today_date, league_ids)
        tomorrow_fixtures = self.get_fixtures_by_date(tomorrow_date, league_ids)
        
        print(f"✅ 获取完成: 今日 {len(today_fixtures)} 场, 明日 {len(tomorrow_fixtures)} 场")
        
        return today_fixtures, tomorrow_fixtures
    
    @staticmethod
    def normalize_fixture(fixture: Dict) -> Dict:
        """
        标准化赛事数据
        
        Args:
            fixture: 原始赛事数据
        
        Returns:
            标准化后的赛事数据
        """
        league = fixture.get("league", {})
        teams = fixture.get("teams", {})
        venue = fixture.get("fixture", {}).get("venue", {})
        
        return {
            "fixture_id": fixture.get("fixture", {}).get("id"),
            "date": fixture.get("fixture", {}).get("date"),
            "timestamp": fixture.get("fixture", {}).get("timestamp"),
            "status": fixture.get("fixture", {}).get("status", {}).get("short"),
            "league_id": league.get("id"),
            "league_name": league.get("name"),
            "league_country": league.get("country"),
            "league_season": league.get("season"),
            "home_team_id": teams.get("home", {}).get("id"),
            "home_team_name": teams.get("home", {}).get("name"),
            "away_team_id": teams.get("away", {}).get("id"),
            "away_team_name": teams.get("away", {}).get("name"),
            "venue_name": venue.get("name"),
            "venue_city": venue.get("city"),
            "score_home": fixture.get("goals", {}).get("home"),
            "score_away": fixture.get("goals", {}).get("away"),
        }
    
    @staticmethod
    def save_raw_json(
        today_fixtures: List[Dict], 
        tomorrow_fixtures: List[Dict],
        output_dir: str = "data/api_football"
    ) -> str:
        """
        保存原始 JSON 数据
        
        Args:
            today_fixtures: 今天的赛事
            tomorrow_fixtures: 明天的赛事
            output_dir: 输出目录
        
        Returns:
            保存的文件路径
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 生成时间戳文件名
        timestamp = datetime.now(pytz.timezone("Asia/Singapore")).strftime("%Y%m%d_%H%M%S")
        filename = f"{output_dir}/fixtures_{timestamp}.json"
        
        data = {
            "metadata": {
                "timestamp": timestamp,
                "timezone": "Asia/Singapore",
                "today_count": len(today_fixtures),
                "tomorrow_count": len(tomorrow_fixtures),
            },
            "today": today_fixtures,
            "tomorrow": tomorrow_fixtures,
        }
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 JSON 数据已保存: {filename}")
        return filename
    
    @staticmethod
    def save_normalized_csv(
        today_fixtures: List[Dict],
        tomorrow_fixtures: List[Dict],
        output_dir: str = "data/api_football"
    ) -> str:
        """
        保存标准化 CSV 数据
        
        Args:
            today_fixtures: 今天的赛事
            tomorrow_fixtures: 明天的赛事
            output_dir: 输出目录
        
        Returns:
            保存的文件路径
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 合并并标准化数据
        all_fixtures = today_fixtures + tomorrow_fixtures
        normalized = [APIFootballClient.normalize_fixture(f) for f in all_fixtures]
        
        # 生成时间戳文件名
        timestamp = datetime.now(pytz.timezone("Asia/Singapore")).strftime("%Y%m%d_%H%M%S")
        filename = f"{output_dir}/fixtures_{timestamp}.csv"
        
        if not normalized:
            print("⚠️ 没有赛事数据，跳过 CSV 生成")
            return filename
        
        # 写入 CSV
        with open(filename, "w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "fixture_id", "date", "timestamp", "status",
                "league_id", "league_name", "league_country", "league_season",
                "home_team_id", "home_team_name", "away_team_id", "away_team_name",
                "venue_name", "venue_city", "score_home", "score_away"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(normalized)
        
        print(f"📊 CSV 数据已保存: {filename} ({len(normalized)} 场赛事)")
        return filename


def main():
    """CLI 入口点"""
    import argparse
    
    parser = argparse.ArgumentParser(description="API-Football 数据抓取")
    parser.add_argument(
        "--api-key",
        type=str,
        help="API-Football Key (默认从环境变量 API_FOOTBALL_KEY 读取)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/api_football",
        help="输出目录"
    )
    parser.add_argument(
        "--no-json",
        action="store_true",
        help="不保存 JSON 数据"
    )
    parser.add_argument(
        "--no-csv",
        action="store_true",
        help="不保存 CSV 数据"
    )
    
    args = parser.parse_args()
    
    try:
        # 初始化客户端
        client = APIFootballClient(api_key=args.api_key)
        
        # 获取数据
        today_fixtures, tomorrow_fixtures = client.get_fixtures_today_and_tomorrow()
        
        # 保存数据
        if not args.no_json:
            client.save_raw_json(today_fixtures, tomorrow_fixtures, args.output_dir)
        
        if not args.no_csv:
            client.save_normalized_csv(today_fixtures, tomorrow_fixtures, args.output_dir)
        
        print("✨ 数据抓取完成！")
        
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
