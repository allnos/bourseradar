import yfinance as yf
import pandas as pd
import json
import datetime
# import time # Suppression de l'import inutile

# --- 1. FONCTIONS DE RÉCUPÉRATION DYNAMIQUE DES TICKERS (Scraping Wikipedia) ---

def get_sp500_tickers():
    """Récupère le S&P 500 (USA)"""
    try:
        print("Récupération S&P 500 (USA)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        # Correction du format (ex: BRK.B -> BRK-B)
        return [t.replace('.', '-') for t in df['Symbol'].tolist()]
    except:
        return []

def get_nasdaq100_tickers():
    """Récupère le NASDAQ 100 (USA)"""
    try:
        print("Récupération NASDAQ 100 (USA)...")
        # Le tableau est souvent à l'index 4
        # Attention : le nom de la colonne peut être 'Symbol' ou 'Ticker' selon la page Wiki
        df = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]
        # Tentative d'utiliser 'Symbol' comme le S&P 500, sinon 'Ticker'
        col_name = 'Symbol' if 'Symbol' in df.columns else 'Ticker'
        return df[col_name].tolist()
    except:
        return []

def get_cac40_tickers():
    """Récupère le CAC 40 (France)"""
    try:
        print("Récupération CAC 40 (France)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/CAC_40')[4]
        # Ajout du suffixe .PA pour Yahoo Finance
        return [t + ".PA" for t in df['Ticker'].tolist()]
    except:
        return []

def get_dax_tickers():
    """Récupère le DAX (Allemagne)"""
    try:
        print("Récupération DAX (Allemagne)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/DAX')[4]
        # Ajout du suffixe .DE si manquant
        return [t if ".DE" in t else t + ".DE" for t in df['Ticker'].tolist()]
    except:
        return []

def get_ftse100_tickers():
    """Récupère le FTSE 100 (Royaume-Uni)"""
    try:
        print("Récupération FTSE 100 (UK)...")
        df = pd.read_html('https://en.wikipedia.org/wiki/FTSE_100_Index')[4]
        # Ajout du suffixe .L pour Londres
        return [t + ".L" for t in df['Ticker'].tolist()]
    except:
        return []

def get_major_europe_japan_manual():
    """Liste manuelle des leaders pour la couverture des bourses difficiles à scraper (Japon, Suisse, Italie, etc.)"""
    print("Ajout des leaders Japonais, Suisses, Canadiens, etc. (Liste manuelle)...")
    return [
        # JAPON (Leaders)
        "7203.T", "6758.T", "9984.T", "6861.T", "8306.T", "9432.T", "7974.T",
        # SUISSE (SMI Leaders)
        "NESN.SW", "NOVN.SW", "ROG.SW", "UBSG.SW", "ZURN.SW",
        # ITALIE (FTSE Leaders)
        "FER.MI", "ENI.MI", "ISP.MI", "ENEL.MI",
        # ESPAGNE
        "ITX.MC", "IBE.MC",
        # CANADA
        "RY.TO", "TD.TO", "ENB.TO",
        # CHINE / HK
        "0700.HK", "9988.HK", "1299.HK",
        # AUSTRALIE
        "BHP.AX", "CBA.AX", "CSL.AX"
    ]


def get_all_global_tickers():
    """Agrège toutes les listes pour le scan mondial"""
    all_tickers = []
    all_tickers.extend(get_sp500_tickers())
    all_tickers.extend(get_nasdaq100_tickers())
    all_tickers.extend(get_cac40_tickers())
    all_tickers.extend(get_dax_tickers())
    all_tickers.extend(get_ftse100_tickers())
    all_tickers.extend(get_major_europe_japan_manual())

    # --- AMÉLIORATION DE ROBUSTESSE : Nettoyage final des formats ---
    # Enlève les doublons et s'assure que les formats US non-officiels (comme BRK.B)
    # sont convertis en format Yahoo (BRK-B)
    clean_tickers = list(set([t.replace('.', '-') if len(t.split('.')) <= 1 or t.endswith(('.TO', '.AX', '.HK', '.SW', '.MI', '.MC', '.AS
