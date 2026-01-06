import streamlit as st
import google.generativeai as genai
import random
import os
import json
import re
import sys
import io
import time
import requests
import pandas as pd
import zipfile
from io import BytesIO
from ddgs import DDGS
from dotenv import load_dotenv
from datetime import datetime

# 1. 환경 설정 및 인코딩 방어
load_dotenv()
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

# [보안] API 키 로드
try:
    if "GEMINI_API_KEY" in st.secrets:
        GENAI_API_KEY = st.secrets["GEMINI_API_KEY"]
    else:
        GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
except FileNotFoundError:
    GENAI_API_KEY = os.getenv("GEMINI_API_KEY")

try:
    if "UNSPLASH_ACCESS_KEY" in st.secrets:
        UNSPLASH_ACCESS_KEY = st.secrets["UNSPLASH_ACCESS_KEY"]
    else:
        UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
except:
    UNSPLASH_ACCESS_KEY = None

if not GENAI_API_KEY:
    # 썸네일 제작기 모드일 때는 API 키가 없어도 일부 기능이 동작할 수 있으므로 강제 중단하지 않음
    pass

genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel('gemini-3-flash-preview')

# ==========================================
# [공통 유틸리티 & 스타일 엔진]
# ==========================================
def hunt_realtime_info(keyword, mode='general'):
    try:
        with DDGS() as ddgs:
            context = ""
            if mode == 'info':
                try: news_res = list(ddgs.news(keyword, region='kr-kr', timelimit='m', max_results=5))
                except: news_res = []
                web_res = []
                if len(news_res) < 3: web_res = list(ddgs.text(keyword, region='kr-kr', max_results=5))
                results = news_res + web_res
                for r in results: context += f"출처: {r.get('title','')}\n내용: {r.get('body','')}\n\n"
            else:
                results = ddgs.news(keyword, region='kr-kr', safesearch='off', timelimit='w', max_results=6)
                if not results: results = ddgs.text(keyword, region='kr-kr', max_results=6)
                for r in results: context += f"기사: {r.get('title', '')}\n내용: {r.get('body', '')}\n\n"
            return context if context else "검색 정보 없음. 지식 기반 작성."
    except: return "검색 오류. 지식 기반 작성."

def get_ftc_text(url):
    if not url: return ""
    u = url.lower()
    if "coupang" in u: return "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
    if "naver" in u or "smartstore" in u: return "이 포스팅은 네이버 쇼핑커넥트 활동의 일환으로, 판매 발생 시 수수료를 제공받습니다."
    if "oliveyoung" in u: return "이 포스팅은 올리브영 쇼핑 큐레이터 활동의 일환으로, 판매 발생시 수수료를 제공받습니다."
    return "이 포스팅은 제휴 마케팅 활동의 일환으로 커미션를 받습니다."

