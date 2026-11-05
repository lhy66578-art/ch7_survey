import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="생성형 AI 활용 인식 조사 분석",
    page_icon="📊",
    layout="wide"
)

st.title("📊 부산대학교 인문사회계열 '생성형 AI 활용 인식' 조사")
st.markdown("---")

st.markdown("""
### 💡 연구 개요
본 애플리케이션은 **부산대학교 인문사회계열 1학년 학생의 '생성형 AI 활용 인식'** 설문 데이터 분석을 위한 Streamlit 멀티페이지 앱입니다.

#### 🧭 이용 안내
1. **사이드바(왼쪽)**에서 설문지 원본 파일(`survey_raw.csv`)을 업로드해 주세요.
2. 상단 메뉴 또는 왼쪽 페이지 목록에서 **[1_데이터_정제]** 페이지로 이동하여 데이터 정제 및 이상치·결측치 처리를 진행해 주세요.
""")

st.sidebar.header("📁 데이터 파일 업로드")
uploaded_file = st.sidebar.file_uploader("구글 설문지 CSV 파일을 업로드하세요", type=["csv"])

if uploaded_file is not None:
    try:
        # 데이터 로드 시도 (인코딩 자동 대응)
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8')
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding='cp949')

        st.session_state["raw_df"] = df
        st.sidebar.success("✅ 파일 업로드 완료!")

        st.info("왼쪽 메뉴에서 **[1_데이터_정제]** 페이지를 선택해 주세요.")

        with st.expander("🔍 업로드된 원본 데이터 미리보기"):
            st.dataframe(df.head())
            st.write(f"총 응답자 수: **{len(df)}명** | 전체 열 개수: **{len(df.columns)}개**")

    except Exception as e:
        st.sidebar.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
else:
    st.warning("⚠️ 계속 진행하려면 사이드바에서 `survey_raw.csv` 파일을 업로드해 주세요.")