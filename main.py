import os
import feedparser
from bs4 import BeautifulSoup
import requests
from datetime import datetime
from notion_client import Client

# 환경 변수에서 노션 설정 불러오기
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

notion = Client(auth=NOTION_API_KEY)

# 🔍 수집할 키워드 설정 (원하시는 키워드로 변경 가능)
KEYWORD = "알뜰폰"

def save_to_notion(title, link, source):
    """노션 데이터베이스에 항목 추가"""
    try:
        # 중복 등록 방지 (이미 같은 링크가 있는지 확인)
        existing = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={"property": "링크", "url": {"equals": link}}
        )
        if existing["results"]:
            print(f"이미 존재하는 항목 스킵: {title}")
            return

        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "제목": {
                    "title": [{"text": {"content": title}}]
                },
                "링크": {
                    "url": link
                },
                "출처": {
                    "select": {"name": source}
                },
                "수집일시": {
                    "date": {"start": datetime.now().isoformat()}
                }
            }
        )
        print(f"[{source}] 노션 저장 성공: {title}")
    except Exception as e:
        print(f"[{source}] 노션 저장 실패: {e}")

def crawl_google_news(keyword):
    """구글 뉴스 RSS 크롤링"""
    print(f"구글 뉴스 수집 중... (키워드: {keyword})")
    url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)
    
    for entry in feed.entries[:5]:  # 상위 5개만 수집
        save_to_notion(entry.title, entry.link, "구글뉴스")

def crawl_naver_news(keyword):
    """네이버 뉴스 RSS 크롤링 (네이버 오픈 API 대신 RSS 우회 활용)"""
    print(f"네이버 뉴스 수집 중... (키워드: {keyword})")
    # 네이버 뉴스 검색 RSS 주소 활용
    url = f"https://news.naver.com/main/search/search.naver?query={keyword}&s_date=&e_date=&ie=utf8&sm=tab_hty&where=headline"
    # 네이버는 구조가 복잡할 수 있으므로 구글 뉴스와 유사한 방식으로 수집하거나 Open API 대체 가능
    # 예시로 네이버 뉴스 검색 페이지 파싱 방식 적용
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 네이버 뉴스 헤드라인/검색 결과 구조에 맞춰 추출
        items = soup.select('.list_title') # 구조 변경에 따라 다를 수 있음
        for item in items[:5]:
            title = item.get_text().strip()
            link = item.get('href')
            if title and link:
                save_to_notion(title, link, "네이버뉴스")
    except Exception as e:
        print(f"네이버 뉴스 크롤링 에러: {e}")

def crawl_public_portal(keyword):
    """예시: 공공기관 홈페이지(예: 공공데이터포털 또는 특정 지자체/부처 게시판) 크롤링 
       * 대상 공공기관의 실제 HTML 구조에 맞춰 CSS Selector를 수정해야 합니다.
    """
    print(f"공공기관 홈페이지 수집 중... (키워드: {keyword})")
    # 아래 주소는 예시용이며, 원하는 공공기관 공지사항 URL로 변경하세요.
    target_url = f"https://www.korea.kr/news/policyNewsList.do?searchWord={keyword}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        res = requests.get(target_url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 대한민국 정책브리핑(korea.kr) 등 일반적인 게시판 형태의 목록 태그 셀렉터 예시
        articles = soup.select('.board-list li, .item-list li, .tit') 
        
        count = 0
        for article in articles:
            if count >= 5: break
            title_tag = article.select_one('a')
            if title_tag:
                title = title_tag.get_text().strip()
                link = title_tag.get('href')
                if link and not link.startswith('http'):
                    link = "https://www.korea.kr" + link # 상대 주소일 경우 보정
                
                if keyword in title:
                    save_to_notion(title, link, "공공기관")
                    count += 1
    except Exception as e:
        print(f"공공기관 크롤링 에러: {e}")

if __name__ == "__main__":
    crawl_google_news(KEYWORD)
    # crawl_naver_news(KEYWORD) # 필요시 활성화
    crawl_public_portal(KEYWORD)
