# main.py

import os
import json
from flask import Request, abort

# It's best practice to import your trading logic from another file
from trading_strategies import (
    initialize_alpaca_client,
    trade_bull_call_spread,
    trade_bear_call_spread,
    trade_iron_condor
)

def handler(request: Request):
    """
    HTTP Cloud Function entry point that acts as a secure webhook.
    
    Expects a POST request with a JSON payload like:
    {
        "secret_key": "YOUR_SUPER_SECRET_KEY",
        "strategy": "bull_call_spread",
        "params": {
            "underlying_symbol": "COIN",
            "expiration_date": "2025-07-25",
            "long_strike": 220.0,
            "short_strike": 225.0,
            "quantity": 1
        }
    }
    """
    # 1. --- Security Check ---
    # Ensure the request is a POST request
    if request.method != 'POST':
        print("Error: Invalid request method.")
        return abort(405) # Method Not Allowed

    # Get the JSON payload
    try:
        data = request.get_json()
    except Exception as e:
        print(f"Error: Could not parse JSON payload. {e}")
        return abort(400) # Bad Request

    # Authenticate the request using a secret key
    # Compare the key from the payload with a secret stored as an environment variable
    expected_secret = os.environ.get('WEBHOOK_SECRET_KEY')
    if not expected_secret or data.get('secret_key') != expected_secret:
        print("Error: Authentication failed. Invalid secret key.")
        return abort(403) # Forbidden

    # 2. --- Initialize API Client ---
    # Securely get Alpaca keys from environment variables
    api_key = os.environ.get('ALPACA_API_KEY')
    secret_key = os.environ.get('ALPACA_SECRET_KEY')
    use_paper_trading = os.environ.get('ALPACA_PAPER_TRADING', 'true').lower() == 'true'

    if not all([api_key, secret_key]):
        print("Error: Alpaca API credentials are not set in environment variables.")
        return abort(500) # Internal Server Error
        
    try:
        client = initialize_alpaca_client(api_key, secret_key, paper=use_paper_trading)
    except Exception as e:
        print(f"Error: Failed to initialize Alpaca client. {e}")
        return abort(500)

    # 3. --- Route to Strategy ---
    strategy_name = data.get('strategy')
    params = data.get('params', {})
    
    print(f"Received valid request for strategy: {strategy_name} with params: {params}")

    try:
        if strategy_name == 'bull_call_spread':
            trade_bull_call_spread(client=client, **params)
        elif strategy_name == 'bear_call_spread':
            trade_bear_call_spread(client=client, **params)
        elif strategy_name == 'iron_condor':
            trade_iron_condor(client=client, **params)
        else:
            print(f"Error: Unknown strategy '{strategy_name}'")
            return ('Unknown strategy', 400)
            
        return ('Order submitted successfully.', 200)

    except (ValueError, TypeError) as e:
        # Catches bad parameters from the webhook payload (e.g., missing strike)
        print(f"Error: Invalid parameters for strategy {strategy_name}. {e}")
        return (f"Invalid parameters: {e}", 400)
    except Exception as e:
        # Catches API errors from Alpaca or other issues
        print(f"Error executing strategy {strategy_name}. {e}")
        return (f"Execution error: {e}", 500)
