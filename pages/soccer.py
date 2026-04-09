import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import math
import pytz

# --- 1. CONFIG & API SETTINGS ---
API_KEY = "8e1ac8e3fb43757f30f2aec94dbebb81" 
st.set_page_config(page_title="BetSmart Pro | Master Engine", layout="wide")

# --- 2. TIMEZONE CONFIGURATION ---
SAST = pytz.timezone('Africa/Johannesburg')
UTC = pytz.UTC

def convert_to_sast(utc_time_str):
    """Convert UTC time string to SAST"""
    try:
        # Parse UTC time
        if utc_time_str:
            utc_time = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
            # Convert to SAST
            sast_time = utc_time.astimezone(SAST)
            return sast_time
    except:
        pass
    return None

def format_match_time(utc_time_str):
    """Format match time for display"""
    sast_time = convert_to_sast(utc_time_str)
    if sast_time:
        return sast_time.strftime("%d %b %Y | %H:%M")
    return "Time TBD"

# --- 3. LOGO MAPPING SYSTEM ---
def get_team_logo_url(team_name):
    team_ids = {
        "Arsenal": 57, "Aston Villa": 58, "Chelsea": 61, "Liverpool": 64, 
        "Manchester City": 65, "Manchester United": 66, "Newcastle United": 67,
        "Tottenham Hotspur": 73, "West Ham United": 563, "Brentford": 402,
        "Brighton & Hove Albion": 397, "Crystal Palace": 354, "Everton": 62,
        "Fulham": 63, "Leicester City": 338, "Wolverhampton Wanderers": 76,
        "Nottingham Forest": 351, "Bournemouth": 1044, "Southampton": 340,
        "Ipswich Town": 389, "Leeds United": 341
    }
    for key, tid in team_ids.items():
        if key in team_name: 
            return f"https://crests.football-data.org/{tid}.png"
    return "https://cdn-icons-png.flaticon.com/512/5323/5323884.png"

# --- 4. ADVANCED POISSON MODEL ---
def calculate_draw_prob(h_prob, a_prob):
    """Calculate draw probability based on team strength"""
    balance_factor = 1 - abs(h_prob - a_prob) / 100
    return round(26.0 * balance_factor, 1)

def calculate_match_strength(home_team, away_team):
    """Calculate team strength based on historical performance"""
    strength_ratings = {
        "Manchester City": 95, "Liverpool": 92, "Arsenal": 89, "Chelsea": 85,
        "Manchester United": 83, "Tottenham Hotspur": 82, "Newcastle United": 80,
        "Aston Villa": 78, "Brighton & Hove Albion": 76, "West Ham United": 75,
        "Brentford": 73, "Fulham": 72, "Crystal Palace": 70, "Wolverhampton Wanderers": 69,
        "Everton": 68, "Nottingham Forest": 67, "Bournemouth": 66, "Leicester City": 65
    }
    
    home_strength = strength_ratings.get(home_team, 70)
    away_strength = strength_ratings.get(away_team, 70)
    
    return home_strength, away_strength

# --- 5. DATA FETCHING ---
@st.cache_data(ttl=300)
def fetch_data(endpoint):
    """Fetch data from API"""
    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/{endpoint}/?apiKey={API_KEY}&regions=uk&markets=h2h&oddsFormat=decimal"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except:
        return None

# --- 6. UI: HEADER ---
st.title("🏆 BetSmart Pro | Master Engine")
st.subheader("📊 Smart Betting Matrix with Live Odds")

# --- 7. SYNC BUTTON ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🔄 Sync Master Data (Odds, Scores & Times)", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- 8. FETCH MATCH DATA ---
odds_data = fetch_data("odds")
scores_data = fetch_data("scores")

