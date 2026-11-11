# 06 — Demand Forecasting and Indian Seasonality

## Goal

Forecast SKU demand responsibly and use Indian festivals and regional shopping periods as explicit features. Do not present a calendar lookup as a trained demand model.

## Forecasting strategy

Start with a transparent baseline:
- Recent moving average.
- Same weekday/week seasonal naive where enough history exists.
- Prior-year comparable period only when data is available and comparable.

Then benchmark a tabular model such as LightGBM/XGBoost or a time-series foundation model such as Chronos, based on actual compatibility and evaluation. Do not assume a foundation model is automatically better.

Potential feature groups:
- SKU/category identity.
- Lagged units sold (e.g. 7, 14, 28 days where appropriate).
- Rolling mean/median and volatility.
- Price, discount and promotion.
- Views, clicks and conversion when available.
- Day of week, month, payday and month-end.
- Region/state and delivery coverage.
- Festival/event type, days until event, days after event.
- Stock availability and stockout flags.
- Supplier lead time and incoming inventory.

Avoid data leakage: all features for a forecast date must have been available at the time the forecast would have been made.

## Indian festival and regional calendar

Support configurable events including, where relevant:
- Diwali and Dhanteras.
- Navratri and Dussehra.
- Holi.
- Raksha Bandhan.
- Eid al-Fitr and Eid al-Adha.
- Onam.
- Pongal.
- Makar Sankranti.
- Durga Puja.
- Chhath Puja.
- Wedding-season windows.
- Regional sale events and category-specific shopping periods.

Important:
- Many festival dates shift year to year. Use a maintained calendar source and store source, verification date and geography.
- Do not hardcode future lunar dates as permanent facts.
- Festival impact varies by category, region, customer segment and seller's past performance.
- Do not assume every festival increases every category's demand.
- Use seller history around comparable events when available.
- If there is no historical evidence, label the uplift as a scenario assumption, not a learned forecast.

## Festival-aligned analysis

For each relevant event:
1. Identify seller regions and relevant SKUs/categories.
2. Compare demand in pre-event, event and post-event windows across historical years where available.
3. Compare against a non-event baseline.
4. Account for stockouts and promotions.
5. Estimate uplift and uncertainty only when sample size supports it.
6. Recommend a preparation window based on supplier lead time and observed buying lead-in.

## Inventory decision support

Use a documented calculation. A simple initial reorder formula is:

`Reorder quantity = forecast demand over lead time + safety stock - available stock - confirmed incoming stock`

Clamp at zero and apply:
- Minimum order quantity.
- Budget limit.
- Storage capacity.
- Margin floor.
- Supplier constraints.
- Seller risk tolerance.

Safety stock must reflect forecast error and chosen service level. Do not use a fixed arbitrary number without explaining it.

## Evaluation

- Use chronological train/validation/test splits or rolling-origin backtesting.
- Compare against simple baselines.
- Report MAE/WAPE or another metric appropriate to the data; explain limitations around zero demand.
- Evaluate by SKU/category and event window, not only one aggregate score.
- Check forecast bias and prediction interval coverage.
- Exclude or separately model stockout-censored periods.
- Do not claim model accuracy from training fit alone.

## Output contract

A forecast response should include:
- SKU and forecast horizon.
- Point forecast and lower/upper interval where supported.
- Model/baseline name and version.
- Training data window and latest data date.
- Key drivers/features.
- Stockout/data-quality caveats.
- Backtest metrics.
- Whether festival uplift is learned, rule-based or scenario-only.

## Acceptance criteria

- [ ] A baseline forecast works end-to-end.
- [ ] Forecast evaluation uses time-based splits.
- [ ] Festival calendar entries have provenance and geography.
- [ ] Festival effects are not invented where evidence is absent.
- [ ] Replenishment respects lead time, stock, incoming quantity and budget.
- [ ] UI and agent distinguish forecast from observed sales.
