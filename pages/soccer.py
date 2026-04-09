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
        if utc_time_str:
            utc_time = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
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
        "Nottingham Forest": 351, "Bournemouth": 1044
    }
    for key, tid in team_ids.items():
        if key in team_name: 
            return f"https://crests.football-data.org/{tid}.png"
    return "https://cdn-icons-png.flaticon.com/512/5323/5323884.png"

# --- 4. ADVANCED BETTING RECOMMENDATION ENGINE ---
def get_bet_recommendation(match):
    """Generate specific bet recommendations with confidence levels"""
    recommendations = []
    
    # Calculate true probabilities using Poisson
    h_prob = match['H_Prob']
    d_prob = match['D_Prob']
    a_prob = match['A_Prob']
    
    # Calculate Expected Value for each outcome
    home_ev = match.get('EV_Home', 0)
    draw_ev = match.get('EV_Draw', 0)
    away_ev = match.get('EV_Away', 0)
    
    # 1. Value Bet Recommendation
    if home_ev > 5:
        recommendations.append({
            'bet': f"🏠 {match['Home']} to WIN",
            'odds': match['H_Odds'],
            'ev': home_ev,
            'confidence': 'HIGH' if home_ev > 10 else 'MEDIUM',
            'reason': f"Positive EV of {home_ev:.1f}% - Bookmaker undervaluing home team",
            'stake_pct': 3 if home_ev > 10 else 2
        })
    
    if draw_ev > 5:
        recommendations.append({
            'bet': "🤝 DRAW",
            'odds': match['D_Odds'],
            'ev': draw_ev,
            'confidence': 'HIGH' if draw_ev > 10 else 'MEDIUM',
            'reason': f"Draw probability {d_prob:.1f}% offers value at odds {match['D_Odds']:.2f}",
            'stake_pct': 2.5 if draw_ev > 10 else 1.5
        })
    
    if away_ev > 5:
        recommendations.append({
            'bet': f"✈️ {match['Away']} to WIN",
            'odds': match['A_Odds'],
            'ev': away_ev,
            'confidence': 'HIGH' if away_ev > 10 else 'MEDIUM',
            'reason': f"Away team has {a_prob:.1f}% chance at odds {match['A_Odds']:.2f}",
            'stake_pct': 2
        })
    
    # 2. Probability-Based Recommendation (if no value bets)
    if not recommendations:
        if h_prob > 55:
            recommendations.append({
                'bet': f"🏠 {match['Home']} to WIN",
                'odds': match['H_Odds'],
                'ev': home_ev,
                'confidence': 'MEDIUM',
                'reason': f"High probability ({h_prob:.1f}%) of home win",
                'stake_pct': 2
            })
        elif d_prob > 30:
            recommendations.append({
                'bet': "🤝 DRAW",
                'odds': match['D_Odds'],
                'ev': draw_ev,
                'confidence': 'MEDIUM',
                'reason': f"High draw probability ({d_prob:.1f}%)",
                'stake_pct': 1.5
            })
        elif a_prob > 45:
            recommendations.append({
                'bet': f"✈️ {match['Away']} to WIN",
                'odds': match['A_Odds'],
                'ev': away_ev,
                'confidence': 'MEDIUM',
                'reason': f"Strong away team with {a_prob:.1f}% chance",
                'stake_pct': 2
            })
    
    # Sort by EV (highest first)
    recommendations.sort(key=lambda x: x['ev'], reverse=True)
    
    return recommendations

def get_hedge_opportunity(match):
    """Find hedge betting opportunities between two outcomes"""
    hedge_opportunities = []
    
    # Check Home vs Draw hedge
    if match['H_Odds'] > 0 and match['D_Odds'] > 0:
        implied_prob_h = 1 / match['H_Odds']
        implied_prob_d = 1 / match['D_Odds']
        total_implied = implied_prob_h + implied_prob_d
        
        if total_implied < 1:
            hedge_opportunities.append({
                'type': 'Home or Draw (Double Chance)',
                'outcome1': f"{match['Home']} Win",
                'odds1': match['H_Odds'],
                'outcome2': "Draw",
                'odds2': match['D_Odds'],
                'combined_prob': (1 - total_implied) * 100,
                'description': f"Cover both Home Win and Draw - {((1 - total_implied) * 100):.1f}% theoretical edge"
            })
    
    # Check Draw vs Away hedge
    if match['D_Odds'] > 0 and match['A_Odds'] > 0:
        implied_prob_d = 1 / match['D_Odds']
        implied_prob_a = 1 / match['A_Odds']
        total_implied = implied_prob_d + implied_prob_a
        
        if total_implied < 1:
            hedge_opportunities.append({
                'type': 'Draw or Away (Double Chance)',
                'outcome1': "Draw",
                'odds1': match['D_Odds'],
                'outcome2': f"{match['Away']} Win",
                'odds2': match['A_Odds'],
                'combined_prob': (1 - total_implied) * 100,
                'description': f"Cover both Draw and Away Win - {((1 - total_implied) * 100):.1f}% theoretical edge"
            })
    
    # Check Home vs Away hedge (for high-scoring matches)
    if match['H_Odds'] > 0 and match['A_Odds'] > 0:
        implied_prob_h = 1 / match['H_Odds']
        implied_prob_a = 1 / match['A_Odds']
        total_implied = implied_prob_h + implied_prob_a
        
        if total_implied < 1:
            hedge_opportunities.append({
                'type': 'No Draw (BTTS or Either Team)',
                'outcome1': f"{match['Home']} Win",
                'odds1': match['H_Odds'],
                'outcome2': f"{match['Away']} Win",
                'odds2': match['A_Odds'],
                'combined_prob': (1 - total_implied) * 100,
                'description': f"Cover both teams to win (excluding draw)"
            })
    
    return hedge_opportunities

