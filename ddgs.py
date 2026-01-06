
# 이 파일은 기존 ddgs 라이브러리를 대체하여 안정성을 높이는 섀도우(Shadow) 모듈입니다.
# 원본 파일들의 로직을 수정하지 않고 검색 기능을 강화합니다.

import sys
import time
import random
import importlib.util
from collections import deque

# 재귀 임포트 방지를 위한 경로 처리
# 현재 디렉토리가 sys.path의 맨 앞에 있다면 제거하여 실제 라이브러리를 찾도록 함
_current_dir = sys.path[0]
if _current_dir in __file__:
    # 잠시 현재 경로를 path에서 제외
    sys.path = [p for p in sys.path if p != _current_dir]
    try:
        # 실제 duckduckgo_search 또는 ddgs 라이브러리 임포트 시도
        import duckduckgo_search
        # 패키지 구조에 따라 DDGS 위치가 다를 수 있음
        if hasattr(duckduckgo_search, 'DDGS'):
            RealDDGS = duckduckgo_search.DDGS
        else:
            # ddgs 모듈로 시도
            import ddgs
            RealDDGS = ddgs.DDGS
    except ImportError:
        # 라이브러리가 아예 없는 경우 (매우 드문 케이스, 설치 필요)
        try:
            import ddgs
            RealDDGS = ddgs.DDGS
        except:
            RealDDGS = None
    finally:
        # 경로 복구
        sys.path.insert(0, _current_dir)

class DDGS:
    def __init__(self, timeout=20):
        self.timeout = timeout
        self.real_ddgs = RealDDGS(timeout=timeout) if RealDDGS else None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def _safe_search(self, method_name, *args, **kwargs):
        """검색 실행 및 재시도, 실패 시 안전한 더미 데이터 반환"""
        if not self.real_ddgs:
            return self._fallback_results(*args, **kwargs)

        method = getattr(self.real_ddgs, method_name)
        
        # 최대 3회 재시도
        for attempt in range(3):
            try:
                # 제너레이터를 리스트로 변환하여 실제 데이터 확보 시도
                results = list(method(*args, **kwargs))
                if results:
                    return results
                # 결과가 비어있으면 잠시 대기 후 재시도 (일시적 차단 가능성)
                time.sleep(1 + attempt)
            except Exception as e:
                # 에러 발생 시 대기 후 재시도
                time.sleep(2 + attempt)
        
        # 3회 실패 시 폴백 데이터 반환
        return self._fallback_results(*args, **kwargs)

    def news(self, keywords, region='kr-kr', safesearch='off', timelimit=None, max_results=10):
        return self._safe_search('news', keywords, region=region, safesearch=safesearch, timelimit=timelimit, max_results=max_results)

    def text(self, keywords, region='kr-kr', safesearch='off', timelimit=None, max_results=10):
        return self._safe_search('text', keywords, region=region, safesearch=safesearch, timelimit=timelimit, max_results=max_results)
    
    def _fallback_results(self, keywords, **kwargs):
        """검색 실패 시 AI 환각 방지를 위한 에러 메시지 반환"""
        print(f"[System] 검색 연결 불안정: {keywords}")
        
        # 환각(Hallucination)의 원인이 되는 더미 데이터 제거
        # 검색 엔진이 차단되었을 때 AI가 엉뚱한 소설을 쓰지 않도록 명시적인 에러 텍스트 반환
        return [
            {
                "title": "❌ 검색 제한(Rate Limit) 감지됨",
                "body": "DuckDuckGo 검색 사용량이 많아 IP가 일시적으로 차단되었습니다. 잠시 후 다시 시도하거나 IP를 변경(공유기 재부팅 등)해 주세요. 이 상태에서는 정상적인 글 작성이 불가능합니다.",
                "url": "https://duckduckgo.com"
            }
        ]

# 기존 코드와의 호환성을 위해 모듈 레벨 함수들도 필요하다면 노출 (하지만 클래스 사용이 주류임)
