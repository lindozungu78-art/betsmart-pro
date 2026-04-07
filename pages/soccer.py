import streamlit as st
import pandas as pd
import requests

# --- 1. CONFIG & API SETTINGS ---
API_KEY = "8e1ac8e3fb43757f30f2aec94dbebb81" 
st.set_page_config(page_title="BetSmart Pro | 4x4 Matrix", layout="wide")

# --- 2. LOGO MAPPING SYSTEM ---
def get_team_logo_url(team_name):
    """Maps API team names to reliable logo URLs."""
    # Common EPL Team IDs for the football-data.org CDN
    team_ids = {
        "Arsenal": 57, "Aston Villa": 58, "Chelsea": 61, "Liverpool": 64, 
        "Manchester City": 65, "Manchester United": 66, "Newcastle United": 67,
        "Tottenham Hotspur": 73, "West Ham United": 563, "Brentford": 402,
        "Brighton & Hove Albion": 397, "Crystal Palace": 354, "Everton": 62,
        "Fulham": 63, "Leicester City": 338, "Wolverhampton Wanderers": 76,
        "Nottingham Forest": 351, "Bournemouth": 1044, "Luton Town": 389, "Sheffield United": 356
    }
    
    # Try to find a match in our ID list
    for key, tid in team_ids.items():
        if key in team_name:
            return f"https://crests.football-data.org/{tid}.png"
    
    # Fallback soccer icon if no match found
    return "https://cdn-icons-png.flaticon.com/512/5323/5323884.png"

def display_team_logo(team_name):
    logo_url = get_team_logo_url(team_name)
    st.image(logo_url, width=60)

# --- 3. 4x4 MATRIX ENGINE ---
def fetch_matrix_data():
    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey={API_KEY}&regions=uk&markets=h2h&oddsFormat=decimal"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            all_teams = []
            for match in data:
                home_team = match['home_team']
                # Get best home win odds
                h_odds = max([o['price'] for b in match['bookmakers'] for m in b['markets'] for o in m['outcomes'] if o['name'] == home_team])
                prob = (1 / h_odds) * 100
                all_teams.append({"Team": home_team, "Prob": round(prob, 1), "Odds": h_odds})
            
            all_teams.sort(key=lambda x: x['Prob'], reverse=True)
            
            # Ensure we have 16 teams
            while len(all_teams) < 16:
                all_teams.append({"Team": "Searching...", "Prob": 0.0, "Odds": 1.0})

            matrix = {
                "Option A (Bankers)": all_teams[0:4],
                "Option B (Home Edge)": all_teams[4:8],
                "Option C (Value Mix)": all_teams[8:12],
                "Option D (Underdogs)": all_teams[12:16]
            }
            return matrix
    except:
        return None

# --- 4. UI LAYOUT (RESTORED TO PREVIOUS STYLE) ---
st.title("🏆 Dual-Engine Auto-Picker")
st.subheader("📊 BetSmart 4x4 Strategic Matrix")

if st.button("🔄 Sync Live Market Odds"):
    st.cache_data.clear()

matrix_data = fetch_matrix_data()

if matrix_data:
    tabs = st.tabs(list(matrix_data.keys()))
    for i, (group_name, teams) in enumerate(matrix_data.items()):
        with tabs[i]:
            cols = st.columns(4)
            for j, team in enumerate(teams):
                with cols[j]:
                    display_team_logo(team['Team'])
                    st.metric(team['Team'], f"{team['Prob']}%", f"Odds: {team['Odds']}")
            
            if st.button(f"Analyze {group_name}", key=f"btn_{i}"):
                st.session_state.selected_odds = [t['Odds'] for t in teams]
                st.session_state.selected_group = group_name

st.divider()

# --- 5. ZAR SYSTEM 3/4 CALCULATOR ---
st.header("💰 ZAR System 3/4 Calculator")
default_odds = st.session_state.get('selected_odds', [1.57, 1.59, 2.09, 3.30])
current_group = st.session_state.get('selected_group', "Manual Entry")
st.info(f"Analyzing: **{current_group}**")

col1, col2 = st.columns(2)
with col1:
    total_stake = st.number_input("Total Budget (ZAR)", value=100.0)
    o1 = st.number_input("Team 1 Odds", value=float(default_odds[0]))
    o2 = st.number_input("Team 2 Odds", value=float(default_odds[1]))
with col2:
    o3 = st.number_input("Team 3 Odds", value=float(default_odds[2]))
    o4 = st.number_input("Team 4 Odds", value=float(default_odds[3]))

stake_per_bet = total_stake / 4
combos = [o1*o2*o3*stake_per_bet, o1*o2*o4*stake_per_bet, o1*o3*o4*stake_per_bet, o2*o3*o4*stake_per_bet]

res1, res2 = st.columns(2)
res1.success(f"### Max Payout\nR{sum(combos):.2f}")
res2.warning(f"### Safety Net\nR{min(combos):.2f}")
