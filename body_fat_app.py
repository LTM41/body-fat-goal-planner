import math
import csv
import os
import uuid
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st


BODY_CSV = "body_progress.csv"
GOLF_CSV = "golf_progress.csv"
PHOTO_CSV = "photo_progress.csv"
PHOTO_DIR = "progress_photos"


# =============================
# FILE SETUP
# =============================
def ensure_body_csv_exists():
    if not os.path.isfile(BODY_CSV):
        with open(BODY_CSV, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([
                "entry_id",
                "user",
                "date",
                "sex",
                "weight",
                "height",
                "waist",
                "neck",
                "hips",
                "body_fat",
                "body_fat_category",
                "fat_mass",
                "lean_mass",
                "target_body_fat",
                "goal_weight",
                "weeks_to_goal",
                "projected_goal_date",
                "bmi",
                "bmi_category",
                "waist_to_height_ratio",
                "whtr_category"
            ])


def ensure_golf_csv_exists():
    if not os.path.isfile(GOLF_CSV):
        with open(GOLF_CSV, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([
                "entry_id",
                "user",
                "date",
                "holes",
                "steps",
                "calories_burned",
                "score",
                "notes"
            ])


def ensure_photo_csv_exists():
    if not os.path.isfile(PHOTO_CSV):
        with open(PHOTO_CSV, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([
                "entry_id",
                "user",
                "date",
                "front_path",
                "side_path",
                "back_path",
                "notes"
            ])


def ensure_photo_dir_exists():
    os.makedirs(PHOTO_DIR, exist_ok=True)


def sanitize_username(username):
    cleaned = "".join(c for c in str(username) if c.isalnum() or c in (" ", "_", "-")).strip()
    return cleaned or "User"


def get_user_photo_folder(user):
    safe_user = sanitize_username(user)
    folder = os.path.join(PHOTO_DIR, safe_user)
    os.makedirs(folder, exist_ok=True)
    return folder


# =============================
# BODY CALCULATIONS
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
            2
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
            2
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
    if weekly_loss <= 0:
        return 0
    if current_weight <= goal_weight:
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


def body_fat_category(sex, body_fat):
    sex = str(sex).strip().lower()

    if sex == "male":
        if body_fat < 6:
            return "Essential fat"
        if body_fat < 14:
            return "Athletic"
        if body_fat < 18:
            return "Fit"
        if body_fat < 25:
            return "Average"
        return "Overweight"

    if sex == "female":
        if body_fat < 14:
            return "Essential fat"
        if body_fat < 21:
            return "Athletic"
        if body_fat < 25:
            return "Fit"
        if body_fat < 32:
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




# =============================
# BODY FAT ZONE BAR + GOUT RISK
# =============================
def gout_risk_zone_from_body_fat(body_fat_value):
    if body_fat_value < 20:
        return "Healthy", "#16a34a", "Lower gout-risk zone"
    if body_fat_value <= 25:
        return "Maybe", "#f59e0b", "Middle zone"
    return "Danger", "#dc2626", "Higher gout-risk zone"


def render_body_fat_zone_bar(value, min_value=5, max_value=30):
    safe_value = max(min_value, min(max_value, float(value)))
    marker_pct = ((safe_value - min_value) / (max_value - min_value)) * 100
    zone_label, zone_color, zone_text = gout_risk_zone_from_body_fat(safe_value)

    st.markdown(
        f"""
        <div style=\"margin-top:0.35rem;margin-bottom:0.35rem;\">\n            <div style=\"font-size:0.95rem;font-weight:600;\">Body fat health / gout guide</div>\n            <div style=\"position:relative;height:18px;border-radius:999px;overflow:hidden;border:1px solid #d1d5db;\">\n                <div style=\"position:absolute;left:0;width:60%;height:100%;background:#16a34a;\"></div>\n                <div style=\"position:absolute;left:60%;width:20%;height:100%;background:#f59e0b;\"></div>\n                <div style=\"position:absolute;left:80%;width:20%;height:100%;background:#dc2626;\"></div>\n                <div style=\"position:absolute;left:calc({marker_pct}% - 2px);top:0;width:4px;height:100%;background:#111827;\"></div>\n            </div>\n            <div style=\"display:flex;justify-content:space-between;font-size:0.8rem;margin-top:0.25rem;\">\n                <span>5%</span>\n                <span style=\"color:#16a34a;font-weight:600;\">Green: healthier</span>\n                <span style=\"color:#f59e0b;font-weight:600;\">Amber: maybe</span>\n                <span style=\"color:#dc2626;font-weight:600;\">Red: danger</span>\n                <span>30%</span>\n            </div>\n            <div style=\"margin-top:0.35rem;padding:0.45rem 0.7rem;border-radius:0.6rem;background:{zone_color};color:white;font-weight:700;display:inline-block;\">\n                {safe_value:.1f}% — {zone_label} — {zone_text}\n            </div>\n        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================
# CALORIE + MACRO CALCULATIONS
# =============================
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


def build_goal_macro_table(sex, height_inches, age, activity_label, goal_weights, deficit, protein_pct, carbs_pct, fats_pct):
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

        rows.append({
            "goal_weight_lbs": gw,
            "maintenance_cals": int(maint),
            "cutting_cals": int(cut),
            "protein_g": macros["protein_g"],
            "carbs_g": macros["carbs_g"],
            "fats_g": macros["fats_g"],
        })

    return pd.DataFrame(rows)


# =============================
# GOUT DASHBOARD HELPERS
# =============================
def gout_weight_zone(weight_lbs):
    if weight_lbs < 195:
        return "Lower", "#16a34a"
    if weight_lbs <= 210:
        return "Medium", "#f59e0b"
    return "Higher", "#dc2626"


def hydration_target_litres(weight_lbs):
    return round(weight_lbs * 0.015, 1)


def gout_food_guidance():
    return pd.DataFrame([
        {
            "Type": "Better choices",
            "Examples": "eggs, low-fat yogurt, chicken in moderate amounts, fruit, veg, oats, rice, potatoes",
        },
        {
            "Type": "Be careful",
            "Examples": "red meat, large portions of fish, rich sauces, sugary treats, dehydration days",
        },
        {
            "Type": "Avoid in flare",
            "Examples": "beer, spirits in excess, organ meats, anchovies, sardines, binge eating, very sugary drinks",
        },
    ])


# =============================
# GOLF CALCULATIONS
# =============================
def estimate_golf_calories(weight_lbs, steps):
    if weight_lbs < 180:
        calories_per_step = 0.05
    elif weight_lbs < 220:
        calories_per_step = 0.055
    else:
        calories_per_step = 0.06
    return round(steps * calories_per_step)


def fat_equivalent_from_calories(calories_burned):
    return round(calories_burned / 3500, 2)


def monthly_golf_fat_equivalent(golf_df):
    if golf_df.empty:
        return pd.DataFrame()

    temp = golf_df.copy()
    temp["month"] = temp["date"].astype(str).str[:7]
    monthly = temp.groupby("month", as_index=False)[["calories_burned"]].sum()
    monthly["fat_equivalent_lbs"] = monthly["calories_burned"].apply(fat_equivalent_from_calories)
    return monthly


# =============================
# LOAD / SAVE HELPERS
# =============================
def load_body_entries():
    ensure_body_csv_exists()
    return pd.read_csv(BODY_CSV)


def load_golf_entries():
    ensure_golf_csv_exists()
    return pd.read_csv(GOLF_CSV)


def load_photo_entries():
    ensure_photo_csv_exists()
    return pd.read_csv(PHOTO_CSV)


def save_body_df(df):
    df.to_csv(BODY_CSV, index=False)


def save_golf_df(df):
    df.to_csv(GOLF_CSV, index=False)


def save_photo_df(df):
    df.to_csv(PHOTO_CSV, index=False)


def append_body_entry(row):
    df = load_body_entries()
    df.loc[len(df)] = row
    save_body_df(df)


def append_golf_entry(row):
    df = load_golf_entries()
    df.loc[len(df)] = row
    save_golf_df(df)


def append_photo_entry(row):
    df = load_photo_entries()
    df.loc[len(df)] = row
    save_photo_df(df)


def monthly_averages(df):
    if df.empty:
        return pd.DataFrame()

    temp = df.copy()
    temp["month"] = temp["date"].astype(str).str[:7]
    grouped = temp.groupby("month", as_index=False)[["weight", "waist", "body_fat", "bmi"]].mean()
    return grouped.round(2)


def get_known_users(body_df, golf_df, photo_df):
    users = set()

    for df in [body_df, golf_df, photo_df]:
        if not df.empty and "user" in df.columns:
            users.update(df["user"].dropna().astype(str).str.strip())

    return sorted([u for u in users if u])


def latest_per_user(df, sort_col="date"):
    if df.empty:
        return pd.DataFrame()

    temp = df.copy().sort_values(sort_col)
    return temp.groupby("user", as_index=False).tail(1).sort_values("user")


def build_body_entry(
    entry_id,
    user,
    date,
    sex,
    weight,
    height,
    waist,
    neck,
    hips,
    target_body_fat,
    weekly_loss
):
    bf = navy_body_fat(sex, height, waist, neck, hips)
    fat_mass, lean_mass = body_composition(weight, bf)
    goal_weight = goal_weight_for_target_body_fat(lean_mass, target_body_fat)
    weeks = estimated_weeks_to_goal(weight, goal_weight, weekly_loss)
    goal_date = projected_goal_date(weeks)
    bmi_value = bmi(weight, height)
    whtr_value = waist_to_height_ratio(waist, height)

    return {
        "entry_id": entry_id,
        "user": user,
        "date": date,
        "sex": sex,
        "weight": weight,
        "height": height,
        "waist": waist,
        "neck": neck,
        "hips": hips if str(sex).lower() == "female" else 0.0,
        "body_fat": bf,
        "body_fat_category": body_fat_category(sex, bf),
        "fat_mass": fat_mass,
        "lean_mass": lean_mass,
        "target_body_fat": target_body_fat,
        "goal_weight": goal_weight,
        "weeks_to_goal": weeks,
        "projected_goal_date": goal_date,
        "bmi": bmi_value,
        "bmi_category": bmi_category(bmi_value),
        "waist_to_height_ratio": whtr_value,
        "whtr_category": whtr_category(whtr_value),
    }


def build_golf_entry(
    entry_id,
    user,
    date,
    holes,
    steps,
    weight_for_calories,
    score,
    notes
):
    calories = estimate_golf_calories(weight_for_calories, steps)

    return {
        "entry_id": entry_id,
        "user": user,
        "date": date,
        "holes": holes,
        "steps": steps,
        "calories_burned": calories,
        "score": score,
        "notes": notes,
    }


def save_uploaded_photo(uploaded_file, user, date_str, label):
    if uploaded_file is None:
        return ""

    user_folder = get_user_photo_folder(user)
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if not ext:
        ext = ".jpg"

    filename = f"{date_str}_{label}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(user_folder, filename)

    with open(file_path, "wb") as out_file:
        out_file.write(uploaded_file.getbuffer())

    return file_path


def delete_file_if_exists(path):
    if path and isinstance(path, str) and os.path.isfile(path):
        os.remove(path)


# =============================
# APP CONFIG
# =============================
st.set_page_config(page_title="Blazes Body Fat + Golf Tracker Pro", layout="wide")

st.markdown("""
<style>
.block-container {
    padding-top: 1.1rem;
    padding-bottom: 2rem;
}
[data-testid="stMetricValue"] {
    font-size: 1.45rem;
}
.apple-card {
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 14px 14px 12px 14px;
    margin-bottom: 12px;
    background: white;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    min-height: 150px;
}
.apple-card-title {
    font-size: 0.96rem;
    font-weight: 700;
    margin-bottom: 8px;
    line-height: 1.35;
}
.apple-card-body {
    font-size: 0.88rem;
    line-height: 1.6;
    color: #111827;
}
.apple-card-body div {
    white-space: normal;
    word-break: break-word;
}
</style>
""", unsafe_allow_html=True)

ensure_body_csv_exists()
ensure_golf_csv_exists()
ensure_photo_csv_exists()
ensure_photo_dir_exists()

all_body_df = load_body_entries()
all_golf_df = load_golf_entries()
all_photo_df = load_photo_entries()

known_users = get_known_users(all_body_df, all_golf_df, all_photo_df)

st.title("Blazes Body Fat + Golf Tracker Pro")
st.caption("Multi-user body composition, golf logging, leaderboards, editing, deleting, photo progress, and golf fat-equivalent")


# =============================
# SIDEBAR
# =============================
st.sidebar.header("User mode")

default_user = "Lee"
base_users = [default_user] + [u for u in known_users if u != default_user]
user_options = ["All Users"] + base_users if base_users else ["All Users", default_user]

selected_user = st.sidebar.selectbox("Choose user", user_options)
new_user = st.sidebar.text_input("Or type a new user name", value="").strip()

current_user = new_user if new_user else selected_user
is_all_users_mode = current_user == "All Users"

st.sidebar.markdown(f"**Current selection:** {current_user}")

if is_all_users_mode:
    body_df = all_body_df.copy()
    golf_df = all_golf_df.copy()
    photo_df = all_photo_df.copy()
else:
    body_df = all_body_df[all_body_df["user"] == current_user].copy() if not all_body_df.empty else pd.DataFrame()
    golf_df = all_golf_df[all_golf_df["user"] == current_user].copy() if not all_golf_df.empty else pd.DataFrame()
    photo_df = all_photo_df[all_photo_df["user"] == current_user].copy() if not all_photo_df.empty else pd.DataFrame()

tab1, tab2, tab3, tab4 = st.tabs(["Body Tracker", "Golf Tracker", "Leaderboards", "Photo Progress"])


# =========================================================
# BODY TRACKER TAB
# =========================================================
with tab1:
    st.subheader(f"Body Tracker — {current_user}")

    if not is_all_users_mode:
        c1, c2, c3, c4, c5, c6 = st.columns(6)

        with c1:
            sex = st.selectbox("Sex", ["Male", "Female"], index=0)

        with c2:
            weight = st.number_input("Weight (lbs)", min_value=1.0, value=208.0, step=0.1)

        with c3:
            height = st.number_input("Height (inches)", min_value=1.0, value=70.0, step=0.1)

        with c4:
            waist = st.number_input("Waist (inches)", min_value=1.0, value=40.5, step=0.1)

        with c5:
            neck = st.number_input("Neck (inches)", min_value=1.0, value=17.0, step=0.1)

        with c6:
            hips = st.number_input(
                "Hips (inches)",
                min_value=0.0,
                value=0.0 if sex == "Male" else 42.0,
                step=0.1,
                help="Required for females only"
            )

        d1, d2 = st.columns(2)

        with d1:
            target_body_fat = st.slider(
                "Target BF % (choose between 5 and 30)",
                min_value=5,
                max_value=30,
                value=18,
                step=1,
                key="target_body_fat_slider"
            )
            render_body_fat_zone_bar(target_body_fat)

        with d2:
            weekly_loss = st.number_input("Weekly loss", min_value=0.1, value=1.25, step=0.05)

        st.subheader("Calories + macros")
        m1, m2, m3 = st.columns(3)

        with m1:
            age = st.number_input("Age", min_value=10, max_value=100, value=48, step=1)

        with m2:
            activity_label = st.selectbox(
                "Activity level",
                ["Sedentary", "Lightly active", "Moderately active", "Very active", "Extra active"],
                index=2,
            )

        with m3:
            calorie_deficit = st.number_input("Calorie deficit", min_value=0, max_value=1500, value=500, step=50)

        m4, m5, m6 = st.columns(3)

        with m4:
            protein_pct = st.number_input("Protein %", min_value=10, max_value=60, value=30, step=1)

        with m5:
            carbs_pct = st.number_input("Carbs %", min_value=10, max_value=70, value=40, step=1)

        with m6:
            fats_pct = st.number_input("Fats %", min_value=10, max_value=50, value=30, step=1)

        if protein_pct + carbs_pct + fats_pct != 100:
            st.warning("Protein %, carbs %, and fats % should add up to 100.")

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

        save_body_clicked = st.button("Save body entry", use_container_width=True)

        try:
            preview = build_body_entry(
                entry_id="preview",
                user=current_user,
                date=datetime.now().strftime("%Y-%m-%d"),
                sex=sex,
                weight=weight,
                height=height,
                waist=waist,
                neck=neck,
                hips=hips,
                target_body_fat=target_body_fat,
                weekly_loss=weekly_loss
            )

            if save_body_clicked:
                entry = build_body_entry(
                    entry_id=str(uuid.uuid4()),
                    user=current_user,
                    date=datetime.now().strftime("%Y-%m-%d"),
                    sex=sex,
                    weight=weight,
                    height=height,
                    waist=waist,
                    neck=neck,
                    hips=hips,
                    target_body_fat=target_body_fat,
                    weekly_loss=weekly_loss
                )
                append_body_entry(entry)
                st.success(f"Body entry saved for {current_user}.")
                st.rerun()

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

            row1 = st.columns(4)
            row1[0].metric("Body Fat %", preview["body_fat"])
            row1[1].metric("Fat Mass", f'{preview["fat_mass"]} lbs')
            row1[2].metric("Lean Mass", f'{preview["lean_mass"]} lbs')
            row1[3].metric("Goal Weight", f'{preview["goal_weight"]} lbs')

            st.subheader("Progress to target")
            st.progress(progress_ratio(preview["body_fat"], start_bf=30, target_bf=target_body_fat))
            st.caption(f"{current_user}: tracking toward {target_body_fat}% body fat")
            render_body_fat_zone_bar(preview["body_fat"])

            row2 = st.columns(4)
            row2[0].metric("BMI", preview["bmi"])
            row2[1].metric("BMI Zone", preview["bmi_category"])
            row2[2].metric("WHtR", preview["waist_to_height_ratio"])
            row2[3].metric("WHtR Zone", preview["whtr_category"])

            st.subheader("Goal countdown")
            row3 = st.columns(4)
            row3[0].metric("Lbs to Lose", round(max(0, weight - preview["goal_weight"]), 2))
            row3[1].metric("Weeks to Goal", preview["weeks_to_goal"])
            row3[2].metric("Goal Date", preview["projected_goal_date"])
            row3[3].metric("Body Fat Zone", preview["body_fat_category"])

            st.subheader("Weight milestones")
            row4 = st.columns(3)
            row4[0].metric("200 lbs", predict_date_for_weight(weight, 200, weekly_loss))
            row4[1].metric("195 lbs", predict_date_for_weight(weight, 195, weekly_loss))
            row4[2].metric("190 lbs", predict_date_for_weight(weight, 190, weekly_loss))

            st.subheader("Calories and macros right now")
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Maintenance Calories", f"{int(current_maintenance)} kcal")
            mc2.metric("Cutting Calories", f"{int(current_cutting)} kcal")
            mc3.metric("Protein", f"{current_macros['protein_g']} g")
            mc4.metric("Carbs / Fats", f"{current_macros['carbs_g']} g / {current_macros['fats_g']} g")

            st.subheader("Calories and macros at goal weights")
            goal_weights = [
                round(weight),
                200,
                195,
                190,
                round(preview["goal_weight"]),
            ]
            goal_weights = sorted(set([gw for gw in goal_weights if gw > 0]), reverse=True)

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

            # Estimate body fat at each goal weight using current lean mass
            est_rows = []
            lean_mass_est = preview["lean_mass"]

            for gw in goal_macro_df["goal_weight_lbs"]:
                est_bf = round((1 - (lean_mass_est / gw)) * 100, 1)
                zone_label, zone_color, _ = gout_risk_zone_from_body_fat(est_bf)
                est_rows.append((est_bf, zone_label, zone_color))

            goal_macro_df["est_body_fat_%"] = [r[0] for r in est_rows]
            goal_macro_df["gout_zone"] = [r[1] for r in est_rows]

            def color_rows(row):
                idx = row.name
                color = est_rows[idx][2]
                return [f"background-color: {color}; color: white" if col == "gout_zone" else "" for col in row.index]

            styled_df = goal_macro_df.style.apply(color_rows, axis=1)

            st.dataframe(styled_df, use_container_width=True)

            st.subheader("Gout Risk Dashboard")

            bf_zone_label, bf_zone_color, bf_zone_text = gout_risk_zone_from_body_fat(preview["body_fat"])
            weight_zone_label, weight_zone_color = gout_weight_zone(weight)
            water_target = hydration_target_litres(weight)

            gd1, gd2, gd3, gd4 = st.columns(4)

            with gd1:
                st.markdown(
                    f"""
                    <div style="padding:0.8rem;border-radius:0.8rem;background:{bf_zone_color};color:white;font-weight:700;text-align:center;">
                        Body Fat Risk<br>{preview["body_fat"]}%<br>{bf_zone_label}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with gd2:
                st.markdown(
                    f"""
                    <div style="padding:0.8rem;border-radius:0.8rem;background:{weight_zone_color};color:white;font-weight:700;text-align:center;">
                        Weight Risk<br>{weight} lbs<br>{weight_zone_label}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with gd3:
                st.metric("Hydration Target", f"{water_target} L / day")

            with gd4:
                st.metric("Weekly Loss Target", f"{weekly_loss} lbs")

            st.caption(
                "Guide only: gout risk is influenced by body fat, weight, hydration, alcohol, sugar intake, purine intake, medicines, and uric acid levels."
            )

            st.markdown("### Flare-day food guide")
            st.dataframe(gout_food_guidance(), use_container_width=True)

            st.markdown("### Quick gout tips")
            tip1, tip2, tip3 = st.columns(3)
            tip1.info("Drink steadily through the day and especially after golf or training.")
            tip2.info("Avoid binge meals, heavy alcohol, and dehydration when symptoms are brewing.")
            tip3.info("Aim to move from red → amber → green as weight and body fat come down.")

        except ValueError as e:
            st.error(str(e))

    if is_all_users_mode:
        if body_df.empty:
            st.info("No body entries saved yet.")
        else:
            latest_body = latest_per_user(body_df)

            st.subheader("Latest body stats by user")
            show_cols = [
                "user", "date", "sex", "weight", "waist", "body_fat",
                "fat_mass", "lean_mass", "bmi", "waist_to_height_ratio"
            ]
            st.dataframe(latest_body[show_cols], use_container_width=True)

            st.subheader("User comparison")
            u1, u2, u3 = st.columns(3)
            u1.metric("Users Logged", latest_body["user"].nunique())
            u2.metric("Lowest Body Fat", f'{latest_body["body_fat"].min()} %')
            u3.metric("Lowest Weight", f'{latest_body["weight"].min()} lbs')

            st.subheader("Body charts by user")
            st.line_chart(body_df.pivot_table(index="date", columns="user", values="weight", aggfunc="last"))
            st.line_chart(body_df.pivot_table(index="date", columns="user", values="body_fat", aggfunc="last"))
            st.line_chart(body_df.pivot_table(index="date", columns="user", values="waist", aggfunc="last"))

            st.subheader("All body entries")
            st.dataframe(body_df, use_container_width=True)

    else:
        if not body_df.empty:
            st.subheader("Body charts")
            cc1, cc2 = st.columns(2)

            with cc1:
                st.line_chart(body_df.set_index("date")["weight"])
                st.line_chart(body_df.set_index("date")["waist"])

            with cc2:
                st.line_chart(body_df.set_index("date")["body_fat"])
                st.line_chart(body_df.set_index("date")["bmi"])

            monthly_df = monthly_averages(body_df)
            if not monthly_df.empty:
                st.subheader("Monthly averages")
                st.dataframe(monthly_df, use_container_width=True)

            st.subheader("Best body stats")
            b1, b2, b3 = st.columns(3)
            b1.metric("Lowest Weight", f'{body_df["weight"].min()} lbs')
            b2.metric("Lowest Waist", f'{body_df["waist"].min()} in')
            b3.metric("Lowest Body Fat", f'{body_df["body_fat"].min()} %')

            st.subheader("Saved body entries")
            st.dataframe(body_df, use_container_width=True)

            st.subheader("Edit or delete body entry")
            body_options_df = body_df.sort_values("date", ascending=False).copy()
            body_options_df["label"] = (
                body_options_df["date"].astype(str)
                + " | "
                + body_options_df["weight"].astype(str)
                + " lbs | BF "
                + body_options_df["body_fat"].astype(str)
                + "%"
            )

            selected_body_id = st.selectbox(
                "Choose body entry",
                body_options_df["entry_id"].tolist(),
                format_func=lambda x: body_options_df.loc[body_options_df["entry_id"] == x, "label"].iloc[0],
                key="body_edit_select"
            )

            selected_body_row = all_body_df[all_body_df["entry_id"] == selected_body_id].iloc[0]

            with st.form("edit_body_form"):
                eb1, eb2, eb3 = st.columns(3)

                with eb1:
                    edit_date = st.text_input("Date", value=str(selected_body_row["date"]))
                    edit_sex = st.selectbox(
                        "Sex",
                        ["Male", "Female"],
                        index=0 if str(selected_body_row["sex"]) == "Male" else 1,
                        key="edit_body_sex"
                    )
                    edit_weight = st.number_input(
                        "Weight (lbs)",
                        min_value=1.0,
                        value=float(selected_body_row["weight"]),
                        step=0.1
                    )

                with eb2:
                    edit_height = st.number_input(
                        "Height (inches)",
                        min_value=1.0,
                        value=float(selected_body_row["height"]),
                        step=0.1
                    )
                    edit_waist = st.number_input(
                        "Waist (inches)",
                        min_value=1.0,
                        value=float(selected_body_row["waist"]),
                        step=0.1
                    )
                    edit_neck = st.number_input(
                        "Neck (inches)",
                        min_value=1.0,
                        value=float(selected_body_row["neck"]),
                        step=0.1
                    )

                with eb3:
                    edit_hips = st.number_input(
                        "Hips (inches)",
                        min_value=0.0,
                        value=float(selected_body_row["hips"]),
                        step=0.1
                    )

                    existing_target = int(selected_body_row["target_body_fat"]) if pd.notna(selected_body_row["target_body_fat"]) else 18
                    if existing_target < 5 or existing_target > 30:
                        existing_target = 18

                    edit_target_bf = st.slider(
                        "Target BF % (choose between 5 and 30)",
                        min_value=5,
                        max_value=30,
                        value=existing_target,
                        step=1,
                        key="edit_target_bf"
                    )
                    render_body_fat_zone_bar(edit_target_bf)

                    edit_weekly_loss = st.number_input(
                        "Weekly loss",
                        min_value=0.1,
                        value=1.25,
                        step=0.05
                    )

                update_body = st.form_submit_button("Update body entry")

            col_del1, _ = st.columns([1, 3])
            with col_del1:
                delete_body = st.button("Delete body entry", type="secondary")

            if update_body:
                try:
                    updated = build_body_entry(
                        entry_id=selected_body_id,
                        user=current_user,
                        date=edit_date,
                        sex=edit_sex,
                        weight=edit_weight,
                        height=edit_height,
                        waist=edit_waist,
                        neck=edit_neck,
                        hips=edit_hips,
                        target_body_fat=edit_target_bf,
                        weekly_loss=edit_weekly_loss
                    )

                    for key, value in updated.items():
                        all_body_df.loc[all_body_df["entry_id"] == selected_body_id, key] = value

                    save_body_df(all_body_df)
                    st.success("Body entry updated.")
                    st.rerun()

                except ValueError as e:
                    st.error(str(e))

            if delete_body:
                all_body_df = all_body_df[all_body_df["entry_id"] != selected_body_id].copy()
                save_body_df(all_body_df)
                st.success("Body entry deleted.")
                st.rerun()

        else:
            st.info(f"No body entries saved yet for {current_user}.")


# =========================================================
# GOLF TRACKER TAB
# =========================================================
with tab2:
    st.subheader(f"Golf Tracker — {current_user}")

    if not is_all_users_mode:
        g1, g2, g3 = st.columns(3)

        with g1:
            golf_date = st.date_input("Round date", value=datetime.now())
            holes = st.selectbox("Holes played", [9, 10, 12, 18], index=3)

        with g2:
            steps = st.number_input("Steps walked", min_value=0, value=12000, step=500)
            score = st.number_input("Score", min_value=0, value=90, step=1)

        with g3:
            notes = st.text_input("Notes", value="")

        current_weight_for_golf = st.number_input(
            "Current weight for calorie estimate (lbs)",
            min_value=1.0,
            value=208.0,
            step=0.1,
            key="golf_weight"
        )

        estimated_calories = estimate_golf_calories(current_weight_for_golf, steps)
        st.metric("Estimated calories burned", f"{estimated_calories} kcal")

        save_golf_clicked = st.button("Save golf round")

        if save_golf_clicked:
            entry = build_golf_entry(
                entry_id=str(uuid.uuid4()),
                user=current_user,
                date=str(golf_date),
                holes=holes,
                steps=steps,
                weight_for_calories=current_weight_for_golf,
                score=score,
                notes=notes
            )
            append_golf_entry(entry)
            st.success(f"Golf round saved for {current_user}.")
            st.rerun()

    if is_all_users_mode:
        if golf_df.empty:
            st.info("No golf rounds saved yet.")
        else:
            st.subheader("Golf summary by user")

            summary = golf_df.groupby("user", as_index=False).agg(
                rounds_logged=("date", "count"),
                total_steps=("steps", "sum"),
                total_calories=("calories_burned", "sum"),
                avg_score=("score", "mean")
            )
            summary["avg_score"] = summary["avg_score"].round(1)
            summary["fat_equivalent_lbs"] = summary["total_calories"].apply(fat_equivalent_from_calories)

            st.dataframe(summary, use_container_width=True)

            st.subheader("Golf charts by user")
            st.line_chart(golf_df.pivot_table(index="date", columns="user", values="steps", aggfunc="sum"))
            st.line_chart(golf_df.pivot_table(index="date", columns="user", values="calories_burned", aggfunc="sum"))
            st.line_chart(golf_df.pivot_table(index="date", columns="user", values="score", aggfunc="mean"))

            st.subheader("All golf entries")
            st.dataframe(golf_df, use_container_width=True)

    else:
        if not golf_df.empty:
            st.subheader("Golf summary")

            gs1, gs2, gs3, gs4 = st.columns(4)
            gs1.metric("Rounds Logged", len(golf_df))
            gs2.metric("Total Steps", int(golf_df["steps"].sum()))
            gs3.metric("Total Calories", int(golf_df["calories_burned"].sum()))
            gs4.metric("Average Steps / Round", int(golf_df["steps"].mean()))

            total_golf_calories = int(golf_df["calories_burned"].sum())
            fat_equivalent = fat_equivalent_from_calories(total_golf_calories)

            st.subheader("Golf fat-loss impact")
            gf1, gf2, gf3 = st.columns(3)
            gf1.metric("Total Golf Calories", f"{total_golf_calories} kcal")
            gf2.metric("Fat-Equivalent Burned", f"{fat_equivalent} lbs")
            gf3.metric("Average Calories / Round", f"{int(golf_df['calories_burned'].mean())} kcal")

            monthly_fat_df = monthly_golf_fat_equivalent(golf_df)
            if not monthly_fat_df.empty:
                st.subheader("Monthly golf fat-equivalent")
                st.dataframe(monthly_fat_df, use_container_width=True)

            st.subheader("Golf charts")
            gc1, gc2 = st.columns(2)

            with gc1:
                st.line_chart(golf_df.set_index("date")["steps"])
                st.line_chart(golf_df.set_index("date")["calories_burned"])

            with gc2:
                st.line_chart(golf_df.set_index("date")["score"])
                golf_by_holes = golf_df.groupby("holes", as_index=False)[["steps", "calories_burned"]].mean()
                st.dataframe(golf_by_holes, use_container_width=True)

            if not body_df.empty:
                st.subheader("Body weight vs golf activity")
                merged = pd.merge(
                    body_df[["date", "weight"]],
                    golf_df[["date", "steps", "calories_burned"]],
                    on="date",
                    how="inner"
                )

                if not merged.empty:
                    mg1, mg2 = st.columns(2)
                    with mg1:
                        st.line_chart(merged.set_index("date")["weight"])
                    with mg2:
                        st.line_chart(merged.set_index("date")["steps"])
                else:
                    st.info(f"No matching dates yet between body entries and golf rounds for {current_user}.")

            st.subheader("Saved golf rounds")
            st.dataframe(golf_df, use_container_width=True)

            st.subheader("Edit or delete golf round")
            golf_options_df = golf_df.sort_values("date", ascending=False).copy()
            golf_options_df["label"] = (
                golf_options_df["date"].astype(str)
                + " | "
                + golf_options_df["holes"].astype(str)
                + " holes | score "
                + golf_options_df["score"].astype(str)
            )

            selected_golf_id = st.selectbox(
                "Choose golf round",
                golf_options_df["entry_id"].tolist(),
                format_func=lambda x: golf_options_df.loc[golf_options_df["entry_id"] == x, "label"].iloc[0],
                key="golf_edit_select"
            )

            selected_golf_row = all_golf_df[all_golf_df["entry_id"] == selected_golf_id].iloc[0]

            with st.form("edit_golf_form"):
                gg1, gg2, gg3 = st.columns(3)

                with gg1:
                    edit_golf_date = st.text_input("Round date", value=str(selected_golf_row["date"]))
                    existing_holes = int(selected_golf_row["holes"])
                    if existing_holes not in [9, 10, 12, 18]:
                        existing_holes = 18
                    edit_holes = st.selectbox(
                        "Holes played",
                        [9, 10, 12, 18],
                        index=[9, 10, 12, 18].index(existing_holes),
                        key="edit_holes"
                    )

                with gg2:
                    edit_steps = st.number_input("Steps walked", min_value=0, value=int(selected_golf_row["steps"]), step=500)
                    edit_score = st.number_input("Score", min_value=0, value=int(selected_golf_row["score"]), step=1)

                with gg3:
                    edit_weight_for_cal = st.number_input("Weight for calorie estimate", min_value=1.0, value=208.0, step=0.1)
                    edit_notes = st.text_input("Notes", value=str(selected_golf_row["notes"]))

                update_golf = st.form_submit_button("Update golf round")

            gd1, _ = st.columns([1, 3])
            with gd1:
                delete_golf = st.button("Delete golf round", type="secondary")

            if update_golf:
                updated = build_golf_entry(
                    entry_id=selected_golf_id,
                    user=current_user,
                    date=edit_golf_date,
                    holes=edit_holes,
                    steps=edit_steps,
                    weight_for_calories=edit_weight_for_cal,
                    score=edit_score,
                    notes=edit_notes
                )

                for key, value in updated.items():
                    all_golf_df.loc[all_golf_df["entry_id"] == selected_golf_id, key] = value

                save_golf_df(all_golf_df)
                st.success("Golf round updated.")
                st.rerun()

            if delete_golf:
                all_golf_df = all_golf_df[all_golf_df["entry_id"] != selected_golf_id].copy()
                save_golf_df(all_golf_df)
                st.success("Golf round deleted.")
                st.rerun()

        else:
            st.info(f"No golf rounds saved yet for {current_user}.")


# =========================================================
# LEADERBOARDS TAB
# =========================================================
with tab3:
    st.subheader("Leaderboards")

    if all_body_df.empty and all_golf_df.empty:
        st.info("No data saved yet.")
    else:
        if not all_body_df.empty:
            latest_body = latest_per_user(all_body_df)

            st.markdown("### Body leaderboards")

            lb1, lb2, lb3 = st.columns(3)

            with lb1:
                lowest_bf = latest_body.sort_values("body_fat").head(5)[["user", "body_fat", "date"]]
                st.markdown("**Lowest body fat**")
                st.dataframe(lowest_bf, use_container_width=True)

            with lb2:
                lowest_weight = latest_body.sort_values("weight").head(5)[["user", "weight", "date"]]
                st.markdown("**Lowest weight**")
                st.dataframe(lowest_weight, use_container_width=True)

            with lb3:
                lowest_waist = latest_body.sort_values("waist").head(5)[["user", "waist", "date"]]
                st.markdown("**Lowest waist**")
                st.dataframe(lowest_waist, use_container_width=True)

            first_body = all_body_df.sort_values("date").groupby("user", as_index=False).head(1)
            latest_body2 = all_body_df.sort_values("date").groupby("user", as_index=False).tail(1)

            weight_loss_df = pd.merge(
                first_body[["user", "weight"]].rename(columns={"weight": "start_weight"}),
                latest_body2[["user", "weight"]].rename(columns={"weight": "latest_weight"}),
                on="user",
                how="inner"
            )
            weight_loss_df["weight_lost"] = (weight_loss_df["start_weight"] - weight_loss_df["latest_weight"]).round(2)
            weight_loss_df = weight_loss_df.sort_values("weight_lost", ascending=False)

            st.markdown("### Most weight lost")
            st.dataframe(weight_loss_df[["user", "start_weight", "latest_weight", "weight_lost"]], use_container_width=True)

        if not all_golf_df.empty:
            st.markdown("### Golf leaderboards")

            golf_summary = all_golf_df.groupby("user", as_index=False).agg(
                rounds_logged=("date", "count"),
                total_steps=("steps", "sum"),
                total_calories=("calories_burned", "sum"),
                avg_score=("score", "mean")
            )
            golf_summary["avg_score"] = golf_summary["avg_score"].round(1)
            golf_summary["fat_equivalent_lbs"] = golf_summary["total_calories"].apply(fat_equivalent_from_calories)

            gl1, gl2, gl3, gl4 = st.columns(4)

            with gl1:
                most_steps = golf_summary.sort_values("total_steps", ascending=False).head(5)
                st.markdown("**Most golf steps**")
                st.dataframe(most_steps[["user", "total_steps"]], use_container_width=True)

            with gl2:
                most_rounds = golf_summary.sort_values("rounds_logged", ascending=False).head(5)
                st.markdown("**Most rounds logged**")
                st.dataframe(most_rounds[["user", "rounds_logged"]], use_container_width=True)

            with gl3:
                best_score = golf_summary.sort_values("avg_score", ascending=True).head(5)
                st.markdown("**Best average score**")
                st.dataframe(best_score[["user", "avg_score"]], use_container_width=True)

            with gl4:
                most_fat_equiv = golf_summary.sort_values("fat_equivalent_lbs", ascending=False).head(5)
                st.markdown("**Most golf fat-equivalent**")
                st.dataframe(most_fat_equiv[["user", "fat_equivalent_lbs"]], use_container_width=True)


# =========================================================
# PHOTO PROGRESS TAB
# =========================================================
with tab4:
    st.subheader(f"Photo Progress — {current_user}")

    if is_all_users_mode:
        if photo_df.empty:
            st.info("No photo entries saved yet.")
        else:
            st.subheader("Latest photo sets by user")
            latest_photos = latest_per_user(photo_df)
            st.dataframe(latest_photos[["user", "date", "notes"]], use_container_width=True)

            selected_photo_user = st.selectbox(
                "Choose user to view photos",
                sorted(photo_df["user"].dropna().unique().tolist()),
                key="all_users_photo_view"
            )

            selected_user_photos = photo_df[photo_df["user"] == selected_photo_user].sort_values("date", ascending=False)

            if not selected_user_photos.empty:
                chosen_photo_id = st.selectbox(
                    "Choose photo set",
                    selected_user_photos["entry_id"].tolist(),
                    format_func=lambda x: selected_user_photos.loc[selected_user_photos["entry_id"] == x, "date"].iloc[0],
                    key="all_users_photo_set"
                )

                chosen_row = selected_user_photos[selected_user_photos["entry_id"] == chosen_photo_id].iloc[0]

                p1, p2, p3 = st.columns(3)
                with p1:
                    if chosen_row["front_path"] and os.path.isfile(chosen_row["front_path"]):
                        st.image(chosen_row["front_path"], caption="Front")
                with p2:
                    if chosen_row["side_path"] and os.path.isfile(chosen_row["side_path"]):
                        st.image(chosen_row["side_path"], caption="Side")
                with p3:
                    if chosen_row["back_path"] and os.path.isfile(chosen_row["back_path"]):
                        st.image(chosen_row["back_path"], caption="Back")
    else:
        st.markdown("### Upload a new photo set")

        photo_date = st.date_input("Photo date", value=datetime.now(), key="photo_date")
        photo_notes = st.text_input("Photo notes", value="", key="photo_notes")

        pp1, pp2, pp3 = st.columns(3)
        with pp1:
            front_file = st.file_uploader("Front photo", type=["jpg", "jpeg", "png"], key="front_upload")
        with pp2:
            side_file = st.file_uploader("Side photo", type=["jpg", "jpeg", "png"], key="side_upload")
        with pp3:
            back_file = st.file_uploader("Back photo", type=["jpg", "jpeg", "png"], key="back_upload")

        save_photos_clicked = st.button("Save photo set")

        if save_photos_clicked:
            if front_file is None and side_file is None and back_file is None:
                st.error("Please upload at least one photo.")
            else:
                date_str = str(photo_date)
                front_path = save_uploaded_photo(front_file, current_user, date_str, "front")
                side_path = save_uploaded_photo(side_file, current_user, date_str, "side")
                back_path = save_uploaded_photo(back_file, current_user, date_str, "back")

                photo_entry = {
                    "entry_id": str(uuid.uuid4()),
                    "user": current_user,
                    "date": date_str,
                    "front_path": front_path,
                    "side_path": side_path,
                    "back_path": back_path,
                    "notes": photo_notes
                }
                append_photo_entry(photo_entry)
                st.success(f"Photo set saved for {current_user}.")
                st.rerun()

        if not photo_df.empty:
            st.markdown("### Latest saved photo set")
            latest_row = photo_df.sort_values("date", ascending=False).iloc[0]

            lp1, lp2, lp3 = st.columns(3)
            with lp1:
                if latest_row["front_path"] and os.path.isfile(latest_row["front_path"]):
                    st.image(latest_row["front_path"], caption="Front")
            with lp2:
                if latest_row["side_path"] and os.path.isfile(latest_row["side_path"]):
                    st.image(latest_row["side_path"], caption="Side")
            with lp3:
                if latest_row["back_path"] and os.path.isfile(latest_row["back_path"]):
                    st.image(latest_row["back_path"], caption="Back")

            st.markdown("### Photo history")
            st.dataframe(photo_df[["date", "notes"]].sort_values("date", ascending=False), use_container_width=True)

            st.markdown("### View older photo sets")
            photo_options_df = photo_df.sort_values("date", ascending=False).copy()
            photo_options_df["label"] = photo_options_df["date"].astype(str) + " | " + photo_options_df["notes"].fillna("")

            selected_photo_id = st.selectbox(
                "Choose photo set",
                photo_options_df["entry_id"].tolist(),
                format_func=lambda x: photo_options_df.loc[photo_options_df["entry_id"] == x, "label"].iloc[0],
                key="photo_edit_select"
            )

            selected_photo_row = all_photo_df[all_photo_df["entry_id"] == selected_photo_id].iloc[0]

            vp1, vp2, vp3 = st.columns(3)
            with vp1:
                if selected_photo_row["front_path"] and os.path.isfile(selected_photo_row["front_path"]):
                    st.image(selected_photo_row["front_path"], caption="Front")
            with vp2:
                if selected_photo_row["side_path"] and os.path.isfile(selected_photo_row["side_path"]):
                    st.image(selected_photo_row["side_path"], caption="Side")
            with vp3:
                if selected_photo_row["back_path"] and os.path.isfile(selected_photo_row["back_path"]):
                    st.image(selected_photo_row["back_path"], caption="Back")

            st.markdown("### Delete photo set")
            delete_photo = st.button("Delete selected photo set", type="secondary")

            if delete_photo:
                delete_file_if_exists(selected_photo_row["front_path"])
                delete_file_if_exists(selected_photo_row["side_path"])
                delete_file_if_exists(selected_photo_row["back_path"])

                all_photo_df = all_photo_df[all_photo_df["entry_id"] != selected_photo_id].copy()
                save_photo_df(all_photo_df)
                st.success("Photo set deleted.")
                st.rerun()
        else:
            st.info(f"No photo sets saved yet for {current_user}.")