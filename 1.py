import streamlit as st
import google.generativeai as genai
import random
import os
import json
import re
import sys
import io
from ddgs import DDGS
from dotenv import load_dotenv
from datetime import datetime

# ==========================================
# 1. 환경 설정
# ==========================================
load_dotenv()
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GENAI_API_KEY:
    st.error("🚨 GEMINI_API_KEY를 .env 파일에서 찾을 수 없습니다.")
    st.stop()

genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel('gemini-3-flash-preview')

# ==========================================
# 2. 공통 함수
# ==========================================

def hunt_realtime_info(keyword):
    """실시간 정보 수집"""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(keyword, region='kr-kr', safesearch='off', timelimit='w', max_results=6))
            if not results:
                results = list(ddgs.text(keyword, region='kr-kr', max_results=6))
            context = ""
            for r in results:
                context += f"정보원: {r.get('title', '')}\n핵심내용: {r.get('body', '')}\n\n"
            return context if context else "최신 트렌드 분석을 기반으로 집필합니다."
    except:
        return "최신 트렌드 분석을 기반으로 집필합니다."

def clean_all_tags(text):
    """HTML 태그 제거"""
    text = re.sub(r'<[^>]*>', '', text)
    text = text.replace("**", "").replace("__", "").replace("*", "")
    return text.strip()

def get_ftc_text(url):
    """공정위 문구"""
    if not url: return ""
    u = url.lower()
    if "coupang" in u: return "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
    if "naver" in u or "smartstore" in u: return "이 포스팅은 네이버 쇼핑커넥트 활동의 일환으로, 판매 발생 시 수수료를 제공받습니다."
    if "oliveyoung" in u: return "이 포스팅은 올리브영 쇼핑 큐레이터 활동의 일환으로, 판매 발생시 수수료를 제공받습니다."
    return "이 포스팅은 제휴 마케팅 활동의 일환으로 커미션를 받습니다."

# ==========================================
# 3. 네이버 수익형 (11.py)
# ==========================================

NAVER_PROFIT_PERSONAS = [
    {
        "role": "30대 워킹맘",
        "tone": "친근한 존댓말",
        "keywords": ["진짜", "완전", "대박", "리얼", "솔직히"],
        "emoji_style": "😊 💕 👍 ✨ 🔥",
        "intro_style": "일상 에피소드"
    },
    {
        "role": "20대 직장인",
        "tone": "가벼운 반말",
        "keywords": ["ㅇㅁ", "가성비", "꿀템", "핵이득", "존맛"],
        "emoji_style": "🔥 💯 ✅ 💸 ⚡",
        "intro_style": "문제 상황 제시"
    },
    {
        "role": "40대 구매 전문가",
        "tone": "정중한 존댓말",
        "keywords": ["실제로", "확실히", "분명", "경험상", "추천드립니다"],
        "emoji_style": "✅ 💡 📊 👌 ⭐",
        "intro_style": "통계/데이터"
    },
    {
        "role": "블로그 마니아",
        "tone": "설명형 존댓말",
        "keywords": ["정리해드릴게요", "알려드립니다", "확인해보세요", "참고하세요"],
        "emoji_style": "📌 ✏️ 💬 🎯 📝",
        "intro_style": "핫한 질문"
    },
    {
        "role": "소비 분석가",
        "tone": "분석적 존댓말",
        "keywords": ["비교해보면", "데이터상", "실측", "결과적으로"],
        "emoji_style": "📈 🔍 💰 🎓 ⚖️",
        "intro_style": "폭로/반전"
    }
]

NAVER_PROFIT_STRUCTURES = {
    1: {"name": "스토리텔링형", "sections": ["개인 경험담", "문제 발견", "제품 만남", "사용 과정", "결과/변화"], "cta_position": "변화 직후"},
    2: {"name": "데이터 분석형", "sections": ["시장 현황", "수치 비교", "스펙 분석", "가격 분석", "종합 평가"], "cta_position": "핵심 데이터 후"},
    3: {"name": "비교 대결형", "sections": ["경쟁 제품들", "1차 비교", "심층 비교", "상황별 추천", "최종 승자"], "cta_position": "비교 결과 후"},
    4: {"name": "폭로 고발형", "sections": ["충격 사실", "업계 속사정", "진실 분석", "대안 제시", "행동 촉구"], "cta_position": "진실 폭로 후"},
    5: {"name": "Q&A 해결형", "sections": ["베스트 질문", "오해 바로잡기", "핵심 답변", "추가 팁", "최종 정리"], "cta_position": "핵심 답변 후"}
}

