import yfinance as yf
import pandas as pd
import json
import datetime
import sys
from concurrent.futures import ThreadPoolExecutor

# --- FILTRES ET CRITÈRES BUFFETT ---

# Secteurs exclus (Qualitatif) : Trop cycliques ou complexes pour une analyse simplifiée.
EXCLUDED_SECTORS = [
    'Technology', 'Biotechnology', 'Basic Materials', 'Energy', 
    'Oil & Gas', 'Mining', 'Semiconductors', 'Aerospace & Defense', 
    'Capital Goods', 'Industrials', 'Real Estate' 
]

# Secteurs exemptés du critère strict de Dette/Capitaux Propres (< 1.0).
# Car ils utilisent l'effet de levier de manière structurelle (Banques, Services Publics).
EXEMPTED_DEBT_SECTORS = ['Financial Services', 'Utilities']


# --- 1. FONCTIONS ROBUSTES DE CALCUL DES RATIOS ---

def get_safe_float(info, key, reject_value):
    """Récupère une valeur de manière sécurisée ou renvoie une valeur de rejet."""
    val = info.get(key)
    try:
        return float(val) if val is not None else reject_value
    except (ValueError, TypeError):
        return reject_value

def calculate_roe(stock):
    """Calcule le Return on Equity (ROE)."""
    try:
        net_income = stock.financials.loc['Net Income'].iloc[0]
        total_equity = stock.balance_sheet.loc['Total Stockholder Equity'].iloc[0]
        if total_equity > 0:
            return net_income / total_equity
        return -1.0 
    except Exception:
        return -1.0

def calculate_gpm(stock):
    """Calcule la Marge Brute (Gross Profit Margin)."""
    try:
        gross_profit = stock.financials.loc['Gross Profit'].iloc[0]
        total_revenue = stock.financials.loc['Total Revenue'].iloc[0]
        if total_revenue > 0:
            return gross_profit / total_revenue
        return -1.0
    except Exception:
        return -1.0

def calculate_de_ratio(stock):
    """Calcule le Ratio Dette/Capitaux Propres (Debt-to-Equity)."""
    try:
        # Tente de récupérer les données des états financiers pour plus de précision
        total_debt = stock.balance_sheet.loc['Total Debt'].iloc[0]
        total_equity = stock.balance_sheet.loc['Total Stockholder Equity'].iloc[0]

        if total_equity > 0:
            return total_debt / total_equity
        return 9999.0 
    except Exception:
        # Fallback si les états financiers ne sont pas disponibles
        total_debt = get_safe_float(stock.info, 'totalDebt', reject_value=0.0)
        total_equity = get_safe_float(stock.info, 'totalStockholderEquity', reject_value=-1.0)
        if total_equity > 0:
            return total_debt / total_equity
        return 9999.0


# --- 2. FONCTIONS DE RÉCUPÉRATION DES TICKERS (VIA WIKIPEDIA) ---

def get_tickers_from_wiki(url, table_index, symbol_col, suffix=""):
    """Fonction générique pour scraper les tickers depuis une page Wikipedia."""
    try:
        print(f"  > Scraping de {url}...")
        df = pd.read_html(url)[table_index]
        return [t.replace('.', '-') + suffix for t in df[symbol_col].tolist()]
    except Exception as e:
        print(f"  > Erreur lors du scraping de {url}: {e}")
        return []

