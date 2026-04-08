import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="BetSmart Pro V3", layout="wide")

# --- CORE VALUE ENGINE ---
def calculate_value(h_odds, d_odds, a_odds):
    h_implied, a_implied = (1/h_odds), (1/a_odds)
    balance_factor = 1 - abs(h_implied - a_implied)
    fair_draw_prob = 0.26 * balance_factor
    
    rem = 1.0 - fair_draw_prob
    fair_h = (h_implied / (h_implied + a_implied)) * rem
    fair_a = (a_implied / (h_implied + a_implied)) * rem
    
    return {
        "H": {"prob": fair_h, "ev": (fair_h * h_odds) - 1},
        "D": {"prob": fair_draw_prob, "ev": (fair_draw_prob * d_odds) - 1},
        "A": {"prob": fair_a, "ev": (fair_a * a_odds) - 1}
    }

# --- FOOTBALL-DATA.ORG SYNC ---
def sync_football_data(api_key):
    # Fetching upcoming matches for the English Premier League (PL)
    url = "https://api.football-data.org/v4/competitions/PL/matches?status=SCHEDULED"
    headers = {"X-Auth-Token": api_key}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()['matches']
        else:
            st.error(f"API Error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

# --- UI TABS ---
tab1, tab2, tab3 = st.tabs(["🎯 Value Engine", "📅 Live Fixtures", "🧮 3/4 Calculator"])

with tab1:
    st.header("Strategic Value Matrix")
    c1, c2, c3 = st.columns(3)
    h_in = c1.number_input("Home Odds", value=2.10)
    d_in = c2.number_input("Draw Odds", value=3.20)
    a_in = c3.number_input("Away Odds", value=3.50)
    
    analysis = calculate_value(h_in, d_in, a_in)
    
    cols = st.columns(3)
    for i, outcome in enumerate(["H", "D", "A"]):
        data = analysis[outcome]
        with cols[i]:
            st.metric(f"Fair {outcome} Prob", f"{data['prob']*100:.1f}%")
            edge = data['ev'] * 100
            if edge > 5:
                st.success(f"✅ VALUE: +{edge:.1f}% Edge")
            else:
                st.error(f"❌ NO VALUE: {edge:.1f}% Edge")

with tab2:
    st.header("Premier League Fixtures (Football-Data.org)")
    api_key = st.text_input("Enter Football-Data.org API Key", type="password")
    if st.button("🔄 Sync Upcoming Matches"):
        matches = sync_football_data(api_key)
        if matches:
            fixture_list = []
            for m in matches:
                fixture_list.append({
                    "Date": m['utcDate'][:10],
                    "Home Team": m['homeTeam']['name'],
                    "Away Team": m['awayTeam']['name']
                })
            st.table(fixture_list)

with tab3:
    st.header("System 3/4 Payout Calculator")
    bankroll = st.number_input("Current Bankroll (ZAR)", value=500.0)
    risk = st.slider("Risk (%)", 1, 10, 5) / 100
    wager = bankroll * risk
    
    st.write(f"**Total Stake:** R{wager:.2f} (R{wager/4:.2f} per Treble)")
    
    o_cols = st.columns(4)
    odds = [o_cols[i].number_input(f"Match {i+1} Odds", value=2.0, key=f"o{i}") for i in range(4)]
    
    w_cols = st.columns(4)
    wins = [w_cols[i].checkbox(f"Match {i+1} Win", key=f"w{i}") for i in range(4)]
    
    # Calculation logic for 4 Trebles
    payout = 0
    spb = wager / 4
    combos = [(0,1,2), (0,1,3), (0,2,3), (1,2,3)]
    for c in combos:
        if wins[c[0]] and wins[c[1]] and wins[c[2]]:
            payout += (odds[c[0]] * odds[c[1]] * odds[c[2]] * spb)
    
    profit = payout - wager
    st.subheader(f"Total Payout: R{payout:.2f}")
    if profit > 0:
        st.write(f"💰 Net Profit: R{profit:.2f}")
        st.write(f"🔒 **80% Rollover:** R{profit*0.8:.2f}")
        st.write(f"🏦 **20% Savings:** R{profit*0.2:.2f}")
    else:
        st.write(f"📉 Total Loss: R{abs(profit):.2f}")
