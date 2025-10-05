# Monitoring & Observability TODO

## Current Monitoring Capabilities

### ✅ Logging
- `logs/bot.log` - Main application log (INFO level)
- `logs/systemd.log` - Systemd service logs
- Circuit breaker state - Persistent API health tracking
- Position lock files - Race condition prevention

### ✅ View Logs
```bash
tail -f logs/bot.log                    # Real-time main log
tail -f logs/systemd.log                # Service logs
grep "BUY\|SELL" logs/bot.log           # Trade activity
grep "ERROR" logs/bot.log               # Errors only
journalctl -u cryptbot.service -f       # Systemd journal
```

### ✅ Current Metrics Logged
- Account equity & buying power
- Current BTC position & price
- 50-day SMA calculation
- Buy/sell signals with reasoning
- Order IDs and status
- Entry prices for stop loss tracking
- Circuit breaker state changes
- API errors and retries
- Volatility filter triggers

## 🔧 TODO: Missing Monitoring Features

### High Priority
- [ ] **Log rotation** - Logs will grow indefinitely
- [ ] **Alerting/Notifications** - Email, SMS, or Slack alerts for:
  - Trade executions
  - Errors/crashes
  - Stop loss triggers
  - Circuit breaker trips
- [ ] **Order fill confirmations** - Verify orders actually filled (not just submitted)
- [ ] **Health check endpoint** - Simple HTTP endpoint for external monitoring

### Medium Priority
- [ ] **Trade performance tracking**
  - Profit/Loss calculations
  - Win rate statistics
  - Drawdown tracking
  - Position history
- [ ] **Performance metrics**
  - Execution time per cycle
  - Memory usage
  - API latency
- [ ] **Daily/Weekly reports** - Automated performance summaries

### Low Priority (Nice to Have)
- [ ] **Dashboard/UI** - Web interface for visualization
- [ ] **Prometheus/Grafana integration** - Advanced metrics
- [ ] **Backtesting results** - Historical performance analysis
- [ ] **Real-time position monitoring** - Current P&L display
- [ ] **Configuration validation alerts** - Warn if settings look unusual

## Implementation Ideas

### Quick Wins (Easy to Implement)
1. Add logrotate configuration for log management
2. Simple email alerts using Python's smtplib
3. Add trade summary to end of each rebalance cycle
4. Create simple health check script

### More Complex
1. Build lightweight FastAPI endpoint for status
2. Integrate with existing monitoring services (Healthchecks.io, UptimeRobot)
3. Add database for trade history
4. Create Grafana dashboard