# Create a dictionary for match times and scores
match_info = {}
if scores_data:
    for match in scores_data:
        home_team = match.get('home_team', '')
        away_team = match.get('away_team', '')
        match_key = f"{home_team}_vs_{away_team}"
        
        # Get match time
        commence_time = match.get('commence_time')
        if commence_time:
            match_info[match_key] = {
                'time': commence_time,
                'status': '🏁 FT' if match.get('completed') else ('🔴 LIVE' if match.get('scores') else '📅 Upcoming'),
                'score': f"{match['scores'][0]['score']} - {match['scores'][1]['score']}" if match.get('scores') else "vs"
            }

# --- 9. PROCESS MATCHES FOR MATRIX ---
if odds_data:
    all_matches = []
    
    for match in odds_data:
        home = match.get('home_team', '')
        away = match.get('away_team', '')
        
        if not home or not away:
            continue
            
        # Extract odds
        try:
            outcomes = match['bookmakers'][0]['markets'][0]['outcomes']
            h_odds = next((o['price'] for o in outcomes if o['name'] == home), 2.0)
            a_odds = next((o['price'] for o in outcomes if o['name'] == away), 2.0)
            d_odds = next((o['price'] for o in outcomes if o['name'] == "Draw"), 3.2)
        except:
            continue
        
        # Calculate probabilities
        h_prob = (1/h_odds)*100 if h_odds > 0 else 33
        a_prob = (1/a_odds)*100 if a_odds > 0 else 33
        d_prob = calculate_draw_prob(h_prob, a_prob)
        
        # Get match time and info
        match_key = f"{home}_vs_{away}"
        match_time_info = match_info.get(match_key, {})
        match_time = match_time_info.get('time', '')
        match_status = match_time_info.get('status', '📅 Upcoming')
        
        # Format time for SAST
        formatted_time = format_match_time(match_time) if match_time else "Time TBD"
        
        all_matches.append({
            "Home": home,
            "Away": away,
            "H_Prob": round(h_prob, 1),
            "D_Prob": d_prob,
            "A_Prob": round(a_prob, 1),
            "H_Odds": h_odds,
            "D_Odds": d_odds,
            "A_Odds": a_odds,
            "Match_Time": formatted_time,
            "Match_Status": match_status,
            "EV_Home": round((h_odds * (h_prob/100)) - 1, 3) * 100,
            "EV_Draw": round((d_odds * (d_prob/100)) - 1, 3) * 100,
            "EV_Away": round((a_odds * (a_prob/100)) - 1, 3) * 100
        })
    
    if all_matches:
        # Sort matches
        all_matches.sort(key=lambda x: x['H_Prob'], reverse=True)
        
        # Create 4x4 Matrix with enhanced info
        matrix_options = {
            "🏦 Option A (Bankers - High Probability)": all_matches[0:4] if len(all_matches) >= 4 else all_matches,
            "⚡ Option B (Home Edge)": all_matches[4:8] if len(all_matches) >= 8 else all_matches[4:],
            "🎯 Option C (Draw/Value)": sorted(all_matches, key=lambda x: x['D_Prob'], reverse=True)[0:4],
            "💎 Option D (Underdogs - High Value)": all_matches[-4:] if len(all_matches) >= 4 else all_matches
        }
        
        # Display tabs for each option
        tabs = st.tabs(list(matrix_options.keys()))
        
        for tab_idx, (group_name, matches) in enumerate(matrix_options.items()):
            with tabs[tab_idx]:
                st.markdown(f"### {group_name}")
                
                # Create columns for matches
                cols = st.columns(min(4, len(matches)))
                
                for idx, match in enumerate(matches):
                    with cols[idx % 4]:
                        # Team logos and names
                        col_logo1, col_vs, col_logo2 = st.columns([1, 1, 1])
                        with col_logo1:
                            st.image(get_team_logo_url(match['Home']), width=50)
                            st.caption(match['Home'])
                        with col_vs:
                            st.markdown("<h3 style='text-align: center'>VS</h3>", unsafe_allow_html=True)
                        with col_logo2:
                            st.image(get_team_logo_url(match['Away']), width=50)
                            st.caption(match['Away'])
                        
                        # Match time and status
                        st.markdown(f"🕒 **Time:** {match['Match_Time']}")
                        st.markdown(f"📊 **Status:** {match['Match_Status']}")
                        
                        st.divider()
                        
                        # Probabilities and odds
                        col_prob, col_odds = st.columns(2)
                        with col_prob:
                            st.metric("🏠 Home Win", f"{match['H_Prob']}%", 
                                     delta=f"Draw: {match['D_Prob']}%")
                            st.metric("🤝 Draw", f"{match['D_Prob']}%")
                            st.metric("✈️ Away Win", f"{match['A_Prob']}%")
                        
                        with col_odds:
                            st.metric("Home Odds", f"{match['H_Odds']:.2f}")
                            st.metric("Draw Odds", f"{match['D_Odds']:.2f}")
                            st.metric("Away Odds", f"{match['A_Odds']:.2f}")
                        
                        # Expected Value indicator
                        ev_color = "🟢" if match['EV_Home'] > 5 else ("🟡" if match['EV_Home'] > 0 else "🔴")
                        st.markdown(f"{ev_color} **EV Home:** {match['EV_Home']:+.1f}%")
                        
                        # Select button
                        if st.button(f"Select {match['Home']} vs {match['Away']}", key=f"select_{tab_idx}_{idx}"):
                            st.session_state.selected_match = match
                            st.session_state.selected_odds = [match['H_Odds'], match['D_Odds'], match['A_Odds']]
                            st.success(f"✅ Selected: {match['Home']} vs {match['Away']}")
        
        # --- 10. VALUE BETS SECTION ---
        st.divider()
        st.header("🎯 Top Value Betting Opportunities")
        
        # Filter matches with positive EV
        value_matches = [m for m in all_matches if m['EV_Home'] > 5 or m['EV_Draw'] > 5 or m['EV_Away'] > 5]
        value_matches.sort(key=lambda x: max(x['EV_Home'], x['EV_Draw'], x['EV_Away']), reverse=True)
        
        if value_matches:
            cols = st.columns(3)
            for idx, match in enumerate(value_matches[:6]):
                with cols[idx % 3]:
                    with st.container(border=True):
                        st.markdown(f"**{match['Home']} vs {match['Away']}**")
                        st.caption(f"🕒 {match['Match_Time']}")
                        
                        best_ev = max(match['EV_Home'], match['EV_Draw'], match['EV_Away'])
                        best_bet = "HOME" if best_ev == match['EV_Home'] else ("DRAW" if best_ev == match['EV_Draw'] else "AWAY")
                        
                        st.metric(f"Best Bet: {best_bet}", f"+{best_ev:.1f}% EV")
                        st.info(f"Odds: {match[f'{best_bet[0]}_Odds']:.2f}")
        else:
            st.info("No strong value bets found at this time")
        
        # --- 11. ZAR SYSTEM CALCULATOR ---
        st.divider()
        st.header("💰 ZAR System 3/4 Calculator")
        
        col1, col2 = st.columns(2)
        
        with col1:
            total_wager = st.number_input("Total Wager (ZAR)", value=100.0, step=10.0)
            
            # Show selected match if any
            if 'selected_match' in st.session_state:
                selected = st.session_state.selected_match
                st.info(f"📌 Selected: {selected['Home']} vs {selected['Away']} at {selected['Match_Time']}")
                default_odds = [selected['H_Odds'], selected['D_Odds'], selected['A_Odds'], 3.0]
            else:
                default_odds = [1.57, 1.59, 2.09, 3.30]
            
            o1 = st.number_input("Odds 1", value=float(default_odds[0]), step=0.01)
            o2 = st.number_input("Odds 2", value=float(default_odds[1]), step=0.01)
        
        with col2:
            o3 = st.number_input("Odds 3", value=float(default_odds[2]), step=0.01)
            o4 = st.number_input("Odds 4", value=float(default_odds[3]), step=0.01)
        
        # Calculate system bets
        if total_wager > 0:
            spb = total_wager / 4
            combos = [
                o1 * o2 * o3 * spb,
                o1 * o2 * o4 * spb,
                o1 * o3 * o4 * spb,
                o2 * o3 * o4 * spb
            ]
            
            result_cols = st.columns(3)
            with result_cols[0]:
                st.metric("Total Wager", f"R{total_wager:.2f}")
            with result_cols[1]:
                st.success(f"### Max Win (4/4)\n**Payout:** R{sum(combos):.2f}\n**Profit:** R{sum(combos)-total_wager:.2f}")
            with result_cols[2]:
                st.warning(f"### Safety Net (3/4)\n**Payout:** R{min(combos):.2f}\n**Profit/Loss:** R{min(combos)-total_wager:.2f}")
        
        # --- 12. LIVE SCORES EXPANDER ---
        st.divider()
        with st.expander("🏟️ Live Scores & Upcoming Matches (SAST)", expanded=False):
            if scores_data:
                for match in scores_data[:15]:  # Show up to 15 matches
                    home = match.get('home_team', 'Unknown')
                    away = match.get('away_team', 'Unknown')
                    commence_time = match.get('commence_time')
                    
                    # Convert to SAST
                    match_time = format_match_time(commence_time) if commence_time else "Time TBD"
                    
                    # Get score
                    score = "vs"
                    if match.get('scores') and len(match['scores']) >= 2:
                        score = f"{match['scores'][0].get('score', 0)} - {match['scores'][1].get('score', 0)}"
                    
                    # Status
                    if match.get('completed'):
                        status = "🏁 Full Time"
                    elif match.get('scores'):
                        status = "🔴 LIVE"
                    else:
                        status = "📅 Upcoming"
                    
                    # Display match
                    cols = st.columns([2, 1, 2, 2])
                    with cols[0]:
                        st.image(get_team_logo_url(home), width=40)
                        st.write(f"**{home}**")
                    with cols[1]:
                        st.markdown(f"<h3 style='text-align: center'>{score}</h3>", unsafe_allow_html=True)
                    with cols[2]:
                        st.image(get_team_logo_url(away), width=40)
                        st.write(f"**{away}**")
                    with cols[3]:
                        st.write(f"🕒 {match_time}")
                        st.write(f"{status}")
                    
                    st.divider()
            else:
                st.write("No match data available")
        
        # --- 13. TEAM STATISTICS ---
        with st.expander("📊 Team Statistics & Form Guide", expanded=False):
            st.markdown("### Current Season Form")
            
            # Create form guide dataframe
            form_data = []
            teams = list(set([m['Home'] for m in all_matches] + [m['Away'] for m in all_matches]))[:10]
            
            for team in teams:
                team_matches = [m for m in all_matches if m['Home'] == team or m['Away'] == team]
                avg_home_prob = sum(m['H_Prob'] for m in team_matches if m['Home'] == team) / max(len([m for m in team_matches if m['Home'] == team]), 1)
                
                form_data.append({
                    'Team': team,
                    'Home Win %': f"{avg_home_prob:.1f}%",
                    'Matches': len(team_matches),
                    'Best Odds': f"{min([m['H_Odds'] for m in team_matches if m['Home'] == team], default=0):.2f}"
                })
            
            st.dataframe(pd.DataFrame(form_data), use_container_width=True)
        
    else:
        st.error("No matches could be processed. Please check API connection.")
else:
    st.warning("Unable to fetch odds data. Please check your internet connection and API key.")

# --- 14. FOOTER ---
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
    <p>⚠️ Disclaimer: Betting involves risk. This tool is for informational purposes only.</p>
    <p>🕒 All times are in South African Standard Time (SAST)</p>
</div>
""", unsafe_allow_html=True)
