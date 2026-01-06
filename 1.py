import streamlit as st
import google.generativeai as genai
import random
import os
import json
import re
import sys
import io
import traceback
import textwrap
from ddgs import DDGS
from dotenv import load_dotenv
from datetime import datetime

# 1. 환경 설정 및 인코딩 방어
# 1. 환경 설정 및 인코딩 방어
load_dotenv()
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

# [Cloud/Local] API 키 로드 우선순위:
# 1. Streamlit Cloud Secrets (st.secrets)
# 2. 로컬 환경 변수 (.env)
# 3. 코드 내 하드코딩 (최후의 수단 - 비추천)
try:
    if "GEMINI_API_KEY" in st.secrets:
        GENAI_API_KEY = st.secrets["GEMINI_API_KEY"]
    else:
        GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
except FileNotFoundError:
    GENAI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GENAI_API_KEY:
    # 사용자 편의를 위해 최후의 수단으로 키가 없으면 에러 대신 안내
    st.error("🚨 API 키가 없습니다. Streamlit Cloud의 Secrets에 'GEMINI_API_KEY'를 설정해주세요.")
    st.stop()

genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel('gemini-3-flash-preview') 

# 2. [데이터] 스타일 엔진 (복사용 서식)
DIVIDERS = [
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "────────────────────────────",
    "◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈", "============================================"
]

def get_rich_h3(text):
    # 네이버 에디터에서 19px 굵은 제목으로 인식되는 코드
    return f'\n{random.choice(DIVIDERS)}\n<span style="font-size: 19px; font-weight: bold; color: #000000;">📍 {text}</span>\n'

# 3. [기능] 실시간 정보 사냥
def hunt_realtime_info(keyword):
    try:
        with DDGS() as ddgs:
            results = ddgs.news(keyword, region='kr-kr', safesearch='off', timelimit='w', max_results=6)
            if not results:
                results = ddgs.text(keyword, region='kr-kr', max_results=6)
            context = ""
            for r in results:
                context += f"기사: {r.get('title', '')}\n내용: {r.get('body', '')}\n\n"
            return context
    except:
        return "최신 트렌드 데이터와 실시간 분석 정보를 기반으로 집필합니다."

# 4. [기능] 텍스트 정제 (사용자 화면용)
def clean_all_tags(text):
    # HTML 태그 및 마크다운 기호 삭제
    text = re.sub(r'<[^>]*>', '', text)
    text = text.replace("**", "").replace("__", "").replace("*", "")
    return text.strip()

def get_ftc_text(url):
    if not url: return ""
    u = url.lower()
    if "coupang" in u: return "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
    if "naver" in u or "smartstore" in u: return "이 포스팅은 네이버 쇼핑커넥트 활동의 일환으로, 판매 발생 시 수수료를 제공받습니다."
    if "oliveyoung" in u: return "이 포스팅은 올리브영 쇼핑 큐레이터 활동의 일환으로, 판매 발생시 수수료를 제공받습니다."
    return "이 포스팅은 제휴 마케팅 활동의 일환으로 커미션를 받습니다."

# 5. 메인 UI
st.set_page_config(page_title="GHOST v8.8 Weaver", layout="wide")
st.title("💀 GHOST SYSTEM v8.8: THE GREAT WEAVER")
st.markdown("<p style='color:#666;'>매번 다른 서사 구조와 자극적인 제목으로 AI임을 완벽히 숨깁니다.</p>", unsafe_allow_html=True)

if 'rich_content' not in st.session_state: st.session_state.rich_content = ""
if 'display_content' not in st.session_state: st.session_state.display_content = ""

col1, col2 = st.columns(2)
with col1:
    target_keyword = st.text_input("💎 키워드", placeholder="예: 무선 청소기 추천")
    target_product = st.text_input("📦 상품명", placeholder="예: 다이슨 V15")
with col2:
    affiliate_url = st.text_input("🔗 제휴 링크", placeholder="http://...")

