# 백화점 3사 자동 수집기

신세계V · 현대백화점 · 롯데온 메인 프로모션 + MD 추천 상품을 30분마다 자동 수집합니다.

## 구조

```
.
├── .github/workflows/collect.yml   ← GitHub Actions 스케줄러
├── collectors/
│   ├── base.py                     ← 공통 베이스 클래스
│   ├── shinsegae.py                ← 신세계V
│   ├── hyundai.py                  ← 현대백화점
│   └── lotte.py                    ← 롯데온
├── collector_main.py               ← 통합 실행 진입점
├── analyzer.py                     ← 누적 통계 분석기
├── data/
│   ├── shinsegae/YYYY/MM/DD/       ← 신세계 원본 데이터
│   ├── hyundai/YYYY/MM/DD/         ← 현대 원본 데이터
│   └── lotte/YYYY/MM/DD/           ← 롯데 원본 데이터
└── stats/
    ├── shinsegae/summary.json      ← 신세계 누적 통계
    ├── hyundai/summary.json        ← 현대 누적 통계
    ├── lotte/summary.json          ← 롯데 누적 통계
    └── combined.json               ← 3사 통합 통계
```

## 로컬 실행

```bash
pip install -r requirements.txt
playwright install chromium --with-deps

# 3사 순차 수집
python collector_main.py

# 3사 병렬 수집 (빠름)
python collector_main.py --parallel

# 특정 사이트만
python collector_main.py --store hyundai

# 브라우저 보면서 디버그
python collector_main.py --store lotte --show

# 분석
python analyzer.py
```

## GitHub 설정 (최초 1회)

1. 레포 생성 후 코드 push
2. Settings → Actions → General → Workflow permissions → **Read and write** 선택
3. Actions 탭 → 수동 실행으로 첫 수집 확인