DIVIDERS = [
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    "────────────────────────────",
    "◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈",
    "============================================"
]

def get_naver_h3(text):
    """네이버 19px 소제목"""
    return f'\n{random.choice(DIVIDERS)}\n<span style="font-size: 19px; font-weight: bold; color: #000000;">📍 {text}</span>\n'

def generate_naver_profit_prompt(keyword, product, url, facts, persona, structure):
    """네이버 수익형 프롬프트"""
    current_date = datetime.now().strftime("%Y년 %m월 %d일")
    
    return f"""
당신은 지금 {persona["role"]}입니다. 블로그를 {random.randint(3, 8)}년째 운영 중입니다.

[철칙 - 위반 시 즉시 폐기]
1. "안녕하세요", "오늘은", "알아보겠습니다" 같은 AI 티 나는 문구 절대 금지
2. 예의 바른 인사 금지. 바로 충격/위기/호기심으로 시작!
3. 메타 언급 금지 ("태그를 사용", "방식으로", "구조는")
4. 마크다운(*, #, -, **) 절대 금지. 오직 <b>태그만!
5. 🚫 자기소개 절대 금지 ("저는", "블로거", "리뷰어", "전문가입니다", "~년차", "운영중")
6. 🚫 쿠팡 언급 절대 금지 ("쿠팡에서", "쿠팡으로", "쿠팡 파트너스")
7. 🚫 마무리 멘트 절대 금지 ("결론", "마무리", "마치며", "정리하면", "요약하면", "끝으로", "마지막으로")
8. 🚫 날짜 노출 절대 금지 ("2025년", "1월", "오늘", "어제", "내일", 구체적 날짜 표기)

[작성 정보]
- 날짜: {current_date} (참고용, 본문에 절대 쓰지 마세요!)
- 키워드: {keyword}
- 제품: {product}
- 링크: {url}
- 실시간 이슈: {facts}
- 캐릭터 말투: {persona["tone"]}
- 자주 쓸 말: {", ".join(persona["keywords"])}
- 이모지: {persona["emoji_style"]} (본문에 자연스럽게)
- 구조: {structure["name"]}

[글자수]
정확히 1800~2400자 (엄수)

[JSON 응답]
{{
    "title": "제목",
    "content": "본문",
    "meta_description": "SEO 요약 (150자)",
    "hashtags": "7개"
}}

[🔥 제목 작성법 - 클릭 유도 필수!]
8가지 패턴 중 1개:
1. 손해 공포형: "이거 모르면 {{금액}}원 날립니다"
2. 정보 격차형: "알 사람은 다 아는 {{상품}} 진실"
3. 시간 압박형: "지금만 {{혜택}}, 내일부터 인상"
4. 후회 경고형: "{{행동}} 했다가 멘붕 왔습니다"
5. 내부자 폭로형: "업계인이 폭로하는 {{진실}}"
6. 비교 충격형: "{{A}} vs {{B}}, 결과 충격"
7. 반전 경험형: "{{기대}}했는데 {{반전}}"
8. 긴급 정보형: "지금 당장 확인하세요, {{위험}}"

제목 규칙:
- {keyword} 반드시 포함
- 15~25자
- 구체적 숫자 사용
- 이모지 금지

[💣 도입부 (첫 5문장이 생명)]
5가지 후킹 전략 중 1개:
1. 충격 사실: "이거 알면 절대 못합니다." + 수치 증명
2. 손해 경험: "{{금액}}원 날렸습니다." + 이유
3. 시간 압박: "지금만입니다." + 손해
4. 정보 격차: "알 사람만 압니다." + 모르면 손해
5. 반전 경험: "{{기대}}했는데 {{반전}}"

도입 필수:
✅ 첫 문장 5단어 이내
✅ 구체적 숫자 2개+
✅ 이모지 1~2개
✅ {persona["intro_style"]}로 시작

[본문 구성]
{", ".join(structure["sections"])}로 전개

각 섹션:
- 소제목: [TITLE]제목[/TITLE]
- 키워드/숫자 <b>태그</b> 강조
- 이모지 자연스럽게
- FOMO 문구 반복

🔥 중간 재후킹 (3번째 섹션):
- "여기까지만 알아도 {{금액}}원 아낍니다"
- "근데 진짜 중요한 건 지금부터예요"

FOMO 문구 (최소 5회):
"이거 모르고 샀다간...", "안 쓰면 바보", "알 사람만 안다", "지금 아니면 기회 없어요", "뒤늦게 알고 후회했어요"

[CTA 배치]
[[CTA_1]]을 {structure["cta_position"]}에 1번
[[CTA_2]]를 FAQ 직전에 1번
총 2번 배치

[FAQ 필수 3개]
Q1: 가장 큰 실수/오해
Q2: 꼭 확인해야 할 것
Q3: 지금 사야 하는 이유

[마무리]
FAQ 후 마지막 2~3문장으로 강하게:
"지금 안 하면 진짜 후회합니다", "{{금액}}원 날리기 싫으면 지금 바로"
→ 행동 촉구만! 정리/요약 절대 금지!

[해시태그]
7개 (이모지 없이, 검색 키워드)

{product}에 대한 {structure["name"]} 스타일 원고를 작성하세요.
JSON만 출력하세요.
"""

