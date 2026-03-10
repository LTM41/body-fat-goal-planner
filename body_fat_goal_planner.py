import math
import uuid
import os
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st


PROGRESS_CSV = "body_fat_goal_progress.csv"
STATS_CSV = "body_fat_app_stats.csv"


# =============================
# CALCULATIONS
# =============================
def navy_body_fat(sex, height, waist, neck, hips=0):
    sex = str(sex).strip().lower()

    if min(height, waist, neck) <= 0:
        raise ValueError("Height, waist, and neck must all be greater than zero.")

    if sex == "male":
        if waist <= neck:
            raise ValueError("For males, waist must be larger than neck.")
        return round(
            86.010 * math.log10(waist - neck)
            - 70.041 * math.log10(height)
            + 36.76,
            2,
        )

    if sex == "female":
        if hips <= 0:
            raise ValueError("For females, hips must be greater than zero.")
        if (waist + hips) <= neck:
            raise ValueError("For females, waist + hips must be larger than neck.")
        return round(
            163.205 * math.log10(waist + hips - neck)
            - 97.684 * math.log10(height)
            - 78.387,
            2,
        )

    raise ValueError("Sex must be Male or Female.")


def body_composition(weight, body_fat):
    fat_mass = round(weight * (body_fat / 100), 2)
    lean_mass = round(weight - fat_mass, 2)
    return fat_mass, lean_mass


def goal_weight_for_target_body_fat(lean_mass, target_body_fat):
    if not (0 < target_body_fat < 100):
        raise ValueError("Target body fat must be between 0 and 100.")
    return round(lean_mass / (1 - target_body_fat / 100), 2)


def estimated_weeks_to_goal(current_weight, goal_weight, weekly_change=1.25):
    if weekly_change <= 0:
        return 0
    if current_weight == goal_weight:
        return 0
    return math.ceil(abs(current_weight - goal_weight) / weekly_change)


def projected_goal_date(weeks_to_goal):
    return (datetime.now() + timedelta(weeks=weeks_to_goal)).strftime("%Y-%m-%d")


def bmi(weight_lbs, height_inches):
    return round((weight_lbs / (height_inches ** 2)) * 703, 2)


def bmi_category(bmi_value):
    if bmi_value < 18.5:
        return "Underweight"
    if bmi_value < 25:
        return "Healthy"
    if bmi_value < 30:
        return "Overweight"
    return "Obese"


def waist_to_height_ratio(waist_inches, height_inches):
    return round(waist_inches / height_inches, 3)


def whtr_category(ratio):
    if ratio < 0.5:
        return "Healthy"
    if ratio < 0.6:
        return "Moderate risk"
    return "High risk"


def body_fat_category(sex, body_fat_value):
    sex = str(sex).strip().lower()

    if sex == "male":
        if body_fat_value < 6:
            return "Essential fat"
        if body_fat_value < 14:
            return "Athletic"
        if body_fat_value < 18:
            return "Fit"
        if body_fat_value < 25:
            return "Average"
        return "Overweight"

    if sex == "female":
        if body_fat_value < 14:
            return "Essential fat"
        if body_fat_value < 21:
            return "Athletic"
        if body_fat_value < 25:
            return "Fit"
        if body_fat_value < 32:
            return "Average"
        return "Overweight"

    return "Unknown"


def predict_date_for_weight(current_weight, target_weight, weekly_change):
    if weekly_change <= 0:
        return "N/A"
    if current_weight == target_weight:
        return "Reached"
    weeks = math.ceil(abs(current_weight - target_weight) / weekly_change)
    return (datetime.now() + timedelta(weeks=weeks)).strftime("%Y-%m-%d")


def progress_ratio(current_bf, start_bf=30, target_bf=18):
    if start_bf <= target_bf:
        return 0.0
    ratio = (start_bf - current_bf) / (start_bf - target_bf)
    return max(0.0, min(1.0, ratio))


def gout_risk_zone_from_body_fat(body_fat_value):
    if body_fat_value < 20:
        return "Healthy", "#2ECC71", "Lower risk zone"
    if body_fat_value <= 25:
        return "Average", "#F4B400", "Middle zone"
    return "Higher risk", "#E53935", "Higher risk zone"


