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

# --- 4. BETTING RECOMMENDATION ENGINE ---
def get_bet_recommendation(match):
    """Generate specific bet recommendations with confidence levels"""
    recommendations = []
    
    h_prob = match['H_Prob']
    d_prob = match['D_Prob']
    a_prob = match['A_Prob']
    
    home_ev = match.get('EV_Home', 0)
    draw_ev = match.get('EV_Draw', 0)
    away_ev = match.get('EV_Away', 0)
    
    # Value Bet Recommendation
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
    
    # Probability-Based Recommendation (if no value bets)
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
    
    return hedge_opportunities

def calculate_hedge_bet(odds1, odds2, total_stake):
    """Calculate optimal stakes for hedging two outcomes"""
    stake1 = total_stake / (1 + (odds1 / odds2))
    stake2 = total_stake - stake1
    
    profit1 = (stake1 * odds1) - total_stake
    profit2 = (stake2 * odds2) - total_stake
    min_profit = min(profit1, profit2)
    
    return {
        'stake1': stake1,
        'stake2': stake2,
        'profit1': profit1,
        'profit2': profit2,
        'min_profit': min_profit,
        'roi': (min_profit / total_stake) * 100 if total_stake > 0 else 0
    }

def calculate_arbitrage(odds_list, total_stake):
    """Calculate arbitrage opportunity across multiple outcomes"""
    implied_prob = sum(1/odds for odds in odds_list)
    
    if implied_prob < 1:
        stakes = []
        for odds in odds_list:
            stake = total_stake / (odds * implied_prob)
            stakes.append(stake)
        
        return {
            'is_arbitrage': True,
            'arbitrage_pct': (1 - implied_prob) * 100,
            'stakes': stakes,
            'guaranteed_profit': (total_stake / implied_prob) - total_stake
        }
    else:
        return {'is_arbitrage': False}

# --- 5. DATA FETCHING ---
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

