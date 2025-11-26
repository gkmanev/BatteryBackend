import pandas as pd
import numpy as np
import pulp as pl # optimization lib
import os
from datetime import datetime, timedelta
from openpyxl import Workbook
import math
from django.utils import timezone
from battery_backed.models import Price



def run_optimizer():
    price_diff_threshold = 60

    df_dam = pd.DataFrame()

    # Retrieve tomorrow's day-ahead prices from the database
    now = timezone.now().astimezone(timezone.get_current_timezone())
    tomorrow = now.date() + timedelta(days=1)
    tomorrow_start = timezone.make_aware(
        datetime.combine(tomorrow, datetime.min.time()),
        timezone.get_current_timezone(),
    )
    tomorrow_end = tomorrow_start + timedelta(days=1)

    prices_qs = Price.objects.filter(
        timestamp__gte=tomorrow_start, timestamp__lt=tomorrow_end
    ).order_by("timestamp")

    if prices_qs.exists():
        df_dam = pd.DataFrame(list(prices_qs.values("timestamp", "price")))

    df_dam = df_dam.rename(columns={"timestamp": "DateRange", "price": "Price"})
    
    # Parameters - can be modified as needed
    max_capacity = 100  # MWh
    capacity_hours =4
    max_charge_rate = max_capacity / capacity_hours  # MW
    max_discharge_rate = max_capacity / capacity_hours  # MW
    initial_soc = 0  # kWh
    charge_efficiency = 1
    discharge_efficiency = 1
    max_cycles_per_day = 2  # Number of charge/discharge cycles allowed per day
    access_cost_per_mwh = 0  # EUR per MWh
    min_soc = 0  # Minimum state of charge to prevent deep discharge


    # Replace any occurrences of '-' with NaN
    df_dam['Price'] = df_dam['Price'].replace('-', np.nan)

    # Drop any rows where 'Price' is NaN
    df_dam = df_dam.dropna(subset=['Price'])
    # Convert the prices to float
    df_dam['Price'] = df_dam['Price'].astype(float)
  

    #Extract the prices and count total hours
    market_prices = df_dam['Price'].tolist()

    # Total number of hours based on CSV data
    total_hours = len(market_prices)
   
    print(total_hours)

    
    # Ensure there is data for the specified week range
    if total_hours == 0:
        raise ValueError(f"No data available")

    # Define the optimization problem
    model = pl.LpProblem("Battery_Operation_Profit_Maximization", pl.LpMaximize)

    # Decision variables
    charge_to_battery = pl.LpVariable.dicts("Charge_to_Battery", range(total_hours), lowBound=0, upBound=max_charge_rate * charge_efficiency)
    purchase_from_market = pl.LpVariable.dicts("Purchase_from_Market", range(total_hours), lowBound=0, upBound=max_charge_rate)
    discharge_from_battery = pl.LpVariable.dicts("Discharge_from_Battery", range(total_hours), lowBound=0, upBound=max_discharge_rate)
    sell_to_market = pl.LpVariable.dicts("Sell_to_Market", range(total_hours), lowBound=0, upBound=max_discharge_rate * discharge_efficiency)
    soc = pl.LpVariable.dicts("SoC", range(total_hours + 1), lowBound=min_soc, upBound=max_capacity)
    is_charging = pl.LpVariable.dicts("IsCharging", range(total_hours), cat='Binary')
    is_discharging = pl.LpVariable.dicts("IsDischarging", range(total_hours), cat='Binary')
    start_charge = pl.LpVariable.dicts("StartCharge", range(total_hours), cat='Binary')
    start_discharge = pl.LpVariable.dicts("StartDischarge", range(total_hours), cat='Binary')
    
    
    # Updated objective function
    model += pl.lpSum([
        (sell_to_market[h] * (market_prices[h] - access_cost_per_mwh)) - 
        (purchase_from_market[h] * (market_prices[h] + access_cost_per_mwh)) 
        for h in range(total_hours)
    ])

    # Initial SoC
    model += soc[0] == initial_soc

    #Constraints
    for h in range(total_hours):
        # Charge or discharge indication
        model += purchase_from_market[h] <= max_charge_rate * is_charging[h]
        model += sell_to_market[h] <= max_discharge_rate * is_discharging[h]
        
        # Prevent simultaneous charging and discharging
        model += is_charging[h] + is_discharging[h] <= 1

        # Transition detection
        if h > 0:
            model += start_charge[h] >= is_charging[h] - is_charging[h - 1]
            model += start_discharge[h] >= is_discharging[h] - is_discharging[h - 1]

        # SoC update based on charge and discharge within the same hour
        if h == 0:
            model += soc[h] == initial_soc + charge_to_battery[h] - discharge_from_battery[h]
        else:
            model += soc[h] == soc[h - 1] + charge_to_battery[h] - discharge_from_battery[h]

        # Efficiency constraints
        model += charge_to_battery[h] == purchase_from_market[h] * charge_efficiency
        model += sell_to_market[h] == discharge_from_battery[h] * discharge_efficiency

    # SoC constraints for all hours
    for h in range(total_hours + 1):
        model += soc[h] <= max_capacity
        model += soc[h] >= min_soc  # Ensure SoC does not drop below minimum

    num_days = max(1, math.ceil(total_hours / 24))
    # Limit the number of charge and discharge events
    model += pl.lpSum([start_discharge[h] for h in range(total_hours)]) <= max_cycles_per_day * num_days


    # Solve the problem
    model.solve(pl.PULP_CBC_CMD(msg=False))  # Suppress solver output

    # Extract results
    charge_to_battery_amounts = np.array([charge_to_battery[h].varValue for h in range(total_hours)])
    purchase_from_market_amounts = np.array([purchase_from_market[h].varValue for h in range(total_hours)])
    discharge_from_battery_amounts = np.array([discharge_from_battery[h].varValue for h in range(total_hours)])
    sell_to_market_amounts = np.array([sell_to_market[h].varValue for h in range(total_hours)])
    soc_values = np.array([soc[h].varValue for h in range(total_hours)])

    power_arr = (charge_to_battery_amounts - discharge_from_battery_amounts).tolist()   
    print(power_arr)

    # # Create initial DataFrame
    df = pd.DataFrame(power_arr, columns=["schedule"])

    df.reset_index(drop=True, inplace=True)
    
    # Generate a date range starting from today at 1:00 AM, ending at 1:00 AM the next day + 1 hour
    
    schedule_start = df_dam['DateRange'].min().replace(minute=0, second=0, microsecond=0)
    date_range = pd.date_range(start=schedule_start, periods=total_hours, freq='H')
    df.index = date_range

       
    # Resample to 15-minute intervals and forward fill missing values
    minute_schedule = df.resample('15T').ffill()  
    #add 23:15, 23:30, 23:45
    last_value = minute_schedule['schedule'].iloc[-1]
    day_end = schedule_start.replace(hour=23, minute=0, second=0, microsecond=0)

    today_23_15 = day_end + timedelta(minutes=15)
    today_23_30 = day_end + timedelta(minutes=30)
    today_23_45 = day_end + timedelta(minutes=45)

    additional_times = pd.to_datetime([today_23_15, today_23_30, today_23_45])
    additional_values = [last_value] * len(additional_times)

    # Create a new DataFrame for the additional rows
    additional_df = pd.DataFrame({'schedule': additional_values}, index=additional_times)
    
    # Concatenate the additional rows with the existing DataFrame
    minute_schedule = pd.concat([minute_schedule, additional_df])


    
    # Sort the DataFrame by the index (timestamps)
    minute_schedule = minute_schedule.sort_index()

    #return minute_schedule    

    invertor = minute_schedule['schedule'].to_list()
    

    dam = schedule_start.date()
    fn = "sent_optimized_schedules"
    file_name = f"batt1_{dam}.xlsx"
    filepath = os.path.join(fn, file_name)
    # Create a workbook and select the active worksheet
    wb = Workbook()
    ws = wb.active
    # Write each value into separate cells in row 10, starting from column 2
    for i, value in enumerate(invertor, start=4):
        ws.cell(row=11, column=i, value=value)
    
    # directories = [d for d in os.listdir() if os.path.isdir(d)]
    # print("Directories:", directories)
    # Save to an Excel file
    wb.save(filepath)