def get_all_global_tickers():
    """Agrège les tickers des principales bourses mondiales."""
    all_tickers = []
    print("--- Démarrage de la récupération mondiale des Tickers (via Wikipedia) ---")

    # USA (Indices larges)
    all_tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', 0, 'Symbol'))
    all_tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/Nasdaq-100', 4, 'Symbol'))

    # Europe (Principales Bourses)
    all_tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/CAC_40', 4, 'Ticker', suffix=".PA"))
    all_tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/DAX', 4, 'Ticker', suffix=".DE"))
    all_tickers.extend(get_tickers_from_wiki('https://en.wikipedia.org/wiki/FTSE_100_Index', 4, 'Ticker', suffix=".L"))

    # Asie et autres (couverture manuelle pour les bourses difficiles à scraper)
    print("  > Ajout des leaders Japonais, Suisses, Canadiens (Manuel)...")
    all_tickers.extend([
        "7203.T", "6758.T", "9984.T", "6861.T", "8306.T", "9432.T", "7974.T", # Japon (Nikkei Leaders)
        "NESN.SW", "NOVN.SW", "ROG.SW", "UBSG.SW", "ZURN.SW", # Suisse (Swiss Market Index Leaders)
        "RY.TO", "TD.TO", "ENB.TO", "SHOP.TO", # Canada
        "BHP.AX", "CBA.AX", "CSL.AX", "WBC.AX", # Australie
        "0700.HK", "9988.HK", "1299.HK", # Hong Kong
    ])

    clean_tickers = list(set(filter(None, all_tickers))) # Nettoyage et dédoublonnage
    print(f"--- Tickers agrégés : {len(clean_tickers)} ---")
    return clean_tickers

# --- 3. ANALYSE PRINCIPALE MULTITHREADÉE ---

def process_ticker(ticker):
    """Analyse un seul ticker et applique les 4 filtres de Buffett."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Données de base
        price = stock.fast_info.last_price
        sector = info.get('sector', 'N/A')

        # 1. Exclusion Sectorielle
        if sector in EXCLUDED_SECTORS:
            return None

        # 2. Calcul des Ratios
        pe_val = get_safe_float(info, 'trailingPE', reject_value=9999.0)
        roe_val = calculate_roe(stock)
        gpm_val = calculate_gpm(stock)
        de_val = calculate_de_ratio(stock)

        # 3. Application des 4 Filtres Stricts
        is_pe_ok = (0.0 < pe_val < 15.0)
        is_roe_ok = (roe_val > 0.15)
        is_gpm_ok = (gpm_val > 0.20)
        
        # LOGIQUE D'EXCEPTION D/E : < 1.0 OU fait partie des secteurs exemptés
        is_de_ok = (de_val < 1.0) or (sector in EXEMPTED_DEBT_SECTORS)

        if is_pe_ok and is_roe_ok and is_gpm_ok and is_de_ok:
            
            name = info.get('longName', ticker)
            currency = info.get('currency', 'USD')
            tag = "Valeur d'Or"

            if sector in EXEMPTED_DEBT_SECTORS:
                tag = f"Valeur d'Or (Dette adaptée : {sector})"

            return {
                "symbol": ticker,
                "name": name,
                "sector": sector,
                "pe": round(pe_val, 2),
                "roe": round(roe_val * 100, 2),
                "gpm": round(gpm_val * 100, 2),
                "de_ratio": round(de_val, 2),
                "price": round(price, 2),
                "currency": currency,
                "tag": tag
            }
        return None
    
    except Exception:
        # print(f"Erreur d'analyse pour {ticker}: {e}", file=sys.stderr)
        return None

def run_global_analysis():
    all_tickers = get_all_global_tickers()
    
    # Limiter la taille du scan pour éviter les timeouts (optionnel)
    tickers_to_scan = all_tickers[:2500] 
    
    print(f"Démarrage de l'analyse multithreadée pour {len(tickers_to_scan)} actions...")
    
    # Utilisation du multithreading pour accélérer le processus (Max 10 threads)
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(process_ticker, tickers_to_scan))

    undervalued_stocks = [r for r in results if r is not None]

    # Tri par P/E croissant
    undervalued_stocks.sort(key=lambda x: x['pe'])
    
    final_data = {
        "last_updated": datetime.datetime.utcnow().strftime("%d/%m/%Y à %H:%M GMT"),
        "count": len(undervalued_stocks),
        "data": undervalued_stocks
    }

    with open("data.json", "w") as f:
        json.dump(final_data, f, indent=4)
    
    print(f"--- ANALYSE COMPLÈTE. Résultat : {len(undervalued_stocks)} actions trouvées. ---")

if __name__ == "__main__":
    # Désactiver les avertissements pandas pour un affichage plus propre
    pd.options.mode.chained_assignment = None 
    run_global_analysis()