if st.button("🚀 무한 변칙 원고 생성"):
    if not target_keyword or not target_product or not affiliate_url:
        st.warning("⚠️ 모든 정보를 입력해주세요.")
    else:
        with st.spinner('실시간 정보를 수집하고 독창적인 서사를 엮는 중...'):
            try:
                real_facts = hunt_realtime_info(target_keyword)
                
                # 검색 제한 감지 시 처리
                if "❌ 검색 제한" in real_facts:
                    st.warning("⚠️ 검색량이 많아 잠시 차단되었습니다. AI의 배경지식으로 작성합니다.")
                    real_facts = "실시간 정보를 가져올 수 없습니다. 귀하의 전문 지식을 바탕으로 가장 정확하고 유용한 정보를 작성하세요."
                # 5가지 구조 중 랜덤 선택 (서사 방식 변경)
                narrative_style = random.randint(1, 5) 
                disclosure = get_ftc_text(affiliate_url)

                # [단계 2] 프롬프트 설계 (예시를 제거하고 창의성을 극대화)
                current_date = datetime.now().strftime("%Y년 %m월 %d일")
                prompt = f"""
                당신은 네이버 상위 0.0001% 마케팅 천재이자 심리학을 통달한 전문 작가입니다.
                오늘 날짜는 {current_date}입니다. 이 날짜를 기준으로 과거와 미래를 명확히 구분하여 작성하세요.
                '{target_keyword}'독자가 당신의 글을 읽으면 '이건 진짜 사람이 썼다'고 확신하게 만드는 2,500자 이상의 문서를 작성하세요.

                [입력 데이터]
                - 작성일: {current_date}
                - 키워드: {target_keyword}
                - 상품명: {target_product}
                - 링크: {affiliate_url}
                - 실시간 이슈: {real_facts}
                - 서사 스타일 코드: {narrative_style} (1:폭로, 2:취재, 3:경험전환, 4:비교분석, 5:미래예측)

                [필수 작성 지침 - AI 흔적 말살]
                1. **제목**: 구체적인 예시 없이, '공포/이득/호기심' 중 하나의 트리거를 선택해 창조하세요. 제목에 '{target_keyword}'가 반드시 포함되어야 합니다.
                2. **입막음**: 본문에 "태그를 사용하겠습니다", "지침에 따라" 같은 메타 발언이나 인사말은 **절대** 금지입니다. 바로 원고 내용으로 시작하세요.
                3. **마크다운 금지**: *, # 기호 금지. 강조는 오직 <b>태그만 사용하세요. (태그 설명도 하지 마세요)
                4. **본문 강조 기술**: 수치, 제품명, 핵심 장점은 반드시 <b>태그로 감싸 시각적 만족도를 높이세요.
                5. **무제한 랜덤 CTA**: 이 글의 맥락을 완벽히 이해하고, 독자가 지금 당장 이 제품을 사지 않으면 손해라는 창작 멘트를 [[CTA_1]], [[CTA_2]] 위치에 매번 다르게 창작하세요.
                6. **글의 구조**: 
                    - 도입부: 뉴스 기반 위기론/트렌드 분석
                   - 상단: [핵심 요약 박스] - 3줄 요약 + 주요 스펙(속성) 3가지
                   - 본문: 소제목 5개 이상. 각 섹션은 '사실-분석-주관적 견해'로 상세히 서술. 소제목은 [TITLE]텍스트[/TITLE] 형식으로 출력.
                   - 중반: [상세 스펙 및 속성] - 수치와 단위를 포함하여 전문적으로 기술.
                   - 하단: [액션 체크리스트] - 구매 전 필수 확인 사항 5가지.
                   - 마무리: 심층 Q&A 3세트 및 전문가 총평.
                7. **해시태그**: 본문 최하단에 관련 태그 7개를 생성하세요.
                """

                response = model.generate_content(prompt)
                raw_text = response.text
                
                # 1. 소제목 치환 (Rich Text용)
                def replace_h3(match): return get_rich_h3(match.group(1))
                rich_text = re.sub(r'\[TITLE\](.*?)\[/TITLE\]', replace_h3, raw_text)
                
                # 2. CTA 치환
                def cta_replacer(match):
                    return f'\n\n<span style="color: #00C73C; font-weight: bold;">👉 {target_product} 최저가 확인 및 상세 정보: {affiliate_url}</span>\n\n'
                rich_text = re.sub(r'\[\[CTA_\d\]\]', cta_replacer, rich_text)

                # 3. 최종 조립 (복사용)
                final_rich = f"{disclosure}\n\n{rich_text}\n\n"
                
                st.session_state.rich_content = final_rich
                # 4. 화면 표시용 (모든 HTML 태그 강제 삭제 - 지침 언급 차단)
                st.session_state.display_content = clean_all_tags(final_rich)

            except Exception as e:
                st.error(f"오류 발생: {e}")

# [결과 출력 영역]
if st.session_state.display_content:
    st.divider()
    st.subheader("📋 네이버 블로그 원고 (확인용)")
    st.text_area("내용을 확인하세요. (복사는 아래 버튼 사용)", 
                 value=st.session_state.display_content, height=600)
    
    # [핵심] 리치 텍스트 복사 버튼
    # 테이블 주변 공백 제거 로직 추가
    safe_content = st.session_state.rich_content.replace("`", "\\`").replace("$", "\\$")
    safe_content = re.sub(r'>\s*\n\s*<', '><', safe_content)
    safe_content = re.sub(r'\n+\s*(<table)', r'\1', safe_content)
    rich_html_code = safe_content.replace("\n", "<br>")
    
    st.components.v1.html(f"""
        <button onclick="copyRichText()" style="width:100%; padding:20px; background:#111; color:#00FF7F; border:2px solid #00FF7F; border-radius:12px; font-weight:bold; cursor:pointer; font-size:18px; box-shadow: 0 0 15px rgba(0, 255, 127, 0.4);">
            📋 네이버 블로그 서식 포함 전체 복사하기
        </button>
        <script>
        function copyRichText() {{
            try {{
                const html = `{rich_html_code}`;
                const type = "text/html";
                const blob = new Blob([html], {{ type }});
                const data = [new ClipboardItem({{ [type]: blob }})];
                navigator.clipboard.write(data).then(() => alert("✅ 19px 소제목과 굵은 글씨 서식이 복사되었습니다!"));
            }} catch (err) {{
                alert("복사 실패: 브라우저 보안 설정을 확인하세요.");
            }}
        }}
        </script>
    """, height=100)