# --- 6. MAIN UI ---
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
    
    # --- 7. SMART BETTING MATRIX ---
    st.header("🎯 Smart Betting Matrix with AI Recommendations")
    
    all_matches.sort(key=lambda x: max(x['EV_Home'], x['EV_Draw'], x['EV_Away']), reverse=True)
    top_value_matches = all_matches[:8]
    
    for idx, match in enumerate(top_value_matches):
        with st.container():
            st.markdown(f"### Match {idx + 1}: {match['Home']} vs {match['Away']}")
            
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
                for hedge_idx, hedge in enumerate(hedge_opportunities):
                    with st.expander(f"🎲 {hedge['type']}"):
                        st.write(hedge['description'])
                        st.write(f"Outcome 1: {hedge['outcome1']} @ {hedge['odds1']:.2f}")
                        st.write(f"Outcome 2: {hedge['outcome2']} @ {hedge['odds2']:.2f}")
            
            st.divider()
    
    # --- 8. HEDGE BETTING CALCULATOR SECTION ---
    st.header("🔒 Hedge Betting Calculator")
    
    tab1, tab2, tab3 = st.tabs(["Two-Way Hedge", "Three-Way Arbitrage", "Dutching Calculator"])
    
    with tab1:
        st.subheader("Two-Way Hedge (Cover 2 Outcomes)")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            outcome1_name = st.text_input("Outcome 1 Name", "Team A Win", key="hedge_out1")
            odds1 = st.number_input("Odds 1", min_value=1.01, value=2.0, step=0.05, key="hedge_odds1")
        
        with col_b:
            outcome2_name = st.text_input("Outcome 2 Name", "Team B Win", key="hedge_out2")
            odds2 = st.number_input("Odds 2", min_value=1.01, value=3.0, step=0.05, key="hedge_odds2")
        
        hedge_total = st.number_input("Total Stake (R)", min_value=100, value=1000, step=100, key="hedge_total")
        
        if st.button("Calculate Hedge Bet", key="calc_hedge"):
            hedge_result = calculate_hedge_bet(odds1, odds2, hedge_total)
            
            st.markdown("---")
            st.markdown("### 📊 Hedge Bet Results")
            
            col_r1, col_r2, col_r3 = st.columns(3)
            
            with col_r1:
                st.metric(f"Stake on {outcome1_name}", f"R{hedge_result['stake1']:.2f}")
                st.metric(f"Payout if Wins", f"R{hedge_result['stake1'] * odds1:.2f}")
                st.metric(f"Profit if Wins", f"R{hedge_result['profit1']:.2f}")
            
            with col_r2:
                st.metric(f"Stake on {outcome2_name}", f"R{hedge_result['stake2']:.2f}")
                st.metric(f"Payout if Wins", f"R{hedge_result['stake2'] * odds2:.2f}")
                st.metric(f"Profit if Wins", f"R{hedge_result['profit2']:.2f}")
            
            with col_r3:
                st.success(f"💰 **Guaranteed Minimum Profit**")
                st.metric("Profit", f"R{hedge_result['min_profit']:.2f}")
                st.metric("ROI", f"{hedge_result['roi']:.1f}%")
                st.metric("Total Risk", f"R{hedge_total:.2f}")
    
    with tab2:
        st.subheader("Three-Way Arbitrage (Cover All Outcomes)")
        
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            outcome_a = st.text_input("Outcome A", "Home Win", key="arb_out_a")
            odds_a = st.number_input("Odds A", min_value=1.01, value=2.5, step=0.05, key="arb_odds_a")
        
        with col_b:
            outcome_b = st.text_input("Outcome B", "Draw", key="arb_out_b")
            odds_b = st.number_input("Odds B", min_value=1.01, value=3.2, step=0.05, key="arb_odds_b")
        
        with col_c:
            outcome_c = st.text_input("Outcome C", "Away Win", key="arb_out_c")
            odds_c = st.number_input("Odds C", min_value=1.01, value=2.8, step=0.05, key="arb_odds_c")
        
        arb_total = st.number_input("Total Stake (R)", min_value=100, value=1000, step=100, key="arb_total")
        
        if st.button("Find Arbitrage Opportunity", key="calc_arb"):
            odds_list = [odds_a, odds_b, odds_c]
            arb_result = calculate_arbitrage(odds_list, arb_total)
            
            if arb_result['is_arbitrage']:
                st.success(f"✅ **Arbitrage Opportunity Found!** ({arb_result['arbitrage_pct']:.2f}% guaranteed return)")
                
                st.markdown("### 📊 Arbitrage Stakes")
                
                col_s1, col_s2, col_s3 = st.columns(3)
                
                with col_s1:
                    st.metric(f"Stake on {outcome_a}", f"R{arb_result['stakes'][0]:.2f}")
                    st.metric(f"Payout", f"R{arb_result['stakes'][0] * odds_a:.2f}")
                
                with col_s2:
                    st.metric(f"Stake on {outcome_b}", f"R{arb_result['stakes'][1]:.2f}")
                    st.metric(f"Payout", f"R{arb_result['stakes'][1] * odds_b:.2f}")
                
                with col_s3:
                    st.metric(f"Stake on {outcome_c}", f"R{arb_result['stakes'][2]:.2f}")
                    st.metric(f"Payout", f"R{arb_result['stakes'][2] * odds_c:.2f}")
                
                st.success(f"💰 **Guaranteed Profit:** R{arb_result['guaranteed_profit']:.2f} ({arb_result['arbitrage_pct']:.2f}% ROI)")
                
            else:
                st.warning("No arbitrage opportunity found. The combined implied probability is > 100%")
                implied_prob_sum = sum(1/odds for odds in odds_list)
                st.info(f"Combined Implied Probability: {implied_prob_sum * 100:.1f}%")
    
    with tab3:
        st.subheader("Dutching Calculator (Cover Multiple Outcomes)")
        
        num_outcomes = st.selectbox("Number of outcomes", [2, 3, 4], key="dutch_num")
        
        outcomes = []
        odds_list = []
        
        cols = st.columns(num_outcomes)
        for i in range(num_outcomes):
            with cols[i]:
                outcome = st.text_input(f"Outcome {i+1}", f"Option {i+1}", key=f"dutch_out_{i}")
                odds = st.number_input(f"Odds {i+1}", min_value=1.01, value=2.0 + i*0.5, step=0.05, key=f"dutch_odds_{i}")
                outcomes.append(outcome)
                odds_list.append(odds)
        
        dutch_total = st.number_input("Total Stake (R)", min_value=100, value=500, step=100, key="dutch_total")
        
        if st.button("Calculate Dutching Stakes", key="calc_dutch"):
            implied_probs = [1/odds for odds in odds_list]
            total_implied = sum(implied_probs)
            
            stakes = [(dutch_total * (1/odds_list[i])) / total_implied for i in range(num_outcomes)]
            
            st.markdown("### 📊 Dutching Distribution")
            
            for i in range(num_outcomes):
                st.metric(f"Stake on {outcomes[i]}", f"R{stakes[i]:.2f}")
                st.metric(f"Payout if wins", f"R{stakes[i] * odds_list[i]:.2f}")
                st.metric(f"Profit if wins", f"R{(stakes[i] * odds_list[i]) - dutch_total:.2f}")
                st.divider()
            
            min_profit = min([(stakes[i] * odds_list[i]) - dutch_total for i in range(num_outcomes)])
            st.success(f"💰 **Minimum Guaranteed Profit:** R{min_profit:.2f}")
    
    # --- 9. LIVE SCORES ---
    st.divider()
    with st.expander("🏟️ Live Scores & Match Times (SAST)", expanded=False):
        if scores_data:
            for match in scores_data[:10]:
                home = match.get('home_team', 'Unknown')
                away = match.get('away_team', 'Unknown')
                commence_time = match.get('commence_time')
                
                match_time = format_match_time(commence_time) if commence_time else "Time TBD"
                score = "vs"
                if match.get('scores') and len(match['scores']) >= 2:
                    score = f"{match['scores'][0].get('score', 0)} - {match['scores'][1].get('score', 0)}"
                
                status = "🏁 FT" if match.get('completed') else ("🔴 LIVE" if match.get('scores') else "📅 Upcoming")
                
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
            st.write("No live data available")

else:
    st.warning("Unable to fetch odds data. Please check your connection.")

# --- 10. FOOTER ---
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
    <p>⚠️ Disclaimer: Hedge betting involves risk. Always verify odds before placing bets.</p>
    <p>💡 Tip: Use hedge betting to lock in profits or reduce risk on existing bets</p>
</div>
""", unsafe_allow_html=True)
