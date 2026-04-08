# backtest.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import json
import math
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# ==================== BACKTESTING ENGINE ====================

class BettingBacktest:
    def __init__(self, initial_bankroll=10000):
        self.initial_bankroll = initial_bankroll
        self.current_bankroll = initial_bankroll
        self.bets_placed = []
        self.results = []
        
    # Team statistics cache
    def get_team_stats(self):
        return {
            "Manchester City": {"attack": 92, "defense": 88, "form": 9.2, "home_advantage": 1.4},
            "Liverpool": {"attack": 89, "defense": 85, "form": 8.7, "home_advantage": 1.3},
            "Arsenal": {"attack": 86, "defense": 84, "form": 8.5, "home_advantage": 1.3},
            "Chelsea": {"attack": 82, "defense": 79, "form": 7.8, "home_advantage": 1.2},
            "Manchester United": {"attack": 80, "defense": 77, "form": 7.5, "home_advantage": 1.2},
            "Tottenham": {"attack": 83, "defense": 75, "form": 7.7, "home_advantage": 1.2},
            "Newcastle": {"attack": 78, "defense": 80, "form": 7.9, "home_advantage": 1.1},
            "Aston Villa": {"attack": 79, "defense": 72, "form": 7.4, "home_advantage": 1.1},
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
        if mean == 0:
            return 0
        return (math.exp(-mean) * mean ** actual) / math.factorial(actual)
    
    def calculate_match_probabilities(self, home_team, away_team, team_stats):
        """Calculate win/draw/loss probabilities"""
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
    
    def calculate_expected_value(self, odds, probability):
        """Calculate Expected Value"""
        if odds <= 0 or probability <= 0:
            return -1
        return (odds * (probability / 100)) - 1
    
    def kelly_criterion(self, odds, probability, bankroll):
        """Calculate Kelly stake"""
        b = odds - 1
        p = probability / 100
        q = 1 - p
        
        if b <= 0 or p <= 0 or p >= 1:
            return 0
        
        f = (p * b - q) / b
        # Use 25% Kelly for safety
        return max(0, f * 0.25 * bankroll)
    
    def fetch_historical_odds(self, days_back=90):
        """Fetch historical match data from API"""
        try:
            # Using The Odds API for historical data
            # Note: You'll need to implement actual historical data fetching
            # For demonstration, we'll create synthetic historical data
            
            team_stats = self.get_team_stats()
            teams = list(team_stats.keys())
            historical_matches = []
            
            # Generate synthetic historical data for backtesting
            np.random.seed(42)
            
            for _ in range(200):  # 200 historical matches
                home = np.random.choice(teams)
                away = np.random.choice([t for t in teams if t != home])
                
                # Calculate true probabilities
                h_prob, d_prob, a_prob = self.calculate_match_probabilities(home, away, team_stats)
                
                # Generate market odds (slightly inefficient)
                h_odds = (1 / (h_prob/100)) * np.random.uniform(0.92, 1.05)
                d_odds = (1 / (d_prob/100)) * np.random.uniform(0.94, 1.08)
                a_odds = (1 / (a_prob/100)) * np.random.uniform(0.92, 1.05)
                
                # Determine actual result based on true probabilities
                result_rand = np.random.random() * 100
                if result_rand < h_prob:
                    result = "HOME"
                elif result_rand < h_prob + d_prob:
                    result = "DRAW"
                else:
                    result = "AWAY"
                
                # Create match record
                match = {
                    "date": datetime.now() - timedelta(days=np.random.randint(1, days_back)),
                    "home_team": home,
                    "away_team": away,
                    "home_odds": round(h_odds, 2),
                    "draw_odds": round(d_odds, 2),
                    "away_odds": round(a_odds, 2),
                    "true_home_prob": h_prob,
                    "true_draw_prob": d_prob,
                    "true_away_prob": a_prob,
                    "actual_result": result,
                    "home_score": np.random.poisson(h_prob/30),
                    "away_score": np.random.poisson(a_prob/30)
                }
                historical_matches.append(match)
            
            return historical_matches
        
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return []
    
    def simulate_betting_strategies(self, historical_matches):
        """Test different betting strategies"""
        
        strategies = {
            "Value Betting (EV > 5%)": self.value_betting_strategy,
            "Kelly Criterion": self.kelly_strategy,
            "Home Favorites": self.home_favorites_strategy,
            "Draw Specialists": self.draw_specialists_strategy,
            "Conservative Value (EV > 10%)": lambda m, b: self.value_betting_strategy(m, b, min_ev=10)
        }
        
        results = {}
        
        for strategy_name, strategy_func in strategies.items():
            print(f"\nTesting: {strategy_name}")
            bankroll = self.initial_bankroll
            bets_log = []
            
            for match in historical_matches:
                bet_info = strategy_func(match, bankroll)
                if bet_info:
                    stake = bet_info['stake']
                    odds = bet_info['odds']
                    bet_type = bet_info['bet_type']
                    
                    # Determine if bet won
                    if bet_type == "HOME" and match['actual_result'] == "HOME":
                        profit = stake * (odds - 1)
                        won = True
                    elif bet_type == "DRAW" and match['actual_result'] == "DRAW":
                        profit = stake * (odds - 1)
                        won = True
                    elif bet_type == "AWAY" and match['actual_result'] == "AWAY":
                        profit = stake * (odds - 1)
                        won = True
                    else:
                        profit = -stake
                        won = False
                    
                    bankroll += profit
                    
                    bets_log.append({
                        'match': f"{match['home_team']} vs {match['away_team']}",
                        'bet_type': bet_type,
                        'odds': odds,
                        'stake': stake,
                        'won': won,
                        'profit': profit,
                        'bankroll_after': bankroll
                    })
            
            # Calculate statistics
            results[strategy_name] = self.calculate_statistics(bets_log, bankroll)
            results[strategy_name]['bets_log'] = bets_log
        
        return results
    
    def value_betting_strategy(self, match, bankroll, min_ev=5):
        """Bet only when Expected Value > min_ev%"""
        home_ev = self.calculate_expected_value(match['home_odds'], match['true_home_prob'])
        draw_ev = self.calculate_expected_value(match['draw_odds'], match['true_draw_prob'])
        away_ev = self.calculate_expected_value(match['away_odds'], match['true_away_prob'])
        
        best_ev = max(home_ev, draw_ev, away_ev)
        best_ev_pct = best_ev * 100
        
        if best_ev_pct > min_ev:
            if best_ev == home_ev:
                bet_type = "HOME"
                odds = match['home_odds']
            elif best_ev == draw_ev:
                bet_type = "DRAW"
                odds = match['draw_odds']
            else:
                bet_type = "AWAY"
                odds = match['away_odds']
            
            # Use 2% of bankroll for value bets
            stake = bankroll * 0.02
            
            return {
                'bet_type': bet_type,
                'odds': odds,
                'stake': stake,
                'ev': best_ev_pct
            }
        return None
    
    def kelly_strategy(self, match, bankroll):
        """Use Kelly Criterion for stake sizing"""
        home_ev = self.calculate_expected_value(match['home_odds'], match['true_home_prob'])
        draw_ev = self.calculate_expected_value(match['draw_odds'], match['true_draw_prob'])
        away_ev = self.calculate_expected_value(match['away_odds'], match['true_away_prob'])
        
        best_ev = max(home_ev, draw_ev, away_ev)
        
        if best_ev > 0:
            if best_ev == home_ev:
                bet_type = "HOME"
                odds = match['home_odds']
                prob = match['true_home_prob']
            elif best_ev == draw_ev:
                bet_type = "DRAW"
                odds = match['draw_odds']
                prob = match['true_draw_prob']
            else:
                bet_type = "AWAY"
                odds = match['away_odds']
                prob = match['true_away_prob']
            
            stake = self.kelly_criterion(odds, prob, bankroll)
            
            if stake > 0:
                return {
                    'bet_type': bet_type,
                    'odds': odds,
                    'stake': stake,
                    'ev': best_ev * 100
                }
        return None
    
    def home_favorites_strategy(self, match, bankroll):
        """Bet on home teams with >55% probability and positive EV"""
        if match['true_home_prob'] > 55 and match['home_odds'] < 1.8:
            home_ev = self.calculate_expected_value(match['home_odds'], match['true_home_prob'])
            if home_ev > 0.02:
                stake = bankroll * 0.03  # 3% of bankroll
                return {
                    'bet_type': "HOME",
                    'odds': match['home_odds'],
                    'stake': stake,
                    'ev': home_ev * 100
                }
        return None
    
    def draw_specialists_strategy(self, match, bankroll):
        """Specialized strategy for draw betting"""
        if match['true_draw_prob'] > 30 and match['draw_odds'] > 3.0:
            draw_ev = self.calculate_expected_value(match['draw_odds'], match['true_draw_prob'])
            if draw_ev > 0.05:
                stake = bankroll * 0.02
                return {
                    'bet_type': "DRAW",
                    'odds': match['draw_odds'],
                    'stake': stake,
                    'ev': draw_ev * 100
                }
        return None
    
    def calculate_statistics(self, bets_log, final_bankroll):
        """Calculate performance metrics"""
        if not bets_log:
            return {
                'total_bets': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'total_profit': 0,
                'roi': 0,
                'final_bankroll': final_bankroll,
                'sharpe_ratio': 0,
                'max_drawdown': 0
            }
        
        total_bets = len(bets_log)
        wins = sum(1 for bet in bets_log if bet['won'])
        losses = total_bets - wins
        win_rate = (wins / total_bets) * 100 if total_bets > 0 else 0
        
        total_staked = sum(bet['stake'] for bet in bets_log)
        total_profit = sum(bet['profit'] for bet in bets_log)
        roi = (total_profit / total_staked) * 100 if total_staked > 0 else 0
        
        # Calculate Sharpe Ratio
        returns = [bet['profit'] / bet['stake'] if bet['stake'] > 0 else 0 for bet in bets_log]
        sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        
        # Calculate Maximum Drawdown
        cumulative_profit = 0
        peak = 0
        max_drawdown = 0
        
        for bet in bets_log:
            cumulative_profit += bet['profit']
            if cumulative_profit > peak:
                peak = cumulative_profit
            drawdown = (peak - cumulative_profit) / self.initial_bankroll * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
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
            'max_drawdown': round(max_drawdown, 2)
        }
    
    def generate_report(self, results):
        """Generate detailed backtest report"""
        print("\n" + "="*80)
        print("BACKTEST REPORT - BETTING STRATEGY PERFORMANCE")
        print("="*80)
        print(f"Initial Bankroll: R{self.initial_bankroll:,.2f}")
        print(f"Test Period: Last 200 Matches\n")
        
        # Create comparison dataframe
        comparison = []
        for strategy, stats in results.items():
            comparison.append({
                'Strategy': strategy,
                'Total Bets': stats['total_bets'],
                'Win Rate': f"{stats['win_rate']}%",
                'Total Profit': f"R{stats['total_profit']:,.2f}",
                'ROI': f"{stats['roi']}%",
                'Final Bankroll': f"R{stats['final_bankroll']:,.2f}",
                'Total Return': f"{stats['total_return']}%",
                'Sharpe Ratio': stats['sharpe_ratio'],
                'Max DD': f"{stats['max_drawdown']}%"
            })
        
        df_results = pd.DataFrame(comparison)
        print(df_results.to_string(index=False))
        
        # Best performing strategy
        print("\n" + "="*80)
        print("BEST PERFORMING STRATEGY")
        print("="*80)
        
        best_strategy = max(results.items(), key=lambda x: x[1]['total_profit'])
        print(f"🏆 {best_strategy[0]}")
        print(f"   Total Profit: R{best_strategy[1]['total_profit']:,.2f}")
        print(f"   ROI: {best_strategy[1]['roi']}%")
        print(f"   Win Rate: {best_strategy[1]['win_rate']}%")
        print(f"   Sharpe Ratio: {best_strategy[1]['sharpe_ratio']}")
        
        # Risk metrics
        print("\n" + "="*80)
        print("RISK METRICS")
        print("="*80)
        
        for strategy, stats in results.items():
            print(f"\n{strategy}:")
            print(f"   Max Drawdown: {stats['max_drawdown']}%")
            print(f"   Sharpe Ratio: {stats['sharpe_ratio']}")
            print(f"   Risk/Reward: {stats['roi'] / stats['max_drawdown'] if stats['max_drawdown'] > 0 else 0:.2f}")
        
        return df_results
    
    def plot_performance(self, results):
        """Create performance visualization"""
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            
            # 1. Cumulative Profit by Strategy
            ax1 = axes[0, 0]
            for strategy, stats in results.items():
                if 'bets_log' in stats and stats['bets_log']:
                    cumulative = np.cumsum([bet['profit'] for bet in stats['bets_log']])
                    ax1.plot(cumulative, label=strategy[:20])
            ax1.set_xlabel('Bet Number')
            ax1.set_ylabel('Cumulative Profit (R)')
            ax1.set_title('Strategy Performance Comparison')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 2. Win Rates
            ax2 = axes[0, 1]
            strategies = list(results.keys())
            win_rates = [results[s]['win_rate'] for s in strategies]
            colors = ['green' if wr > 50 else 'red' for wr in win_rates]
            ax2.barh(strategies, win_rates, color=colors)
            ax2.set_xlabel('Win Rate (%)')
            ax2.set_title('Win Rates by Strategy')
            ax2.axvline(x=50, color='black', linestyle='--', alpha=0.5)
            
            # 3. ROI Comparison
            ax3 = axes[1, 0]
            rois = [results[s]['roi'] for s in strategies]
            colors = ['green' if roi > 0 else 'red' for roi in rois]
            ax3.bar(strategies, rois, color=colors)
            ax3.set_ylabel('ROI (%)')
            ax3.set_title('Return on Investment by Strategy')
            ax3.axhline(y=0, color='black', linestyle='--', alpha=0.5)
            plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # 4. Risk/Reward Analysis
            ax4 = axes[1, 1]
            risk_reward = [results[s]['roi'] / results[s]['max_drawdown'] if results[s]['max_drawdown'] > 0 else 0 for s in strategies]
            ax4.scatter([results[s]['max_drawdown'] for s in strategies], 
                       [results[s]['roi'] for s in strategies],
                       s=[results[s]['total_bets'] for s in strategies], alpha=0.5)
            
            for i, strategy in enumerate(strategies):
                ax4.annotate(strategy[:15], 
                           (results[strategy]['max_drawdown'], results[strategy]['roi']))
            
            ax4.set_xlabel('Max Drawdown (%)')
            ax4.set_ylabel('ROI (%)')
            ax4.set_title('Risk vs Return Analysis')
            ax4.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig('backtest_results.png', dpi=100, bbox_inches='tight')
            plt.show()
            print("\n📊 Performance chart saved as 'backtest_results.png'")
            
        except Exception as e:
            print(f"Could not generate plots: {e}")
    
    def export_results(self, results, filename='backtest_results.json'):
        """Export results to JSON"""
        export_data = {}
        for strategy, stats in results.items():
            export_data[strategy] = {k: v for k, v in stats.items() if k != 'bets_log'}
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"\n📁 Results exported to {filename}")

