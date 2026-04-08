# backtest.py
import streamlit as st
import pandas as pd
import numpy as np
import math
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Simple team statistics
TEAM_STATS = {
    "Manchester City": {"attack": 92, "defense": 88, "home_adv": 1.4},
    "Liverpool": {"attack": 89, "defense": 85, "home_adv": 1.3},
    "Arsenal": {"attack": 86, "defense": 84, "home_adv": 1.3},
    "Chelsea": {"attack": 82, "defense": 79, "home_adv": 1.2},
    "Manchester United": {"attack": 80, "defense": 77, "home_adv": 1.2},
    "Tottenham": {"attack": 83, "defense": 75, "home_adv": 1.2},
    "Newcastle": {"attack": 78, "defense": 80, "home_adv": 1.1},
    "Aston Villa": {"attack": 79, "defense": 72, "home_adv": 1.1},
    "Brighton": {"attack": 76, "defense": 74, "home_adv": 1.1},
    "West Ham": {"attack": 74, "defense": 71, "home_adv": 1.1},
    "Brentford": {"attack": 73, "defense": 70, "home_adv": 1.0},
    "Fulham": {"attack": 71, "defense": 69, "home_adv": 1.0},
    "Crystal Palace": {"attack": 70, "defense": 68, "home_adv": 1.0},
    "Wolves": {"attack": 69, "defense": 67, "home_adv": 1.0},
    "Everton": {"attack": 67, "defense": 69, "home_adv": 1.0},
    "Nottingham": {"attack": 66, "defense": 68, "home_adv": 0.9},
    "Bournemouth": {"attack": 68, "defense": 65, "home_adv": 0.9},
    "Leicester": {"attack": 69, "defense": 66, "home_adv": 0.9}
}

def get_team_stats(team_name):
    """Get team stats with default values"""
    for key in TEAM_STATS:
        if key.lower() in team_name.lower():
            return TEAM_STATS[key]
    return {"attack": 70, "defense": 70, "home_adv": 1.0}

def calculate_probabilities(home_team, away_team):
    """Calculate match probabilities using simple method"""
    home_stats = get_team_stats(home_team)
    away_stats = get_team_stats(away_team)
    
    # Calculate expected goals
    home_xg = (home_stats['attack'] / 100) * (away_stats['defense'] / 100) * 1.35 * home_stats['home_adv']
    away_xg = (away_stats['attack'] / 100) * (home_stats['defense'] / 100) * 1.35
    
    # Simple probability estimation
    total_goals = home_xg + away_xg
    if total_goals > 0:
        home_prob = (home_xg / total_goals) * 60  # Base 60% for home advantage
        away_prob = (away_xg / total_goals) * 40
    else:
        home_prob = 50
        away_prob = 30
    
    draw_prob = 100 - home_prob - away_prob
    
    # Adjust for reasonability
    home_prob = max(20, min(70, home_prob))
    draw_prob = max(15, min(35, draw_prob))
    away_prob = max(15, min(50, away_prob))
    
    # Normalize
    total = home_prob + draw_prob + away_prob
    home_prob = (home_prob / total) * 100
    draw_prob = (draw_prob / total) * 100
    away_prob = (away_prob / total) * 100
    
    return home_prob, draw_prob, away_prob

def calculate_ev(odds, probability):
    """Calculate Expected Value"""
    if odds <= 0 or probability <= 0:
        return -1
    return (odds * (probability / 100)) - 1

def kelly_stake(odds, probability, bankroll):
    """Calculate Kelly stake"""
    try:
        b = odds - 1
        p = probability / 100
        q = 1 - p
        
        if b <= 0 or p <= 0 or p >= 1:
            return 0
        
        f = (p * b - q) / b
        # Use 20% Kelly for safety, max 5% of bankroll
        return min(max(0, f * 0.2 * bankroll), bankroll * 0.05)
    except:
        return 0

