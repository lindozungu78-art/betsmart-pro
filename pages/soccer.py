import streamlit as st
import pandas as pd
import requests

# --- 1. CONFIG & API SETTINGS ---
# Using your provided API Key
API_KEY = "8e1ac8e3fb43757f30f2aec94dbebb81" 
st.set_page_config(page_title="BetSmart Pro | 4x4 Matrix", layout="wide")

# --- 2. LOGO FALLBACK ---
def display_team_logo():
    icon_url = "https://cdn-icons-png.flaticon.com/512/5323/5323884.png"
    st.image(icon_url, width=50)

# --- 3. 4x4 MATRIX ENGINE ---
def fetch_matrix_data():
    # Fetching EPL (Premier League) odds as the primary source
    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey={API_KEY}&regions=uk&markets=h2h&oddsFormat=decimal"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            all_teams = []
            for match in data:
                home_team = match['home_team']
                # Get best home win odds available in the market
                h_odds = max([o['price'] for b in match['bookmakers'] for m in b['markets'] for o in m['outcomes'] if o['name'] == home_team])
                prob = (1 / h_odds) * 100
                all_teams.append({"Team": home_team, "Prob": round(prob, 1), "Odds": h_odds})
            
            # Sort from highest probability to lowest
            all_teams.sort(key=lambda x: x['Prob'], reverse=True)
            
            # Safety check to ensure we have at least 16 teams
            if len(all_teams) < 16:
                # Add dummy placeholders if league has fewer active matches this week
                while len(all_teams) < 16:
                    all_teams.append({"Team": "Pending Fixture", "Prob": 0.0, "Odds": 1.0})

            # Divide into 4 distinct strategy options
            matrix = {
                "Option A (Bankers)": all_teams[0:4],
                "Option B (Home Edge)": all_teams[4:8],
                "Option C (Value Mix)": all_teams[8:12],
                "Option D (Underdogs)": all_teams[12:16]
            }
            return matrix
    except:
        return None

# --- 4. UI LAYOUT ---
st.title("📊 BetSmart 4x4 Strategic Matrix")
st.write(f"Synced with The-Odds-API | Key: {API_KEY[:4]}****")

# Refresh button to trigger new API call
if st.button("🔄 Sync Live Market Odds"):
    st.cache_data.clear()

matrix_data = fetch_matrix_data()

if matrix_data:
    # Use Tabs for a clean mobile experience
    tabs = st.tabs(list(matrix_data.keys()))
    
    for i, (group_name, teams) in enumerate(matrix_data.items()):
        with tabs[i]:
            st.subheader(f"Ranked Strategy: {group_name}")
            cols = st.columns(4)
            for j, team in enumerate(teams):
                with cols[j]:
                    display_team_logo()
                    st.metric(team['Team'], f"{team['Prob']}%", f"Odds: {team['Odds']}")
            
            # Button to load this specific group into the ZAR calculator
            if st.button(f"Load {group_name} into Calculator", key=f"btn_{i}"):
                st.session_state.selected_odds = [t['Odds'] for t in teams]
                st.session_state.selected_group = group_name
                st.success(f"{group_name} loaded!")

else:
    st.error("API Error: Verify your key or check if the league is out of season.")

st.divider()

# --- 5. ZAR SYSTEM 3/4 CALCULATOR ---
st.header("💰 ZAR System 3/4 Calculator")

# Load values from session state (if button clicked) or use defaults
default_odds = st.session_state.get('selected_odds', [1.50, 1.60, 2.10, 3.30])
current_group = st.session_state.get('selected_group', "Manual Entry")

st.info(f"Analyzing: **{current_group}**")

col1, col2 = st.columns(2)
with col1:
    total_stake = st.number_input("Total Stake (ZAR)", value=100.0, step=10.0)
    o1 = st.number_input("Team 1 Odds", value=float(default_odds[0]))
    o2 = st.number_input("Team 2 Odds", value=float(default_odds[1]))
with col2:
    o3 = st.number_input("Team 3 Odds", value=float(default_odds[2]))
    o4 = st.number_input("Team 4 Odds", value=float(default_odds[3]))

# System 3/4 Math (4 unique treble combinations)
stake_per_bet = total_stake / 4
combos = [o1*o2*o3*stake_per_bet, o1*o2*o4*stake_per_bet, 
          o1*o3*o4*stake_per_bet, o2*o3*o4*stake_per_bet]

res1, res2 = st.columns(2)
res1.success(f"### Max Payout\nR{sum(combos):.2f}")
res2.warning(f"### Safety Net (3/4 Win)\nR{min(combos):.2f}")