def render_naver_profit():
    """네이버 수익형 UI"""
    st.title("💀 네이버 수익형 v8.8: FOMO 극대화")
    st.markdown("<p style='color:#666;'>매번 다른 페르소나와 구조로 AI 흔적을 완벽히 숨깁니다.</p>", unsafe_allow_html=True)
    
    if 'naver_profit_content' not in st.session_state: 
        st.session_state.naver_profit_content = ""
    if 'naver_profit_display' not in st.session_state: 
        st.session_state.naver_profit_display = ""
    
    col1, col2 = st.columns(2)
    with col1:
        keyword = st.text_input("💎 키워드", key="naver_profit_kw", placeholder="예: 무선 청소기 추천")
        product = st.text_input("📦 상품명", key="naver_profit_prod", placeholder="예: 다이슨 V15")
    with col2:
        url = st.text_input("🔗 제휴 링크", key="naver_profit_url", placeholder="http://...")
    
    if st.button("🚀 FOMO 극대화 원고 생성", key="naver_profit_btn"):
        if not keyword or not product or not url:
            st.warning("⚠️ 모든 정보를 입력해주세요.")
        else:
            with st.spinner('페르소나 선택 중...'):
                try:
                    persona = random.choice(NAVER_PROFIT_PERSONAS)
                    structure_id = random.randint(1, 5)
                    structure = NAVER_PROFIT_STRUCTURES[structure_id]
                    
                    facts = hunt_realtime_info(keyword)
                    prompt = generate_naver_profit_prompt(keyword, product, url, facts, persona, structure)
                    
                    st.info(f"🎭 페르소나: {persona['role']} | 📖 구조: {structure['name']}")
                    
                    response = model.generate_content(prompt)
                    raw_text = response.text
                    
                    json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                        title = data.get('title', f'{keyword} 후기')
                        content = data.get('content', '')
                        content = re.sub(r'\[TITLE\](.*?)\[/TITLE\]', lambda m: get_naver_h3(m.group(1)), content)
                        
                        cta_html = f'<div style="margin: 30px 0; padding: 20px; border: 3px solid #000; background: #fff; border-radius: 5px;"><p style="font-size: 15px; color: #000; margin: 0 0 10px 0; font-weight: bold;">🚨 이거 모르고 사면 손해!</p><p style="font-size: 16px; color: #000; margin: 0; font-weight: bold;">👉 {product} 최저가 & 혜택 확인하기</p></div>'
                        content = content.replace("[[CTA_1]]", cta_html, 1)
                        content = content.replace("[[CTA_2]]", cta_html, 1)
                        content = re.sub(r'\[\[CTA_\d+\]\]', '', content)
                        
                        disclosure = get_ftc_text(url)
                        
                        final = f"""<div style="font-family: 'Nanum Gothic', sans-serif; font-size: 15px; line-height: 1.8; color: #000;">
{disclosure}

<h1 style="font-size: 24px; font-weight: bold; color: #000; margin: 20px 0; padding-bottom: 10px; border-bottom: 2px solid #000;">{title}</h1>

{content}

<div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #0066cc; font-weight: bold;">{data.get('hashtags', '')}</div>
</div>"""
                        
                        st.session_state.naver_profit_content = final
                        st.session_state.naver_profit_display = clean_all_tags(final)
                    else:
                        st.error("JSON 형식을 찾을 수 없습니다.")
                except Exception as e:
                    st.error(f"오류: {e}")
    
    if st.session_state.naver_profit_display:
        st.divider()
        st.subheader("📋 원고 확인")
        st.text_area("내용 확인", value=st.session_state.naver_profit_display, height=500, key="naver_profit_display_area")
        
        safe = st.session_state.naver_profit_content.replace("`", "\\`").replace("$", "\\$")
        safe = re.sub(r'>\s*\n\s*<', '><', safe)
        html_code = safe.replace("\n", "<br>")
        
        st.components.v1.html(f"""
            <button onclick="copyRich()" style="width:100%; padding:20px; background:#111; color:#00FF7F; border:2px solid #00FF7F; border-radius:12px; font-weight:bold; cursor:pointer; font-size:18px;">
                📋 네이버 블로그 서식 포함 복사
            </button>
            <script>
            function copyRich() {{
                const html = `{html_code}`;
                const blob = new Blob([html], {{ type: "text/html" }});
                const data = [new ClipboardItem({{ "text/html": blob }})];
                navigator.clipboard.write(data).then(() => alert("✅ 복사 완료!"));
            }}
            </script>
        """, height=100)