def load_csv_data(uploaded_file):
    """Load CSV with flexible column detection"""
    try:
        # Try different encodings
        df = None
        for encoding in ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']:
            try:
                df = pd.read_csv(uploaded_file, encoding=encoding)
                break
            except:
                continue
        
        if df is None:
            return [], None
        
        # Column detection
        home_col = None
        away_col = None
        home_score_col = None
        away_score_col = None
        home_odds_col = None
        draw_odds_col = None
        away_odds_col = None
        
        # Check each column
        for col in df.columns:
            col_lower = col.lower()
            if any(word in col_lower for word in ['home', 'hometeam', 'home_team', 'home team']):
                home_col = col
            elif any(word in col_lower for word in ['away', 'awayteam', 'away_team', 'away team']):
                away_col = col
            elif any(word in col_lower for word in ['home_score', 'homescore', 'home goals', 'hg']):
                home_score_col = col
            elif any(word in col_lower for word in ['away_score', 'awayscore', 'away goals', 'ag']):
                away_score_col = col
            elif any(word in col_lower for word in ['home_odds', 'homeodds', 'odd_h', 'b365h']):
                home_odds_col = col
            elif any(word in col_lower for word in ['draw_odds', 'drawodds', 'odd_d', 'b365d']):
                draw_odds_col = col
            elif any(word in col_lower for word in ['away_odds', 'awayodds', 'odd_a', 'b365a']):
                away_odds_col = col
        
        # Process matches
        matches = []
        for idx, row in df.iterrows():
            match = {}
            
            # Get team names
            if home_col:
                match['home'] = str(row[home_col])
            if away_col:
                match['away'] = str(row[away_col])
            
            # Get scores
            if home_score_col and away_score_col:
                try:
                    home_score = float(row[home_score_col]) if pd.notna(row[home_score_col]) else None
                    away_score = float(row[away_score_col]) if pd.notna(row[away_score_col]) else None
                    if home_score is not None and away_score is not None:
                        match['home_score'] = int(home_score)
                        match['away_score'] = int(away_score)
                        if match['home_score'] > match['away_score']:
                            match['result'] = 'HOME'
                        elif match['home_score'] == match['away_score']:
                            match['result'] = 'DRAW'
                        else:
                            match['result'] = 'AWAY'
                except:
                    pass
            
            # Get odds
            if home_odds_col:
                match['home_odds'] = float(row[home_odds_col]) if pd.notna(row[home_odds_col]) else 2.0
            if draw_odds_col:
                match['draw_odds'] = float(row[draw_odds_col]) if pd.notna(row[draw_odds_col]) else 3.2
            if away_odds_col:
                match['away_odds'] = float(row[away_odds_col]) if pd.notna(row[away_odds_col]) else 2.0
            
            # Only add if we have teams
            if 'home' in match and 'away' in match:
                # Add default odds if missing
                if 'home_odds' not in match:
                    match['home_odds'] = 2.0
                if 'draw_odds' not in match:
                    match['draw_odds'] = 3.2
                if 'away_odds' not in match:
                    match['away_odds'] = 2.0
                matches.append(match)
        
        return matches, df
    
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return [], None

def run_strategy(matches, strategy_name, bankroll):
    """Run a single betting strategy"""
    bets = []
    current_bankroll = bankroll
    
    for match in matches:
        bet = None
        
        # Calculate probabilities
        home_prob, draw_prob, away_prob = calculate_probabilities(match['home'], match['away'])
        
        # Calculate EVs
        home_ev = calculate_ev(match.get('home_odds', 2.0), home_prob)
        draw_ev = calculate_ev(match.get('draw_odds', 3.2), draw_prob)
        away_ev = calculate_ev(match.get('away_odds', 2.0), away_prob)
        
        if strategy_name == "Value Betting (EV > 5%)":
            if home_ev > 0.05:
                bet = {'type': 'HOME', 'odds': match['home_odds'], 'ev': home_ev, 'stake_pct': 0.02}
            elif draw_ev > 0.05:
                bet = {'type': 'DRAW', 'odds': match['draw_odds'], 'ev': draw_ev, 'stake_pct': 0.02}
            elif away_ev > 0.05:
                bet = {'type': 'AWAY', 'odds': match['away_odds'], 'ev': away_ev, 'stake_pct': 0.02}
        
        elif strategy_name == "Value Betting (EV > 10%)":
            if home_ev > 0.10:
                bet = {'type': 'HOME', 'odds': match['home_odds'], 'ev': home_ev, 'stake_pct': 0.02}
            elif draw_ev > 0.10:
                bet = {'type': 'DRAW', 'odds': match['draw_odds'], 'ev': draw_ev, 'stake_pct': 0.02}
            elif away_ev > 0.10:
                bet = {'type': 'AWAY', 'odds': match['away_odds'], 'ev': away_ev, 'stake_pct': 0.02}
        
        elif strategy_name == "Kelly Criterion":
            evs = {'HOME': home_ev, 'DRAW': draw_ev, 'AWAY': away_ev}
            best_type = max(evs, key=evs.get)
            best_ev = evs[best_type]
            if best_ev > 0:
                odds = match[f"{best_type.lower()}_odds"]
                prob = home_prob if best_type == 'HOME' else (draw_prob if best_type == 'DRAW' else away_prob)
                stake_amount = kelly_stake(odds, prob, current_bankroll)
                if stake_amount > 0:
                    bet = {'type': best_type, 'odds': odds, 'ev': best_ev, 'stake_amount': stake_amount}
        
        elif strategy_name == "Home Favorites":
            if home_prob > 55 and match['home_odds'] < 1.8 and home_ev > 0.02:
                bet = {'type': 'HOME', 'odds': match['home_odds'], 'ev': home_ev, 'stake_pct': 0.03}
        
        elif strategy_name == "Draw Specialists":
            if draw_prob > 30 and match['draw_odds'] > 3.0 and draw_ev > 0.05:
                bet = {'type': 'DRAW', 'odds': match['draw_odds'], 'ev': draw_ev, 'stake_pct': 0.02}
        
        # Place bet if we have one
        if bet:
            # Calculate stake
            if 'stake_amount' in bet:
                stake = bet['stake_amount']
            else:
                stake = current_bankroll * bet['stake_pct']
            
            # Check if bet won
            won = False
            if 'result' in match:
                won = (bet['type'] == match['result'])
            
            if won:
                profit = stake * (bet['odds'] - 1)
            else:
                profit = -stake
            
            current_bankroll += profit
            
            bets.append({
                'match': f"{match['home']} vs {match['away']}",
                'bet': bet['type'],
                'odds': bet['odds'],
                'stake': stake,
                'won': won,
                'profit': profit,
                'ev': bet['ev'] * 100,
                'bankroll': current_bankroll
            })
    
    return bets, current_bankroll

