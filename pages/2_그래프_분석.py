import streamlit as st
import pandas as pd
import numpy as np


class SurveyAnalyzer:
    """설문 데이터 분석 및 시각화를 담당하는 클래스"""

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def get_summary_metrics(self) -> dict:
        """1 요약 지표 계산"""
        total_responses = len(self.df)

        # AI 사용 시간 평균 계산 (결측치 제외)
        mean_ai_time = 0.0
        if "AI사용시간" in self.df.columns:
            valid_time = pd.to_numeric(self.df["AI사용시간"], errors="coerce")
            mean_ai_time = valid_time.mean() if not valid_time.empty else 0.0

        # AI 윤리 의식 평균 계산 (Q6 또는 Q6R 등 관련 문항 탐색)
        ethics_mean = 0.0
        ethics_cols = [c for c in self.df.columns if "Q" in c or "윤리" in c]
        if ethics_cols:
            ethics_data = self.df[ethics_cols].select_dtypes(include=[np.number])
            if not ethics_data.empty:
                ethics_mean = ethics_data.mean().mean()

        return {
            "total": total_responses,
            "mean_time": round(mean_ai_time, 1),
            "ethics_mean": round(ethics_mean, 2)
        }

    def get_college_comparison(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """2 정제 전후 단과대학별 응답자 수 비교 데이터 생성"""
        raw_counts = pd.Series()
        clean_counts = pd.Series()

        if "소속단과대학" in raw_df.columns:
            raw_counts = raw_df["소속단과대학"].value_counts()
        if "소속단과대학" in self.df.columns:
            clean_counts = self.df["소속단과대학"].value_counts()

        comparison_df = pd.DataFrame({
            "정제 전": raw_counts,
            "정제 후": clean_counts
        }).fillna(0)

        return comparison_df

    def render_tab_composition(self):
        """탭 1: 응답자 구성"""
        st.subheader("응답자 구성 분석")

        col1, col2 = st.columns(2)

        with col1:
            if "성별" in self.df.columns:
                st.markdown("**성별 분포**")
                gender_counts = self.df["성별"].value_counts()
                st.bar_chart(gender_counts)

        with col2:
            if "학년" in self.df.columns:
                st.markdown("**학년 분포**")
                grade_counts = self.df["학년"].value_counts().sort_index()
                st.bar_chart(grade_counts)

        if "소속단과대학" in self.df.columns:
            st.markdown("**단과대학별 분포**")
            college_counts = self.df["소속단과대학"].value_counts()
            st.bar_chart(college_counts)

    def render_tab_questions(self):
        """탭 2: 문항별 평균"""
        st.subheader("설문 문항별 평균 점수")

        # 숫자형 설문 문항(Q로 시작하는 컬럼 등) 추출
        q_cols = [c for c in self.df.columns if c.startswith("Q")]
        if q_cols:
            numeric_q = self.df[q_cols].select_dtypes(include=[np.number])
            if not numeric_q.empty:
                means = numeric_q.mean().round(2)
                mean_df = pd.DataFrame({"문항 평균": means})
                st.bar_chart(mean_df)
                st.dataframe(mean_df.T)
            else:
                st.info("분석할 수 있는 숫자형 문항 데이터가 없습니다.")
        else:
            st.info("문항(Q) 데이터를 찾을 수 없습니다.")

    def render_tab_group_comparison(self):
        """탭 3: 집단 비교 (학년별, 단과대학별 평균 및 인원 수)"""
        st.subheader("집단별 비교 분석")

        # 숫자형 문항 컬럼 파악
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        if "학년" in numeric_cols:
            numeric_cols.remove("학년")

        if not numeric_cols:
            st.info("비교할 수 있는 수치 데이터가 부족합니다.")
            return

        # 학년별 집단 비교
        if "학년" in self.df.columns:
            st.markdown("### 학년별 평균 및 인원 수")
            grade_grouped = self.df.groupby("학년")[numeric_cols].agg(["mean", "count"])
            grade_grouped = grade_grouped.round(2)
            st.dataframe(grade_grouped)

        # 단과대학별 집단 비교
        if "소속단과대학" in self.df.columns:
            st.markdown("### 단과대학별 평균 및 인원 수")
            college_grouped = self.df.groupby("소속단과대학")[numeric_cols].agg(["mean", "count"])
            college_grouped = college_grouped.round(2)
            st.dataframe(college_grouped)

    def render_tab_time_vs_score(self):
        """탭 4: 사용 시간과 점수 관계 분석"""
        st.subheader("AI 사용 시간과 주요 문항 관계")

        if "AI사용시간" in self.df.columns:
            q_cols = [c for c in self.df.columns if c.startswith("Q")]
            if q_cols:
                target_q = st.selectbox("분석할 문항 선택", options=q_cols)

                # 산점도 대신 기본 차트 활용을 위해 데이터프레임 구성
                plot_data = self.df[["AI사용시간", target_q]].dropna()
                if not plot_data.empty:
                    plot_data = plot_data.set_index("AI사용시간")
                    st.line_chart(plot_data)
                else:
                    plot_data = self.df[["AI사용시간", target_q]].dropna()
                    st.scatter_chart(plot_data, x="AI사용시간", y=target_q)
            else:
                st.info("분석할 문항(Q)이 존재하지 않습니다.")
        else:
            st.info("AI사용시간 데이터가 존재하지 않습니다.")


def main():
    st.set_page_config(page_title="설문 데이터 그래프 분석", layout="wide")

    st.title("설문 데이터 그래프 분석")
    st.markdown("---")

    # 데이터 로드 확인 (st.session_state["clean_df"] 우선 사용)
    clean_df = None
    raw_df = None

    if "clean_df" in st.session_state:
        clean_df = st.session_state["clean_df"]

    if "raw_df" in st.session_state:
        raw_df = st.session_state["raw_df"]

    # 세션에 데이터가 없을 경우 파일 업로드 안내
    if clean_df is None:
        st.warning("정제된 데이터가 존재하지 않습니다. 먼저 데이터 정제를 진행하거나 CSV 파일을 업로드해 주세요.")
        uploaded_file = st.file_uploader("정제된 CSV 파일 업로드", type=["csv"], key="fallback_upload")
        if uploaded_file is not None:
            clean_df = pd.read_csv(uploaded_file)
            st.session_state["clean_df"] = clean_df
        else:
            st.stop()

    # 분석 객체 생성
    analyzer = SurveyAnalyzer(clean_df)

    # 1. 요약 지표 표시
    st.subheader("요약 지표")
    metrics = analyzer.get_summary_metrics()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="유효 응답 수", value=f"{metrics['total']}명")
    with col2:
        st.metric(label="평균 AI 사용 시간", value=f"{metrics['mean_time']}분")
    with col3:
        st.metric(label="AI 윤리의식 평균", value=f"{metrics['ethics_mean']}점")

    st.markdown("---")

    # 2. 정제 전후 비교 (단과대학별 응답자 수 나란히 가로 막대 표시)
    st.subheader("정제 전후 단과대학별 응답자 수 비교")
    if raw_df is not None:
        comp_df = analyzer.get_college_comparison(raw_df)
        # 한글 이름은 가로 막대(st.bar_chart 활용)
        st.bar_chart(comp_df)
    else:
        st.info("원본 데이터(raw_df)가 없어 정제 전후 비교를 표시할 수 없습니다. 정제 페이지를 먼저 방문해 주세요.")

    st.markdown("---")

    # 3. 탭 4개 구성
    tab1, tab2, tab3, tab4 = st.tabs([
        "응답자 구성",
        "문항별 평균",
        "집단 비교",
        "사용 시간과 점수"
    ])

    with tab1:
        analyzer.render_tab_composition()

    with tab2:
        analyzer.render_tab_questions()

    with tab3:
        analyzer.render_tab_group_comparison()

    with tab4:
        analyzer.render_tab_time_vs_score()


if __name__ == "__main__":
    main()