# ==========================================
# 4. 네이버 정보성
# ==========================================

NAVER_INFO_PERSONAS = [
    {"role": "전문 칼럼니스트", "tone": "정중한 존댓말", "keywords": ["분석하면", "살펴보면", "알 수 있습니다"], "emoji": "📊 💡 ✅"},
    {"role": "정보 큐레이터", "tone": "친절한 설명", "keywords": ["정리하면", "핵심은", "중요한 점은"], "emoji": "📌 ✏️ 💬"},
    {"role": "업계 전문가", "tone": "전문적 존댓말", "keywords": ["실제로", "데이터상", "경험상"], "emoji": "🎓 📈 ⭐"}
]

def get_naver_info_h3(text):
    """네이버 정보성 19px 소제목"""
    styles = [
        'border-left: 10px solid #2c5aa0; padding-left: 15px; border-bottom: 1px solid #eee; margin: 40px 0 20px 0;',
        'border-top: 4px solid #2c5aa0; padding: 15px; border-bottom: 1px solid #eee; margin: 40px 0 20px 0;',
        'display: inline-block; padding: 5px 15px; border: 2px solid #2c5aa0; color: #2c5aa0; border-radius: 20px; margin: 40px 0 20px 0; font-weight: bold;'
    ]
    return f"<h3 style='font-size:19px; font-weight:bold; color:#111; {random.choice(styles)}'>{text}</h3>"