def calculate_stats(bets, initial_bankroll, final_bankroll):
    """Calculate performance statistics"""
    if not bets:
        return {
            'total_bets': 0, 'wins': 0, 'losses': 0, 'win_rate': 0,
            'total_profit': 0, 'total_staked': 0, 'roi': 0,
            'total_return': 0, 'max_drawdown': 0, 'avg_odds': 0, 'avg_ev': 0
        }
    
    total_bets = len(bets)
    wins = sum(1 for b in bets if b['won'])
    losses = total_bets - wins
    win_rate = (wins / total_bets) * 100
    
    total_staked = sum(b['stake'] for b in bets)
    total_profit = sum(b['profit'] for b in bets)
    roi = (total_profit / total_staked) * 100 if total_staked > 0 else 0
    total_return = ((final_bankroll - initial_bankroll) / initial_bankroll) * 100
    
    # Calculate max drawdown
    cumulative = 0
    peak = 0
    max_dd = 0
    for bet in bets:
        cumulative += bet['profit']
        if cumulative > peak:
            peak = cumulative
        dd = (peak - cumulative) / initial_bankroll * 100
        if dd > max_dd:
            max_dd = dd
    
    avg_odds = sum(b['odds'] for b in bets) / total_bets if total_bets > 0 else 0
    avg_ev = sum(b['ev'] for b in bets) / total_bets if total_bets > 0 else 0
    
    return {
        'total_bets': total_bets,
        'wins': wins,
        'losses': losses,
        'win_rate': round(win_rate, 1),
        'total_profit': round(total_profit, 2),
        'total_staked': round(total_staked, 2),
        'roi': round(roi, 1),
        'total_return': round(total_return, 1),
        'max_drawdown': round(max_dd, 1),
        'avg_odds': round(avg_odds, 2),
        'avg_ev': round(avg_ev, 1)
    }

