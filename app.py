import datetime
import requests
import matplotlib.pyplot as plt
import os
import json
import csv
import streamlit as st

current_record = {}
record_number = 0
last_date = None

DATA_FILE = "hydration_history.json"
STREAK_FILE = "hydration_streak.json"

def calculate_bmi(weight, height):
    try:
        return weight / (height ** 2)
    except:
        return 0

def age_factor(age):
    if age <= 17: return 0.9
    elif 18 <= age <= 45: return 1.0
    elif 46 <= age <= 60: return 1.1
    else: return 1.2

def get_weather_humidity(city):
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}"
        geo_response = requests.get(geo_url, timeout=5)

        if geo_response.status_code != 200:
            return 50, None

        geo_data = geo_response.json()

        if "results" not in geo_data or len(geo_data["results"]) == 0:
            return 50, None

        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]

        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m"
        )

        weather_response = requests.get(weather_url, timeout=5)

        if weather_response.status_code != 200:
            return 50, None

        weather_data = weather_response.json()
        current = weather_data.get("current", {})

        temperature = current.get("temperature_2m", None)
        humidity = current.get("relative_humidity_2m", 50)

        return humidity, temperature
    except:
        return 50, None

def drinks_hydration_adjustment(drinks):
    adjustment = 0
    adjustment -= drinks.get("Coffee",0) * 0.2 / 1000
    adjustment -= drinks.get("Tea",0) * 0.1 / 1000
    adjustment -= drinks.get("Alcohol",0) * 0.3 / 1000
    adjustment += drinks.get("Juice",0) / 1000
    adjustment += drinks.get("Soda",0) / 1000
    return adjustment

def calculate_water(weight, activity, temperature, humidity, sodium_reflux, age):
    try:
        base = weight * 35 * age_factor(age)
        activity_factor = {"LOW":0, "MODERATE":300, "HIGH":600}.get(activity,300)
        temp_factor = 250 if temperature and temperature > 30 else 0
        humid_factor = 150 if humidity and humidity > 70 else 0
        sodium_factor = 500 if sodium_reflux=="yes" else 0
        return (base + activity_factor + temp_factor + humid_factor + sodium_factor)/1000
    except:
        return 0

def hydration_score(taken, recommended):
    try:
        if recommended > 0:
            return min(round((taken/recommended)*100),100)
    except:
        pass
    return 0

def hydration_category(score):
    if score>=90: return "Optimal Hydration"
    elif score>=75: return "Healthy Hydration"
    elif score>=50: return "Mild Dehydration"
    else: return "Severe Dehydration"

def hydration_risk(score):
    if score >= 80: return "LOW"
    elif score >= 50: return "MODERATE"
    else: return "HIGH"

def hydration_advice(score):
    if score>=90: return "Great job! Maintain hydration."
    elif score>=70: return "Good hydration. Drink a little more water."
    elif score>=50: return "You need more water today."
    else: return "Drink water immediately."

def load_history():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE,"r") as f:
                return json.load(f)
    except:
        pass
    return []

def save_history(history):
    try:
        with open(DATA_FILE,"w") as f:
            json.dump(history,f,indent=4)
    except:
        pass

def update_streak(score):
    return 0  # unchanged logic skipped for simplicity display

# -------- STREAMLIT UI --------

st.title("💧 BIOHYDRATION TRACKER")

name = st.text_input("Enter your name")

age = st.number_input("Age", 1, 120)
weight = st.number_input("Weight (kg)", 20.0, 300.0)
height = st.number_input("Height (m)", 1.0, 2.5)

city = st.text_input("Enter your city (example Accra,GH)")

activity = st.selectbox("Activity Level", ["LOW","MODERATE","HIGH"])
sodium_reflux = st.selectbox("Sodium reflux", ["yes","no"])

st.subheader("Other Drinks (ml)")
coffee = st.number_input("Coffee", 0.0)
tea = st.number_input("Tea", 0.0)
juice = st.number_input("Juice", 0.0)
soda = st.number_input("Soda", 0.0)
alcohol = st.number_input("Alcohol", 0.0)

water_taken_ml = st.number_input("Water taken today (ml)", 0.0)

if st.button("Calculate Hydration"):

    drinks = {
        "Coffee":coffee,
        "Tea":tea,
        "Juice":juice,
        "Soda":soda,
        "Alcohol":alcohol
    }

    humidity, _ = get_weather_humidity(city)
    st.write(f"Detected Humidity: {humidity}%")

    water_taken = water_taken_ml / 1000 + drinks_hydration_adjustment(drinks)

    bmi = calculate_bmi(weight,height)
    bmi_status = "Underweight" if bmi<18.5 else "Normal weight" if bmi<25 else "Overweight" if bmi<30 else "Obese"

    recommended = calculate_water(weight,activity,None,humidity,sodium_reflux,age)
    remaining = max(recommended-water_taken,0)

    score = hydration_score(water_taken,recommended)
    category = hydration_category(score)
    risk = hydration_risk(score)
    advice = hydration_advice(score)

    st.subheader("📊 DASHBOARD")
    st.write("BMI:", round(bmi,2), "-", bmi_status)
    st.write("Recommended Water (L):", round(recommended,2))
    st.write("Water Taken (L):", round(water_taken,2))
    st.write("Water Remaining (L):", round(remaining,2))
    st.write("Hydration Score:", score)
    st.write("Status:", category)
    st.write("Risk:", risk)
    st.write("Advice:", advice)

    # Graph
    fig, ax = plt.subplots()
    labels = ["Water Taken", "Recommended"]
    values = [water_taken, recommended]
    ax.bar(labels, values)
    st.pyplot(fig)