def get_naver_sales_h3(text):
    divs = ["━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "────────────────────────────", "◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈"]
    return f'\n{random.choice(divs)}\n<span style="font-size: 19px; font-weight: bold; color: #000000;">📍 {text}</span>\n'

def get_naver_info_h3(text):
    color = random.choice(["#1e3a8a", "#065f46", "#b91c1c", "#111827"])
    style = random.choice([f'border-left: 10px solid {color}; padding-left: 15px; border-bottom: 1px solid #eee; margin: 40px 0 20px 0;', f'border-top: 4px solid {color}; padding: 15px; border-bottom: 1px solid #eee; margin: 40px 0 20px 0;', f'display: inline-block; padding: 5px 15px; border: 2px solid {color}; color: {color}; border-radius: 20px; margin: 40px 0 20px 0; font-weight: bold;'])
    font_color = "#111" if "border-bottom" in style else color
    return f"<h3 style='font-size:22px; font-weight:bold; color:{font_color}; {style}'>{text}</h3>"

def get_tistory_premium_style():
    color = "#{:06x}".format(random.randint(0, 0x777777))
    return random.choice([f'border-left: 15px solid {color}; border-bottom: 2px solid {color}; padding: 10px 15px; background: #f8f9fa; font-weight: bold;', f'background: linear-gradient(to right, {color}, white); color: white; padding: 12px 20px; border-radius: 5px; box-shadow: 3px 3px 5px rgba(0,0,0,0.1);', f'border: 2px solid {color}; padding: 15px; border-left: 10px solid {color}; border-radius: 0 10px 10px 0; background: #ffffff;', f'border-top: 1px solid #ddd; border-bottom: 3px double {color}; padding: 10px 0; font-size: 1.5em;'])

def get_tistory_sales_h3(text):
    color = "#{:06x}".format(random.randint(0, 0x777777))
    style = random.choice([f'border-left: 10px solid {color}; border-bottom: 2px solid {color}; padding: 5px 15px; margin: 40px 0 15px 0; font-weight: bold; font-size: 1.3em; display: block;', f'background-color: {color}; color: white; padding: 10px 18px; margin: 40px 0 15px 0; font-weight: bold; border-radius: 5px; display: block;', f'border-bottom: 5px double {color}; padding-bottom: 8px; margin: 40px 0 15px 0; font-weight: bold; font-size: 1.4em; display: block;'])
    return f'<br><h3 style="{style}">{text}</h3>'

def get_info_images(queries, count=5):
    headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"} if UNSPLASH_ACCESS_KEY else {}
    img_urls = []
    for q in queries[:count]:
        try:
            if UNSPLASH_ACCESS_KEY:
                res = requests.get(f"https://api.unsplash.com/search/photos?query={q}&per_page=1", headers=headers, timeout=5)
                if res.status_code == 200 and res.json()['results']:
                    img_urls.append(res.json()['results'][0]['urls']['regular'])
                    continue
            img_urls.append(f"https://loremflickr.com/800/600/business,{q}")
        except: img_urls.append("https://picsum.photos/800/600")
    return img_urls

# --- [새 기능: 키워드 수집기용 스크래퍼] ---
def get_naver_best_keywords(category_id='50000006'):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    url = f"https://snxbest.naver.com/product/best/click?categoryCategoryId={category_id}"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            # 제품명 추출 (정규식 활용 - 1.py의 경량성 유지)
            titles = re.findall(r'"productName":"(.*?)"', res.text)
            links = re.findall(r'"originUrl":"(.*?)"', res.text)
            results = []
            for t, l in zip(titles[:20], links[:20]):
                results.append({"keyword": t, "product": t, "link": l.replace("\\u0026", "&")})
            return results
    except: pass
    return []

def get_coupang_best_keywords(keyword):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    url = f"https://www.coupang.com/np/search?q={keyword}"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            # 쿠팡은 보안이 강해 정식 API 사용 권장이나, 여기서는 간단한 텍스트 파싱 시도
            # 실제 개발 환경에서는 Selenium/Playwright가 필요할 수 있음
            # 키워드 기반이라 DDGS로 대체 검색하여 상위 결과를 가져오는 것이 더 안정적일 수 있음
            with DDGS() as ddgs:
                results = list(ddgs.text(f"{keyword} 추천", max_results=10))
                return [{"keyword": r['title'], "product": r['title'], "link": r['href']} for r in results]
    except: pass
    return []

def create_tistory_sales_cta(product_name, product_url):
    phrase = random.choice(["⚠️ 재고 비상! 품절 임박", "⏳ 오늘만 이 가격!", "🚨 긴급 물량 확보!", "⚡ 품절 대란템!", "💰 최저가 보장"])
    btn = random.choice(["👉 최저가 확인하기", "👉 혜택 적용가 보기", "👉 품절 전 선점하기"])
    return f"""
    <style>
    .blink-border {{ background: #fbf0f6; border: 3px solid red; border-radius: 11px; padding: 18px 16px; margin: 25px 0; animation: blink 1s infinite; }}
    @keyframes blink {{ 50% {{ border-color: transparent; }} }}
    .animate-text {{ animation: pulse 1s infinite alternate; font-weight: 900; font-size: 1.2em; color:#e60000; }}
    @keyframes pulse {{ to {{ transform: scale(1.05); }} }}
    </style>
    <div class="blink-border"><span class="animate-text">{phrase}</span><br><div style="margin-top: 10px;"><a href="{product_url}" target="_blank" style="color:#1a3d7c; font-weight:bold; font-size:1.1em;">👉 {btn} ({product_name})</a></div></div>
    """

# ==========================================
# [썸네일 제작기 데이터]
# ==========================================
THUMBNAIL_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <link href="https://fonts.googleapis.com/css2?family=Black+Han+Sans&family=Do+Hyeon&family=Dokdo&family=Dongle&family=Gaegu&family=Gamja+Flower&family=Gowun+Batang&family=Gowun+Dodum&family=Gugi&family=Hi+Melody&family=Jua&family=Kirang+Haerang&family=Nanum+Brush+Script&family=Nanum+Gothic&family=Nanum+Myeongjo&family=Nanum+Pen+Script&family=Noto+Sans+KR:wght@900&family=Noto+Serif+KR:wght@900&family=Poor+Story&family=Single+Day&family=Song+Myung&family=Sunflower:wght@700&family=Stylish&family=Yeon+Sung&display=swap" rel="stylesheet">
  <style>
    :root { --bg: #0f172a; --panel: #1e293b; --accent: #38bdf8; }
    body { background: #000; color: #fff; font-family: 'Noto Sans KR', sans-serif; margin: 0; padding: 10px; display: flex; flex-direction: column; align-items: center; overflow-x: hidden; }
    .controls { width: 100%; max-width: 600px; background: var(--panel); padding: 15px; border-radius: 12px; margin-bottom: 10px; display: flex; flex-direction: column; gap: 10px; }
    input, textarea, button { width: 100%; padding: 10px; border-radius: 6px; border: none; font-size: 14px; }
    textarea { height: 60px; }
    button { cursor: pointer; font-weight: bold; background: var(--accent); color: #000; }
    .row { display: flex; gap: 5px; }
    canvas { max-width: 100%; border: 1px solid #444; border-radius: 8px; }
    label { font-size: 12px; color: #94a3b8; }
  </style>
</head>
<body>
  <div class="controls">
    <div class="row"><input id="kw" type="text" placeholder="키워드" value="아이폰15"><button onclick="genH()" style="width:80px">AI문구</button></div>
    <textarea id="txt" oninput="draw()">지금 아이폰15 안 사면\n100% 후회하는 이유</textarea>
    <div class="row">
        <button onclick="rndF()">🎲 폰트</button>
        <button onclick="rndB()">🎲 배경</button>
        <button onclick="down()">📥 저장</button>
    </div>
    <div class="row"><label>크기</label><input type="range" id="sz" min="50" max="250" value="100" oninput="draw()"></div>
  </div>
  <canvas id="cv" width="1080" height="1080"></canvas>
  <script>
    const cv = document.getElementById('cv'), ctx = cv.getContext('2d');
    const fonts = ["Black Han Sans", "Do Hyeon", "Jua", "Gugi", "Sunflower", "Noto Sans KR", "Noto Serif KR", "Nanum Pen Script", "Stylish"];
    let fIdx = 0, bg = null;
    const hooks = ["지금 {kw} 모르면\n손해보는 3가지", "{kw} 끝판왕!\n가성비 미쳤습니다", "솔직히 말합니다.\n{kw} 진짜 별로일까?"];
    function draw() {
      if(bg) ctx.drawImage(bg,0,0,1080,1080); else {ctx.fillStyle="#1e293b"; ctx.fillRect(0,0,1080,1080);}
      ctx.fillStyle = "rgba(0,0,0,0.4)"; ctx.fillRect(0,0,1080,1080);
      const lines = document.getElementById('txt').value.split('\\n'), sz = document.getElementById('sz').value;
      ctx.font = `${sz}px "${fonts[fIdx]}"`; ctx.textAlign="center"; ctx.textBaseline="middle"; ctx.strokeStyle="#000"; ctx.lineWidth=sz*0.15; ctx.lineJoin="round";
      let y = 1080/2 - ((lines.length-1)*sz*1.2)/2;
      lines.forEach(l => { ctx.strokeText(l,540,y); ctx.fillStyle="#fff"; ctx.fillText(l,540,y); y+=sz*1.2; });
      ctx.strokeStyle="white"; ctx.lineWidth=10; ctx.strokeRect(40,40,1000,1000);
    }
    function genH() { document.getElementById('txt').value = hooks[Math.floor(Math.random()*hooks.length)].replace("{kw}", document.getElementById('kw').value); draw(); }
    function rndF() { fIdx=(fIdx+1)%fonts.length; draw(); }
    function rndB() { const i=new Image(); i.crossOrigin="Anonymous"; i.src=`https://picsum.photos/1080/1080?random=${Math.random()}`; i.onload=()=>{bg=i; draw();}; }
    function down() { const a=document.createElement('a'); a.download='thumb.png'; a.href=cv.toDataURL(); a.click(); }
    rndB();
  </script>
</body>
</html>
"""

# ==========================================
# [메인 로직]
# ==========================================
st.set_page_config(page_title="GHOST Hub v9.0", layout="wide")

with st.sidebar:
    st.title("🧙‍♂️ GHOST HUB")
    mode = st.radio("모드 선택", 
        ["🟢 네이버 [수익형]", "🟢 네이버 [정보성]", "🟠 티스토리 [정보성]", "🟠 티스토리 [수익형]", "🖼️ 썸네일 제작기", "🔍 키워드 수집기", "🚀 엑셀 일괄 생성기"]
    )
    st.markdown("---")
    if GENAI_API_KEY: st.success("✅ API Connected")
    else: st.error("🚨 API Key Missing")

st.title(f"🚀 {mode}")

if mode == "🚀 엑셀 일괄 생성기":
    st.markdown("### 📊 엑셀 파일을 업로드하여 여러 개의 원고를 한 번에 생성합니다.")
    st.info("엑셀 파일 양식: A열(모드), B열(키워드), C열(상품명), D열(링크)\n* 모드 예시: 네이버수익, 네이버정보, 티스토리정보, 티스토리수익")
    
    uploaded_file = st.file_uploader("엑셀 파일 업로드 (.xlsx)", type=["xlsx"])
    
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.write("업로드된 데이터 미리보기:")
        st.dataframe(df.head())
        
        if st.button("🚀 일괄 생성 시작"):
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, row in df.iterrows():
                try:
                    m = str(row[0]).strip()
                    kw = str(row[1]).strip()
                    prod = str(row[2]).strip() if len(row) > 2 else ""
                    link = str(row[3]).strip() if len(row) > 3 else ""
                    
                    status_text.text(f"처리 중 ({i+1}/{len(df)}): {kw}")
                    
                    # 생성 로직 (기존 함수 재활용)
                    content = ""
                    title = kw
                    
                    if "네이버수익" in m:
                        facts = hunt_realtime_info(kw, 'sales')
                        raw = model.generate_content(f"네이버 수익형 2500자: {kw}, {prod}, {link}, {facts}").text
                        content = re.sub(r'\[TITLE\](.*?)\[/TITLE\]', lambda match: get_naver_sales_h3(match.group(1)), raw)
                        cta = f'<span style="color: #00C73C; font-weight: bold;">👉 {prod} 최저가: {link}</span>'
                        content = re.sub(r'\[\[CTA_\d\]\]', cta, content)
                        content = get_ftc_text(link) + "\n\n" + content
                    elif "네이버정보" in m:
                        facts = hunt_realtime_info(kw, 'info')
                        raw = model.generate_content(f"네이버 정보성 JSON: {kw}, {facts}").text
                        data = json.loads(re.search(r'\{.*\}', raw, re.DOTALL).group())
                        title = data['title']
                        content = re.sub(r'\[\[H3\]\](.*?)\[\[/H3\]\]', lambda match: get_naver_info_h3(match.group(1)), data['content'])
                        imgs = get_info_images(data.get('img_queries', []), 3)
                        for idx, u in enumerate(imgs): content = content.replace(f"[IMG_{idx+1}]", f"<img src='{u}' style='width:100%'>")
                    elif "티스토리정보" in m:
                        facts = hunt_realtime_info(kw, 'info')
                        raw = model.generate_content(f"티스토리 정보성 JSON: {kw}, {facts}").text
                        data = json.loads(re.search(r'\{.*\}', raw, re.DOTALL).group())
                        title = data['title']
                        content = data['content']
                        h3s = re.findall(r'<h3>(.*?)</h3>', content)
                        for h in h3s: content = content.replace(f'<h3>{h}</h3>', f'<br><h3 style="{get_tistory_premium_style()}">{h}</h3>', 1)
                    elif "티스토리수익" in m:
                        facts = hunt_realtime_info(kw, 'sales')
                        raw = model.generate_content(f"티스토리 수익형 JSON: {kw}, {prod}, {link}, {facts}").text
                        data = json.loads(re.search(r'\{.*\}', raw, re.DOTALL).group())
                        title = data['title']
                        content = data['content']
                        h3s = re.findall(r'<h3>(.*?)</h3>', content)
                        for h in h3s: content = content.replace(f'<h3>{h}</h3>', get_tistory_sales_h3(h), 1)
                        cta = create_tistory_sales_cta(prod, link)
                        content = content.replace("[CTA_1]", cta).replace("[CTA_2]", cta)
                    
                    results.append({"filename": f"{i+1}_{title[:20]}.html", "content": content})
                    
                except Exception as e:
                    results.append({"filename": f"{i+1}_에러.txt", "content": f"오류 발생: {str(e)}"})
                
                progress_bar.progress((i + 1) / len(df))
            
            status_text.text("✅ 생성 완료! 압축 파일을 다운로드하세요.")
            
            # ZIP 파일 생성
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for res in results:
                    zip_file.writestr(res["filename"], res["content"])
            
            st.download_button(
                label="📥 생성된 원고 전체 다운로드 (ZIP)",
                data=zip_buffer.getvalue(),
                file_name=f"ghost_bulk_{datetime.now().strftime('%m%d_%H%M')}.zip",
                mime="application/zip"
            )

elif mode == "🖼️ 썸네일 제작기":
    st.markdown("<p style='color:#666;'>글쓰기 완료 후, 이미지로 저장하여 블로그 썸네일로 사용하세요.</p>", unsafe_allow_html=True)
    st.components.v1.html(THUMBNAIL_HTML, height=1200, scrolling=True)

elif mode == "🔍 키워드 수집기":
    st.markdown("### 🔍 키워드 수집 및 관리")
    st.info("자동으로 인기 상품을 가져오거나, 직접 키워드를 입력하여 엑셀 템플릿을 만듭니다.")
    
    if 'collector_data' not in st.session_state:
        st.session_state.collector_data = pd.DataFrame(columns=["모드", "키워드", "상품명", "링크"])

    type_menu = st.radio("수집 방식", ["자동 수집", "직접 입력"], horizontal=True)
    
    if type_menu == "자동 수집":
        col1, col2 = st.columns(2)
        with col1:
            source = st.selectbox("수집 소스", ["네이버 쇼핑 베스트", "쿠팡 검색"])
            target_mode = st.selectbox("적용할 블로그 모드", ["네이버수익", "티스토리수익"])
        
        with col2:
            if source == "네이버 쇼핑 베스트":
                cat_map = {"식품":"50000006", "패션의류":"50000000", "화장품/미용":"50000002", "디지털/가전":"50000003", "생활/건강":"50000008"}
                category = st.selectbox("카테고리 선택", list(cat_map.keys()))
                cat_id = cat_map[category]
            else:
                search_kw = st.text_input("검색 키워드", "캠핑용품")
                
        if st.button("🚀 자동 수집 시작"):
            with st.spinner("수집 중..."):
                if source == "네이버 쇼핑 베스트":
                    data = get_naver_best_keywords(cat_id)
                else:
                    data = get_coupang_best_keywords(search_kw)
                    
                if data:
                    new_df = pd.DataFrame(data)
                    new_df.insert(0, "모드", target_mode)
                    new_df.columns = ["모드", "키워드", "상품명", "링크"]
                    st.session_state.collector_data = pd.concat([st.session_state.collector_data, new_df]).drop_duplicates().reset_index(drop=True)
                    st.success(f"✅ {len(new_df)}개의 아이템을 추가했습니다.")
                else:
                    st.error("데이터를 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.")

    else:
        st.write(" 아래 표에 직접 내용을 입력하거나 수정하세요. (행 추가 가능)")
        if st.button("🧹 전체 초기화"):
            st.session_state.collector_data = pd.DataFrame(columns=["모드", "키워드", "상품명", "링크"])
            st.rerun()

    # 데이터 편집기 (자동/수동 공용)
    edited_df = st.data_editor(
        st.session_state.collector_data, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "모드": st.column_config.SelectboxColumn("모드", options=["네이버수익", "네이버정보", "티스토리정보", "티스토리수익"], required=True),
            "링크": st.column_config.LinkColumn("링크")
        }
    )
    st.session_state.collector_data = edited_df

    if not edited_df.empty:
        # 엑셀 다운로드
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            edited_df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        st.download_button(
            label="📥 최종 리스트 엑셀로 저장 (일괄 생성용)",
            data=output.getvalue(),
            file_name=f"keywords_{datetime.now().strftime('%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

elif mode == "🟢 네이버 [수익형]":
    c1, c2 = st.columns(2)
    with c1:
        keyword, product = st.text_input("💎 키워드"), st.text_input("📦 상품명")
    with c2: link = st.text_input("🔗 제휴 링크")
    
    if st.button("원고 생성"):
        with st.spinner('작성 중...'):
            facts = hunt_realtime_info(keyword, 'sales')
            prompt = f"네이버 수익형 작성: {keyword}, {product}, {link}, {facts}. 2500자 이상, <b>강조, [TITLE]소제목[/TITLE], [[CTA_1]], [[CTA_2]]."
            try:
                res = model.generate_content(prompt).text
                res = re.sub(r'\[TITLE\](.*?)\[/TITLE\]', lambda m: get_naver_sales_h3(m.group(1)), res)
                cta = f'<span style="color: #00C73C; font-weight: bold;">👉 {product} 최저가: {link}</span>'
                res = re.sub(r'\[\[CTA_\d\]\]', cta, res)
                st.markdown(get_ftc_text(link) + "\n\n" + res, unsafe_allow_html=True)
            except Exception as e: st.error(e)

elif mode == "🟢 네이버 [정보성]":
    keyword = st.text_input("💎 정보성 키워드")
    if st.button("정보성 칼럼 생성"):
        with st.spinner('분석 중...'):
            facts = hunt_realtime_info(keyword, 'info')
            prompt = f"주제: {keyword} 정보성 글 JSON: {{'title':'','content':'HTML본문 [[H3]]제목[[/H3]], [IMG_1]~[IMG_3]','img_queries':[],'hashtags':''}}"
            try:
                raw = model.generate_content(prompt).text
                data = json.loads(re.search(r'\{.*\}', raw, re.DOTALL).group())
                content = re.sub(r'\[\[H3\]\](.*?)\[\[/H3\]\]', lambda m: get_naver_info_h3(m.group(1)), data['content'])
                imgs = get_info_images(data.get('img_queries', []), 3)
                for i, u in enumerate(imgs): content = content.replace(f"[IMG_{i+1}]", f"<img src='{u}' style='width:100%'>")
                st.markdown(f"<h1>{data['title']}</h1>{content}", unsafe_allow_html=True)
            except Exception as e: st.error(e)

elif mode == "🟠 티스토리 [정보성]":
    keyword = st.text_input("💎 티스토리 정보 키워드")
    if st.button("티스토리 정보 생성"):
        with st.spinner('작성 중...'):
            facts = hunt_realtime_info(keyword, 'info')
            try:
                raw = model.generate_content(f"티스토리 정보성 JSON: {keyword}, {facts}").text
                data = json.loads(re.search(r'\{.*\}', raw, re.DOTALL).group())
                h3s = re.findall(r'<h3>(.*?)</h3>', data['content'])
                for h in h3s: data['content'] = data['content'].replace(f'<h3>{h}</h3>', f'<br><h3 style="{get_tistory_premium_style()}">{h}</h3>', 1)
                st.text_area("HTML 소스", data['content'], height=300)
                st.markdown(data['content'], unsafe_allow_html=True)
            except Exception as e: st.error(e)

elif mode == "🟠 티스토리 [수익형]":
    c1, c2, c3 = st.columns(3)
    with c1: kw = st.text_input("💎 키워드")
    with c2: prod = st.text_input("📦 상품명")
    with c3: url = st.text_input("🔗 제휴 URL")
    if st.button("티스토리 수익형 생성"):
        with st.spinner('작성 중...'):
            facts = hunt_realtime_info(kw, 'sales')
            try:
                raw = model.generate_content(f"티스토리 수익형 JSON: {kw}, {prod}, {url}, {facts}").text
                data = json.loads(re.search(r'\{.*\}', raw, re.DOTALL).group())
                content = data['content']
                h3s = re.findall(r'<h3>(.*?)</h3>', content)
                for h in h3s: content = content.replace(f'<h3>{h}</h3>', get_tistory_sales_h3(h), 1)
                cta = create_tistory_sales_cta(prod, url)
                content = content.replace("[CTA_1]", cta).replace("[CTA_2]", cta)
                st.text_area("HTML 소스", content, height=300)
                st.markdown(content, unsafe_allow_html=True)
            except Exception as e: st.error(e)