# Main Streamlit App
def main():
    st.set_page_config(page_title="BetSmart Backtest", layout="wide")
    
    st.title("📊 BetSmart Backtesting Engine")
    st.markdown("Test betting strategies against historical football data")
    
    # Sidebar
    with st.sidebar:
        st.header("💰 Settings")
        initial_bankroll = st.number_input("Initial Bankroll (R)", value=10000, step=1000, key="bankroll")
        
        st.header("📁 Upload Data")
        uploaded_file = st.file_uploader(
            "Choose CSV file",
            type=['csv'],
            help="Upload CSV with match data"
        )
        
        st.markdown("---")
        st.markdown("### Expected Columns")
        st.markdown("""
        - **Home team** (home, home_team, hometeam)
        - **Away team** (away, away_team, awayteam)
        - **Odds** (home_odds, draw_odds, away_odds)
        - **Scores** (optional: home_score, away_score)
        """)
    
    if uploaded_file:
        with st.spinner("Loading data..."):
            matches, df = load_csv_data(uploaded_file)
        
        if matches:
            st.success(f"✅ Loaded {len(matches)} matches")
            
            # Show preview
            with st.expander("Preview Data"):
                st.dataframe(df.head(10))
            
            # Select strategies
            st.subheader("🎯 Select Strategies to Test")
            strategies = st.multiselect(
                "Choose strategies:",
                [
                    "Value Betting (EV > 5%)",
                    "Value Betting (EV > 10%)",
                    "Kelly Criterion",
                    "Home Favorites",
                    "Draw Specialists"
                ],
                default=["Value Betting (EV > 5%)", "Kelly Criterion"]
            )
            
            if st.button("🚀 Run Backtest", type="primary"):
                results = {}
                all_bets = {}
                
                progress = st.progress(0)
                
                for i, strategy in enumerate(strategies):
                    bets, final_bankroll = run_strategy(matches, strategy, initial_bankroll)
                    stats = calculate_stats(bets, initial_bankroll, final_bankroll)
                    results[strategy] = stats
                    all_bets[strategy] = bets
                    progress.progress((i + 1) / len(strategies))
                
                # Display results
                st.success("✅ Backtest Complete!")
                
                # Results table
                st.subheader("📈 Results Summary")
                results_df = pd.DataFrame(results).T
                display_cols = ['total_bets', 'wins', 'win_rate', 'total_profit', 'roi', 'total_return', 'max_drawdown', 'avg_ev']
                results_df = results_df[display_cols]
                results_df.columns = ['Bets', 'Wins', 'Win%', 'Profit(R)', 'ROI%', 'Return%', 'MaxDD%', 'AvgEV%']
                st.dataframe(results_df, use_container_width=True)
                
                # Best strategy
                best = max(results.items(), key=lambda x: x[1]['total_profit'])
                st.info(f"🏆 **Best Strategy: {best[0]}** - Profit: R{best[1]['total_profit']:,.2f} (ROI: {best[1]['roi']}%)")
                
                # Charts
                st.subheader("📊 Performance Charts")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Cumulative profit chart
                    fig1 = go.Figure()
                    for strategy in strategies:
                        if all_bets[strategy]:
                            cumulative = np.cumsum([b['profit'] for b in all_bets[strategy]])
                            fig1.add_trace(go.Scatter(y=cumulative, name=strategy, mode='lines'))
                    fig1.update_layout(title="Cumulative Profit", xaxis_title="Bet Number", yaxis_title="Profit (R)")
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    # Win rates
                    fig2 = go.Figure()
                    fig2.add_trace(go.Bar(x=list(results.keys()), y=[r['win_rate'] for r in results.values()]))
                    fig2.update_layout(title="Win Rate by Strategy", xaxis_title="Strategy", yaxis_title="Win Rate (%)")
                    st.plotly_chart(fig2, use_container_width=True)
                
                # ROI comparison
                fig3 = go.Figure()
                rois = [r['roi'] for r in results.values()]
                colors = ['green' if r > 0 else 'red' for r in rois]
                fig3.add_trace(go.Bar(x=list(results.keys()), y=rois, marker_color=colors))
                fig3.update_layout(title="ROI by Strategy", xaxis_title="Strategy", yaxis_title="ROI (%)")
                st.plotly_chart(fig3, use_container_width=True)
                
                # Detailed bet log
                st.subheader("📝 Detailed Bet Log")
                for strategy in strategies:
                    if all_bets[strategy]:
                        with st.expander(f"{strategy} - {len(all_bets[strategy])} bets"):
                            bet_df = pd.DataFrame(all_bets[strategy])
                            bet_df = bet_df[['match', 'bet', 'odds', 'stake', 'won', 'profit', 'ev']]
                            bet_df['won'] = bet_df['won'].apply(lambda x: '✅' if x else '❌')
                            st.dataframe(bet_df, use_container_width=True)
                
                # Recommendations
                st.subheader("💡 Recommendations")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    best_roi = max(results.items(), key=lambda x: x[1]['roi'])
                    st.metric("Best ROI", f"{best_roi[1]['roi']}%", best_roi[0])
                
                with col2:
                    best_winrate = max(results.items(), key=lambda x: x[1]['win_rate'])
                    st.metric("Best Win Rate", f"{best_winrate[1]['win_rate']}%", best_winrate[0])
                
                with col3:
                    lowest_risk = min(results.items(), key=lambda x: x[1]['max_drawdown'])
                    st.metric("Lowest Risk", f"{lowest_risk[1]['max_drawdown']}% DD", lowest_risk[0])
                
        else:
            st.error("Could not parse the file. Please check column names.")
    
    else:
        st.info("👈 Upload a CSV file to start backtesting")
        
        # Sample template
        with st.expander("📄 Sample CSV Format"):
            sample_data = {
                'home_team': ['Arsenal', 'Liverpool', 'Manchester City'],
                'away_team': ['Chelsea', 'Tottenham', 'Manchester United'],
                'home_score': [2, 1, 3],
                'away_score': [1, 1, 1],
                'home_odds': [2.10, 1.80, 1.65],
                'draw_odds': [3.40, 3.50, 3.80],
                'away_odds': [3.20, 4.00, 4.50]
            }
            sample_df = pd.DataFrame(sample_data)
            st.dataframe(sample_df)
            st.caption("Note: Column names are flexible - the system will auto-detect them")

if __name__ == "__main__":
    main()
