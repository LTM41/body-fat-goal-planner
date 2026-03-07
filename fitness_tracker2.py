import math
import csv
import os
from collections import defaultdict
from datetime import datetime, timedelta
import matplotlib.pyplot as plt


CSV_FILE = "body_progress.csv"


def ensure_csv_exists():
    """
    Create the CSV file with headers if it doesn't exist yet.
    """
    if not os.path.isfile(CSV_FILE):
        with open(CSV_FILE, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([
                "date",
                "weight",
                "height",
                "waist",
                "neck",
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


def navy_body_fat_male(height, waist, neck):
    """
    Calculate male body fat % using the U.S. Navy method.
    All measurements must be in inches.
    """
    if waist <= neck:
        raise ValueError("Waist must be larger than neck.")
    if min(height, waist, neck) <= 0:
        raise ValueError("All measurements must be greater than zero.")

    body_fat = (
        86.010 * math.log10(waist - neck)
        - 70.041 * math.log10(height)
        + 36.76
    )
    return round(body_fat, 2)


def body_composition(weight, body_fat):
    """
    Return fat mass and lean mass in lbs.
    """
    fat_mass = round(weight * (body_fat / 100), 2)
    lean_mass = round(weight - fat_mass, 2)
    return fat_mass, lean_mass


def goal_weight_for_target_body_fat(lean_mass, target_body_fat):
    """
    Calculate goal weight based on lean mass and target body fat %.
    """
    if not (0 < target_body_fat < 100):
        raise ValueError("Target body fat must be between 0 and 100.")
    return round(lean_mass / (1 - target_body_fat / 100), 2)


def estimated_weeks_to_goal(current_weight, goal_weight, weekly_loss=1.25):
    """
    Estimate weeks to reach goal.
    """
    if weekly_loss <= 0:
        raise ValueError("Weekly loss must be greater than zero.")
    if current_weight <= goal_weight:
        return 0
    return math.ceil((current_weight - goal_weight) / weekly_loss)


def projected_goal_date(weeks_to_goal):
    """
    Return projected date from today based on weeks to goal.
    """
    return (datetime.now() + timedelta(weeks=weeks_to_goal)).strftime("%Y-%m-%d")


def bmi(weight_lbs, height_inches):
    """
    BMI using lbs and inches.
    """
    return round((weight_lbs / (height_inches ** 2)) * 703, 2)


def bmi_category(bmi_value):
    """
    BMI category.
    """
    if bmi_value < 18.5:
        return "Underweight"
    if bmi_value < 25:
        return "Healthy"
    if bmi_value < 30:
        return "Overweight"
    return "Obese"


def waist_to_height_ratio(waist_inches, height_inches):
    """
    Waist-to-height ratio.
    """
    return round(waist_inches / height_inches, 3)


def whtr_category(ratio):
    """
    Waist-to-height ratio category.
    """
    if ratio < 0.5:
        return "Healthy"
    if ratio < 0.6:
        return "Moderate risk"
    return "High risk"


def body_fat_category(body_fat):
    """
    Male body fat category.
    """
    if body_fat < 6:
        return "Essential fat"
    if body_fat < 14:
        return "Athletic"
    if body_fat < 18:
        return "Fit"
    if body_fat < 25:
        return "Average"
    return "Overweight"


def progress_bar(current_bf, start_bf=30, target_bf=18, bar_length=30):
    """
    Simple text progress bar for body fat progress.
    """
    if start_bf <= target_bf:
        raise ValueError("Start body fat must be greater than target body fat.")

    total_range = start_bf - target_bf
    remaining = max(0, current_bf - target_bf)
    completed_ratio = max(0, min(1, (total_range - remaining) / total_range))

    filled = int(bar_length * completed_ratio)
    empty = bar_length - filled
    return "[" + "#" * filled + "-" * empty + f"] {completed_ratio * 100:.1f}%"


def save_entry(filename, row):
    """
    Save one row to CSV.
    """
    ensure_csv_exists()
    with open(filename, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(row)


def load_entries(filename):
    """
    Load all CSV entries into a list of dictionaries.
    """
    if not os.path.isfile(filename):
        return []

    entries = []
    with open(filename, "r", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Skip any blank rows just in case
            if not row["date"]:
                continue

            entries.append({
                "date": row["date"],
                "weight": float(row["weight"]),
                "height": float(row["height"]),
                "waist": float(row["waist"]),
                "neck": float(row["neck"]),
                "body_fat": float(row["body_fat"]),
                "body_fat_category": row["body_fat_category"],
                "fat_mass": float(row["fat_mass"]),
                "lean_mass": float(row["lean_mass"]),
                "target_body_fat": float(row["target_body_fat"]),
                "goal_weight": float(row["goal_weight"]),
                "weeks_to_goal": int(float(row["weeks_to_goal"])),
                "projected_goal_date": row["projected_goal_date"],
                "bmi": float(row["bmi"]),
                "bmi_category": row["bmi_category"],
                "waist_to_height_ratio": float(row["waist_to_height_ratio"]),
                "whtr_category": row["whtr_category"],
            })
    return entries


def compare_to_last_entry(current_results, entries):
    """
    Compare current entry to last saved entry.
    """
    if not entries:
        return None

    last = entries[-1]
    return {
        "weight_change": round(current_results["weight"] - last["weight"], 2),
        "waist_change": round(current_results["waist"] - last["waist"], 2),
        "body_fat_change": round(current_results["body_fat"] - last["body_fat"], 2),
    }


def compare_to_first_entry(current_results, entries):
    """
    Compare current entry to first saved entry.
    """
    if not entries:
        return None

    first = entries[0]
    return {
        "weight_change_since_first": round(current_results["weight"] - first["weight"], 2),
        "waist_change_since_first": round(current_results["waist"] - first["waist"], 2),
        "body_fat_change_since_first": round(current_results["body_fat"] - first["body_fat"], 2),
    }


def print_change(label, value, unit=""):
    """
    Pretty-print changes in stats.
    """
    if value < 0:
        print(f"{label:<30} down {abs(value)}{unit}")
    elif value > 0:
        print(f"{label:<30} up {value}{unit}")
    else:
        print(f"{label:<30} no change")


def predict_date_for_weight(current_weight, target_weight, weekly_loss):
    """
    Predict date for reaching a target weight.
    """
    if weekly_loss <= 0:
        return "N/A"
    if current_weight <= target_weight:
        return "Already reached"

    weeks = math.ceil((current_weight - target_weight) / weekly_loss)
    return (datetime.now() + timedelta(weeks=weeks)).strftime("%Y-%m-%d")


def monthly_averages(entries):
    """
    Group entries by month and return monthly averages.
    """
    if not entries:
        return {}

    grouped = defaultdict(list)
    for entry in entries:
        month_key = entry["date"][:7]  # YYYY-MM
        grouped[month_key].append(entry)

    averages = {}
    for month, rows in grouped.items():
        averages[month] = {
            "weight": round(sum(r["weight"] for r in rows) / len(rows), 2),
            "waist": round(sum(r["waist"] for r in rows) / len(rows), 2),
            "body_fat": round(sum(r["body_fat"] for r in rows) / len(rows), 2),
            "bmi": round(sum(r["bmi"] for r in rows) / len(rows), 2),
        }

    return dict(sorted(averages.items()))


def show_monthly_averages(entries):
    """
    Print monthly average stats.
    """
    averages = monthly_averages(entries)
    if not averages:
        print("No entries saved yet.")
        return

    print("\nMonthly averages")
    print("-" * 54)
    print(f"{'Month':<10}{'Weight':>10}{'Waist':>10}{'BF %':>10}{'BMI':>10}")
    print("-" * 54)
    for month, stats in averages.items():
        print(
            f"{month:<10}"
            f"{stats['weight']:>10}"
            f"{stats['waist']:>10}"
            f"{stats['body_fat']:>10}"
            f"{stats['bmi']:>10}"
        )
    print()


def show_best_ever_stats(entries):
    """
    Print best-ever stats from saved entries.
    """
    if not entries:
        print("No entries saved yet.")
        return

    lowest_weight = min(entries, key=lambda x: x["weight"])
    lowest_waist = min(entries, key=lambda x: x["waist"])
    lowest_bf = min(entries, key=lambda x: x["body_fat"])

    print("\nBest ever stats")
    print("-" * 40)
    print(f"Lowest weight:       {lowest_weight['weight']} lbs on {lowest_weight['date']}")
    print(f"Lowest waist:        {lowest_waist['waist']} in on {lowest_waist['date']}")
    print(f"Lowest body fat:     {lowest_bf['body_fat']}% on {lowest_bf['date']}")
    print()


def plot_progress(filename):
    """
    Plot weight, waist, body fat, and BMI progress.
    """
    entries = load_entries(filename)

    if len(entries) < 2:
        print("You need at least 2 saved entries to plot progress.")
        return

    dates = [entry["date"] for entry in entries]
    weights = [entry["weight"] for entry in entries]
    waists = [entry["waist"] for entry in entries]
    body_fats = [entry["body_fat"] for entry in entries]
    bmis = [entry["bmi"] for entry in entries]

    plt.figure(figsize=(10, 5))
    plt.plot(dates, weights, marker="o")
    plt.title("Weight Progress")
    plt.xlabel("Date")
    plt.ylabel("Weight (lbs)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

    plt.figure(figsize=(10, 5))
    plt.plot(dates, waists, marker="o")
    plt.title("Waist Progress")
    plt.xlabel("Date")
    plt.ylabel("Waist (inches)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

    plt.figure(figsize=(10, 5))
    plt.plot(dates, body_fats, marker="o")
    plt.title("Body Fat Progress")
    plt.xlabel("Date")
    plt.ylabel("Body Fat (%)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

    plt.figure(figsize=(10, 5))
    plt.plot(dates, bmis, marker="o")
    plt.title("BMI Progress")
    plt.xlabel("Date")
    plt.ylabel("BMI")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def print_dashboard(weight, height, waist, neck, target_body_fat=18, weekly_loss=1.25):
    """
    Calculate metrics and print a dashboard.
    """
    body_fat = navy_body_fat_male(height, waist, neck)
    body_fat_zone = body_fat_category(body_fat)

    fat_mass, lean_mass = body_composition(weight, body_fat)
    goal_weight = goal_weight_for_target_body_fat(lean_mass, target_body_fat)
    lbs_to_lose = round(max(0, weight - goal_weight), 2)
    weeks = estimated_weeks_to_goal(weight, goal_weight, weekly_loss)
    goal_date = projected_goal_date(weeks)

    bmi_value = bmi(weight, height)
    bmi_zone = bmi_category(bmi_value)

    whtr_value = waist_to_height_ratio(waist, height)
    whtr_zone = whtr_category(whtr_value)

    bar = progress_bar(body_fat, start_bf=30, target_bf=target_body_fat)

    results = {
        "weight": weight,
        "height": height,
        "waist": waist,
        "neck": neck,
        "body_fat": body_fat,
        "body_fat_zone": body_fat_zone,
        "fat_mass": fat_mass,
        "lean_mass": lean_mass,
        "goal_weight": goal_weight,
        "lbs_to_lose": lbs_to_lose,
        "weeks": weeks,
        "goal_date": goal_date,
        "bmi": bmi_value,
        "bmi_zone": bmi_zone,
        "whtr": whtr_value,
        "whtr_zone": whtr_zone,
        "target_body_fat": target_body_fat,
        "weekly_loss": weekly_loss,
        "progress_bar": bar,
    }

    print("\n" + "=" * 60)
    print("                    BODY FAT DASHBOARD")
    print("=" * 60)
    print(f"Current weight:               {weight} lbs")
    print(f"Height:                       {height} in")
    print(f"Waist:                        {waist} in")
    print(f"Neck:                         {neck} in")
    print("-" * 60)
    print(f"Estimated body fat:           {body_fat}%")
    print(f"Body fat category:            {body_fat_zone}")
    print(f"Fat mass:                     {fat_mass} lbs")
    print(f"Lean mass:                    {lean_mass} lbs")
    print("-" * 60)
    print(f"Target body fat:              {target_body_fat}%")
    print(f"Goal weight:                  {goal_weight} lbs")
    print(f"Lbs to lose:                  {lbs_to_lose} lbs")
    print(f"Weekly loss assumed:          {weekly_loss} lbs/week")
    print(f"Estimated weeks:              {weeks}")
    print(f"Projected goal date:          {goal_date}")
    print("-" * 60)
    print(f"BMI:                          {bmi_value}")
    print(f"BMI category:                 {bmi_zone}")
    print(f"Waist-to-height ratio:        {whtr_value}")
    print(f"WHtR category:                {whtr_zone}")
    print("-" * 60)
    print(f"Predicted date for 200 lbs:   {predict_date_for_weight(weight, 200, weekly_loss)}")
    print(f"Predicted date for 195 lbs:   {predict_date_for_weight(weight, 195, weekly_loss)}")
    print(f"Predicted date for 190 lbs:   {predict_date_for_weight(weight, 190, weekly_loss)}")
    print("-" * 60)
    print(f"Progress to goal:             {bar}")
    print("=" * 60 + "\n")

    return results


def add_new_entry():
    """
    Ask user for stats, show dashboard, compare with history, optionally save.
    """
    try:
        entries = load_entries(CSV_FILE)

        weight = float(input("Enter weight (lbs): "))
        height = float(input("Enter height (inches): "))
        waist = float(input("Enter waist at belly button (inches): "))
        neck = float(input("Enter neck (inches): "))

        print("\nChoose target body fat:")
        print("1. 20%")
        print("2. 18%")
        print("3. 15%")
        target_choice = input("Choose 1/2/3: ").strip()
        target_map = {"1": 20, "2": 18, "3": 15}
        target_body_fat = target_map.get(target_choice, 18)

        weekly_loss_input = input("Weekly weight loss assumption (default 1.25): ").strip()
        weekly_loss = float(weekly_loss_input) if weekly_loss_input else 1.25

        results = print_dashboard(
            weight=weight,
            height=height,
            waist=waist,
            neck=neck,
            target_body_fat=target_body_fat,
            weekly_loss=weekly_loss
        )

        last_comparison = compare_to_last_entry(results, entries)
        first_comparison = compare_to_first_entry(results, entries)

        if last_comparison:
            print("Compared with last entry")
            print("-" * 34)
            print_change("Weight", last_comparison["weight_change"], " lbs")
            print_change("Waist", last_comparison["waist_change"], " in")
            print_change("Body fat", last_comparison["body_fat_change"], "%")
            print()

        if first_comparison:
            print("Compared with first entry")
            print("-" * 34)
            print_change("Weight", first_comparison["weight_change_since_first"], " lbs")
            print_change("Waist", first_comparison["waist_change_since_first"], " in")
            print_change("Body fat", first_comparison["body_fat_change_since_first"], "%")
            print()

        save = input("Save this entry to CSV? (y/n): ").strip().lower()
        if save == "y":
            date = datetime.now().strftime("%Y-%m-%d")
            save_entry(CSV_FILE, [
                date,
                weight,
                height,
                waist,
                neck,
                results["body_fat"],
                results["body_fat_zone"],
                results["fat_mass"],
                results["lean_mass"],
                results["target_body_fat"],
                results["goal_weight"],
                results["weeks"],
                results["goal_date"],
                results["bmi"],
                results["bmi_zone"],
                results["whtr"],
                results["whtr_zone"]
            ])
            print(f"Saved to {CSV_FILE}")

    except ValueError as error:
        print(f"Input error: {error}")


def quick_demo_with_your_numbers():
    """
    Run a demo using your current example numbers.
    """
    print("\nRunning demo with your numbers:")
    print_dashboard(
        weight=208,
        height=70,
        waist=40.5,
        neck=17,
        target_body_fat=18,
        weekly_loss=1.25
    )


def show_latest_summary():
    """
    Show latest saved entry.
    """
    entries = load_entries(CSV_FILE)
    if not entries:
        print("No saved entries yet.")
        return

    latest = entries[-1]
    print("\nLatest saved entry")
    print("-" * 34)
    print(f"Date:         {latest['date']}")
    print(f"Weight:       {latest['weight']} lbs")
    print(f"Waist:        {latest['waist']} in")
    print(f"Neck:         {latest['neck']} in")
    print(f"Body fat:     {latest['body_fat']}%")
    print(f"BMI:          {latest['bmi']}")
    print(f"WHtR:         {latest['waist_to_height_ratio']}")
    print()


def main():
    """
    Main menu loop.
    """
    ensure_csv_exists()

    while True:
        print("\n=== BODY FAT TRACKER ===")
        print("1. Add new entry")
        print("2. Plot progress graphs")
        print("3. Run demo with your numbers")
        print("4. Show latest saved entry")
        print("5. Show monthly averages")
        print("6. Show best ever stats")
        print("7. Exit")

        choice = input("Choose an option (1/2/3/4/5/6/7): ").strip()

        if choice == "1":
            add_new_entry()
        elif choice == "2":
            plot_progress(CSV_FILE)
        elif choice == "3":
            quick_demo_with_your_numbers()
        elif choice == "4":
            show_latest_summary()
        elif choice == "5":
            show_monthly_averages(load_entries(CSV_FILE))
        elif choice == "6":
            show_best_ever_stats(load_entries(CSV_FILE))
        elif choice == "7":
            print("Good work — keep tracking.")
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, 4, 5, 6, or 7.")


if __name__ == "__main__":
    main()