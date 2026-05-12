import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# 1. 페이지 설정 및 데이터 연결
st.set_page_config(page_title="지하철 공기질 분석 대시보드", layout="wide")

DB_FILE = "subway_airquality.db"

def get_connection():
    """데이터베이스 연결 함수"""
    if not os.path.exists(DB_FILE):
        return None
    return sqlite3.connect(DB_FILE)

# DB 파일 존재 확인
conn = get_connection()

if conn is None:
    st.error(f"❌ 데이터베이스 파일을 찾을 수 없습니다! '{DB_FILE}' 파일이 같은 폴더에 있는지 확인해주세요.")
    st.stop()

# 메인 타이틀
st.title("🚇 서울시 지하철 노선별 공기질 & 승하차인원 분석")
st.markdown("이 대시보드는 지하철 공기질 상태와 이용객 수의 상관관계를 시각화합니다.")

# 2. 사이드바 - 노선 선택 필터
st.sidebar.header("🔍 필터 설정")
# 전체 노선명 가져오기
line_query = "SELECT DISTINCT 노선명 FROM 역사정보 ORDER BY 노선명"
all_lines = pd.read_sql(line_query, conn)['노선명'].tolist()
selected_lines = st.sidebar.multiselect("분석할 노선을 선택하세요", all_lines, default=all_lines)

# 필터링을 위한 SQL 조건문 생성
line_filter = f"WHERE T1.노선명 IN ({str(selected_lines)[1:-1]})" if selected_lines else "WHERE 1=0"

# --- 차트 1: 승하차 인원 상위 20개 역의 미세먼지 수치 ---
st.divider()
st.subheader("1️⃣ 승하차 인원 TOP 20 역의 미세먼지 농도")

query1 = f"""
SELECT T1.역명, AVG(T2.미세먼지) AS 미세먼지, AVG(T2.초미세먼지) AS 초미세먼지, SUM(T3.총승하차인원) AS 총승하차인원
FROM 역사정보 T1
JOIN 공기질측정 T2 ON T1.역ID = T2.역ID
JOIN 승하차인원 T3 ON T1.역ID = T3.역ID
{line_filter}
GROUP BY T1.역ID
ORDER BY 총승하차인원 DESC
LIMIT 20
"""
df1 = pd.read_sql(query1, conn)

if not df1.empty:
    col1, col2 = st.columns([3, 1])
    with col1:
        # 가로 막대 차트 시각화
        fig1 = px.bar(df1, x=['미세먼지', '초미세먼지'], y='역명', 
                     title="이용객 상위 20개 역의 먼지 농도",
                     barmode='group', orientation='h',
                     labels={'value': '농도 (㎍/㎥)', '역명': '지하철역'})
        # 환경부 기준선 추가 (미세먼지 75)
        fig1.add_vline(x=75, line_dash="dash", line_color="red", annotation_text="환경부 기준(75)")
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        st.info("**사용된 SQL**")
        st.code(query1, language='sql')
        st.success("**인사이트**\n1. 이용객이 많은 역들의 미세먼지 농도를 한눈에 비교할 수 있습니다.\n2. 붉은 점선(75㎍/㎥)을 넘는 역은 공기질 관리가 시급함을 의미합니다.")
else:
    st.warning("선택된 노선에 대한 데이터가 없습니다.")


# --- 차트 2: 총승하차인원 vs 미세먼지 산점도 ---
st.divider()
st.subheader("2️⃣ 이용객 수와 미세먼지 농도의 상관관계")

query2 = f"""
SELECT T1.역명, SUM(T3.총승하차인원) AS 총승하차인원, AVG(T2.미세먼지) AS 미세먼지, AVG(T2.이산화탄소) AS 이산화탄소
FROM 역사정보 T1
JOIN 공기질측정 T2 ON T1.역ID = T2.역ID
JOIN 승하차인원 T3 ON T1.역ID = T3.역ID
{line_filter}
GROUP BY T1.역ID
"""
df2 = pd.read_sql(query2, conn)

if not df2.empty:
    col1, col2 = st.columns([3, 1])
    with col1:
        fig2 = px.scatter(df2, x='총승하차인원', y='미세먼지', color='이산화탄소',
                         hover_name='역명', trendline="ols",
                         title="이용객 수 대비 미세먼지 농도 (색상: 이산화탄소)",
                         labels={'총승하차인원': '총 승하차 인원 (명)', '미세먼지': '평균 미세먼지 (㎍/㎥)'})
        st.plotly_chart(fig2, use_container_width=True)
    
    with col2:
        st.info("**사용된 SQL**")
        st.code(query2, language='sql')
        st.success("**인사이트**\n1. 추세선(Trendline)을 통해 이용객 증가가 미세먼지 상승에 미치는 영향을 파악합니다.\n2. 색상이 밝을수록(노란색) 해당 역의 환기 상태(CO2)가 좋지 않음을 나타냅니다.")


# --- 차트 3: 노선별 평균 공기질 비교 ---
st.divider()
st.subheader("3️⃣ 노선별 평균 공기질 비교")

query3 = f"""
SELECT 노선명, AVG(미세먼지) AS 미세먼지, AVG(초미세먼지) AS 초미세먼지, AVG(이산화탄소) AS 이산화탄소
FROM 역사정보 T1
JOIN 공기질측정 T2 ON T1.역ID = T2.역ID
GROUP BY 노선명
ORDER BY CAST(REPLACE(노선명, '호선', '') AS INTEGER)
"""
df3 = pd.read_sql(query3, conn)

if not df3.empty:
    col1, col2 = st.columns([3, 1])
    with col1:
        fig3 = px.bar(df3, x='노선명', y=['미세먼지', '초미세먼지', '이산화탄소'],
                     title="노선별 주요 공기질 지표 평균",
                     barmode='group',
                     labels={'value': '수치', 'variable': '측정항목'})
        st.plotly_chart(fig3, use_container_width=True)
    
    with col2:
        st.info("**사용된 SQL**")
        st.code(query3, language='sql')
        st.success("**인사이트**\n1. '호선' 글자를 제거하고 숫자로 변환(CAST)하여 1호선부터 순서대로 정렬했습니다.\n2. 특정 노선(예: 노후 노선)의 공기질 지표가 타 노선보다 높은지 한눈에 보입니다.")

conn.close()