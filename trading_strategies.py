# trading_strategies.py

import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import APIError
from alpaca_trade_api.entity import OptionOrderRequest, OrderSide, TimeInForce, OrderClass, OrderType

def initialize_alpaca_client(api_key: str, secret_key: str, paper: bool = True):
    """Initializes and returns an Alpaca API client."""
    return tradeapi.REST(key_id=api_key, secret_key=secret_key, paper=paper)

def _get_option_symbol(underlying_symbol: str, expiration_date: str, option_type: str, strike: float) -> str:
    """
    Formats the OCC option symbol required by the Alpaca API.
    Example: SPY251219C00500000
    """
    # expiration_date should be in 'YYYY-MM-DD' format, we convert it to 'YYMMDD'
    yy_mm_dd = expiration_date.replace('-', '')[2:]
    
    # option_type should be 'C' for Call or 'P' for Put
    option_type_char = option_type.upper()[0]
    
    # strike should be formatted to 8 digits (5 integer, 3 decimal)
    strike_formatted = f"{int(strike * 1000):08d}"
    
    return f"{underlying_symbol.upper():<6}{yy_mm_dd}{option_type_char}{strike_formatted}"

def trade_bull_call_spread(
    client: tradeapi.REST, 
    underlying_symbol: str, 
    expiration_date: str, 
    long_strike: float, 
    short_strike: float, 
    quantity: int,
    time_in_force: TimeInForce = TimeInForce.DAY
):
    """
    Executes a Bull Call Spread (Debit Spread).
    Buys a call at a lower strike and sells a call at a higher strike.
    
    Args:
        long_strike: The strike price of the call to buy. Must be < short_strike.
        short_strike: The strike price of the call to sell. Must be > long_strike.
    """
    if not long_strike < short_strike:
        raise ValueError("For a Bull Call Spread, the long_strike must be less than the short_strike.")

    long_call_symbol = _get_option_symbol(underlying_symbol, expiration_date, 'C', long_strike)
    short_call_symbol = _get_option_symbol(underlying_symbol, expiration_date, 'C', short_strike)

    order_data = OptionOrderRequest(
        symbol=underlying_symbol, # The multileg order uses the underlying as the main symbol
        qty=quantity,
        side=OrderSide.BUY, # A debit spread is a net buy
        type=OrderType.LIMIT, # Debit spreads should always use a limit price
        time_in_force=time_in_force,
        order_class=OrderClass.MULTILEG,
        limit_price=0.50,  # **IMPORTANT**: Set your desired net debit price here. E.g., $0.50
        legs=[
            OptionOrderRequest(
                symbol=long_call_symbol,
                qty=quantity,
                side=OrderSide.BUY,
                type=OrderType.LIMIT, # Leg types are ignored in multileg
                time_in_force=time_in_force
            ),
            OptionOrderRequest(
                symbol=short_call_symbol,
                qty=quantity,
                side=OrderSide.SELL,
                type=OrderType.LIMIT,
                time_in_force=time_in_force
            )
        ]
    )
    
    try:
        order = client.submit_order(order_data=order_data)
        print(f"Successfully submitted Bull Call Spread order. Order ID: {order.id}")
        return order
    except APIError as e:
        print(f"Error submitting Bull Call Spread order: {e}")
        raise

def trade_bear_call_spread(
    client: tradeapi.REST,
    underlying_symbol: str,
    expiration_date: str,
    short_strike: float,
    long_strike: float,
    quantity: int,
    time_in_force: TimeInForce = TimeInForce.DAY
):
    """
    Executes a Bear Call Spread (Credit Spread).
    Sells a call at a lower strike and buys a call at a higher strike.
    
    Args:
        short_strike: The strike price of the call to sell. Must be < long_strike.
        long_strike: The strike price of the call to buy. Must be > short_strike.
    """
    if not short_strike < long_strike:
        raise ValueError("For a Bear Call Spread, the short_strike must be less than the long_strike.")

    short_call_symbol = _get_option_symbol(underlying_symbol, expiration_date, 'C', short_strike)
    long_call_symbol = _get_option_symbol(underlying_symbol, expiration_date, 'C', long_strike)

    order_data = OptionOrderRequest(
        symbol=underlying_symbol,
        qty=quantity,
        side=OrderSide.SELL, # A credit spread is a net sell
        type=OrderType.LIMIT,
        time_in_force=time_in_force,
        order_class=OrderClass.MULTILEG,
        limit_price=0.25,  # **IMPORTANT**: Set your desired net credit price here. E.g., $0.25
        legs=[
            OptionOrderRequest(
                symbol=short_call_symbol,
                qty=quantity,
                side=OrderSide.SELL,
                type=OrderType.LIMIT,
                time_in_force=time_in_force
            ),
            OptionOrderRequest(
                symbol=long_call_symbol,
                qty=quantity,
                side=OrderSide.BUY,
                type=OrderType.LIMIT,
                time_in_force=time_in_force
            )
        ]
    )
    
    try:
        order = client.submit_order(order_data=order_data)
        print(f"Successfully submitted Bear Call Spread order. Order ID: {order.id}")
        return order
    except APIError as e:
        print(f"Error submitting Bear Call Spread order: {e}")
        raise

def trade_iron_condor(
    client: tradeapi.REST,
    underlying_symbol: str,
    expiration_date: str,
    long_put_strike: float,
    short_put_strike: float,
    short_call_strike: float,
    long_call_strike: float,
    quantity: int,
    time_in_force: TimeInForce = TimeInForce.DAY
):
    """
    Executes a Short Iron Condor.
    Combines a Bull Put Spread and a Bear Call Spread.
    """
    if not (long_put_strike < short_put_strike < short_call_strike < long_call_strike):
        raise ValueError("Strikes must be in ascending order: long_put < short_put < short_call < long_call.")

    long_put_symbol = _get_option_symbol(underlying_symbol, expiration_date, 'P', long_put_strike)
    short_put_symbol = _get_option_symbol(underlying_symbol, expiration_date, 'P', short_put_strike)
    short_call_symbol = _get_option_symbol(underlying_symbol, expiration_date, 'C', short_call_strike)
    long_call_symbol = _get_option_symbol(underlying_symbol, expiration_date, 'C', long_call_strike)

    order_data = OptionOrderRequest(
        symbol=underlying_symbol,
        qty=quantity,
        side=OrderSide.SELL, # An Iron Condor is a net credit (sell) strategy
        type=OrderType.LIMIT,
        time_in_force=time_in_force,
        order_class=OrderClass.MULTILEG,
        limit_price=0.75, # **IMPORTANT**: Set your desired net credit price here. E.g., $0.75
        legs=[
            # Bull Put Spread part
            OptionOrderRequest(symbol=long_put_symbol, qty=quantity, side=OrderSide.BUY),
            OptionOrderRequest(symbol=short_put_symbol, qty=quantity, side=OrderSide.SELL),
            # Bear Call Spread part
            OptionOrderRequest(symbol=short_call_symbol, qty=quantity, side=OrderSide.SELL),
            OptionOrderRequest(symbol=long_call_symbol, qty=quantity, side=OrderSide.BUY),
        ]
    )
    
    try:
        order = client.submit_order(order_data=order_data)
        print(f"Successfully submitted Iron Condor order. Order ID: {order.id}")
        return order
    except APIError as e:
        print(f"Error submitting Iron Condor order: {e}")
        raise