def render_body_fat_zone_bar(value, min_value=5, max_value=50):
    safe_value = max(min_value, min(max_value, float(value)))
    marker_pct = ((safe_value - min_value) / (max_value - min_value)) * 100
    zone_label, zone_color, zone_text = gout_risk_zone_from_body_fat(safe_value)

    st.markdown(
        f"""
        <div style="margin-top:0.35rem;margin-bottom:0.35rem;">
            <div style="font-size:0.95rem;font-weight:600;">Body fat zone guide (5% to 50%)</div>
            <div class="zone-marker-wrap">
                <div class="zone-marker-bubble" style="left:{marker_pct}%; background:{zone_color};">{safe_value:.1f}%</div>
                <div class="zone-marker-glow" style="left:{marker_pct}%; background:{zone_color};"></div>
                <div class="zone-bar-shell">
                    <div style="position:absolute;left:0;width:33.33%;height:100%;background:#2ECC71;"></div>
                    <div style="position:absolute;left:33.33%;width:11.11%;height:100%;background:#F4B400;"></div>
                    <div style="position:absolute;left:44.44%;width:55.56%;height:100%;background:#E53935;"></div>
                    <div style="position:absolute;left:calc({marker_pct}% - 2px);top:0;width:4px;height:100%;background:#111827;z-index:2;"></div>
                </div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:0.78rem;margin-top:0.4rem;gap:8px;flex-wrap:wrap;">
                <span>5%</span>
                <span style="color:#1E9E5A;font-weight:600;">Healthy</span>
                <span style="color:#D69200;font-weight:600;">Average</span>
                <span style="color:#C62828;font-weight:600;">Higher risk</span>
                <span>50%</span>
            </div>
            <div style="margin-top:0.45rem;padding:0.5rem 0.78rem;border-radius:0.8rem;background:{zone_color};color:white;font-weight:800;display:inline-block;box-shadow:0 12px 26px rgba(31,41,55,0.16);">
                {zone_label} — {zone_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def activity_multiplier_from_label(label):
    activity_map = {
        "Sedentary": 1.2,
        "Lightly active": 1.375,
        "Moderately active": 1.55,
        "Very active": 1.725,
        "Extra active": 1.9,
    }
    return activity_map.get(label, 1.55)


def bmr_mifflin(sex, weight_lbs, height_inches, age):
    weight_kg = weight_lbs * 0.45359237
    height_cm = height_inches * 2.54

    if str(sex).strip().lower() == "male":
        return round((10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5, 0)
    return round((10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161, 0)


def maintenance_calories(sex, weight_lbs, height_inches, age, activity_label):
    bmr_value = bmr_mifflin(sex, weight_lbs, height_inches, age)
    multiplier = activity_multiplier_from_label(activity_label)
    return round(bmr_value * multiplier, 0)


def cutting_calories(maintenance_cals, deficit=500):
    return max(1200, round(maintenance_cals - deficit, 0))


def macro_targets_from_calories(calories, protein_pct=30, carbs_pct=40, fats_pct=30):
    protein_cals = calories * (protein_pct / 100)
    carbs_cals = calories * (carbs_pct / 100)
    fats_cals = calories * (fats_pct / 100)

    protein_g = round(protein_cals / 4)
    carbs_g = round(carbs_cals / 4)
    fats_g = round(fats_cals / 9)

    return {
        "calories": round(calories),
        "protein_g": protein_g,
        "carbs_g": carbs_g,
        "fats_g": fats_g,
    }


def build_goal_macro_table(
    sex,
    height_inches,
    age,
    activity_label,
    goal_weights,
    deficit,
    protein_pct,
    carbs_pct,
    fats_pct,
):
    rows = []

    for gw in goal_weights:
        maint = maintenance_calories(sex, gw, height_inches, age, activity_label)
        cut = cutting_calories(maint, deficit)
        macros = macro_targets_from_calories(
            cut,
            protein_pct=protein_pct,
            carbs_pct=carbs_pct,
            fats_pct=fats_pct,
        )

        rows.append(
            {
                "Weight": f"{gw} lbs",
                "Calories": int(cut),
                "Protein": f"{macros['protein_g']} g",
                "Carbs": f"{macros['carbs_g']} g",
                "Fats": f"{macros['fats_g']} g",
            }
        )

    return pd.DataFrame(rows)


def build_weight_milestones(current_weight, goal_weight):
    low_bound = int(math.floor(min(current_weight, goal_weight) / 5.0) * 5)
    high_bound = int(math.ceil(max(current_weight, goal_weight) / 5.0) * 5)

    milestones = list(range(high_bound, low_bound - 1, -5))

    if round(current_weight) not in milestones:
        milestones.append(round(current_weight))
    if round(goal_weight) not in milestones:
        milestones.append(round(goal_weight))

    milestones = sorted(set([m for m in milestones if m > 0]), reverse=True)
    return milestones


# New function for cleaner macro goal weights (6, rounded to 5-lb increments)
def build_macro_weight_targets(current_weight, goal_weight, count=6):
    current_weight = float(current_weight)
    goal_weight = float(goal_weight)

    if current_weight == goal_weight:
        return [int(round(current_weight / 5.0) * 5)]

    count = max(2, int(count))
    step = (goal_weight - current_weight) / (count - 1)

    weights = []
    for i in range(count):
        value = current_weight + (step * i)
        rounded_value = int(round(value / 5.0) * 5)
        weights.append(rounded_value)

    weights[0] = int(round(current_weight / 5.0) * 5)
    weights[-1] = int(round(goal_weight / 5.0) * 5)

    cleaned = []
    for w in weights:
        if w not in cleaned and w > 0:
            cleaned.append(w)

    if len(cleaned) < count:
        milestone_candidates = build_weight_milestones(current_weight, goal_weight)
        if goal_weight >= current_weight:
            extra_candidates = sorted(set(milestone_candidates))
        else:
            extra_candidates = sorted(set(milestone_candidates), reverse=True)
        for candidate in extra_candidates:
            if candidate not in cleaned:
                cleaned.append(candidate)
            if len(cleaned) >= count:
                break

    return sorted(set(cleaned), reverse=(goal_weight < current_weight))[:count]




def ensure_progress_csv_exists():
    if not os.path.isfile(PROGRESS_CSV):
        pd.DataFrame(columns=["entry_id", "date", "weight", "waist", "body_fat"]).to_csv(PROGRESS_CSV, index=False)


def load_progress_df():
    ensure_progress_csv_exists()
    df = pd.read_csv(PROGRESS_CSV)

    if "entry_id" not in df.columns:
        df.insert(0, "entry_id", [uuid.uuid4().hex[:8] for _ in range(len(df))])
        df.to_csv(PROGRESS_CSV, index=False)

    if df.empty:
        return df

    if "date" in df.columns:
        df["date"] = df["date"].astype(str)
        df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ["weight", "waist", "body_fat"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def save_progress_entry(date_value, weight_value, waist_value, body_fat_value):
    df = load_progress_df()
    if "date_dt" in df.columns:
        df = df.drop(columns=["date_dt"])

    new_row = pd.DataFrame(
        [
            {
                "entry_id": uuid.uuid4().hex[:8],
                "date": str(date_value),
                "weight": round(float(weight_value), 2),
                "waist": round(float(waist_value), 2),
                "body_fat": round(float(body_fat_value), 2),
            }
        ]
    )
    df = pd.concat([df, new_row], ignore_index=True)
    df["date"] = df["date"].astype(str)
    df = df.sort_values(["date", "entry_id"]).reset_index(drop=True)
    df.to_csv(PROGRESS_CSV, index=False)


def delete_progress_entry(entry_id):
    df = load_progress_df()
    if df.empty:
        return
    if "date_dt" in df.columns:
        df = df.drop(columns=["date_dt"])
    df = df[df["entry_id"] != str(entry_id)].copy()
    df.to_csv(PROGRESS_CSV, index=False)



def progress_csv_bytes():
    df = load_progress_df()
    if "date_dt" in df.columns:
        df = df.drop(columns=["date_dt"])
    if df.empty:
        df = pd.DataFrame(columns=["entry_id", "date", "weight", "waist", "body_fat"])
    return df.to_csv(index=False).encode("utf-8")


def ensure_stats_csv_exists():
    if not os.path.isfile(STATS_CSV):
        pd.DataFrame([{"metric": "total_visits", "value": 0}]).to_csv(STATS_CSV, index=False)


def get_total_visits():
    ensure_stats_csv_exists()
    df = pd.read_csv(STATS_CSV)
    if df.empty or "metric" not in df.columns or "value" not in df.columns:
        df = pd.DataFrame([{"metric": "total_visits", "value": 0}])
        df.to_csv(STATS_CSV, index=False)
        return 0
    row = df.loc[df["metric"] == "total_visits", "value"]
    if row.empty:
        df = pd.concat([df, pd.DataFrame([{"metric": "total_visits", "value": 0}])], ignore_index=True)
        df.to_csv(STATS_CSV, index=False)
        return 0
    return int(pd.to_numeric(row.iloc[0], errors="coerce") or 0)


def register_visit_once_per_session():
    ensure_stats_csv_exists()
    if st.session_state.get("visit_registered", False):
        return get_total_visits()

    df = pd.read_csv(STATS_CSV)
    if df.empty or "metric" not in df.columns or "value" not in df.columns:
        df = pd.DataFrame([{"metric": "total_visits", "value": 0}])

    if "total_visits" not in df["metric"].tolist():
        df = pd.concat([df, pd.DataFrame([{"metric": "total_visits", "value": 0}])], ignore_index=True)

    current_value = df.loc[df["metric"] == "total_visits", "value"].iloc[0]
    current_value = int(pd.to_numeric(current_value, errors="coerce") or 0)
    new_value = current_value + 1
    df.loc[df["metric"] == "total_visits", "value"] = new_value
    df.to_csv(STATS_CSV, index=False)
    st.session_state["visit_registered"] = True
    return new_value




# =============================
# APP
# =============================
st.set_page_config(page_title="Body Fat Goal Planner", layout="wide")
total_visits = register_visit_once_per_session()

st.markdown(
    """
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 2.4rem;
    padding-left: 1.5rem;
    padding-right: 1.5rem;
    max-width: 1500px;
    margin: 0 auto;
}

    :root {
        color-scheme: light !important;
    }

    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif;
        color: #1f2937 !important;
        background: #f8fbff !important;
    }

