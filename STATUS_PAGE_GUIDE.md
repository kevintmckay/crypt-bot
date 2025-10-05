# Trading Bots Status Page

## Access

**URL**: http://192.168.86.31:8080

- Auto-refreshes every 30 seconds
- Dark theme
- Mobile responsive

## Features

### Dashboard Shows
- 🪙 **CryptBot** (BTC/USD) status
- 📈 **StockBot** (SPY) status  
- 📧 **Email System** status

### For Each Bot
- Current status (Running/Stopped)
- Symbol trading
- Current position
- Current price
- Account value
- Last trading signal
- Circuit breaker status
- Last update timestamp

## Architecture

```
/var/www/trading-status/
├── status_server.py         # Flask web server
├── templates/
│   └── status.html          # Dark-themed dashboard
├── data/                    # Status data (group: tradingbots)
│   ├── cryptbot-status.json
│   └── stockbot-status.json
└── venv/                    # Python virtual environment
```

## System Service

```bash
# Service management
sudo systemctl status trading-status
sudo systemctl restart trading-status
sudo systemctl stop trading-status
sudo systemctl start trading-status

# View logs
sudo journalctl -u trading-status -f
```

## How Bots Export Status

```python
from core.status_export import export_status

export_status(
    symbol='BTC/USD',
    status='running',
    current_position=0.05,
    current_price=67500.00,
    account_value=5000.00,
    last_signal='HOLD',
    circuit_breaker_status='CLOSED'
)
```

## API Endpoints

- `GET /` - Web dashboard
- `GET /api/status` - JSON status of all bots
- `GET /api/health` - Health check

## Permissions

- **User**: `webstatus` (runs web server)
- **Group**: `tradingbots` (cryptbot, stockbot, webstatus)
- **Data directory**: `/var/www/trading-status/data/` (group writable)

## Auto-Start

✅ Service enabled to start on boot via systemd

## Security Notes

- Web server runs on port 8080 (not 80/443)
- Runs as dedicated `webstatus` user
- Read-only access to bot data
- No authentication (local network only)
