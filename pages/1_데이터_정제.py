import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="데이터 정제", page_icon="🧹", layout="wide")

st.title("🧹 설문 데이터 정제 페이지")
st.markdown("사이드바 설정을 조정하여 설문 데이터를 정제하고 결과를 확인하세요.")

# 1. 파일 업로드 체크
if "raw_df" not in st.session_state:
    st.warning("⚠️ 업로드된 데이터가 없습니다. `Home` 페이지에서 먼저 CSV 파일을 업로드해 주세요.")
    st.stop()

raw_df = st.session_state["raw_df"].copy()
initial_rows = len(raw_df)

# ==========================================
# [사이드바] 설정 컨트롤
# ==========================================
st.sidebar.header("⚙️ 데이터 정제 설정")

# 1. AI 사용 시간 이상치 허용 범위 슬라이더 (분 단위, 예: 0 ~ 600분)
max_ai_time = st.sidebar.slider(
    "AI 사용 시간 이상치 허용 최대값 (분)",
    min_value=30, max_value=600, value=300, step=30,
    help="설정한 분을 초과하는 AI 사용 시간 응답은 이상치(결측치)로 처리됩니다."
)

# 2. 결측치 처리 방식 선택
na_action = st.sidebar.radio(
    "결측치(빈칸) 처리 방식",
    options=["그대로 두기", "행 삭제"],
    index=0,
    help="결측치가 포함된 행을 그대로 둘지, 일괄 삭제할지 선택합니다."
)

st.markdown("---")

# ==========================================
# [정제 프로세스 수행] (원본 보존 및 복사본 정제)
# ==========================================
df_clean = raw_df.copy()
cleaning_logs = []

# 1. 열 제목 축약
original_columns = list(df_clean.columns)
# 구글 설문지 기본형태 가정: 타임스탬프, 성별, 학년, 소속단과대학, AI사용시간, Q1~Q6(6개), 서술형
num_cols = len(df_clean.columns)
new_cols = ['타임스탬프', '성별', '학년', '소속단과대학', 'AI사용시간']
q_count = num_cols - len(new_cols) - 1
if q_count > 0:
    new_cols.extend([f'Q{i}' for i in range(1, q_count + 1)])
new_cols.append('서술형')

# 실제 컬럼 수와 맞지 않을 경우 유연하게 대응
if len(original_columns) == len(new_cols):
    df_clean.columns = new_cols
    cleaning_logs.append("✅ 1. 열 제목 축약 완료 (타임스탬프, 성별, 학년, 소속단과대학, AI사용시간, Q1~Q6..., 서술형)")
else:
    # 컬럼 수가 다를 경우 앞뒤 주요 컬럼만 매핑하고 나머지는 유지
    fallback_cols = original_columns.copy()
    if len(fallback_cols) > 0: fallback_cols[0] = '타임스탬프'
    if len(fallback_cols) > 1: fallback_cols[1] = '성별'
    if len(fallback_cols) > 2: fallback_cols[2] = '학년'
    if len(fallback_cols) > 3: fallback_cols[3] = '소속단과대학'
    if len(fallback_cols) > 4: fallback_cols[4] = 'AI사용시간'
    if len(fallback_cols) > 5: fallback_cols[-1] = '서술형'
    df_clean.columns = fallback_cols
    cleaning_logs.append("⚠️ 1. 열 제목 축약: 컬럼 수 차이로 기본 구조 기반 일부 자동 매핑 완료")

# 2. 중복 제거 (타임스탬프 제외 모든 열이 같으면 첫 행만 남김)
dup_subset = [col for col in df_clean.columns if col != '타임ส탬프']
before_dup = len(df_clean)
df_clean = df_clean.drop_duplicates(subset=dup_subset, keep='first')
removed_dup_count = before_dup - len(df_clean)
cleaning_logs.append(f"✅ 2. 중복 제거 완료: 중복 응답 {removed_dup_count}개 행 제거")

# 3. 학년 표기 통일 ('1학년', '일학년' -> 숫자)
if '학년' in df_clean.columns:
    def parse_grade(val):
        if pd.isna(val): return pd.NA
        val_str = str(val)
        numbers = re.findall(r'\d+', val_str)
        if numbers:
            return int(numbers[0])
        if '일' in val_str or '첫' in val_str:
            return 1
        if '이' in val_str:
            return 2
        return val


    df_clean['학년'] = df_clean['학년'].apply(parse_grade)
    cleaning_logs.append("✅ 3. 학년 표기 통일 완료 (숫자형으로 변환)")

# 4. 단과대학 분류
if '소속단과대학' in df_clean.columns:
    def map_college(val):
        if pd.isna(val): return '기타'
        v = str(val)
        if '인문' in v:
            return '인문대학'
        elif '사과' in v or '사회' in v:
            return '사회과학대학'
        elif '경통' in v or '경제' in v:
            return '경제통상대학'
        elif '경영' in v:
            return '경영대학'
        elif '사범' in v:
            return '사범대학'
        else:
            return '기타'


    df_clean['소속단과대학'] = df_clean['소속단과대학'].apply(map_college)
    cleaning_logs.append("✅ 4. 단과대학 분류 완료 (인문/사회과학/경제통상/경영/사범/기타)")

