import yfinance as yf
import json
import datetime

# --- LISTE DE SÉCURITÉ (GLOBAL TITANS) ---
# On utilise cette liste fixe pour éviter que Wikipédia ne bloque le robot.
tickers_list = [
    # USA
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK-B", "JNJ", "V", "PG", "JPM",
    # France
    "TTE.PA", "LVMH.PA", "AIR.PA", "BNP.PA", "SAN.PA", "OR.PA", "RMS.PA", "AI.PA",
    # Allemagne
    "SAP.DE", "SIE.DE", "ALV.DE", "DTE.DE", "VOW3.DE", "BMW.DE",
    # UK
    "SHEL.L", "HSBA.L", "ULVR.L", "BP.L", "AZN.L",
    # Suisse & Italie
    "NESN.SW", "NOVN.SW", "ROG.SW", "ENEL.MI", "ISP.MI",
    # Canada
    "RY.TO", "TD.TO", "ENB.TO", "CNR.TO",
    # Japon & Asie
    "7203.T", "6758.T", "8306.T", "0700.HK", "9988.HK"
]

# Secteurs exclus
EXCLUDED_SECTORS = [
    'Technology', 'Biotechnology', 'Basic Materials', 'Energy', 
    'Oil & Gas', 'Mining', 'Semiconductors', 'Aerospace & Defense'
]
# Secteurs exemptés de la règle de dette
EXEMPTED_DEBT_SECTORS = ['Financial Services', 'Utilities']

def get_safe_float(info, key, reject_value):
    val = info.get(key)
    try:
        return float(val) if val is not None else reject_value
    except:
        return reject_value

def run_analysis():
    print(f"--- Démarrage Mode Sécurité ({len(tickers_list)} actions) ---")
    undervalued_stocks = []
    
    for ticker in tickers_list:
        try:
            print(f"Analyse de {ticker}...")
            stock = yf.Ticker(ticker)
            
            # On essaie de récupérer l'info, si ça rate, on passe au suivant
            try:
                info = stock.info
            except:
                continue

            # 1. Filtre Secteur
            sector = info.get('sector', 'N/A')
            if sector in EXCLUDED_SECTORS:
                print(f"  -> Rejet Secteur: {sector}")
                continue

            # 2. Récupération Données (Méthode Douce via .info pour éviter les erreurs de bilan)
            pe = get_safe_float(info, 'trailingPE', 9999.0)
            roe = get_safe_float(info, 'returnOnEquity', -1.0)
            # On utilise les marges pré-calculées par Yahoo pour éviter les bugs de calcul manuel
            gpm = get_safe_float(info, 'grossMargins', -1.0) 
            # Ratio D/E
            debt = get_safe_float(info, 'totalDebt', 0.0)
            equity = get_safe_float(info, 'totalStockholderEquity', 1.0)
            de_ratio = debt / equity if equity > 0 else 9999.0

            # 3. Filtres Buffett
            is_pe = (0 < pe < 15)
            is_roe = (roe > 0.15)
            is_gpm = (gpm > 0.20)
            is_de = (de_ratio < 1.0) or (sector in EXEMPTED_DEBT_SECTORS)

            if is_pe and is_roe and is_gpm and is_de:
                name = info.get('longName', ticker)
                currency = info.get('currency', 'USD')
                price = get_safe_float(info, 'currentPrice', 0.0)
                
                tag = "Valeur d'Or"
                if sector in EXEMPTED_DEBT_SECTORS:
                    tag = "Valeur d'Or (Dette adaptée)"

                print(f"✅ TROUVÉ : {name}")
                
                undervalued_stocks.append({
                    "symbol": ticker,
                    "name": name,
                    "sector": sector,
                    "pe": round(pe, 2),
                    "roe": round(roe * 100, 2),
                    "gpm": round(gpm * 100, 2),
                    "de_ratio": round(de_ratio, 2),
                    "price": round(price, 2),
                    "currency": currency,
                    "tag": tag
                })

        except Exception as e:
            print(f"  Erreur sur {ticker}: {e}")
            continue

    # Sauvegarde
    final_data = {
        "last_updated": datetime.datetime.utcnow().strftime("%d/%m/%Y à %H:%M GMT"),
        "count": len(undervalued_stocks),
        "data": undervalued_stocks
    }
    
    with open("data.json", "w") as f:
        json.dump(final_data, f)
    
    print("--- Analyse terminée avec succès ---")

if __name__ == "__main__":
    run_analysis()
