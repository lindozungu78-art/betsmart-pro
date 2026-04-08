import streamlit as st
import pandas as pd
import numpy as np
import math
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
import json

class BettingBacktest:
    def __init__(self, initial_bankroll=10000):
        self.initial_bankroll = initial_bankroll
        
    def get_team_stats(self):
        """Team statistics for probability calculations"""
        return {
            "Manchester City": {"attack": 92, "defense": 88, "home_advantage": 1.4},
            "Liverpool": {"attack": 89, "defense": 85, "home_advantage": 1.3},
            "Arsenal": {"attack": 86, "defense": 84, "home_advantage": 1.3},
            "Chelsea": {"attack": 82, "defense": 79, "home_advantage": 1.2},
            "Manchester United": {"attack": 80, "defense": 77, "home_advantage": 1.2},
            "Tottenham": {"attack": 83, "defense": 75, "home_advantage": 1.2},
            "Newcastle": {"attack": 78, "defense": 80, "home_advantage": 1.1},
            "Aston Villa": {"attack": 79, "defense": 72, "home_advantage": 1.1},
        }
    
    def calculate_xg(self, home_team, away_team, team_stats):
        """Calculate Expected Goals"""
        home_stats = team_stats.get(home_team, {"attack": 70, "defense": 70, "home_advantage": 1.0})
        away_stats = team_stats.get(away_team, {"attack": 70, "defense": 70, "home_advantage": 1.0})
        
        league_avg = 1.35
        home_xg = (home_stats['attack'] / 100) * (away_stats['defense'] / 100) * league_avg * home_stats['home_advantage']
        away_xg = (away_stats['attack'] / 100) * (home_stats['defense'] / 100) * league_avg
        
        return home_xg, away_xg
    
    def poisson_probability(self, actual, mean):
        """Calculate Poisson probability"""
        if mean <= 0:
            return 0
        return (math.exp(-mean) * mean ** actual) / math.factorial(actual)
    
    def calculate_match_probabilities(self, home_team, away_team, team_stats):
        """Calculate win/draw/loss probabilities"""
        try:
            home_xg, away_xg = self.calculate_xg(home_team, away_team, team_stats)
            
            max_goals = 8
            home_win_prob = 0
            draw_prob = 0
            away_win_prob = 0
            
            for i in range(max_goals + 1):
                for j in range(max_goals + 1):
                    prob = self.poisson_probability(i, home_xg) * self.poisson_probability(j, away_xg)
                    if i > j:
                        home_win_prob += prob
                    elif i == j:
                        draw_prob += prob
                    else:
                        away_win_prob += prob
            
            draw_prob = draw_prob * 0.92
            total = home_win_prob + draw_prob + away_win_prob
            
            if total > 0:
                home_win_prob = (home_win_prob / total) * 100
                draw_prob = (draw_prob / total) * 100
                away_win_prob = (away_win_prob / total) * 100
            else:
                home_win_prob = draw_prob = away_win_prob = 33.33
            
            return home_win_prob, draw_prob, away_win_prob
        except:
            return 33.33, 33.33, 33.33
    
    def calculate_expected_value(self, odds, probability):
        """Calculate Expected Value"""
        try:
            if odds <= 0 or probability <= 0:
                return -1
            return (odds * (probability / 100)) - 1
        except:
            return -1
    
    def kelly_criterion(self, odds, probability, bankroll):
        """Calculate Kelly stake"""
        try:
            b = odds - 1
            p = probability / 100
            q = 1 - p
            
            if b <= 0 or p <= 0 or p >= 1:
                return 0
            
            f = (p * b - q) / b
            # Use 25% Kelly for safety
            return max(0, min(f * 0.25 * bankroll, bankroll * 0.05))  # Max 5% of bankroll
        except:
            return 0
    
    def load_csv_data(self, uploaded_file):
        """Load and parse CSV file with flexible column mapping"""
        try:
            # Try different encodings
            for encoding in ['utf-8', 'latin1', 'iso-8859-1']:
                try:
                    df = pd.read_csv(uploaded_file, encoding=encoding)
                    break
                except:
                    continue
            
            # Look for required columns with flexible naming
            home_team_col = None
            away_team_col = None
            home_score_col = None
            away_score_col = None
            home_odds_col = None
            draw_odds_col = None
            away_odds_col = None
            
            # Column name mapping
            col_mapping = {
                'home_team': ['home', 'home team', 'home_team', 'hometeam', 'home club', 'home name'],
                'away_team': ['away', 'away team', 'away_team', 'awayteam', 'away club', 'away name'],
                'home_score': ['home_score', 'home score', 'homescore', 'home goals', 'hg'],
                'away_score': ['away_score', 'away score', 'awayscore', 'away goals', 'ag'],
                'home_odds': ['home_odds', 'home odds', 'homeodd', 'odd_h', 'b365h', 'b365 home'],
                'draw_odds': ['draw_odds', 'draw odds', 'drawodd', 'odd_d', 'b365d', 'b365 draw'],
                'away_odds': ['away_odds', 'away odds', 'awayodd', 'odd_a', 'b365a', 'b365 away']
            }
            
            for col in df.columns:
                col_lower = col.lower()
                for key, patterns in col_mapping.items():
                    if any(pattern in col_lower for pattern in patterns):
                        if key == 'home_team':
                            home_team_col = col
                        elif key == 'away_team':
                            away_team_col = col
                        elif key == 'home_score':
                            home_score_col = col
                        elif key == 'away_score':
                            away_score_col = col
                        elif key == 'home_odds':
                            home_odds_col = col
                        elif key == 'draw_odds':
                            draw_odds_col = col
                        elif key == 'away_odds':
                            away_odds_col = col
            
            # Create standardized dataframe
            matches = []
            for idx, row in df.iterrows():
                match = {}
                
                # Get team names
                if home_team_col:
                    match['home_team'] = str(row[home_team_col])
                if away_team_col:
                    match['away_team'] = str(row[away_team_col])
                
                # Get scores if available
                if home_score_col and away_score_col:
                    try:
                        match['home_score'] = int(row[home_score_col])
                        match['away_score'] = int(row[away_score_col])
                        if match['home_score'] > match['away_score']:
                            match['result'] = "HOME"
                        elif match['home_score'] == match['away_score']:
                            match['result'] = "DRAW"
                        else:
                            match['result'] = "AWAY"
                    except:
                        match['result'] = None
                
                # Get odds
                if home_odds_col:
                    match['home_odds'] = float(row[home_odds_col]) if pd.notna(row[home_odds_col]) else 2.0
                if draw_odds_col:
                    match['draw_odds'] = float(row[draw_odds_col]) if pd.notna(row[draw_odds_col]) else 3.2
                if away_odds_col:
                    match['away_odds'] = float(row[away_odds_col]) if pd.notna(row[away_odds_col]) else 2.0
                
                # Skip if missing essential data
                if 'home_team' in match and 'away_team' in match:
                    matches.append(match)
            
            return matches, df
        
        except Exception as e:
            st.error(f"Error loading file: {str(e)}")
            return [], None
    
    def simulate_strategy(self, matches, strategy_name, bankroll):
        """Simulate a specific betting strategy"""
        bets = []
        current_bankroll = bankroll
        
        for match in matches:
            bet = None
            
            if strategy_name == "Value Betting (EV > 5%)":
                bet = self.value_betting_strategy(match, current_bankroll, min_ev=5)
            elif strategy_name == "Value Betting (EV > 10%)":
                bet = self.value_betting_strategy(match, current_bankroll, min_ev=10)
            elif strategy_name == "Kelly Criterion":
                bet = self.kelly_strategy(match, current_bankroll)
            elif strategy_name == "Home Favorites":
                bet = self.home_favorites_strategy(match, current_bankroll)
            elif strategy_name == "Draw Specialists":
                bet = self.draw_specialists_strategy(match, current_bankroll)
            elif strategy_name == "Conservative (EV > 8% & 2% stake)":
                bet = self.conservative_strategy(match, current_bankroll)
            
            if bet:
                # Determine if bet won
                if 'result' in match and match['result']:
                    won = (bet['bet_type'] == match['result'])
                else:
                    # If no result data, assume loss
                    won = False
                
                if won:
                    profit = bet['stake'] * (bet['odds'] - 1)
                else:
                    profit = -bet['stake']
                
                current_bankroll += profit
                
                bets.append({
                    'home': match.get('home_team', 'Unknown'),
                    'away': match.get('away_team', 'Unknown'),
                    'bet_type': bet['bet_type'],
                    'odds': bet['odds'],
                    'stake': bet['stake'],
                    'won': won,
                    'profit': profit,
                    'ev': bet.get('ev', 0),
                    'bankroll_after': current_bankroll
                })
        
        return bets, current_bankroll
    
    def value_betting_strategy(self, match, bankroll, min_ev=5):
        """Bet when Expected Value exceeds threshold"""
        try:
            # Calculate probabilities
            team_stats = self.get_team_stats()
            home_prob, draw_prob, away_prob = self.calculate_match_probabilities(
                match.get('home_team', ''), 
                match.get('away_team', ''), 
                team_stats
            )
            
            # Calculate EV
            home_ev = self.calculate_expected_value(match.get('home_odds', 2.0), home_prob)
            draw_ev = self.calculate_expected_value(match.get('draw_odds', 3.2), draw_prob)
            away_ev = self.calculate_expected_value(match.get('away_odds', 2.0), away_prob)
            
            # Find best EV
            ev_dict = {'HOME': home_ev, 'DRAW': draw_ev, 'AWAY': away_ev}
            best_type = max(ev_dict, key=ev_dict.get)
            best_ev = ev_dict[best_type]
            
            if best_ev * 100 > min_ev:
                odds = match.get(f"{best_type.lower()}_odds", 2.0)
                stake = bankroll * 0.02  # 2% flat stake
                
                return {
                    'bet_type': best_type,
                    'odds': odds,
                    'stake': stake,
                    'ev': best_ev * 100
                }
            return None
        except:
            return None
    
    def kelly_strategy(self, match, bankroll):
        """Use Kelly Criterion for stake sizing"""
        try:
            team_stats = self.get_team_stats()
            home_prob, draw_prob, away_prob = self.calculate_match_probabilities(
                match.get('home_team', ''),
                match.get('away_team', ''),
                team_stats
            )
            
            home_ev = self.calculate_expected_value(match.get('home_odds', 2.0), home_prob)
            draw_ev = self.calculate_expected_value(match.get('draw_odds', 3.2), draw_prob)
            away_ev = self.calculate_expected_value(match.get('away_odds', 2.0), away_prob)
            
            ev_dict = {'HOME': home_ev, 'DRAW': draw_ev, 'AWAY': away_ev}
            best_type = max(ev_dict, key=ev_dict.get)
            best_ev = ev_dict[best_type]
            
            if best_ev > 0:
                odds = match.get(f"{best_type.lower()}_odds", 2.0)
                prob = home_prob if best_type == 'HOME' else (draw_prob if best_type == 'DRAW' else away_prob)
                stake = self.kelly_criterion(odds, prob, bankroll)
                
                if stake > 0:
                    return {
                        'bet_type': best_type,
                        'odds': odds,
                        'stake': stake,
                        'ev': best_ev * 100
                    }
            return None
        except:
            return None
    
    def home_favorites_strategy(self, match, bankroll):
        """Bet on strong home favorites"""
        try:
            team_stats = self.get_team_stats()
            home_prob, _, _ = self.calculate_match_probabilities(
                match.get('home_team', ''),
                match.get('away_team', ''),
                team_stats
            )
            
            home_odds = match.get('home_odds', 2.0)
            home_ev = self.calculate_expected_value(home_odds, home_prob)
            
            if home_prob > 55 and home_odds < 1.8 and home_ev > 0.02:
                stake = bankroll * 0.03
                return {
                    'bet_type': "HOME",
                    'odds': home_odds,
                    'stake': stake,
                    'ev': home_ev * 100
                }
            return None
        except:
            return None
    
    def draw_specialists_strategy(self, match, bankroll):
        """Specialized strategy for draws"""
        try:
            team_stats = self.get_team_stats()
            _, draw_prob, _ = self.calculate_match_probabilities(
                match.get('home_team', ''),
                match.get('away_team', ''),
                team_stats
            )
            
            draw_odds = match.get('draw_odds', 3.2)
            draw_ev = self.calculate_expected_value(draw_odds, draw_prob)
            
            if draw_prob > 30 and draw_odds > 3.0 and draw_ev > 0.05:
                stake = bankroll * 0.02
                return {
                    'bet_type': "DRAW",
                    'odds': draw_odds,
                    'stake': stake,
                    'ev': draw_ev * 100
                }
            return None
        except:
            return None
    
    def conservative_strategy(self, match, bankroll):
        """Conservative strategy with higher EV threshold"""
        try:
            team_stats = self.get_team_stats()
            home_prob, draw_prob, away_prob = self.calculate_match_probabilities(
                match.get('home_team', ''),
                match.get('away_team', ''),
                team_stats
            )
            
            home_ev = self.calculate_expected_value(match.get('home_odds', 2.0), home_prob)
            draw_ev = self.calculate_expected_value(match.get('draw_odds', 3.2), draw_prob)
            away_ev = self.calculate_expected_value(match.get('away_odds', 2.0), away_prob)
            
            ev_dict = {'HOME': home_ev, 'DRAW': draw_ev, 'AWAY': away_ev}
            best_type = max(ev_dict, key=ev_dict.get)
            best_ev = ev_dict[best_type]
            
            if best_ev * 100 > 8:  # Higher threshold
                odds = match.get(f"{best_type.lower()}_odds", 2.0)
                stake = bankroll * 0.015  # Lower stake
                
                return {
                    'bet_type': best_type,
                    'odds': odds,
                    'stake': stake,
                    'ev': best_ev * 100
                }
            return None
        except:
            return None
    
    def calculate_statistics(self, bets, final_bankroll):
        """Calculate performance metrics"""
        if not bets:
            return {
                'total_bets': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'total_profit': 0,
                'total_staked': 0,
                'roi': 0,
                'final_bankroll': final_bankroll,
                'total_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'avg_odds': 0,
                'avg_ev': 0
            }
        
        total_bets = len(bets)
        wins = sum(1 for bet in bets if bet['won'])
        losses = total_bets - wins
        win_rate = (wins / total_bets) * 100 if total_bets > 0 else 0
        
        total_staked = sum(bet['stake'] for bet in bets)
        total_profit = sum(bet['profit'] for bet in bets)
        roi = (total_profit / total_staked) * 100 if total_staked > 0 else 0
        
        # Calculate Sharpe Ratio
        returns = [bet['profit'] / bet['stake'] if bet['stake'] > 0 else 0 for bet in bets]
        sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        
        # Calculate Maximum Drawdown
        cumulative_profit = 0
        peak = 0
        max_drawdown = 0
        
        for bet in bets:
            cumulative_profit += bet['profit']
            if cumulative_profit > peak:
                peak = cumulative_profit
            drawdown = (peak - cumulative_profit) / self.initial_bankroll * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        avg_odds = np.mean([bet['odds'] for bet in bets])
        avg_ev = np.mean([bet['ev'] for bet in bets])
        
        return {
            'total_bets': total_bets,
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 2),
            'total_profit': round(total_profit, 2),
            'total_staked': round(total_staked, 2),
            'roi': round(roi, 2),
            'final_bankroll': round(final_bankroll, 2),
            'total_return': round(((final_bankroll - self.initial_bankroll) / self.initial_bankroll) * 100, 2),
            'sharpe_ratio': round(sharpe_ratio, 3),
            'max_drawdown': round(max_drawdown, 2),
            'avg_odds': round(avg_odds, 2),
            'avg_ev': round(avg_ev, 2)
        }

# Streamlit UI for backtesting
def run_backtest_ui():
    st.set_page_config(page_title="BetSmart Backtest Engine", layout="wide")
    
    st.title("📊 BetSmart Backtesting Engine")
    st.markdown("Test betting strategies against historical football data")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        initial_bankroll = st.number_input("Initial Bankroll (R)", value=10000, step=1000)
        
        st.header("📁 Upload Data")
        uploaded_file = st.file_uploader(
            "Upload CSV/Excel file", 
            type=['csv', 'xlsx', 'xls', 'txt'],
            help="Upload football match data with odds and results"
        )
        
        st.markdown("""
        **Supported column names:**
        - Home team: `home`, `home team`, `home_team`
        - Away team: `away`, `away team`, `away_team`
        - Scores: `home_score`, `away_score`, `home goals`, `away goals`
        - Odds: `home_odds`, `draw_odds`, `away_odds`, `B365H`, `B365D`, `B365A`
        """)
        
        st.info("💡 The system will automatically detect column names")
    
    if uploaded_
