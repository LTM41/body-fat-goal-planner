import math
import uuid
import os
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

PROGRESS_CSV = "body_fat_goal_progress.csv"


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


def estimated_weeks_to_goal(current_weight, goal_weight, weekly_loss=1.25):
    if weekly_loss <= 0 or current_weight <= goal_weight:
        return 0
    return math.ceil((current_weight - goal_weight) / weekly_loss)


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


def predict_date_for_weight(current_weight, target_weight, weekly_loss):
    if weekly_loss <= 0:
        return "N/A"
    if current_weight <= target_weight:
        return "Reached"
    weeks = math.ceil((current_weight - target_weight) / weekly_loss)
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


def build_projection_df(current_weight, goal_weight, weekly_loss):
    if weekly_loss <= 0:
        return pd.DataFrame({"Week": [0], "Projected weight": [round(current_weight, 1)]})

    weeks_needed = max(0, estimated_weeks_to_goal(current_weight, goal_weight, weekly_loss))
    rows = []

    for week in range(weeks_needed + 1):
        projected = max(goal_weight, current_weight - (weekly_loss * week))
        rows.append({"Week": week, "Projected weight": round(projected, 1)})

    if rows and rows[-1]["Projected weight"] != round(goal_weight, 1):
        rows.append({"Week": weeks_needed + 1, "Projected weight": round(goal_weight, 1)})

    return pd.DataFrame(rows)


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


# =============================
# APP
# =============================
st.set_page_config(page_title="Body Fat Goal Planner", layout="wide")