.stApp {
    background:
        radial-gradient(circle at top right, rgba(163, 191, 250, 0.16), transparent 26%),
        radial-gradient(circle at bottom left, rgba(182, 226, 211, 0.14), transparent 24%),
        linear-gradient(180deg, #f8fbff 0%, #f5f7fb 52%, #fdfaf7 100%) !important;
    color: #1f2937 !important;
}

    section[data-testid="stSidebar"],
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    .main,
    .block-container {
        background: transparent !important;
        color: #1f2937 !important;
    }

    h1, h2, h3, h4, h5, h6,
    p, label, span, div, small, strong, em, li {
        color: #1f2937 !important;
    }


    a, a:visited {
        color: #4f7ddf !important;
    }

    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] *,
    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] *,
    [data-testid="stText"],
    [data-testid="stText"] * {
        color: #1f2937 !important;
    }

[data-baseweb="select"] > div,
[data-baseweb="input"] > div,
[data-baseweb="base-input"],
textarea,
input {
    background: #ffffff !important;
    color: #1f2937 !important;
    border-color: #d7dee8 !important;
}

textarea::placeholder,
input::placeholder {
    color: #6b7280 !important;
}

[data-baseweb="select"] *,
[data-baseweb="input"] *,
[data-baseweb="base-input"] * {
    color: #1f2937 !important;
}

    table, thead, tbody, tr, th, td,
    [data-testid="stDataFrame"],
    [data-testid="stDataFrame"] * {
        color: #1f2937 !important;
        background: transparent !important;
    }