def generate_naver_info_prompt(keyword, facts, persona):
    """네이버 정보성 프롬프트"""
    return f"""
당신은 {persona["role"]}입니다.

[철칙]
1. AI 인사말 금지 ("안녕하세요", "오늘은", "알아보겠습니다")
2. 자기소개 금지
3. 마무리 멘트 금지 ("결론", "마무리", "마치며")
4. 날짜 노출 금지
5. 마크다운 금지, <b>태그만 사용

[작성 정보]
- 키워드: {keyword}
- 실시간 정보: {facts}
- 말투: {persona["tone"]}
- 자주 쓸 표현: {", ".join(persona["keywords"])}
- 이모지: {persona["emoji"]} (본문에 자연스럽게)

[글자수]
정확히 1800~2400자

[JSON 응답]
{{
    "title": "제목 (15-25자, {keyword} 포함)",
    "content": "본문",
    "hashtags": "7개"
}}

[구조]
도입: 주제 소개 (이모지 포함)
본문: 5개 소제목 [TITLE]제목[/TITLE]
- 소제목마다 <b>태그</b>로 키워드 강조
- 이모지 {persona["emoji"]} 자연스럽게 배치

[필수 섹션]
1. ✅ 체크리스트
   <div style="background:#f8f9fa; padding:15px; border-left:4px solid #2c5aa0; margin:20px 0;">
   <b>📋 핵심 체크리스트</b><br>
   ☑️ 항목 1<br>
   ☑️ 항목 2<br>
   ☑️ 항목 3
   </div>

2. 📊 속성표
   <table style="width:100%; border-collapse:collapse; margin:20px 0;">
   <tr style="background:#f8f9fa;"><th style="border:1px solid #ddd; padding:10px;">항목</th><th style="border:1px solid #ddd; padding:10px;">내용</th></tr>
   <tr><td style="border:1px solid #ddd; padding:10px;"><b>대상</b></td><td style="border:1px solid #ddd; padding:10px;">내용</td></tr>
   </table>

3. ❓ Q&A (3~5개)
   <div style="margin:30px 0;">
   <b style="color:#2c5aa0;">Q1. 질문?</b><br>
   A1. 답변...<br><br>
   <b style="color:#2c5aa0;">Q2. 질문?</b><br>
   A2. 답변...
   </div>

[해시태그]
7개 (이모지 없이)

JSON만 출력하세요.
"""

def render_naver_info():
    """네이버 정보성 UI"""
    st.title("🟢 네이버 정보성 v16.2: 체크리스트 & Q&A")
    
    if 'naver_info_content' not in st.session_state: 
        st.session_state.naver_info_content = ""
    if 'naver_info_display' not in st.session_state: 
        st.session_state.naver_info_display = ""
    
    keyword = st.text_input("💎 키워드", key="naver_info_kw", placeholder="예: 건강보험 환급 방법")
    
    if st.button("🚀 전문 칼럼 생성", key="naver_info_btn"):
        if not keyword:
            st.warning("⚠️ 키워드를 입력해주세요.")
        else:
            with st.spinner('전문가 페르소나 접속 중...'):
                try:
                    persona = random.choice(NAVER_INFO_PERSONAS)
                    facts = hunt_realtime_info(keyword)
                    prompt = generate_naver_info_prompt(keyword, facts, persona)
                    
                    st.info(f"🎭 페르소나: {persona['role']}")
                    
                    response = model.generate_content(prompt)
                    raw_text = response.text
                    
                    json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                        title = data.get('title', f'{keyword} 완전 정리')
                        content = data.get('content', '')
                        content = re.sub(r'\[TITLE\](.*?)\[/TITLE\]', lambda m: get_naver_info_h3(m.group(1)), content)
                        
                        final = f"""<div style="font-family: 'Nanum Gothic', sans-serif; font-size: 15px; line-height: 1.8; color: #000;">
<h1 style="font-size: 24px; font-weight: bold; color: #000; margin: 20px 0; padding-bottom: 10px; border-bottom: 2px solid #2c5aa0;">{title}</h1>

{content}

<div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #0066cc; font-weight: bold;">{data.get('hashtags', '')}</div>
</div>"""
                        
                        st.session_state.naver_info_content = final
                        st.session_state.naver_info_display = clean_all_tags(final)
                    else:
                        st.error("JSON 형식을 찾을 수 없습니다.")
                except Exception as e:
                    st.error(f"오류: {e}")
    
    if st.session_state.naver_info_display:
        st.divider()
        st.subheader("📋 원고 확인")
        st.text_area("내용 확인", value=st.session_state.naver_info_display, height=500, key="naver_info_display_area")
        
        safe = st.session_state.naver_info_content.replace("`", "\\`").replace("$", "\\$")
        safe = re.sub(r'>\s*\n\s*<', '><', safe)
        html_code = safe.replace("\n", "<br>")
        
        st.components.v1.html(f"""
            <button onclick="copyRich()" style="width:100%; padding:20px; background:#03cf5d; color:white; border:none; border-radius:12px; font-weight:bold; cursor:pointer; font-size:18px;">
                🟢 전문가 칼럼 복사하기
            </button>
            <script>
            function copyRich() {{
                const html = `{html_code}`;
                const blob = new Blob([html], {{ type: "text/html" }});
                const data = [new ClipboardItem({{ "text/html": blob }})];
                navigator.clipboard.write(data).then(() => alert("✅ 복사 완료!"));
            }}
            </script>
        """, height=100)

