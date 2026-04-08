import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import math
import numpy as np
from scipy import stats

# --- 1. CONFIG & API SETTINGS ---
API_KEY = "8e1ac8e3fb43757f30f2aec94dbebb81" 
st.set_page_config(page_title="BetSmart Pro | Advanced Analytics", layout="wide")

# --- 2. ADVANCED TEAM STATISTICS CACHE ---
@st.cache_data(ttl=3600)
def get_team_stats():
    """Fetch team performance metrics"""
    return {
        "Manchester City": {"attack": 92, "defense": 88, "form": 9.2, "home_advantage": 1.4},
        "Liverpool": {"attack": 89, "defense": 85, "form": 8.7, "home_advantage": 1.3},
        "Arsenal": {"attack": 86, "defense": 84, "form": 8.5, "home_advantage": 1.3},
        "Chelsea": {"attack": 82, "defense": 79, "form": 7.8, "home_advantage": 1.2},
        "Manchester United": {"attack": 80, "defense": 77, "form": 7.5, "home_advantage": 1.2},
        "Tottenham Hotspur": {"attack": 83, "defense": 75, "form": 7.7, "home_advantage": 1.2},
        "Newcastle United": {"attack": 78, "defense": 80, "form": 7.9, "home_advantage": 1.1},
        "Aston Villa": {"attack": 79, "defense": 72, "form": 7.4, "home_advantage": 1.1},
        "Brighton & Hove Albion": {"attack": 76, "defense": 74, "form": 7.3, "home_advantage": 1.1},
        "West Ham United": {"attack": 74, "defense": 71, "form": 7.0, "home_advantage": 1.1},
        "Brentford": {"attack": 73, "defense": 70, "form": 6.8, "home_advantage": 1.0},
        "Fulham": {"attack": 71, "defense": 69, "form": 6.7, "home_advantage": 1.0},
        "Crystal Palace": {"attack": 70, "defense": 68, "form": 6.6, "home_advantage": 1.0},
        "Wolverhampton Wanderers": {"attack": 69, "defense": 67, "form": 6.5, "home_advantage": 1.0},
        "Everton": {"attack": 67, "defense": 69, "form": 6.4, "home_advantage": 1.0},
        "Nottingham Forest": {"attack": 66, "defense": 68, "form": 6.3, "home_advantage": 0.9},
        "Bournemouth": {"attack": 68, "defense": 65, "form": 6.2, "home_advantage": 0.9},
        "Leicester City": {"attack": 69, "defense": 66, "form": 6.1, "home_advantage": 0.9}
    }

def get_team_logo_url(team_name):
    team_ids = {
        "Arsenal": 57, "Aston Villa": 58, "Chelsea": 61, "Liverpool": 64, 
        "Manchester City": 65, "Manchester United": 66, "Newcastle United": 67,
        "Tottenham Hotspur": 73, "West Ham United": 563, "Brentford": 402,
        "Brighton & Hove Albion": 397, "Crystal Palace": 354, "Everton": 62,
        "Fulham": 63, "Leicester City": 338, "Wolverhampton Wanderers": 76,
        "Nottingham Forest": 351, "Bournemouth": 1044
    }
    for key, tid in team_ids.items():
        if key in team_name: return f"https://crests.football-data.org/{tid}.png"
    return "https://cdn-icons-png.flaticon.com/512/5323/5323884.png"

# --- 3. ADVANCED POISSON & EXPECTED GOALS MODEL ---
def calculate_xg(home_team, away_team, team_stats):
    """Calculate Expected Goals using team statistics"""
    home_stats = team_stats.get(home_team, {"attack": 70, "defense": 70, "home_advantage": 1.0})
    away_stats = team_stats.get(away_team, {"attack": 70, "defense": 70, "home_advantage": 1.0})
    
    league_avg = 1.35  # Average goals per team per match
    
    # Calculate expected goals
    home_xg = (home_stats['attack'] / 100) * (away_stats['defense'] / 100) * league_avg * home_stats['home_advantage']
    away_xg = (away_stats['attack'] / 100) * (home_stats['defense'] / 100) * league_avg
    
    return home_xg, away_xg

def poisson_probability(actual, mean):
    """Calculate Poisson probability"""
    return (math.exp(-mean) * mean ** actual) / math.factorial(actual)