# ==================== MAIN EXECUTION ====================

def run_backtest():
    print("🚀 Starting Betting Strategy Backtest...")
    print("-" * 50)
    
    # Initialize backtest engine
    backtest = BettingBacktest(initial_bankroll=10000)
    
    # Fetch historical data
    print("📊 Fetching historical match data...")
    historical_matches = backtest.fetch_historical_odds(days_back=180)
    print(f"✅ Loaded {len(historical_matches)} historical matches")
    
    # Run simulations
    print("\n🔄 Running strategy simulations...")
    results = backtest.simulate_betting_strategies(historical_matches)
    
    # Generate report
    df_results = backtest.generate_report(results)
    
    # Plot performance
    try:
        backtest.plot_performance(results)
    except:
        pass
    
    # Export results
    backtest.export_results(results)
    
    # Additional analysis
    print("\n" + "="*80)
    print("KEY INSIGHTS & RECOMMENDATIONS")
    print("="*80)
    
    best_roi_strategy = max(results.items(), key=lambda x: x[1]['roi'])
    best_sharpe_strategy = max(results.items(), key=lambda x: x[1]['sharpe_ratio'])
    lowest_dd_strategy = min(results.items(), key=lambda x: x[1]['max_drawdown'])
    
    print(f"\n💡 Best ROI: {best_roi_strategy[0]} ({best_roi_strategy[1]['roi']}%)")
    print(f"📈 Best Risk-Adjusted: {best_sharpe_strategy[0]} (Sharpe: {best_sharpe_strategy[1]['sharpe_ratio']})")
    print(f"🛡️ Lowest Risk: {lowest_dd_strategy[0]} (Max DD: {lowest_dd_strategy[1]['max_drawdown']}%)")
    
    print("\n✅ Backtest Complete!")
    
    return results, df_results

if __name__ == "__main__":
    results, df = run_backtest()