# ==========================================
# 5. 티스토리 정보성 (p.py 재작성)
# ==========================================

TISTORY_INFO_PERSONAS = [
    {"role": "트렌드 분석가", "tone": "세련된 존댓말", "keywords": ["주목할 점은", "흥미로운 것은", "특징적인"], "emoji": "📊 💡 ✨"},
    {"role": "콘텐츠 큐레이터", "tone": "친근한 존댓말", "keywords": ["정리하면", "핵심은", "중요한 건"], "emoji": "📌 ✏️ 💬"},
    {"role": "정보 전문가", "tone": "전문적 존댓말", "keywords": ["분석하면", "데이터상", "실제로"], "emoji": "🎓 📈 ⭐"}
]

def get_tistory_info_h3():
    """티스토리 정보성 화려한 소제목"""
    color = "#{:06x}".format(random.randint(0, 0x777777))
    styles = [
        f'border-left: 15px solid {color}; padding: 10px 15px; background: #f8f9fa; font-weight: bold; margin: 40px 0 20px 0;',
        f'background: linear-gradient(to right, {color}, transparent); padding: 12px 20px; border-radius: 5px; margin: 40px 0 20px 0;',
        f'border: 2px solid {color}; padding: 15px; border-left: 10px solid {color}; border-radius: 0 10px 10px 0; margin: 40px 0 20px 0;'
    ]
    return random.choice(styles)

def generate_tistory_info_prompt(keyword, facts, persona):
    """티스토리 정보성 프롬프트 - 주제 이탈 방지"""
    return f"""
당신은 {keyword}에 대한 {persona["role"]}입니다.

[절대 규칙 - 매우 중요!]
1. 🚫 {keyword} 주제에서 절대 벗어나지 마세요
2. 🚫 관련 없는 경제/투자/전략 이야기 금지
3. 🚫 억지로 미래 예측이나 분석 넣지 마세요
4. 🚫 글자수 채우려고 이상한 내용 추가 금지
5. 🚫 AI 인사말/자기소개/마무리 멘트 금지
6. 🚫 날짜 노출 금지
7. 마크다운 금지, HTML만 사용

[작성 정보]
- 주제: {keyword} (이 주제만 다루세요!)
- 실시간 정보: {facts}
- 말투: {persona["tone"]}
- 자주 쓸 표현: {", ".join(persona["keywords"])}
- 이모지: {persona["emoji"]} (본문에 자연스럽게)

[글자수]
정확히 1800~2400자
(주제 관련 내용으로만! 글자수 채우려고 주제 벗어나지 마세요)

[JSON 응답]
{{
    "title": "제목 (15-25자, {keyword} 포함)",
    "content": "본문",
    "hashtags": "7개"
}}

[작성 방향]
- {keyword}의 핵심만 집중적으로 다루세요
- 구체적 사실과 정보 위주로 작성
- 독자가 {keyword}에 대해 궁금해할 내용만
- 주제와 관련 없으면 절대 쓰지 마세요

[구조]
도입: {keyword} 관련 후킹 (이모지 포함)
본문: 5개 소제목 [TITLE]제목[/TITLE]
- {keyword}와 직접 관련된 내용만
- <b>태그</b>로 키워드 강조
- 이모지 자연스럽게

[필수 요소]
✅ {keyword}에 대한 구체적 정보
✅ 실용적인 내용
✅ 독자가 바로 적용할 수 있는 것
❌ 관련 없는 경제/투자 이야기
❌ 억지 예측이나 전망
❌ 주제 벗어난 내용

[해시태그]
{keyword} 관련 7개 (이모지 없이)

JSON만 출력하세요.
"""