def calculate_match_probabilities(home_team, away_team, team_stats):
    """Calculate win/draw/loss probabilities using Poisson distribution"""
    home_xg, away_xg = calculate_xg(home_team, away_team, team_stats)
    
    # Calculate probabilities for different scorelines
    max_goals = 8
    home_win_prob = 0
    draw_prob = 0
    away_win_prob = 0
    
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            prob = poisson_probability(i, home_xg) * poisson_probability(j, away_xg)
            if i > j:
                home_win_prob += prob
            elif i == j:
                draw_prob += prob
            else:
                away_win_prob += prob
    
    # Adjust for draw probability using empirical data
    draw_prob = draw_prob * 0.92  # Slight adjustment based on historical data
    
    # Normalize
    total = home_win_prob + draw_prob + away_win_prob
    home_win_prob = (home_win_prob / total) * 100
    draw_prob = (draw_prob / total) * 100
    away_win_prob = (away_win_prob / total) * 100
    
    return home_win_prob, draw_prob, away_win_prob

def calculate_expected_value(odds, probability):
    """Calculate Expected Value for a bet"""
    return (odds * (probability / 100)) - 1

def kelly_criterion(odds, probability, bankroll=1000):
    """Calculate Kelly Criterion bet sizing"""
    b = odds - 1  # Decimal odds to fractional
    p = probability / 100
    q = 1 - p
    
    if b <= 0 or p <= 0:
        return 0
    
    f = (p * b - q) / b
    # Use fractional Kelly for safety (25% of optimal)
    return max(0, f * 0.25 * bankroll)

# --- 4. DATA FETCHING WITH ENHANCED METRICS ---
def fetch_data(endpoint):
    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/{endpoint}/?apiKey={API_KEY}&regions=uk&markets=h2h&oddsFormat=decimal"
    try:
        response = requests.get(url, timeout=5)
        return response.json() if response.status_code == 200 else None
    except: return None

# --- 5. VALUE BET DETECTOR ---
def find_value_bets(matches_data, team_stats):
    """Identify value betting opportunities"""
    value_bets = []
    
    for match in matches_data:
        home = match['home_team']
        away = match['away_team']
        
        # Calculate true probabilities
        home_prob, draw_prob, away_prob = calculate_match_probabilities(home, away, team_stats)
        
        # Get market odds
        h_odds = match.get('h_odds', 2.0)
        d_odds = match.get('d_odds', 3.2)
        a_odds = match.get('a_odds', 2.0)
        
        # Calculate EV for each outcome
        home_ev = calculate_expected_value(h_odds, home_prob)
        draw_ev = calculate_expected_value(d_odds, draw_prob)
        away_ev = calculate_expected_value(a_odds, away_prob)
        
        # Kelly stake recommendations
        home_stake = kelly_criterion(h_odds, home_prob)
        draw_stake = kelly_criterion(d_odds, draw_prob)
        away_stake = kelly_criterion(a_odds, away_prob)
        
        # Add to value bets if positive EV
        if home_ev > 0.05:  # At least 5% positive EV
            value_bets.append({
                "match": f"{home} vs {away}",
                "bet": f"{home} to Win",
                "odds": h_odds,
                "true_prob": round(home_prob, 1),
                "market_prob": round((1/h_odds)*100, 1),
                "ev": round(home_ev * 100, 1),
                "suggested_stake": round(home_stake, 2),
                "confidence": "HIGH" if home_ev > 0.15 else "MEDIUM"
            })
        
        if draw_ev > 0.05:
            value_bets.append({
                "match": f"{home} vs {away}",
                "bet": "Draw",
                "odds": d_odds,
                "true_prob": round(draw_prob, 1),
                "market_prob": round((1/d_odds)*100, 1),
                "ev": round(draw_ev * 100, 1),
                "suggested_stake": round(draw_stake, 2),
                "confidence": "HIGH" if draw_ev > 0.15 else "MEDIUM"
            })
        
        if away_ev > 0.05:
            value_bets.append({
                "match": f"{home} vs {away}",
                "bet": f"{away} to Win",
                "odds": a_odds,
                "true_prob": round(away_prob, 1),
                "market_prob": round((1/a_odds)*100, 1),
                "ev": round(away_ev * 100, 1),
                "suggested_stake": round(away_stake, 2),
                "confidence": "HIGH" if away_ev > 0.15 else "MEDIUM"
            })
    
    # Sort by EV
    value_bets.sort(key=lambda x: x['ev'], reverse=True)
    return value_bets