# --- 5. HEDGE BETTING CALCULATOR ---
def calculate_hedge_bet(odds1, odds2, total_stake):
    """Calculate optimal stakes for hedging two outcomes"""
    # Calculate stakes to guarantee profit
    stake1 = total_stake / (1 + (odds1 / odds2))
    stake2 = total_stake - stake1
    
    # Calculate profits
    profit1 = (stake1 * odds1) - total_stake
    profit2 = (stake2 * odds2) - total_stake
    min_profit = min(profit1, profit2)
    
    return {
        'stake1': stake1,
        'stake2': stake2,
        'profit1': profit1,
        'profit2': profit2,
        'min_profit': min_profit,
        'roi': (min_profit / total_stake) * 100
    }

def calculate_arbitrage(odds1, odds2, odds3):
    """Calculate arbitrage opportunity across 3 outcomes"""
    implied_prob = (1/odds1 + 1/odds2 + 1/odds3)
    
    if implied_prob < 1:
        arbitrage_pct = (1 - implied_prob) * 100
        stakes = []
        total_stake = 100
        
        for odds in [odds1, odds2, odds3]:
            stake = total_stake / (odds * implied_prob)
            stakes.append(stake)
        
        return {
            'is_arbitrage': True,
            'arbitrage_pct': arbitrage_pct,
            'stakes': stakes,
            'guaranteed_profit': (total_stake / implied_prob) - total_stake
        }
    else:
        return {'is_arbitrage': False}

# --- 6. DATA FETCHING ---
@st.cache_data(ttl=300)
def fetch_data(endpoint):
    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/{endpoint}/?apiKey={API_KEY}&regions=uk&markets=h2h&oddsFormat=decimal"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

# --- 7. MAIN UI ---
st.title("🏆 BetSmart Pro | Master Engine")
st.subheader("📊 AI-Powered Betting Recommendations & Hedge Calculator")

# Sync button
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🔄 Sync Master Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Fetch data
odds_data = fetch_data("odds")
scores_data = fetch_data("scores")