[data-testid="stMetricValue"] {
    font-size: 1.08rem;
    line-height: 1.35;
    white-space: normal;
    word-break: break-word;
    overflow-wrap: anywhere;
}

[data-testid="stMetricLabel"] {
    font-size: 0.82rem;
    white-space: normal;
    word-break: break-word;
}

[data-testid="stMetric"] {
    background: transparent;
    border: none;
    padding: 0;
    border-radius: 0;
    box-shadow: none;
    backdrop-filter: none;
    min-height: 0;
}


    .zone-marker-wrap *,
    .zone-bar-shell *,
    [data-testid="stExpander"] *,
    [data-testid="stSelectbox"] *,
    [data-testid="stNumberInput"] *,
    [data-testid="stDateInput"] *,
    [data-testid="stTextArea"] *,
    [data-testid="stSlider"] * {
        color: #1f2937 !important;
    }


.beauty-divider {
    height: 1px;
    width: 100%;
    background: linear-gradient(90deg, rgba(163,191,250,0) 0%, rgba(163,191,250,0.42) 50%, rgba(163,191,250,0) 100%);
    margin: 6px 0 14px 0;
}

.zone-marker-wrap {
    position: relative;
    margin-top: 8px;
}

.zone-marker-bubble {
    position: absolute;
    top: -8px;
    transform: translateX(-50%);
    padding: 6px 12px;
    border-radius: 999px;
    color: white;
    font-size: 0.76rem;
    font-weight: 800;
    box-shadow: 0 10px 22px rgba(31, 41, 55, 0.18);
    white-space: nowrap;
    z-index: 3;
}