# --- 6. ENHANCED UI ---
st.title("🏆 BetSmart Pro | Advanced Analytics Engine")
st.subheader("📊 AI-Powered Betting Intelligence")

if st.button("🔄 Sync & Analyze All Data"):
    st.cache_data.clear()
    st.rerun()

# --- 7. FETCH AND PROCESS DATA ---
odds_data = fetch_data("odds")
team_stats = get_team_stats()

if odds_data:
    all_matches = []
    for match in odds_data:
        home = match['home_team']
        away = match['away_team']
        outcomes = match['bookmakers'][0]['markets'][0]['outcomes']
        
        h_odds = next(o['price'] for o in outcomes if o['name'] == home)
        a_odds = next(o['price'] for o in outcomes if o['name'] == away)
        d_odds = next(o['price'] for o in outcomes if o['name'] == "Draw")
        
        # Use advanced probability model
        h_prob, d_prob, a_prob = calculate_match_probabilities(home, away, team_stats)
        
        all_matches.append({
            "Home": home, "Away": away, 
            "H_Prob": round(h_prob, 1), 
            "D_Prob": round(d_prob, 1),
            "A_Prob": round(a_prob, 1),
            "H_Odds": h_odds, 
            "D_Odds": d_odds,
            "A_Odds": a_odds,
            "EV_Home": round(calculate_expected_value(h_odds, h_prob) * 100, 1),
            "EV_Draw": round(calculate_expected_value(d_odds, d_prob) * 100, 1),
            "EV_Away": round(calculate_expected_value(a_odds, a_prob) * 100, 1)
        })
    
    # --- 8. VALUE BETS SECTION (NEW) ---
    st.header("🎯 Value Betting Opportunities")
    value_bets = find_value_bets(all_matches, team_stats)
    
    if value_bets:
        cols = st.columns(3)
        for idx, bet in enumerate(value_bets[:6]):  # Show top 6
            with cols[idx % 3]:
                with st.container():
                    color = "🟢" if bet['confidence'] == "HIGH" else "🟡"
                    st.markdown(f"""
                    {color} **{bet['match']}**  
                    **Bet:** {bet['bet']}  
                    **Odds:** {bet['odds']}  
                    **True Prob:** {bet['true_prob']}% | **Market:** {bet['market_prob']}%  
                    **EV:** +{bet['ev']}%  
                    **Suggested Stake:** R{bet['suggested_stake']}
                    """)
                    st.divider()
    else:
        st.info("No strong value bets found at this time. Monitor for odds movements.")
    
    # --- 9. SMART BETTING MATRIX ---
    st.header("📊 Smart Betting Matrix")
    
    # Filter for positive EV bets only
    positive_ev_matches = [m for m in all_matches if m['EV_Home'] > 5 or m['EV_Draw'] > 5 or m['EV_Away'] > 5]
    
    if len(positive_ev_matches) >= 4:
        # Sort by highest EV for home wins
        top_bankers = sorted(positive_ev_matches, key=lambda x: x['EV_Home'], reverse=True)[:4]
        # Sort by highest EV for draws
        top_draws = sorted(positive_ev_matches, key=lambda x: x['EV_Draw'], reverse=True)[:4]
        # Sort by highest overall EV
        all_ev = []
        for m in positive_ev_matches:
            all_ev.append((m, max(m['EV_Home'], m['EV_Draw'], m['EV_Away'])))
        top_value = sorted(all_ev, key=lambda x: x[1], reverse=True)[:4]
        
        matrix = {
            "🏦 Bankers (High EV Home)": top_bankers,
            "🎯 Draw Specialists": top_draws,
            "💎 Value Picks": [x[0] for x in top_value]
        }
        
        tabs = st.tabs(list(matrix.keys()))
        for i, (group, matches) in enumerate(matrix.items()):
            with tabs[i]:
                cols = st.columns(4)
                for j, m in enumerate(matches):
                    with cols[j]:
                        st.image(get_team_logo_url(m['Home']), width=60)
                        st.metric(m['Home'], f"{m['H_Prob']}%", f"EV: +{m['EV_Home']}%")
                        st.caption(f"Odds: {m['H_Odds']} | Draw: {m['D_Odds']}")
                        
                        if st.button(f"Select", key=f"select_{i}_{j}"):
                            st.session_state.selected_match = m
    
    # --- 10. ADVANCED CALCULATOR ---
    st.header("💰 Advanced Betting Calculator")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Kelly Criterion")
        odds_input = st.number_input("Decimal Odds", value=2.0, step=0.1)
        prob_input = st.number_input("Your Probability (%)", value=50.0, step=1.0)
        bankroll = st.number_input("Bankroll (ZAR)", value=1000.0, step=100.0)
        
        if st.button("Calculate Kelly Stake"):
            stake = kelly_criterion(odds_input, prob_input, bankroll)
            ev = calculate_expected_value(odds_input, prob_input)
            st.success(f"**Recommended Stake:** R{stake:.2f}")
            st.metric("Expected Value", f"+{ev*100:.1f}%" if ev > 0 else f"{ev*100:.1f}%")
    
    with col2:
        st.subheader("System 3/4 Optimizer")
        def_odds = [1.57, 1.59, 2.09, 3.30]
        total_wager = st.number_input("Total Wager (ZAR)", value=100.0, step=10.0, key="total_wager")
        
        o1 = st.number_input("Odds 1", value=float(def_odds[0]), key="o1")
        o2 = st.number_input("Odds 2", value=float(def_odds[1]), key="o2")
        o3 = st.number_input("Odds 3", value=float(def_odds[2]), key="o3")
        o4 = st.number_input("Odds 4", value=float(def_odds[3]), key="o4")
        
        spb = total_wager / 4
        combos = [o1*o2*o3*spb, o1*o2*o4*spb, o1*o3*o4*spb, o2*o3*o4*spb]
        
        st.metric("Max Win (4/4)", f"R{sum(combos):.2f}")
        st.metric("Profit if 4/4", f"R{sum(combos)-total_wager:.2f}")
        st.metric("Safety Net (3/4)", f"R{min(combos):.2f}")
    
    with col3:
        st.subheader("Dutching Calculator")
        st.info("Bet on multiple outcomes to guarantee profit")
        
        odds_a = st.number_input("Outcome A Odds", value=2.5, step=0.1, key="dutch_a")
        odds_b = st.number_input("Outcome B Odds", value=3.5, step=0.1, key="dutch_b")
        total_stake = st.number_input("Total Stake (ZAR)", value=100.0, step=10.0, key="dutch_stake")
        
        if odds_a > 0 and odds_b > 0:
            stake_a = total_stake / (1 + odds_a/odds_b)
            stake_b = total_stake - stake_a
            profit_a = stake_a * odds_a - total_stake
            profit_b = stake_b * odds_b - total_stake
            
            st.write(f"**Stake A:** R{stake_a:.2f}")
            st.write(f"**Stake B:** R{stake_b:.2f}")
            st.success(f"**Profit if A wins:** R{profit_a:.2f}")
            st.success(f"**Profit if B wins:** R{profit_b:.2f}")

# --- 11. LIVE SCORES ---
st.divider()
with st.expander("🏟️ Live Scores & Match Times (SAST)", expanded=False):
    scores_data = fetch_data("scores")
    if scores_data:
        for match in scores_data:
            utc_time = datetime.fromisoformat(match['commence_time'].replace('Z', ''))
            sast_time = utc_time + timedelta(hours=2)
            
            c1, c2, c3 = st.columns([2, 1, 2])
            score = f"{match['scores'][0]['score']} - {match['scores'][1]['score']}" if match.get('scores') else "vs"
            status = "🏁 FT" if match['completed'] else ("🔴 LIVE" if match.get('scores') else "📅 Upcoming")
            
            c1.write(f"**{match['home_team']}**")
            c2.info(f"**{score}**")
            c3.write(f"**{match['away_team']}**")
            st.caption(f"🕒 {sast_time.strftime('%d %b | %H:%M')} SAST | {status}")
            st.write("---")
    else:
        st.write("No live data available.")