if odds_data:
    all_matches = []
    
    for match in odds_data:
        home = match.get('home_team', '')
        away = match.get('away_team', '')
        
        if not home or not away:
            continue
            
        try:
            outcomes = match['bookmakers'][0]['markets'][0]['outcomes']
            h_odds = next((o['price'] for o in outcomes if o['name'] == home), 2.0)
            a_odds = next((o['price'] for o in outcomes if o['name'] == away), 2.0)
            d_odds = next((o['price'] for o in outcomes if o['name'] == "Draw"), 3.2)
        except:
            continue
        
        # Calculate probabilities
        h_prob = (1/h_odds)*100
        a_prob = (1/a_odds)*100
        d_prob = 100 - h_prob - a_prob
        d_prob = max(15, min(35, d_prob))
        
        # Calculate EV
        home_ev = ((h_odds * (h_prob/100)) - 1) * 100
        draw_ev = ((d_odds * (d_prob/100)) - 1) * 100
        away_ev = ((a_odds * (a_prob/100)) - 1) * 100
        
        all_matches.append({
            "Home": home, "Away": away,
            "H_Prob": round(h_prob, 1), "D_Prob": round(d_prob, 1), "A_Prob": round(a_prob, 1),
            "H_Odds": h_odds, "D_Odds": d_odds, "A_Odds": a_odds,
            "EV_Home": round(home_ev, 1), "EV_Draw": round(draw_ev, 1), "EV_Away": round(away_ev, 1)
        })
    
    # --- 8. SMART BETTING MATRIX WITH RECOMMENDATIONS ---
    st.header("🎯 Smart Betting Matrix with AI Recommendations")
    
    # Sort and create matrix
    all_matches.sort(key=lambda x: max(x['EV_Home'], x['EV_Draw'], x['EV_Away']), reverse=True)
    
    top_value_matches = all_matches[:8]  # Top 8 value matches
    
    # Display matches with recommendations
    for idx, match in enumerate(top_value_matches):
        with st.container():
            st.markdown(f"### Match {idx + 1}: {match['Home']} vs {match['Away']}")
            
            # Get recommendations
            recommendations = get_bet_recommendation(match)
            hedge_opportunities = get_hedge_opportunity(match)
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.image(get_team_logo_url(match['Home']), width=80)
                st.markdown(f"**{match['Home']}**")
                st.metric("Win Probability", f"{match['H_Prob']}%", 
                         delta=f"EV: {match['EV_Home']:+.1f}%")
                st.caption(f"Odds: {match['H_Odds']:.2f}")
            
            with col2:
                st.image(get_team_logo_url(match['Away']), width=80)
                st.markdown(f"**{match['Away']}**")
                st.metric("Win Probability", f"{match['A_Prob']}%",
                         delta=f"EV: {match['EV_Away']:+.1f}%")
                st.caption(f"Odds: {match['A_Odds']:.2f}")
            
            with col3:
                st.metric("Draw Probability", f"{match['D_Prob']}%",
                         delta=f"EV: {match['EV_Draw']:+.1f}%")
                st.caption(f"Odds: {match['D_Odds']:.2f}")
            
            # Bet Recommendations
            if recommendations:
                st.markdown("#### 💡 Recommended Bets")
                rec_cols = st.columns(len(recommendations))
                for rec_idx, rec in enumerate(recommendations):
                    with rec_cols[rec_idx]:
                        color = "🟢" if rec['confidence'] == 'HIGH' else "🟡"
                        st.info(f"{color} **{rec['bet']}**")
                        st.write(f"Odds: {rec['odds']:.2f}")
                        st.write(f"EV: +{rec['ev']:.1f}%")
                        st.write(f"Suggested Stake: {rec['stake_pct']}%")
                        st.caption(rec['reason'])
            
            # Hedge Opportunities
            if hedge_opportunities:
                st.markdown("#### 🔒 Hedge Opportunities")
                for hedge in hedge_opportunities:
                    with st.expander(f"🎲 {hedge['type']}"):
                        st.write(hedge['description'])
                        st.write(f"Outcome 1: {hedge['outcome1']} @ {hedge['odds1']:.2f}")
                        st.write(f"Outcome 2: {hedge['outcome2']} @ {hedge['odds2']:.2f}")
                        
                        # Quick hedge calculator
                        hedge_amount = st.number_input(f"Hedge Amount (R)", 
                                                      min_value=100, 
                                                      value=500, 
                                                      step=100,
                                                      key=f"hedge_{idx}_{rec_idx if 'rec_idx' in locals() else 0}")
                        
                        if hedge_amount > 0:
                            hedge_result = calculate_hedge_bet(hedge['odds1'], hedge['odds2'], hedge_amount)
                            st.write(f"💰 **Stake 1 ({hedge['outcome1']}):** R{hedge_result['stake1']:.2f}")
                            st.write(f"💰 **Stake 2 ({hedge['outcome2']}):** R{hedge_result['stake2']:.2f}")
                            st.success(f"✅ **Guaranteed Profit:** R{hedge_result['min_profit']:.2f} ({hedge_result['roi']:.1f}% ROI)")
            
            st.divider()
    
    # --- 9. HEDGE BETTING CALCULATOR SECTION ---
    st.header("🔒 Advanced Hedge Betting Calculator")
    st.markdown("Place bets on two different bookmakers to guarantee profit")
    
    tab1, tab2, tab3 = st.tabs(["Two-Way Hedge", "Three-Way Arbitrage", "Dutching Calculator"])
    
    with tab1:
        st.subheader("Two-Way Hedge (Cover 2 Outcomes)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Outcome 1 (Bookmaker A)**")
            outcome1_name = st.text_input("Outcome 1 Name", "Team A Win")
            odds1 = st.number_input("Odds 1", min_value=1.01, value=2.0, step=0.05)
        
        with col2:
            st.markdown("**Outcome 2 (Bookmaker B)**")
            outcome2_name = st.text_input("Outcome 2 Name", "Team B Win")
            odds2 = st.number_input("Odds 2", min_value=1.01, value=3.0, step=0.05)
        
        total_hedge_stake = st.number_input("Total Stake (R)", min_value=100, value=1000, step=100)
        
        if st.button("Calculate Hedge Bet"):
            hedge_result = calculate_hedge_bet(odds1, odds2, total_hedge_stake)
            
            st.markdown("---")
            st.markdown("### 📊 Hedge Bet Results")
            
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                st.metric(f"Stake on {outcome1_name}", f"R{hedge_result['stake1']:.2f}")
                st.metric(f"Payout if Wins", f"R{hedge_result['stake1'] * odds1:.2f}")
                st.metric(f"Profit if Wins", f"R{hedge_result['profit1']:.2f}")
            
            with col_b:
                st.metric(f"Stake on {outcome2_name}", f"R{hedge_result['stake2']:.2f}")
                st.metric(f"Payout if Wins", f"R{hedge_result['stake2'] * odds2:.2f}")
                st.metric(f"Profit if Wins", f"R{hedge_result['profit2']:.2f}")
            
            with col_c:
                st.success(f"💰 **Guaranteed Minimum Profit**")
                st.metric("Profit", f"R{hedge_result['min_profit']:.2f}")
                st.metric("ROI", f"{hedge_result['roi']:.1f}%")
                st.metric("Total Risk", f"R{total_hedge_stake:.2f}")
    
    with tab2:
        st.subheader("Three-Way Arbitrage (Cover All Outcomes)")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            outcome_a = st.text_input("Outcome A", "Home Win", key="arb_a")
            odds_a = st.number_input("Odds A", min_value=1.01, value=2.5, step=0.05, key="arb_odds_a")
        
        with col2:
            outcome_b = st.text_input("Outcome B", "Draw", key="arb_b")
            odds_b = st.number_input("Odds B", min_value=1.01, value=3.2, step=0.05, key="arb_odds_b")
        
        with col3:
            outcome_c = st.text_input("Outcome C", "Away Win", key="arb_c")
            odds_c = st.number_input("Odds C", min_value=1.01, value=2.8, step=0.05, key="arb_odds_c")
        
        arbitrage_stake = st.number_input("Total Stake (R)", min_value=100, value=1000, step=100, key="arb_stake")
        
        if st.button("Find Arbitrage Opportunity"):
            arb_result = calculate_arbitrage(odds_a, odds_b, odds_c)
            
            if arb_result['is_arbitrage']:
                st.success(f"✅ **Arbitrage Opportunity Found!** ({arb_result['arbitrage_pct']:.2f}% guaranteed return)")
                
                st.markdown("### 📊 Arbitrage Stakes")
                
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    stake_a = (arbitrage_stake / (odds_a * (1/odds_a + 1/odds_b + 1/odds_c))) if odds_a > 0 else 0
                    st.metric(f"Stake on {outcome_a}", f"R{stake_a:.2f}")
                    st.metric(f"Payout", f"R{stake_a * odds_a:.2f}")
                
                with col_b:
                    stake_b = (arbitrage_stake / (odds_b * (1/odds_a + 1/odds_b + 1/odds_c))) if odds_b > 0 else 0
                    st.metric(f"Stake on {outcome_b}", f"R{stake_b:.2f}")
                    st.metric(f"Payout", f"R{stake_b * odds_b:.2f}")
                
                with col_c:
                    stake_c = (arbitrage_stake / (odds_c * (1/odds_a + 1/odds_b + 1/odds_c))) if odds_c > 0 else 0
                    st.metric(f"Stake on {outcome_c}", f"R{stake_c:.2f}")
                    st.metric(f"Payout", f"R{stake_c * odds_c:.2f}")
                
                total_staked = stake_a + stake_b + stake_c
                guaranteed_profit = (stake_a * odds_a) - total_staked
                
                st.success(f"💰 **Guaranteed Profit:** R{guaranteed_profit:.2f} ({arb_result['arbitrage_pct']:.2f}% ROI)")
                
            else:
                st.warning("No arbitrage opportunity found. The combined implied probability is > 100%")
                st.info(f"Combined Implied Probability: {(1/odds_a + 1/odds_b + 1/odds_c) * 100:.1f}%")
    
    with tab3:
        st.subheader("Dutching Calculator (Cover Multiple Outcomes)")
        st.markdown("Distribute stake across multiple outcomes to guarantee profit if any wins")
        
        num_outcomes = st.selectbox("Number of outcomes", [2, 3, 4])
        
        outcomes = []
        odds_list = []
        
        cols = st.columns(num_outcomes)
        for i in range(num_outcomes):
            with cols[i]:
                outcome = st.text_input(f"Outcome {i+1}", f"Option {i+1}", key=f"dutch_outcome_{i}")
                odds = st.number_input(f"Odds {i+1}", min_value=1.01, value=2.0 + i*0.5, step=0.05, key=f"dutch_odds_{i}")
                outcomes.append(outcome)
                odds_list.append(odds)
        
        dutch