st.markdown(
    """
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 2.4rem;
    max-width: 1240px;
}

html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at top right, rgba(163, 191, 250, 0.16), transparent 26%),
        radial-gradient(circle at bottom left, rgba(182, 226, 211, 0.14), transparent 24%),
        linear-gradient(180deg, #f8fbff 0%, #f5f7fb 52%, #fdfaf7 100%);
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
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(250, 251, 253, 0.92) 100%);
    border: 1px solid rgba(231, 235, 241, 0.95);
    padding: 13px 15px;
    border-radius: 22px;
    box-shadow: 0 14px 30px rgba(114, 132, 160, 0.10);
    backdrop-filter: blur(10px);
    min-height: 112px;
}

.top-summary-card {
    background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(249,250,252,0.94) 100%);
    border: 1px solid rgba(231, 235, 241, 0.98);
    border-radius: 24px;
    padding: 16px 18px 14px 18px;
    box-shadow: 0 16px 34px rgba(114, 132, 160, 0.10);
    margin-bottom: 14px;
}

.top-summary-kicker {
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #7b8ba5;
    margin-bottom: 4px;
}

.top-summary-value {
    font-size: 1.2rem;
    font-weight: 800;
    color: #1f2937;
    line-height: 1.2;
    margin-bottom: 4px;
}

.top-summary-note {
    font-size: 0.82rem;
    line-height: 1.45;
    color: #6b7280;
}

.brand-badge {
    width: 82px;
    height: 82px;
    border-radius: 24px;
    background: transparent;
    border: none;
    box-shadow: none;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2rem;
    margin: 0.15rem 0 0.55rem 0;
}

.apple-card {
    border: 1px solid rgba(231, 235, 241, 0.98);
    border-radius: 24px;
    padding: 18px 18px 14px 18px;
    margin-bottom: 14px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.97) 0%, rgba(249, 250, 252, 0.93) 100%);
    box-shadow: 0 16px 34px rgba(114, 132, 160, 0.10);
    backdrop-filter: blur(10px);
    min-height: 176px;
}

.apple-card-title {
    font-size: 0.88rem;
    font-weight: 700;
    margin-bottom: 8px;
    line-height: 1.4;
    white-space: normal;
    word-break: break-word;
    overflow-wrap: anywhere;
}

.apple-card-badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    color: white;
    font-weight: 700;
    font-size: 0.68rem;
    margin-bottom: 10px;
    line-height: 1.3;
    white-space: normal;
    word-break: break-word;
    overflow-wrap: anywhere;
    max-width: 100%;
}

.apple-card-body {
    font-size: 0.82rem;
    line-height: 1.6;
    color: #111827;
}

.apple-card-body div {
    white-space: normal;
    word-break: break-word;
    overflow-wrap: anywhere;
}

.apple-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 22px 38px rgba(114, 132, 160, 0.14);
    transition: all 0.22s ease;
}

.panel-card {
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(250, 251, 253, 0.92) 100%);
    border: 1px solid rgba(231, 235, 241, 0.98);
    border-radius: 28px;
    padding: 20px 20px 14px 20px;
    box-shadow: 0 16px 34px rgba(114, 132, 160, 0.10);
    backdrop-filter: blur(10px);
    margin-bottom: 18px;
}

.input-shell {
    background: linear-gradient(180deg, rgba(255,255,255,0.97) 0%, rgba(249,250,252,0.93) 100%);
    border: 1px solid rgba(231, 235, 241, 0.98);
    border-radius: 26px;
    padding: 18px 18px 10px 18px;
    box-shadow: 0 16px 34px rgba(114, 132, 160, 0.10);
    margin-bottom: 16px;
}

.input-group-title {
    font-size: 0.82rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #7b8ba5;
    margin-bottom: 10px;
}

.hero-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.99) 0%, rgba(238,245,255,0.98) 42%, rgba(251,247,243,0.98) 100%);
    border: 1px solid rgba(231, 235, 241, 0.98);
    border-radius: 34px;
    padding: 28px 28px 24px 28px;
    box-shadow: 0 22px 48px rgba(114, 132, 160, 0.14);
    margin: 10px 0 20px 0;
    position: relative;
    overflow: hidden;
}

.hero-orb {
    position: absolute;
    border-radius: 999px;
    filter: blur(2px);
    opacity: 0.55;
}

.hero-orb.one {
    width: 180px;
    height: 180px;
    right: -42px;
    top: -36px;
    background: rgba(163, 191, 250, 0.26);
}

.hero-orb.two {
    width: 120px;
    height: 120px;
    right: 92px;
    bottom: -42px;
    background: rgba(182, 226, 211, 0.24);
}

.section-row-space {
    margin-top: 4px;
    margin-bottom: 6px;
}

.callout-chip {
    display: inline-block;
    padding: 7px 13px;
    border-radius: 999px;
    background: rgba(255,255,255,0.86);
    border: 1px solid rgba(231, 235, 241, 0.98);
    color: #516072;
    font-size: 0.79rem;
    font-weight: 700;
    margin: 6px 8px 0 0;
    box-shadow: 0 6px 18px rgba(114, 132, 160, 0.08);
}

.soft-note {
    color: #6b7280;
    font-size: 0.92rem;
    line-height: 1.65;
}

.chart-panel {
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(249, 250, 252, 0.94) 100%);
    border: 1px solid rgba(231, 235, 241, 0.98);
    border-radius: 26px;
    padding: 18px 18px 14px 18px;
    box-shadow: 0 18px 38px rgba(114, 132, 160, 0.12);
    backdrop-filter: blur(10px);
    margin-bottom: 18px;
    min-height: 430px;
    display: flex;
    flex-direction: column;
}

.chart-note {
    color: #6b7280;
    font-size: 0.9rem;
    line-height: 1.6;
    margin-bottom: 10px;
    min-height: 58px;
}

.chart-frame {
    background: linear-gradient(180deg, rgba(255,255,255,0.72) 0%, rgba(244,247,251,0.82) 100%);
    border: 1px solid rgba(231, 235, 241, 0.92);
    border-radius: 22px;
    padding: 10px 12px 6px 12px;
    margin-top: 10px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
}

.chart-kicker {
    font-size: 0.76rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #7b8ba5;
    margin-bottom: 4px;
    min-height: 18px;
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
    background: rgba(255, 255, 255, 0.9);
}

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-baseweb="base-input"] {
    border-radius: 16px !important;
}

.stButton > button {
    border-radius: 18px;
    border: 1px solid rgba(231, 235, 241, 0.98);
    background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(244,247,251,0.92) 100%);
    box-shadow: 0 10px 22px rgba(114, 132, 160, 0.10);
    font-weight: 700;
    padding-top: 0.55rem;
    padding-bottom: 0.55rem;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("<h1>Body Fat Burning Planner <span style='position:relative; top:4px;'>🔥</span></h1>", unsafe_allow_html=True)
st.caption("Calm, honest fat-loss planning — realistic timelines, macro guidance and progress tracking.")

st.markdown(
    """
    <div class="hero-card">
        <div class="hero-orb one"></div>
        <div class="hero-orb two"></div>
        <div style="position:relative;z-index:2;">
            <div style="font-size:0.82rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#6f87a7;margin-bottom:8px;">Body Fat Burning Planner</div>
            <div style="font-size:1.42rem;font-weight:800;margin-bottom:8px;line-height:1.2;color:#1f2937;">Calm planning for steady body recomposition</div>
            <div class="soft-note" style="max-width:760px;">
                Enter your details on the left and your results update live on the right.
                This planner is designed to feel calm, honest, and easy to follow — because real fat loss usually takes consistency over time, not perfection in a few weeks.
            </div>
            <div style="margin-top:12px;">
                <span class="callout-chip">Calm layout</span>
                <span class="callout-chip">Realistic timelines</span>
                <span class="callout-chip">Clear macro targets</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="panel-card" style="margin-top:-4px;">
        <div style="font-size:0.95rem;font-weight:700;margin-bottom:4px;">Planner, not a promise</div>
        <div class="soft-note">
            These numbers are estimates based on the information you enter. Real progress varies with sleep, adherence, activity, hydration, and normal body fluctuations.
        </div>
        <div style="margin-top:8px;">
            <span class="callout-chip">Estimate based</span>
            <span class="callout-chip">Realistic pace</span>
            <span class="callout-chip">Built for consistency</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([0.92, 1.08], gap="large")

with left:
    st.markdown(
        """
        <div class="panel-card">
            <div style="font-size:1.05rem;font-weight:700;margin-bottom:4px;">Your inputs</div>
            <div class="soft-note">Adjust the settings below and the planner updates live.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sex = st.selectbox("Sex", ["Male", "Female"], index=0)
    age = st.number_input("Age", min_value=10, max_value=100, value=48, step=1)
    weight = st.number_input("Weight (lbs)", min_value=1.0, value=208.0, step=0.1)
    height = st.number_input("Height (inches)", min_value=1.0, value=70.0, step=0.1)
    waist = st.number_input("Waist (inches)", min_value=1.0, value=40.5, step=0.1)
    neck = st.number_input("Neck (inches)", min_value=1.0, value=17.0, step=0.1)
    st.markdown('<div class="input-shell"><div class="input-group-title">Goal settings</div></div>', unsafe_allow_html=True)

    hips = st.number_input(
        "Hips (inches)",
        min_value=0.0,
        value=0.0 if sex == "Male" else 42.0,
        step=0.1,
        help="Required for females only",
    )

    try:
        preview_bf = navy_body_fat(sex, height, waist, neck, hips)
    except ValueError:
        preview_bf = 25.0

    target_body_fat = st.slider(
        "Target BF %",
        min_value=5,
        max_value=50,
        value=18,
        step=1,
    )
    render_body_fat_zone_bar(target_body_fat)

    weekly_loss = st.number_input(
        "Weekly loss target (lbs)",
        min_value=0.1,
        max_value=3.0,
        value=1.25,
        step=0.05,
    )

    activity_label = st.selectbox(
        "Activity level",
        ["Sedentary", "Lightly active", "Moderately active", "Very active", "Extra active"],
        index=2,
    )

    calorie_deficit = st.number_input(
        "Calorie deficit",
        min_value=0,
        max_value=1500,
        value=500,
        step=50,
    )
    st.markdown('<div class="input-shell"><div class="input-group-title">Macro split</div></div>', unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    with m1:
        protein_pct = st.number_input("Protein %", min_value=10, max_value=60, value=30, step=1)
    with m2:
        carbs_pct = st.number_input("Carbs %", min_value=10, max_value=70, value=40, step=1)
    with m3:
        fats_pct = st.number_input("Fats %", min_value=10, max_value=50, value=30, step=1)

    if protein_pct + carbs_pct + fats_pct != 100:
        st.warning("Protein %, carbs %, and fats % should add up to 100.")

    top1, top2, top3 = st.columns(3)
    with top1:
        st.markdown(
            f"""
            <div class="top-summary-card">
                <div class="top-summary-kicker">Current weight</div>
                <div class="top-summary-value">{weight:.1f} lbs</div>
                <div class="top-summary-note">Your starting point for this plan.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with top2:
        st.markdown(
            f"""
            <div class="top-summary-card">
                <div class="top-summary-kicker">Target body fat</div>
                <div class="top-summary-value">{target_body_fat}%</div>
                <div class="top-summary-note">The body-fat level you are aiming for.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with top3:
        st.markdown(
            f"""
            <div class="top-summary-card">
                <div class="top-summary-kicker">Weekly pace</div>
                <div class="top-summary-value">{weekly_loss:.2f} lbs</div>
                <div class="top-summary-note">A steady weekly fat-loss target.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="panel-card" style="padding-bottom:14px;">
            <div style="font-size:1rem;font-weight:700;margin-bottom:4px;">V1 essentials</div>
            <div class="soft-note">A few simple launch-ready tools for saving data and understanding how the planner works.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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

    st.markdown(
        """
        <div class="panel-card" style="padding-bottom:14px;">
            <div style="font-size:1rem;font-weight:700;margin-bottom:4px;">Mindset and community</div>
            <div class="soft-note">Use the extra space to keep the planner motivating, realistic, and useful.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("### Community board")
    st.caption("A calmer, more honest guide: real fat loss takes time, consistency, and patience.")

    cb1, cb2 = st.columns(2)
    with cb1:
        st.markdown(
            """
            <div class="apple-card">
                <div class="apple-card-title">Honest timeline</div>
                <div class="apple-card-body">
                    <div>Most people will not get truly lean in 30 days.</div>
                    <div>Real change usually takes months, not weeks.</div>
                    <div>Steady progress is more realistic and more sustainable.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with cb2:
        st.markdown(
            """
            <div class="apple-card">
                <div class="apple-card-title">Consistency wins</div>
                <div class="apple-card-body">
                    <div>You do not need perfection.</div>
                    <div>You need enough good days, repeated over time.</div>
                    <div>Habits beat short bursts of extreme effort.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    cb3, cb4 = st.columns(2)
    with cb3:
        st.markdown(
            """
            <div class="apple-card">
                <div class="apple-card-title">Enjoy the ride</div>
                <div class="apple-card-body">
                    <div>Fat loss is not a sprint. It is a marathon.</div>
                    <div>Build a routine you can live with.</div>
                    <div>Enjoy the ride to the you that you really want.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with cb4:
        st.markdown(
            """
            <div class="apple-card">
                <div class="apple-card-title">Advertise here</div>
                <div class="apple-card-body">
                    <div>Your business could appear in this space.</div>
                    <div>Ideal for fitness, golf, nutrition, coaching, or local services.</div>
                    <div>Contact Blaze to reserve a slot.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="panel-card" style="padding-bottom:14px;">
            <div style="font-size:1rem;font-weight:700;margin-bottom:4px;">Progress tracker</div>
            <div class="soft-note">Log your real progress and compare it with the plan over time.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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

    tracker_col1, tracker_col2 = st.columns(2)
    with tracker_col1:
        save_progress_clicked = st.button("Save progress entry", use_container_width=True)
    with tracker_col2:
        progress_df_sidebar = load_progress_df()
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
            delete_progress_clicked = st.button("Delete selected entry", use_container_width=True)
        else:
            delete_entry_id = None
            delete_progress_clicked = False

    if save_progress_clicked:
        save_progress_entry(progress_date, progress_weight, progress_waist, progress_body_fat)
        st.success("Progress entry saved.")
        st.rerun()

    if delete_progress_clicked and delete_entry_id:
        delete_progress_entry(delete_entry_id)
        st.success("Progress entry deleted.")
        st.rerun()

with right:
    st.markdown(
        """
        <div class="panel-card">
            <div style="font-size:1.05rem;font-weight:700;margin-bottom:4px;">Your results</div>
            <div class="soft-note">Live results, milestones, and macro guidance.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="panel-card">
            <div style="font-size:1rem;font-weight:700;margin-bottom:4px;">How it works</div>
            <div class="soft-note">
                This planner estimates body fat from your measurements, then uses your lean mass to project a goal weight at your chosen target body-fat level.
                It also gives a simple calorie and macro guide based on your current details and activity level.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="panel-card" style="padding-bottom:14px;">
            <div style="font-size:1rem;font-weight:700;margin-bottom:4px;">Disclaimer</div>
            <div class="soft-note">
                This planner provides estimates for educational purposes only and is not medical advice.
                Real progress varies with health, hydration, adherence, sleep, stress, and normal body fluctuations.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
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

        st.markdown('<div class="section-row-space"></div>', unsafe_allow_html=True)
        r1 = st.columns(4)
        r1[0].metric("Body Fat %", bf)
        r1[1].metric("Fat Mass", f"{fat_mass} lbs")
        r1[2].metric("Lean Mass", f"{lean_mass} lbs")
        r1[3].metric("Goal Weight", f"{goal_weight} lbs")

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

        st.markdown('<div class="section-row-space"></div>', unsafe_allow_html=True)
        r2 = st.columns(4)
        r2[0].metric("BMI", bmi_value)
        r2[1].metric("BMI Zone", bmi_category(bmi_value))
        r2[2].metric("WHtR", whtr_value)
        r2[3].metric("WHtR Zone", whtr_category(whtr_value))

        st.markdown('<div class="section-row-space"></div>', unsafe_allow_html=True)
        r3a = st.columns(2)
        r3a[0].metric("Lbs to Lose", round(max(0, weight - goal_weight), 2))
        r3a[1].metric("Weeks to Goal", weeks_to_goal)

        st.markdown('<div class="section-row-space"></div>', unsafe_allow_html=True)
        r3b = st.columns([1.35, 1])
        r3b[0].metric("Goal Date", goal_date)
        r3b[1].metric("Body Fat Zone", body_fat_category(sex, bf))

        if not progress_df.empty:
            st.markdown(
                """
                <div class="panel-card" style="padding-bottom:14px;">
                    <div style="font-size:1rem;font-weight:700;margin-bottom:4px;">Real progress</div>
                    <div class="soft-note">Your saved entries sit here so you can compare actual progress with the plan.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            pg1, pg2, pg3 = st.columns(3)
            latest_progress = progress_df.sort_values("date").iloc[-1]
            pg1.metric("Latest Logged Weight", f"{latest_progress['weight']} lbs")
            pg2.metric("Latest Logged Waist", f"{latest_progress['waist']} in")
            pg3.metric("Latest Logged Body Fat", f"{latest_progress['body_fat']} %")

            compare_df = progress_df.copy()
            if "date_dt" in compare_df.columns and compare_df["date_dt"].notna().any():
                first_date = compare_df["date_dt"].min()
                compare_df["Week"] = ((compare_df["date_dt"] - first_date).dt.days / 7).fillna(0).round().astype(int)
            else:
                compare_df["Week"] = range(len(compare_df))

            projected_compare = build_projection_df(weight, goal_weight, weekly_loss).copy()
            if not projected_compare.empty:
                projected_compare = projected_compare.rename(columns={"Projected weight": "Projected weight line"})

            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                actual_vs_projected = pd.merge(
                    compare_df[["Week", "weight"]].rename(columns={"weight": "Actual weight line"}),
                    projected_compare[["Week", "Projected weight line"]],
                    on="Week",
                    how="outer",
                ).sort_values("Week")
                st.markdown(
                    """
                    <div class="chart-panel">
                        <div class="chart-kicker">Progress chart</div>
                        <div style="font-size:1rem;font-weight:700;margin-bottom:4px;">Actual vs projected weight</div>
                        <div class="chart-note">A calm side-by-side view of where you are versus the pace of the plan.</div>
                        <div class="chart-frame">
                    """,
                    unsafe_allow_html=True,
                )
                st.line_chart(actual_vs_projected.set_index("Week"), use_container_width=True)
                st.markdown("</div></div>", unsafe_allow_html=True)
            with chart_col2:
                st.markdown(
                    """
                    <div class="chart-panel">
                        <div class="chart-kicker">Progress chart</div>
                        <div style="font-size:1rem;font-weight:700;margin-bottom:4px;">Actual body fat trend</div>
                        <div class="chart-note">Your logged body-fat entries shown as a simple trend over time.</div>
                        <div class="chart-frame">
                    """,
                    unsafe_allow_html=True,
                )
                st.line_chart(compare_df.set_index("date")["body_fat"], use_container_width=True)
                st.markdown("</div></div>", unsafe_allow_html=True)

            with st.expander("Show saved progress table"):
                st.dataframe(progress_df.sort_values("date", ascending=False), use_container_width=True, hide_index=True)

        st.markdown('<div class="beauty-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="panel-card" style="padding-bottom:14px;">
                <div style="font-size:1rem;font-weight:700;margin-bottom:4px;">Your fat-loss path</div>
                <div class="soft-note">Milestones and macro targets are shown in simple cards so the journey feels easier to follow.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        projection_df = build_projection_df(weight, goal_weight, weekly_loss)
        st.markdown(
            """
            <div class="chart-panel">
                <div class="chart-kicker">Projection chart</div>
                <div style="font-size:1rem;font-weight:700;margin-bottom:4px;">Projected weight trend</div>
                <div class="chart-note">
                    A simple week-by-week view of steady progress toward your goal.
                    This is meant to guide you, not pressure you.
                </div>
                <div class="chart-frame">
            """,
            unsafe_allow_html=True,
        )
        st.line_chart(projection_df.set_index("Week")["Projected weight"], use_container_width=True)
        st.markdown("</div></div>", unsafe_allow_html=True)

        st.subheader("Weight milestones")
        milestone_weights = build_weight_milestones(weight, goal_weight)
        st.caption("Simple guide: these are your estimated dates for each milestone weight.")

        milestone_cards_per_row = 2
        for i in range(0, len(milestone_weights), milestone_cards_per_row):
            row_items = milestone_weights[i:i + milestone_cards_per_row]
            cols = st.columns(milestone_cards_per_row)

            for col, mw in zip(cols, row_items):
                target_date = predict_date_for_weight(weight, mw, weekly_loss)

                if mw == round(goal_weight):
                    badge_text = "Goal"
                    badge_color = "#7FA3D6"
                elif mw < weight:
                    badge_text = "Milestone"
                    badge_color = "#8FC9A8"
                else:
                    badge_text = "Current range"
                    badge_color = "#A8B7C9"

                with col:
                    st.markdown(
                        f"""
                        <div class="apple-card">
                            <div class="apple-card-title">Weight: {mw} lbs</div>
                            <div class="apple-card-badge" style="background:{badge_color};">{badge_text}</div>
                            <div class="apple-card-body">
                                <div><strong>Status:</strong> {badge_text}</div>
                                <div><strong>Target date:</strong> {target_date}</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        with st.expander("Show milestone table"):
            milestone_df = pd.DataFrame(
                {
                    "Weight": [f"{mw} lbs" for mw in milestone_weights],
                    "Target date": [predict_date_for_weight(weight, mw, weekly_loss) for mw in milestone_weights],
                }
            )
            st.dataframe(milestone_df, use_container_width=True, hide_index=True)

        st.markdown('<div class="beauty-divider"></div>', unsafe_allow_html=True)
        st.subheader("Calories and macros today")

        if not macro_total_ok:
            st.error("Protein %, carbs %, and fats % must add up to exactly 100 before macro guidance can be shown.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Maintenance Calories", f"{int(current_maintenance)} kcal")
            c2.metric("Cutting Calories", f"{int(current_cutting)} kcal")
            c3.metric("Protein", f"{current_macros['protein_g']} g")
            c4.metric("Carbs / Fats", f"{current_macros['carbs_g']} g / {current_macros['fats_g']} g")

            st.subheader("Calories and macros at goal weights")
            goal_weights = build_weight_milestones(weight, goal_weight)

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

            st.caption("Simple guide: each card shows a calm daily target for that body weight.")

            est_rows = []
            for gw in goal_weights:
                est_bf = round((1 - (lean_mass / gw)) * 100, 1)
                zone_label, zone_color, _ = gout_risk_zone_from_body_fat(est_bf)
                est_rows.append((gw, est_bf, zone_label, zone_color))

            cards_per_row = 2
            for i in range(0, len(est_rows), cards_per_row):
                row_items = est_rows[i:i + cards_per_row]
                cols = st.columns(cards_per_row)

                for col, item in zip(cols, row_items):
                    gw, est_bf, zone_label, zone_color = item
                    row_data = goal_macro_df[goal_macro_df["Weight"] == f"{gw} lbs"].iloc[0]

                    with col:
                        st.markdown(
                            f"""
                            <div class="apple-card">
                                <div class="apple-card-title">Weight: {row_data['Weight']}</div>
                                <div class="apple-card-badge" style="background:{zone_color};">{zone_label} · est {est_bf}% body fat</div>
                                <div class="apple-card-body">
                                    <div><strong>Zone:</strong> {zone_label}</div>
                                    <div><strong>Estimated body fat:</strong> {est_bf}%</div>
                                    <div><strong>Calories:</strong> {row_data['Calories']} kcal</div>
                                    <div><strong>Protein:</strong> {row_data['Protein']}</div>
                                    <div><strong>Carbs:</strong> {row_data['Carbs']}</div>
                                    <div><strong>Fats:</strong> {row_data['Fats']}</div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

            with st.expander("Show macro table"):
                st.dataframe(goal_macro_df, use_container_width=True, hide_index=True)

    except ValueError as e:
        st.error(str(e))

st.markdown(
    """
    <div style="margin-top:18px;color:#6b7280;font-size:0.84rem;text-align:center;line-height:1.6;">
        Body Fat Burning Planner · Version 1<br>
        Built for calm, realistic progress. Estimates only — not medical advice.
    </div>
    """,
    unsafe_allow_html=True,
)