.zone-marker-glow {
    position: absolute;
    top: 16px;
    width: 18px;
    height: 18px;
    border-radius: 999px;
    transform: translateX(-50%);
    filter: blur(10px);
    opacity: 0.48;
    z-index: 1;
}

.zone-bar-shell {
    position: relative;
    height: 22px;
    border-radius: 999px;
    overflow: hidden;
    border: 1px solid #d1d5db;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
    margin-top: 34px;
}

    [data-testid="stExpander"] {
        border: 1px solid #e7ebf1;
        border-radius: 18px;
        overflow: hidden;
        background: rgba(255, 255, 255, 0.96) !important;
        color: #1f2937 !important;
    }

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-baseweb="base-input"] {
    border-radius: 16px !important;
}

    .stButton > button {
        border-radius: 18px;
        border: 1px solid rgba(231, 235, 241, 0.98);
        background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(244,247,251,0.92) 100%) !important;
        box-shadow: 0 10px 22px rgba(114, 132, 160, 0.10);
        font-weight: 700;
        padding-top: 0.55rem;
        padding-bottom: 0.55rem;
        color: #1f2937 !important;
    }

    button, button *,
    [data-testid="baseButton-secondary"],
    [data-testid="baseButton-secondary"] *,
    [data-testid="baseButton-primary"],
    [data-testid="baseButton-primary"] * {
        color: #1f2937 !important;
    }

</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<div id="top"></div>', unsafe_allow_html=True)
title_col, visits_col = st.columns([0.82, 0.18])
with title_col:
    st.title("Body Fat Burning Planner 🔥")
    st.caption("Calm, honest fat-loss planning — realistic timelines, macro guidance and progress tracking.")