def render_tistory_info():
    """티스토리 정보성 UI"""
    st.title("🟠 티스토리 정보성: 주제 집중 모드")
    st.markdown("<p style='color:#666;'>주제에서 절대 벗어나지 않는 고품질 정보 콘텐츠</p>", unsafe_allow_html=True)
    
    if 'tistory_info_content' not in st.session_state: 
        st.session_state.tistory_info_content = ""
    if 'tistory_info_display' not in st.session_state: 
        st.session_state.tistory_info_display = ""
    
    keyword = st.text_input("💎 키워드", key="tistory_info_kw", placeholder="예: 연예인 은퇴 선언")
    
    if st.button("🚀 고품질 콘텐츠 생성", key="tistory_info_btn"):
        if not keyword:
            st.warning("⚠️ 키워드를 입력해주세요.")
        else:
            with st.spinner('전문가 페르소나 접속 중...'):
                try:
                    persona = random.choice(TISTORY_INFO_PERSONAS)
                    facts = hunt_realtime_info(keyword)
                    prompt = generate_tistory_info_prompt(keyword, facts, persona)
                    
                    st.info(f"🎭 페르소나: {persona['role']}")
                    
                    response = model.generate_content(prompt)
                    raw_text = response.text
                    
                    json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                        title = data.get('title', f'{keyword} 완전 분석')
                        content = data.get('content', '')
                        
                        def replace_h3(match):
                            style = get_tistory_info_h3()
                            return f"<h3 style='{style}'>{match.group(1)}</h3>"
                        
                        content = re.sub(r'\[TITLE\](.*?)\[/TITLE\]', replace_h3, content)
                        
                        final = f"""<div style="font-family: 'Noto Sans KR', sans-serif; font-size: 16px; line-height: 1.8; color: #333; max-width: 800px; margin: auto;">
<h1 style="font-size: 32px; font-weight: bold; color: #222; margin: 30px 0; text-align: center;">{title}</h1>

<div style="padding: 15px; background: #f1f3f5; border-radius: 8px; margin: 20px 0;">
<b style="color: #495057;">💡 핵심 요약:</b> {keyword}에 대한 심층 분석
</div>

{content}

<div style="margin-top: 40px; padding-top: 20px; border-top: 2px solid #dee2e6; color: #6c757d; font-size: 14px;">{data.get('hashtags', '')}</div>
</div>"""
                        
                        st.session_state.tistory_info_content = final
                        st.session_state.tistory_info_display = clean_all_tags(final)
                    else:
                        st.error("JSON 형식을 찾을 수 없습니다.")
                except Exception as e:
                    st.error(f"오류: {e}")
    
    if st.session_state.tistory_info_display:
        st.divider()
        st.subheader("📋 원고 확인")
        st.text_area("내용 확인", value=st.session_state.tistory_info_display, height=500, key="tistory_info_display_area")
        
        safe = st.session_state.tistory_info_content.replace("`", "\\`").replace("$", "\\$")
        html_code = safe.replace("\n", "")
        
        st.components.v1.html(f"""
            <button onclick="copyRich()" style="width:100%; padding:20px; background:#FF6B35; color:white; border:none; border-radius:12px; font-weight:bold; cursor:pointer; font-size:18px;">
                🟠 티스토리 HTML 복사하기
            </button>
            <script>
            function copyRich() {{
                const html = `{html_code}`;
                const blob = new Blob([html], {{ type: "text/html" }});
                const data = [new ClipboardItem({{ "text/html": blob }})];
                navigator.clipboard.write(data).then(() => alert("✅ 복사 완료! 티스토리 HTML 모드에 붙여넣기 하세요"));
            }}
            </script>
        """, height=100)