# 5. 이상치 처리 (AI사용시간 '1시간 30분' -> 90 분 단위 숫자 + 사이드바 기준 적용)
if 'AI사용시간' in df_clean.columns:
    def parse_ai_time(val):
        if pd.isna(val): return pd.NA
        v_str = str(val).strip()
        # 이미 숫자 형태인 경우
        if v_str.isdigit():
            return int(v_str)

        total_mins = 0
        # 시간 추출 (예: 1시간, 2시간)
        hour_match = re.search(r'(\d+)\s*시간', v_str)
        if hour_match:
            total_mins += int(hour_match.group(1)) * 60

        # 분 추출 (예: 30분)
        min_match = re.search(r'(\d+)\s*분', v_str)
        if min_match:
            total_mins += int(min_match.group(1))

        if total_mins == 0 and not hour_match and not min_match:
            # 숫지만 추출 시도
            nums = re.findall(r'\d+', v_str)
            if nums:
                total_mins = int(nums[0])
            else:
                return pd.NA

        # 사이드바에서 설정한 허용 범위 초과 시 이상치(결측치)로 처리
        if total_mins > max_ai_time or total_mins < 0:
            return pd.NA

        return total_mins


    df_clean['AI사용시간'] = df_clean['AI사용시간'].apply(parse_ai_time)
    cleaning_logs.append(f"✅ 5. AI사용시간 정제 완료 (분 단위 변환 및 허용범위 {max_ai_time}분 기준 이상치 처리)")

# 6. 결측치 확인 및 처리 방식 적용
missing_counts = df_clean.isnull().sum()
total_missing = missing_counts.sum()

if na_action == "행 삭제":
    before_dropna = len(df_clean)
    df_clean = df_clean.dropna()
    dropped_na_rows = before_dropna - len(df_clean)
    cleaning_logs.append(f"✅ 6. 결측치 처리 ('행 삭제' 선택): 결측 포함 행 {dropped_na_rows}개 삭제")
else:
    cleaning_logs.append("✅ 6. 결측치 처리 ('그대로 두기' 선택): 빈칸 유지")

# 7. 점수 역산 계산 (Q6이 존재하고 숫자형태일 경우 Q6R = 6 - Q6 계산)
q6_col = 'Q6' if 'Q6' in df_clean.columns else (f'Q{q_count}' if q_count > 0 else None)
if q6_col and q6_col in df_clean.columns:
    df_clean[q6_col] = pd.to_numeric(df_clean[q6_col], errors='coerce')
    df_clean['Q6R'] = 6 - df_clean[q6_col]
    cleaning_logs.append(f"✅ 7. 점수 역산 완료 (Q6R = 6 - {q6_col} 생성)")
else:
    cleaning_logs.append("ℹ️ 7. 점수 역산: 대상 문항(Q6)을 찾지 못해 건너<건너뜀>")

# ==========================================
# [가운데 화면] 결과 표시
# ==========================================

# 맨 위 제목 및 응답자 수 / 전체 데이터 요약 카드
st.markdown("### 📈 데이터 현황 요약")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="원본 응답자 수", value=f"{initial_rows}명")
with col2:
    st.metric(label="정제 후 응답자 수", value=f"{len(df_clean)}명", delta=f"{len(df_clean) - initial_rows}명")
with col3:
    st.metric(label="총 결측치(빈칸) 수", value=f"{total_missing}개")
with col4:
    st.metric(label="이상치 허용 기준", value=f"최대 {max_ai_time}분")

st.markdown("---")

# 열별 빈칸 수 표시 테이블
with st.expander("📊 열별 빈칸(결측치) 개수 상세 확인"):
    missing_df = pd.DataFrame({'결측치 수': missing_counts})
    st.dataframe(missing_df.T)

# 데이터 정제 결과 카드(로그) 및 정제된 데이터 표시
st.markdown("### 📝 데이터 정제 결과 및 로그")
with st.container():
    for log in cleaning_logs:
        st.markdown(f"- {log}")

st.markdown("### ✨ 최종 정제된 데이터 미리보기")
st.dataframe(df_clean)

# ==========================================
# 세션 스토리지 저장 및 CSV 다운로드
# ==========================================
st.session_state["clean_df"] = df_clean

st.markdown("---")
st.subheader("💾 정제된 데이터 저장 및 다운로드")

csv_data = df_clean.to_csv(index=False).encode('utf-8-sig')

st.download_button(
    label="📥 정제된 데이터 CSV로 내려받기",
    data=csv_data,
    file_name="survey_cleaned.csv",
    mime="text/csv",
)