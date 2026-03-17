"""
行政处罚案例爬虫
用于从信用中国、地方市场监管局等平台采集价格违规案例
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import os
from typing import List, Dict
from pathlib import Path


class CaseCrawler:
    """行政处罚案例爬虫"""

    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir) if output_dir else Path(__file__).parent.parent.parent / "data" / "raw" / "cases"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def crawl_credit_china(self, keyword: str = "价格", max_pages: int = 5):
        """
        爬取信用中国网站

        Args:
            keyword: 搜索关键词
            max_pages: 最大爬取页数
        """
        print(f"[+] 开始爬取信用中国，关键词: {keyword}")

        cases = []

        for page in range(1, max_pages + 1):
            try:
                # 信用中国搜索接口（需要根据实际URL调整）
                url = f"https://www.creditchina.gov.cn/xinyongxinxi/list?searchType=company&page={page}&keyword={keyword}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }

                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    # 解析页面，提取案例信息
                    page_cases = self._parse_credit_china_page(response.text)
                    cases.extend(page_cases)
                    print(f"  第{page}页: 获取{len(page_cases)}条案例")
                else:
                    print(f"  第{page}页: 请求失败，状态码{response.status_code}")

                time.sleep(2)  # 礼貌爬取

            except Exception as e:
                print(f"  第{page}页: 爬取失败 - {str(e)}")

        # 保存结果
        self._save_cases(cases, "credit_china_cases.json")
        return cases

    def crawl_local_market(self, urls: List[str]):
        """
        爬取地方市场监督管理局官网

        Args:
            urls: 各地市场监管局URL列表
        """
        print(f"[+] 开始爬取地方市场监管局，共{len(urls)}个站点")

        all_cases = []

        for idx, url in enumerate(urls, 1):
            try:
                print(f"  正在爬取: {url}")
                response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)

                if response.status_code == 200:
                    cases = self._parse_local_market_page(response.text)
                    all_cases.extend(cases)
                    print(f"    获取{len(cases)}条案例")
                else:
                    print(f"    请求失败，状态码{response.status_code}")

                time.sleep(1)

            except Exception as e:
                print(f"    爬取失败 - {str(e)}")

        self._save_cases(all_cases, "local_market_cases.json")
        return all_cases

    def _parse_credit_china_page(self, html: str) -> List[Dict]:
        """解析信用中国页面"""
        soup = BeautifulSoup(html, 'html.parser')
        cases = []

        # TODO: 根据实际页面结构调整选择器
        # items = soup.find_all('div', class_='case-item')
        # for item in items:
        #     case = {
        #         'title': item.find('h3').text.strip(),
        #         'url': item.find('a')['href'],
        #         'date': item.find('span', class_='date').text.strip(),
        #         'department': item.find('span', class_='dept').text.strip(),
        #         'violation_type': self._classify_violation(item.text)
        #     }
        #     cases.append(case)

        return cases

    def _parse_local_market_page(self, html: str) -> List[Dict]:
        """解析地方市场监管局页面"""
        soup = BeautifulSoup(html, 'html.parser')
        cases = []

        # TODO: 根据实际页面结构调整选择器
        # items = soup.find_all('tr', class_='case-row')
        # for item in items:
        #     case = {
        #         'title': item.find('td', class_='title').text.strip(),
        #         'company': item.find('td', class_='company').text.strip(),
        #         'violation': item.find('td', class_='violation').text.strip(),
        #         'penalty': item.find('td', class_='penalty').text.strip(),
        #         'date': item.find('td', class_='date').text.strip()
        #     }
        #     cases.append(case)

        return cases

    def _classify_violation(self, text: str) -> str:
        """违规类型分类"""
        violation_types = {
            '虚构原价': ['虚构', '原价', '不存在', '无成交'],
            '虚假折扣': ['折扣', '优惠', '促销', '虚假'],
            '价格误导': ['误导', '比价', '划线价'],
            '要素缺失': ['未明码标价', '未标示', '要素不全']
        }

        for vtype, keywords in violation_types.items():
            if any(kw in text for kw in keywords):
                return vtype

        return '其他'

    def _save_cases(self, cases: List[Dict], filename: str):
        """保存案例到JSON文件"""
        output_path = self.output_dir / filename

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(cases, f, ensure_ascii=False, indent=2)

        print(f"[+] 已保存{len(cases)}条案例到 {output_path}")


def main():
    """主函数"""
    crawler = CaseCrawler()

    # 示例：爬取信用中国
    # cases = crawler.crawl_credit_china(keyword="价格欺诈", max_pages=3)

    # 示例：爬取地方市场监管局
    local_urls = [
        # "http://scjgj.beijing.gov.cn",  # 北京
        # "http://scjgj.sh.gov.cn",       # 上海
        # "http://amr.zj.gov.cn",        # 浙江
    ]
    # crawler.crawl_local_market(local_urls)

    # 测试：创建示例数据
    sample_cases = [
        {
            "case_id": "case_001",
            "title": "某酒店虚标划线价案",
            "company": "兰州市某酒店",
            "violation_type": "虚构原价",
            "description": "该酒店在携程平台设置的'划线价'远高于其实际成交价，涉嫌虚假价格比较",
            "penalty_amount": "50000",
            "law_reference": "《明码标价和禁止价格欺诈规定》第十六条",
            "date": "2024-05-24",
            "region": "甘肃省"
        },
        {
            "case_id": "case_002",
            "title": "某电商虚假折扣促销案",
            "company": "上海某电子商务公司",
            "violation_type": "虚假折扣",
            "description": "宣称'限时特价，5折优惠'，但实际未降低原价，通过拉高基准价实现虚假折扣",
            "penalty_amount": "30000",
            "law_reference": "《价格法》第十四条第（四）项",
            "date": "2024-04-15",
            "region": "上海市"
        }
    ]

    crawler._save_cases(sample_cases, "sample_cases.json")
    print("[+] 创建示例数据完成")


if __name__ == "__main__":
    main()