# ==========================================
# 6. 티스토리 수익형 (기존 유지)
# ==========================================

def create_tistory_cta(product, url):
    """티스토리 애니메이션 CTA"""
    phrases = [
        "🔥 놓치면 후회할 특가!",
        "⚡ 지금이 최저가 타이밍!",
        "💝 이 가격 다시 없어요!",
        "🎯 스마트한 선택 지금!",
        "✨ 베스트 딜 확인하기!"
    ]
    phrase = random.choice(phrases)
    
    colors = ["#FF6B9D", "#C44569", "#F8B500", "#00D9FF"]
    bg = random.choice(colors)
    
    return f"""
<div style="background: linear-gradient(135deg, {bg}15 0%, {bg}05 100%); 
            border: 3px solid {bg}; 
            border-radius: 15px; 
            padding: 25px; 
            margin: 35px 0; 
            text-align: center;
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
            animation: pulse 2s infinite;">
    <p style="font-size: 20px; font-weight: bold; color: {bg}; margin: 0 0 15px 0;">
        {phrase}
    </p>
    <a href="{url}" target="_blank" rel="noopener" 
       style="display: inline-block; 
              background: {bg}; 
              color: white; 
              padding: 15px 40px; 
              border-radius: 30px; 
              text-decoration: none; 
              font-weight: bold; 
              font-size: 18px;
              transition: transform 0.3s;">
        👉 {product} 최저가 보러가기
    </a>
</div>
<style>
@keyframes pulse {{
    0%, 100% {{ transform: scale(1); }}
    50% {{ transform: scale(1.02); }}
}}
</style>
"""

def render_tistory_profit():
    """티스토리 수익형 UI (기존 t정보.py 유지)"""
    st.title("🟠 티스토리 수익형: 애니메이션 CTA")
    st.markdown("<p style='color:#666;'>t정보.py 기능 (기존 파일 그대로 사용하세요)</p>", unsafe_allow_html=True)
    
    st.info("💡 이 모드는 기존 t정보.py 파일을 그대로 사용하세요. 애니메이션 CTA와 화려한 디자인이 이미 완벽합니다!")
    
    st.code("""
# 기존 t정보.py를 사용하세요
# 특징:
# - 애니메이션 깜빡이는 CTA
# - 화려한 색상과 디자인
# - 이모지 효과
# - 구매 심리 자극
    """, language="python")

# ==========================================
# 7. 메인 UI
# ==========================================

st.set_page_config(page_title="GHOST HUB", layout="wide", initial_sidebar_state="expanded")

st.sidebar.title("💀 GHOST HUB")
st.sidebar.markdown("---")

mode = st.sidebar.radio(
    "모드 선택",
    [
        "🟢 네이버 수익형 (FOMO)",
        "🟢 네이버 정보성 (체크리스트)",
        "🟠 티스토리 정보성 (주제집중)",
        "🟠 티스토리 수익형 (기존파일)"
    ],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
### 📊 모드별 특징

**🟢 네이버 수익형**
- FOMO 극대화
- 페르소나 5개 랜덤
- CTA 2개
- 나눔고딕 15px

**🟢 네이버 정보성**
- 체크리스트 자동
- Q&A 3~5개
- 속성표 생성
- 전문 칼럼 스타일

**🟠 티스토리 정보성**
- 주제 이탈 방지
- 화려한 HTML
- 그라데이션
- 고품질 콘텐츠

**🟠 티스토리 수익형**
- 기존 t정보.py 사용
- 애니메이션 CTA
- 깜빡이는 효과
""")

# 모드에 따라 렌더링
if mode == "🟢 네이버 수익형 (FOMO)":
    render_naver_profit()
elif mode == "🟢 네이버 정보성 (체크리스트)":
    render_naver_info()
elif mode == "🟠 티스토리 정보성 (주제집중)":
    render_tistory_info()
else:
    render_tistory_profit()