with visits_col:
    st.markdown(
        f"""
        <div style="text-align:right; padding-top:14px; opacity:0.88;">
            <div style="font-size:0.62rem; font-weight:700; color:#7b8794; margin-bottom:1px; letter-spacing:0.06em; text-transform:uppercase;">Visitors</div>
            <div style="font-size:0.92rem; font-weight:700; color:#4b5563;">{total_visits}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div style="padding:4px 2px 10px 2px; margin-top:4px;">
        <div style="font-size:0.9rem;font-weight:700;margin-bottom:6px;">Quick links</div>
        <div style="font-size:0.85rem;line-height:1.8;margin-bottom:10px;">
            <a href="#inputs">Inputs</a> ·
            <a href="#results">Results</a> ·
            <a href="#progress">Progress</a> ·
            <a href="#milestones">Milestones</a> ·
            <a href="#macros">Macros</a> ·
            <a href="#top">Top</a>
        </div>
        <div style="font-size:0.9rem;font-weight:700;margin-bottom:6px;">How to use</div>
        <div style="font-size:0.85rem;line-height:1.6;color:#6b7280;">
            Fill in your details on the left, then read your results on the right.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)





left, right = st.columns([0.92, 1.08], gap="large")

st.markdown('<div id="inputs"></div>', unsafe_allow_html=True)
with left:


    sex = st.selectbox("Choose sex", ["Choose sex", "Male", "Female"], index=0)
    age = st.number_input("Age", min_value=10, max_value=100, value=30, step=1)
    weight = st.number_input("Weight (lbs)", min_value=1.0, value=180.0, step=0.1)
    height = st.number_input("Height (inches)", min_value=1.0, value=68.0, step=0.1)
    waist = st.number_input("Waist (inches — around belly button)", min_value=1.0, value=36.0, step=0.1)
    neck = st.number_input("Neck (inches — just below Adam’s apple)", min_value=1.0, value=15.0, step=0.1)

    hips = st.number_input(
        "Hips (inches — widest point)",
        min_value=0.0,
        value=0.0 if sex == "Male" else 40.0,
        step=0.1,
        help="Required for females only",
    )

    try:
        if sex == "Choose sex":
            preview_bf = 25.0
        else:
            preview_bf = navy_body_fat(sex, height, waist, neck, hips)
    except ValueError:
        preview_bf = 25.0

    target_body_fat = st.slider(
        "Target BF %",
        min_value=5,
        max_value=50,
        value=20,
        step=1,
    )
    render_body_fat_zone_bar(target_body_fat)

    weekly_loss = st.number_input(
        "Weekly loss target (lbs)",
        min_value=0.1,
        max_value=3.0,
        value=1.0,
        step=0.05,
    )

    activity_label = st.selectbox(
        "Activity level",
        ["Sedentary", "Lightly active", "Moderately active", "Very active", "Extra active"],
        index=1,
    )

    calorie_deficit = st.number_input(
        "Calorie deficit",
        min_value=0,
        max_value=1500,
        value=400,
        step=50,
    )

    m1, m2, m3 = st.columns(3)
    with m1:
        protein_pct = st.number_input("Protein %", min_value=10, max_value=60, value=30, step=1)
    with m2:
        carbs_pct = st.number_input("Carbs %", min_value=10, max_value=70, value=40, step=1)
    with m3:
        fats_pct = st.number_input("Fats %", min_value=10, max_value=50, value=30, step=1)

    if protein_pct + carbs_pct + fats_pct != 100:
        st.warning("Protein %, carbs %, and fats % should add up to 100.")


    st.subheader("Tools")
    st.caption("Download or reset your progress data.")

    download_col1, download_col2 = st.columns(2)
    with download_col1:
        st.download_button(
            "Download progress CSV",
            data=progress_csv_bytes(),
            file_name="body_fat_goal_progress.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with download_col2:
        if st.button("Reset progress data", use_container_width=True):
            pd.DataFrame(columns=["entry_id", "date", "weight", "waist", "body_fat"]).to_csv(PROGRESS_CSV, index=False)
            st.success("Progress data reset.")
            st.rerun()


    st.subheader("Progress tracker")
    st.caption("Log your real progress and compare it with the plan over time.")

    progress_date = st.date_input("Progress date", value=datetime.now(), key="progress_date")

    pt1, pt2, pt3 = st.columns(3)
    with pt1:
        progress_weight = st.number_input(
            "Progress weight (lbs)",
            min_value=1.0,
            value=float(weight),
            step=0.1,
            key="progress_weight",
        )
    with pt2:
        progress_waist = st.number_input(
            "Progress waist (inches)",
            min_value=1.0,
            value=float(waist),
            step=0.1,
            key="progress_waist",
        )
    with pt3:
        progress_body_fat = st.number_input(
            "Progress body fat %",
            min_value=1.0,
            max_value=60.0,
            value=float(round(preview_bf, 2)),
            step=0.1,
            key="progress_body_fat",
        )

    progress_df_sidebar = load_progress_df()

    action_col1, action_col2 = st.columns([1, 1])
    with action_col1:
        save_progress_clicked = st.button("Save progress entry", use_container_width=True)
    with action_col2:
        if not progress_df_sidebar.empty:
            delete_progress_clicked = st.button("Delete selected entry", use_container_width=True)
        else:
            delete_progress_clicked = False

    if not progress_df_sidebar.empty:
        delete_options_df = progress_df_sidebar.sort_values(["date", "entry_id"], ascending=[False, False]).copy()
        delete_options_df["delete_label"] = (
            delete_options_df["date"].astype(str)
            + " | "
            + delete_options_df["weight"].astype(str)
            + " lbs | BF "
            + delete_options_df["body_fat"].astype(str)
            + "%"
        )
        delete_entry_id = st.selectbox(
            "Delete saved entry",
            options=delete_options_df["entry_id"].tolist(),
            format_func=lambda x: delete_options_df.loc[delete_options_df["entry_id"] == x, "delete_label"].iloc[0],
            key="delete_progress_entry_id",
        )
    else:
        delete_entry_id = None

    if save_progress_clicked:
        save_progress_entry(progress_date, progress_weight, progress_waist, progress_body_fat)
        st.success("Progress entry saved.")
        st.rerun()

    if delete_progress_clicked and delete_entry_id:
        delete_progress_entry(delete_entry_id)
        st.success("Progress entry deleted.")
        st.rerun()


    if not progress_df_sidebar.empty:
        st.markdown('<div id="progress"></div>', unsafe_allow_html=True)
        st.subheader("Real progress")
        st.caption("Your saved entries sit here so you can compare actual progress with the plan.")

        latest_progress = progress_df_sidebar.sort_values("date").iloc[-1]
        latest_progress_df = pd.DataFrame(
            [
                {"Latest measure": "Weight", "Value": f"{latest_progress['weight']} lbs"},
                {"Latest measure": "Waist", "Value": f"{latest_progress['waist']} in"},
                {"Latest measure": "Body fat", "Value": f"{latest_progress['body_fat']} %"},
            ]
        )
        st.dataframe(latest_progress_df, use_container_width=True, hide_index=True)

        with st.expander("Show saved progress table"):
            st.dataframe(progress_df_sidebar.sort_values("date", ascending=False), use_container_width=True, hide_index=True)
st.markdown('<div id="results"></div>', unsafe_allow_html=True)
with right:


    try:
        if sex == "Choose sex":
            raise ValueError("Please choose Male or Female to calculate your results.")
        bf = navy_body_fat(sex, height, waist, neck, hips)
        fat_mass, lean_mass = body_composition(weight, bf)
        goal_weight = goal_weight_for_target_body_fat(lean_mass, target_body_fat)
        weeks_to_goal = estimated_weeks_to_goal(weight, goal_weight, weekly_loss)
        goal_date = projected_goal_date(weeks_to_goal)
        bmi_value = bmi(weight, height)
        whtr_value = waist_to_height_ratio(waist, height)

        current_maintenance = maintenance_calories(
            sex=sex,
            weight_lbs=weight,
            height_inches=height,
            age=age,
            activity_label=activity_label,
        )
        current_cutting = cutting_calories(current_maintenance, calorie_deficit)
        current_macros = macro_targets_from_calories(
            current_cutting,
            protein_pct=protein_pct,
            carbs_pct=carbs_pct,
            fats_pct=fats_pct,
        )
        macro_total_ok = (protein_pct + carbs_pct + fats_pct) == 100
        progress_df = load_progress_df()
        if "date_dt" in progress_df.columns:
            progress_df = progress_df.sort_values(["date_dt", "entry_id"], ascending=[True, True]).reset_index(drop=True)

        st.markdown('<div class="beauty-divider"></div>', unsafe_allow_html=True)
        st.subheader("Progress to target")
        if not progress_df.empty and "body_fat" in progress_df.columns:
            start_bf_for_progress = float(progress_df["body_fat"].dropna().iloc[0]) if not progress_df["body_fat"].dropna().empty else bf
        else:
            start_bf_for_progress = bf
        progress_value = progress_ratio(bf, start_bf=start_bf_for_progress, target_bf=target_body_fat)
        st.progress(progress_value)
        st.caption(f"Tracking from {round(start_bf_for_progress, 1)}% toward {target_body_fat}% body fat")
        render_body_fat_zone_bar(bf)


        months_to_goal = round(weeks_to_goal / 4.345, 1) if weeks_to_goal > 0 else 0

        overview_rows = [
            {"Measure": "Body fat %", "Value": bf},
            {"Measure": "Fat mass", "Value": f"{fat_mass} lbs"},
            {"Measure": "Lean mass", "Value": f"{lean_mass} lbs"},
            {"Measure": "Goal weight", "Value": f"{goal_weight} lbs"},
            {"Measure": "BMI", "Value": bmi_value},
            {"Measure": "BMI zone", "Value": bmi_category(bmi_value)},
            {"Measure": "WHtR (waist-to-height ratio)", "Value": whtr_value},
            {"Measure": "WHtR zone", "Value": whtr_category(whtr_value)},
            {"Measure": "Lbs to goal", "Value": round(abs(weight - goal_weight), 2)},
            {"Measure": "Weeks to goal", "Value": weeks_to_goal},
            {"Measure": "Months to goal", "Value": months_to_goal},
            {"Measure": "Goal date", "Value": goal_date},
            {"Measure": "Body fat zone", "Value": body_fat_category(sex, bf)},
        ]

        st.subheader("Results summary")
        st.dataframe(pd.DataFrame(overview_rows), use_container_width=True, hide_index=True)

        st.markdown('<div class="beauty-divider"></div>', unsafe_allow_html=True)
        st.subheader("Your fat-loss path")
        st.caption("Milestones and macro targets are shown below in a cleaner list format.")


        st.markdown('<div id="milestones"></div>', unsafe_allow_html=True)
        st.subheader("Weight milestones")
        milestone_weights = build_weight_milestones(weight, goal_weight)
        st.caption("Simple guide: these are your estimated dates for each milestone weight.")

        milestone_rows = []
        for mw in milestone_weights:
            if mw == round(goal_weight):
                status = "Goal"
            elif goal_weight < weight:
                status = "Milestone" if mw < weight else "Current range"
            else:
                status = "Milestone" if mw > weight else "Current range"

            milestone_rows.append(
                {
                    "Weight": f"{mw} lbs",
                    "Status": status,
                    "Target date": predict_date_for_weight(weight, mw, weekly_loss),
                }
            )

        milestone_df = pd.DataFrame(milestone_rows)
        st.dataframe(milestone_df, use_container_width=True, hide_index=True)

        st.markdown('<div class="beauty-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div id="macros"></div>', unsafe_allow_html=True)
        st.subheader("Calories and macros today")

        if not macro_total_ok:
            st.error("Protein %, carbs %, and fats % must add up to exactly 100 before macro guidance can be shown.")
        else:
            current_macro_df = pd.DataFrame(
                [
                    {"Today": "Maintenance calories", "Value": f"{int(current_maintenance)} kcal"},
                    {"Today": "Cutting calories", "Value": f"{int(current_cutting)} kcal"},
                    {"Today": "Protein", "Value": f"{current_macros['protein_g']} g"},
                    {"Today": "Carbs / fats", "Value": f"{current_macros['carbs_g']} g / {current_macros['fats_g']} g"},
                ]
            )
            st.dataframe(current_macro_df, use_container_width=True, hide_index=True)

            st.subheader("Calories and macros at goal weights")
            goal_weights = build_macro_weight_targets(weight, goal_weight, count=6)

            goal_macro_df = build_goal_macro_table(
                sex=sex,
                height_inches=height,
                age=age,
                activity_label=activity_label,
                goal_weights=goal_weights,
                deficit=calorie_deficit,
                protein_pct=protein_pct,
                carbs_pct=carbs_pct,
                fats_pct=fats_pct,
            )

            st.caption("Simple guide: each row shows a calm daily target for one of your 6 key goal weights.")

            est_rows = []
            for gw in goal_weights:
                est_bf = round((1 - (lean_mass / gw)) * 100, 1)
                zone_label, _, _ = gout_risk_zone_from_body_fat(est_bf)
                est_rows.append((gw, est_bf, zone_label))

            goal_macro_df = goal_macro_df.copy()
            goal_macro_df["Estimated BF %"] = [row[1] for row in est_rows]
            goal_macro_df["Zone"] = [row[2] for row in est_rows]
            goal_macro_df = goal_macro_df[["Weight", "Zone", "Estimated BF %", "Calories", "Protein", "Carbs", "Fats"]]

            st.dataframe(goal_macro_df, use_container_width=True, hide_index=True)

    except ValueError as e:
        st.error(str(e))


st.markdown(
    """
    <div style="text-align:center; margin-top:10px; margin-bottom:6px;">
        <a href="#top" style="text-decoration:none;font-weight:700;color:#4f7ddf;">
            Back to top
        </a>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div style="margin-top:18px;color:#6b7280;font-size:0.84rem;text-align:center;line-height:1.6;">
        Body Fat Burning Planner<br>
        Built for calm, realistic progress.
        <div style="margin-top:8px;font-size:0.8rem;line-height:1.6;">
            Disclaimer: This planner provides estimates for educational purposes only and is not medical advice.
            Real progress varies with health, hydration, adherence, sleep, stress, and normal body fluctuations.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)