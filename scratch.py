import sys
try:
    from vnstock_data.market import market_margin_ratio
    for source in ['KBS', 'VCI', 'TCBS', 'SSI', 'DNSE']:
        try:
            df = market_margin_ratio('TCB', source=source)
            if df is not None and not df.empty:
                print("Success with {}: {} rows".format(source, len(df)))
            else:
                print("Failed with {}: empty".format(source))
        except Exception as e:
            print("Failed with {}: {}".format(source, e))
except Exception as e:
    print("Import error: {}".format(e))
