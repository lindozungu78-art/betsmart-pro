import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import math

# --- 1. CONFIG & API ---
API_KEY = "8e1ac8e3fb43757f30f2aec94dbebb81" 
st.set_page_config(page_title="BetSmart Pro | Draw Engine", layout="wide")

# --- 2. POISSON DRAW ENGINE ---
def calculate_draw_prob(home_win_prob, away_win_prob):
    """
    Estimates draw probability based on win/loss ratios.
    Matches with closely matched teams (e.g., 35% vs 35%) 
    score higher on the Draw Engine.
    """
    total_win_prob = (home_win_prob + away_win_prob) / 100
    # Average draw rate in top leagues is ~24-28%
    # We adjust this based on how 'balanced' the match is
    balance_factor = 1 - abs(home_win_prob - away_win_prob) / 100
    draw_prob = 26.0 * balance_factor 
    return round(draw_prob, 1)

# --- 3. DATA FETCHING ---
def fetch_matrix_data():
    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey={API_KEY}&regions=uk&markets=h2h&oddsFormat=decimal"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            all_matches = []
            for match in data:
                home_team = match['home_team']
                away_team = match['away_team']
                
                # Get best odds for Home, Draw, Away
                outcomes = match['bookmakers'][0]['markets'][0]['outcomes']
                h_odds = next(o['price'] for o in outcomes if o['name'] == home_team)
                a_odds = next(o['price'] for o in outcomes if o['name'] == away_team)
                d_odds = next(o['price'] for o in outcomes if o['name'] == "Draw")
                
                h_prob = (1/h_odds)*100
                a_prob = (1/a_odds)*100
                d_prob = calculate_draw_prob(h_prob, a_prob)
                
                all_matches.append({
                    "Home": home_team, "Away": away_team,
                    "H_Prob": round(h_prob, 1), "D_Prob": d_prob, "A_Prob": round(a_prob, 1),
                    "H_Odds": h_odds, "D_Odds": d_odds, "A_Odds": a_odds
                })
            
            all_matches.sort(key=lambda x: x['H_Prob'], reverse=True)
            while len(all_matches) < 16: 
                all_matches.append({"Home": "Pending", "Away": "...", "H_Prob": 0, "D_Prob": 0, "A_Prob": 0, "H_Odds": 1, "D_Odds": 1, "A_Odds": 1})
            
            return {
                "Option A (Bankers)": all_matches[0:4],
                "Option B (Home Edge)": all_matches[4:8],
                "Option C (Draw/Value)": sorted(all_matches, key=lambda x: x['D_Prob'], reverse=True)[0:4],
                "Option D (Underdogs)": all_matches[12:16]
            }
    except: return None

# --- 4. UI LOGIC ---
st.title("🏆 Dual-Engine Auto-Picker")
st.subheader("📊 4x4 Matrix with Draw Analytics")

if st.button("🔄 Sync Market Data"):
    st.cache_data.clear()

matrix = fetch_matrix_data()
if matrix:
    tabs = st.tabs(list(matrix.keys()))
    for i, (group, matches) in enumerate(matrix.items()):
        with tabs[i]:
            cols = st.columns(4)
            for j, m in enumerate(matches):
                with cols[j]:
                    st.write(f"**{m['Home']}**")
                    st.caption(f"vs {m['Away']}")
                    st.metric("Win Prob", f"{m['H_Prob']}%")
                    st.metric("Draw Prob", f"{m['D_Prob']}%", delta_color="normal")
                    if st.button(f"Bet {m['Home']}", key=f"h_{i}_{j}"):
                        st.session_state.temp_odds = m['H_Odds']
            
            if st.button(f"Load {group} Odds", key=f"grp_{i}"):
                st.session_state.selected_odds = [x['H_Odds'] for x in matches]
                st.session_state.selected_group = group

st.divider()

# --- 5. CALCULATOR (Wager vs Profit) ---
st.header("💰 ZAR System 3/4 Calculator")
def_odds = st.session_state.get('selected_odds', [1.57, 1.59, 2.09, 3.30])

c1, c2 = st.columns(2)
with c1:
    total_wager = st.number_input("Total Wager (ZAR)", value=100.0, step=10.0)
    o1 = st.number_input("Odds 1", value=float(def_odds[0]))
    o2 = st.number_input("Odds 2", value=float(def_odds[1]))
with c2:
    o3 = st.number_input("Odds 3", value=float(def_odds[2]))
    o4 = st.number_input("Odds 4", value=float(def_odds[3]))

# System 3/4 Math
spb = total_wager / 4
combos = [o1*o2*o3*spb, o1*o2*o4*spb, o1*o3*o4*spb, o2*o3*o4*spb]
max_pay = sum(combos)
min_pay = min(combos)

r1, r2, r3 = st.columns(3)
r1.metric("Total Wager", f"R{total_wager:.2f}")

with r2:
    st.success("### Max Win (4/4)")
    st.write(f"**Payout:** R{max_pay:.2f}")
    st.write(f"**Profit:** R{max_pay - total_wager:.2f}")

with r3:
    st.warning("### Safety Net (3/4)")
    st.write(f"**Payout:** R{min_pay:.2f}")
    st.write(f"**Profit/Loss:** R{min_pay - total_wager:.2f}")
    
