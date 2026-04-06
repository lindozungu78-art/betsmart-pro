import streamlit as st
import pandas as pd
import requests
from scipy.stats import poisson

# --- 1. NEW LOGO FALLBACK SYSTEM ---
def display_team_logo(logo_url, team_name):
    """Displays a team logo with a fallback if the link is broken."""
    fallback_url = "https://cdn-icons-png.flaticon.com/512/5323/5323884.png" # Soccer ball icon
    try:
        # Check if URL is valid and reachable
        if pd.isna(logo_url) or logo_url == "":
            st.image(fallback_url, width=70)
        else:
            response = requests.get(logo_url, timeout=2)
            if response.status_code == 200:
                st.image(logo_url, width=70)
            else:
                st.image(fallback_url, width=70)
    except:
        st.image(fallback_url, width=70)

# --- 2. APP CONFIG & STYLE ---
st.set_page_config(page_title="BetSmart Pro", layout="wide")
st.title("🏆 Dual-Engine Auto-Picker")

# --- 3. SOCCER PREDICTOR LOGIC (POISSON) ---
def get_predictions():
    # This mimics your API data fetching
    # Using your current high-confidence picks as the baseline
    data = [
        {"Team": "Liverpool FC", "Prob": 65.9, "Date": "2026-04-11", "Logo_URL": "https://crests.football-data.org/64.png"},
        {"Team": "West Ham United FC", "Prob": 65.1, "Date": "2026-04-10", "Logo_URL": "https://crests.football-data.org/563.png"},
        {"Team": "Manchester United FC", "Prob": 62.8, "Date": "2026-04-13", "Logo_URL": "https://crests.football-data.org/66.png"},
        {"Team": "Brentford FC", "Prob": 61.0, "Date": "2026-04-11", "Logo_URL": "https://crests.football-data.org/402.png"}
    ]
    return data

picks = get_predictions()

st.subheader("🔥 Top 4 'Value' Picks")
cols = st.columns(4)

for i, pick in enumerate(picks):
    with cols[i]:
        display_team_logo(pick['Logo_URL'], pick['Team'])
        st.metric(label=pick['Team'], value=f"{pick['Prob']}%")
        st.caption(f"📅 {pick['Date']}")
        st.write("✅ VALUE FOUND")

st.divider()

# --- 4. ZAR SYSTEM 3/4 CALCULATOR ---
st.header("💰 ZAR System 3/4 Calculator")
st.info("Strategy: Win even if one team lets you down (Safety Net).")

with st.container():
    col1, col2 = st.columns(2)
    
    with col1:
        total_stake = st.number_input("Total Budget (ZAR)", min_value=10.0, value=100.0, step=10.0)
        odds1 = st.number_input("Game 1 Odds", value=1.57)
        odds2 = st.number_input("Game 2 Odds", value=1.59)
    
    with col2:
        odds3 = st.number_input("Game 3 Odds", value=2.09)
        odds4 = st.number_input("Game 4 Odds", value=3.30)

    # Calculation logic for 3/4 system (4 combinations)
    stake_per_bet = total_stake / 4
    
    # Combinations (The 4 Trebles)
    c1 = odds1 * odds2 * odds3 * stake_per_bet
    c2 = odds1 * odds2 * odds4 * stake_per_bet
    c3 = odds1 * odds3 * odds4 * stake_per_bet
    c4 = odds2 * odds3 * odds4 * stake_per_bet
    
    max_payout = c1 + c2 + c3 + c4
    min_safety_return = min(c1, c2, c3, c4) # Worst case if 3 win

    st.divider()
    
    res1, res2 = st.columns(2)
    res1.success(f"### Max Payout\nR{max_payout:.2f}")
    res2.warning(f"### Safety Net\nR{min_safety_return:.2f}")

    st.write(f"**Instructions:** On your betting app, choose **'Trebles (x4)'** and enter a stake of **R{stake_per_bet:.2f}** per bet.")
