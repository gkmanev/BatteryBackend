import math
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pulp as pl  # optimization lib
from django.utils import timezone
from openpyxl import Workbook

from battery_backed.models import BatterySchedule, Price


def run_optimizer(dev_id: str = "batt1"):
    df_dam = pd.DataFrame()

    # ------------------------------------------------------------------
    # 1) Load prices for "tomorrow" (or today, depending on now/date)
    #    Prices are assumed to be at 15-minute resolution in the DB.
    # ------------------------------------------------------------------
    now = timezone.now().astimezone(timezone.get_current_timezone())
    tomorrow = now.date()  # if you want next day use: now.date() + timedelta(days=1)

    tomorrow_start = timezone.make_aware(
        datetime.combine(tomorrow, datetime.min.time()),
        timezone.get_current_timezone(),
    )
    tomorrow_end = tomorrow_start + timedelta(days=1)

    print(f"Creating schedule for: {tomorrow_start}||{tomorrow_end}")

    prices_qs = (
        Price.objects
        .filter(timestamp__gte=tomorrow_start, timestamp__lt=tomorrow_end)
        .order_by("timestamp")
    )

    if prices_qs.exists():
        df_dam = pd.DataFrame(list(prices_qs.values("timestamp", "price")))
    else:
        raise ValueError("No price data available for the selected day.")

    df_dam = df_dam.rename(columns={"timestamp": "DateRange", "price": "Price"})

    # ------------------------------------------------------------------
    # 2) Clean / prepare data (15-min prices)
    # ------------------------------------------------------------------
    df_dam["Price"] = df_dam["Price"].replace("-", np.nan)
    df_dam = df_dam.dropna(subset=["Price"])
    df_dam["Price"] = df_dam["Price"].astype(float)

    # Ensure ordered by time
    df_dam = df_dam.sort_values("DateRange").reset_index(drop=True)

    market_prices = df_dam["Price"].tolist()
    total_steps = len(market_prices)         # number of 15-min intervals
    dt_hours = 0.25                          # 15 minutes in hours

    if total_steps == 0:
        raise ValueError("No data available after cleaning.")

    # ------------------------------------------------------------------
    # 3) Battery parameters (energy in MWh, power in MW)
    # ------------------------------------------------------------------
    max_capacity = 100            # MWh
    capacity_hours = 4
    max_charge_rate = max_capacity / capacity_hours      # MW
    max_discharge_rate = max_capacity / capacity_hours   # MW

    # Per-step energy limits (MWh per 15 min)
    max_charge_energy_step = max_charge_rate * dt_hours
    max_discharge_energy_step = max_discharge_rate * dt_hours

    initial_soc = 0               # MWh
    charge_efficiency = 1.0
    discharge_efficiency = 1.0
    max_cycles_per_day = 2
    access_cost_per_mwh = 0      # EUR/MWh
    min_soc = 0                  # MWh

    # ------------------------------------------------------------------
    # 4) Define optimization problem
    # ------------------------------------------------------------------
    model = pl.LpProblem("Battery_Operation_Profit_Maximization", pl.LpMaximize)

    idx = range(total_steps)

    # Energy going into/out of battery during each 15-min interval (MWh)
    charge_to_battery = pl.LpVariable.dicts(
        "Charge_to_Battery", idx, lowBound=0,
        upBound=max_charge_energy_step * charge_efficiency
    )
    discharge_from_battery = pl.LpVariable.dicts(
        "Discharge_from_Battery", idx, lowBound=0,
        upBound=max_discharge_energy_step
    )

    # Energy traded with market (MWh per 15 min)
    purchase_from_market = pl.LpVariable.dicts(
        "Purchase_from_Market", idx, lowBound=0,
        upBound=max_charge_energy_step
    )
    sell_to_market = pl.LpVariable.dicts(
        "Sell_to_Market", idx, lowBound=0,
        upBound=max_discharge_energy_step * discharge_efficiency
    )

    # State of charge (MWh) at each step boundary
    soc = pl.LpVariable.dicts(
        "SoC", range(total_steps + 1), lowBound=min_soc, upBound=max_capacity
    )

    # Binary indicators
    is_charging = pl.LpVariable.dicts("IsCharging", idx, cat="Binary")
    is_discharging = pl.LpVariable.dicts("IsDischarging", idx, cat="Binary")
    start_charge = pl.LpVariable.dicts("StartCharge", idx, cat="Binary")
    start_discharge = pl.LpVariable.dicts("StartDischarge", idx, cat="Binary")

    # ------------------------------------------------------------------
    # 5) Objective: maximize net profit (EUR)
    # ------------------------------------------------------------------
    model += pl.lpSum(
        (sell_to_market[t] * (market_prices[t] - access_cost_per_mwh)) -
        (purchase_from_market[t] * (market_prices[t] + access_cost_per_mwh))
        for t in idx
    )

    # Initial SoC
    model += soc[0] == initial_soc

    # ------------------------------------------------------------------
    # 6) Constraints per 15-min step
    # ------------------------------------------------------------------
    for t in idx:
        # Link charge/discharge power to binary flags
        model += purchase_from_market[t] <= max_charge_energy_step * is_charging[t]
        model += sell_to_market[t] <= max_discharge_energy_step * is_discharging[t]

        # No simultaneous charge & discharge
        model += is_charging[t] + is_discharging[t] <= 1

        # Start event detection
        if t == 0:
            model += start_charge[t] >= is_charging[t]
            model += start_discharge[t] >= is_discharging[t]
        else:
            model += start_charge[t] >= is_charging[t] - is_charging[t - 1]
            model += start_discharge[t] >= is_discharging[t] - is_discharging[t - 1]

        # SoC dynamics
        model += soc[t + 1] == soc[t] + charge_to_battery[t] - discharge_from_battery[t]

        # Efficiency relationships
        model += charge_to_battery[t] == purchase_from_market[t] * charge_efficiency
        model += sell_to_market[t] == discharge_from_battery[t] * discharge_efficiency

    # SoC bounds are already handled in variable definition, but you can keep:
    for t in range(total_steps + 1):
        model += soc[t] <= max_capacity
        model += soc[t] >= min_soc

    # Cycle limit: max_cycles_per_day * number_of_days in horizon
    horizon_hours = total_steps * dt_hours
    num_days = max(1, math.ceil(horizon_hours / 24.0))
    model += pl.lpSum(start_discharge[t] for t in idx) <= max_cycles_per_day * num_days

    # ------------------------------------------------------------------
    # 7) Solve and build 15-min schedule aligned with prices
    # ------------------------------------------------------------------
    model.solve(pl.PULP_CBC_CMD(msg=False))

    charge_to_battery_amounts = np.array([charge_to_battery[t].varValue for t in idx])
    discharge_from_battery_amounts = np.array([discharge_from_battery[t].varValue for t in idx])
    soc_values = np.array([soc[t + 1].varValue for t in idx])  # SoC at end of each step

    # Positive = charging, Negative = discharging (MWh per 15 minutes)
    power_arr = (charge_to_battery_amounts - discharge_from_battery_amounts).tolist()

    # Create schedule DataFrame with the SAME timestamps as prices (15-min)
    df_schedule = pd.DataFrame(
        {"schedule": power_arr},
        index=df_dam["DateRange"]
    )

    # ------------------------------------------------------------------
    # 8) Save schedule to database (BatterySchedule)
    # ------------------------------------------------------------------
    soc_series = df_schedule["schedule"].cumsum()

    BatterySchedule.objects.filter(
        devId=dev_id,
        timestamp__gte=tomorrow_start,
        timestamp__lt=tomorrow_end,
    ).delete()

    schedule_objects = []
    for timestamp, energy_mwh in df_schedule["schedule"].items():
        invertor_power_mw = energy_mwh / dt_hours
        soc_value = soc_series.loc[timestamp]
        schedule_objects.append(
            BatterySchedule(
                devId=dev_id,
                timestamp=timestamp,
                invertor=invertor_power_mw,
                flow=energy_mwh,
                soc=soc_value,
            )
        )

    BatterySchedule.objects.bulk_create(schedule_objects)

    # ------------------------------------------------------------------
    # 9) Export schedule to Excel (one value per 15-min interval)
    # ------------------------------------------------------------------
    dam = df_dam["DateRange"].min().date()
    fn = "sent_optimized_schedules"
    file_name = f"{dev_id}_{dam}.xlsx"
    filepath = os.path.join(fn, file_name)

    wb = Workbook()
    ws = wb.active

    # Example: write schedule values on row 11, starting from column 4 (D11)
    for i, value in enumerate(df_schedule["schedule"], start=4):
        ws.cell(row=11, column=i, value=value)

    wb.save(filepath)

    return df_schedule, soc_values
