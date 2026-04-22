def fetch_pair_data(ticker, tf):
    # Объявляем pair_name с дефолтным значением до блока try
    pair_name = next((k for k, v in DEFAULT_PAIRS.items() if v == ticker), ticker.replace("=X","").replace("=F",""))
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={tf}&range=10d"
        data = requests.get(url, timeout=12).json()
        quotes = data["chart"]["result"][0]["indicators"]["quote"][0]
        closes = quotes["close"][-350:]
        highs = quotes["high"][-350:]
        lows = quotes["low"][-350:]

        # Проверка наличия данных
        if len(closes) == 0:
            return None

        # Ваш существующий код для анализа данных
        has_news, news_title = has_high_impact_news(pair_name)
        if has_news:
            return {"Пара": pair_name, "Новости": news_title}
        # Можно добавить ещё обработку, например, индикаторы и т.д.

    except Exception as e:
        # Можно логировать ошибку для отладки
        # print(f"Error fetching data for {ticker}: {e}")
        pass

    return None
