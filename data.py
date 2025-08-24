#------------------------------DATA-COLLECTION----------------------------------#
import os
import requests
import numpy as np
import pandas as pd
import fastf1
import statistics
from collections import defaultdict

cache_file = 'cache.csv'

#--------------------------------FUNCTIONS------------------------------------#
# Example Dataframe
def getDataFrame(): 
    s = pd.Series(["Max", "Charles", "Lewis"], index=[1,2,3])
    d = pd.DataFrame({
        "Belgium": pd.Series(["Max", "Charles", "Lewis"], index=[1,2,3]), 
        "Austria": pd.Series(["Lando", "Oscar", "Charles"], index=[1,2,3])
    })
    return d

# Gets Race Results of Last 5 Rounds Formatted
def getResults(i): 
    dataSet = {}
    for round in range((i-4), (i+1)):
        season = requests.get(f'http://api.jolpi.ca/ergast/f1/2025/{round}/results')
        if season: 
            data = season.json()
            races = data['MRData']['RaceTable']['Races']
            for race in races: 
                ranking = []
                for result in race['Results']:
                    #print(f"{result['position']}: {result['Driver']['givenName']} {result['Driver']['familyName']}")
                    ranking.append(result['Driver']['familyName'])      
                dataSet[race['raceName']]=pd.Series(ranking, index=range(1, (len(ranking)+1)))      
    res = pd.DataFrame(dataSet)
    print(res)

# Assign Driver to their Num
def getDriverNames():
    driver_ids = {}
    res = requests.get('http://api.jolpi.ca/ergast/f1/2025/drivers')
    data = res.json()
    drivers = data['MRData']['DriverTable']['Drivers']
    for driver in drivers: 
        id = int(driver['permanentNumber'])
        driver_ids[id] = f'{driver['givenName']} {driver['familyName']}'
    return driver_ids

# Returns Array of Driver Names
def getDrivers(): 
    driver_names = []
    res = requests.get('http://api.jolpi.ca/ergast/f1/2025/drivers')
    data = res.json()
    drivers = data['MRData']['DriverTable']['Drivers']
    for driver in drivers: 
        driver_names.append(driver['familyName'])
    df = pd.DataFrame({'driver': driver_names})
    return df

# Get Circuits 
def getCircuits(): 
    countries = []
    res = requests.get('http://api.jolpi.ca/ergast/f1/2025/circuits')
    data = res.json()
    circuits = data['MRData']['CircuitTable']['Circuits']
    for circuit in circuits: 
        countries.append(circuit['Location']['locality'])
    return countries

# One-Hot Encoding Drivers
def encodeDrivers(df_drivers): 
    df_encoded = pd.get_dummies(df_drivers, dtype=int)
    return df_encoded

# Assign Driver to their Code (Jolpica-F1 API Notation)
def getDriverIDs(): 
    res = requests.get('http://api.jolpi.ca/ergast/f1/2025/driverstandings')
    data  = res.json()
    driver_ids = {}
    standings = data['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings']
    for std in standings:   
        #driver_ids.append(std['Driver']['code'])
        driver_ids[std['Driver']['driverId']] = std['Driver']['code']
    return driver_ids

# Form - Returns DF for 2025 Driver Standings (WDC)
def getDriverStandings(): 
    driver_ids, driver_standings = [], []
    res = requests.get('http://api.jolpi.ca/ergast/f1/2025/driverstandings')
    data = res.json()
    standings = data['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings']
    for std in standings:   
        driver_ids.append(std['Driver']['driverId'])
        driver_standings.append(std['position'])
    df = pd.DataFrame({
        'driver_id': pd.Series(driver_ids),
        'driver_standing': pd.Series(driver_standings)
    })
    return df

# Feature - Returns DF for Driver's Lap Time on that Previous Year's Circuit (FastF1 Telemetry Data)
def getPrevYrTime(drivers, yr, circuit): 
    dataSet = defaultdict(list)
    race = fastf1.get_session(yr, circuit, 'R')
    race.load()
    for driver in drivers: 
        code = drivers[driver]
        avg_lap_time = np.nan
        if len(race.laps.pick_drivers(code)) != 0:
            laps = race.laps.pick_drivers(code).pick_not_deleted()
            avg_lap_time = pd.to_timedelta(laps['LapTime']).mean()
            if pd.notnull(avg_lap_time):
                avg_lap_time = avg_lap_time.total_seconds()
            else:
                avg_lap_time = np.nan
        dataSet['driver_id'].append(driver)
        dataSet['prev_yr_lap_time'].append(avg_lap_time)    
    df = pd.DataFrame(dataSet)
    return df

# Feature - Lap Times for Last 5 Rounds
def getLastFiveRounds(drivers, round_num): 
    locations = []
    dataSet = defaultdict(list)
    for i in range((round_num -5), round_num):
        res = requests.get(f'http://api.jolpi.ca/ergast/f1/2025/{i}/races')
        data = res.json()
        location = data['MRData']['RaceTable']['Races'][0]['Circuit']['Location']['locality']
        locations.append(location)
    for driver in drivers: 
        code = drivers[driver]
        dataSet['driver_id'].append(driver)
        for i in range(0,5):
            race = fastf1.get_session(2025, locations[i], 'R')
            race.load()
            avg_lap_time = np.nan
            if len(race.laps.pick_drivers(code)) != 0:      # Check if Driver Was in the Race
                laps = race.laps.pick_drivers(code).pick_not_deleted()
                avg_lap_time = pd.to_timedelta(laps['LapTime']).mean()
                if pd.notnull(avg_lap_time):
                    avg_lap_time = avg_lap_time.total_seconds()
                else:
                    avg_lap_time = np.nan
            dataSet[f'prev_lap_time_r{i+1}'].append(avg_lap_time)
    df = pd.DataFrame(dataSet)
    return df

# Update Cache, Pass in DF to be Merged
def updateCache(cache_file, data):
    if os.path.exists(cache_file): 
        if os.path.getsize(cache_file) > 0:
            df_cached = pd.read_csv(cache_file)
            df_merged = pd.merge(df_cached, data, on='driver_id')
            df_merged.to_csv(cache_file, index=False)
            return df_merged
        elif os.path.getsize(cache_file) <= 0: 
            data.to_csv(cache_file, index=False)
            return data
    else: 
        print("File Does Not Exist")

# Calculate Avg Lap Times of 5 Prev Rounds
def getAvg(cache_file):
    df_cached = pd.read_csv(cache_file)
    dataSet = defaultdict(list)
    cols = ['prev_lap_time_r1', 'prev_lap_time_r2', 'prev_lap_time_r3', 'prev_lap_time_r4', 'prev_lap_time_r5']
    for _, row in df_cached.iterrows(): 
        dataSet['driver_id'].append(row['driver_id'])
        total, rowLen = 0, 0
        for col in cols: 
            if pd.notna(row[col]):
                total += row[col]
                rowLen += 1
        if rowLen != 0: 
            avg = total / rowLen
        else: 
            avg = np.nan
        dataSet['avg_prev_lap_time'].append(avg)
    return pd.DataFrame(dataSet)
   
# DF of Driver, Constructor Pairings
def getConstructors(drivers):
    dataSet = defaultdict(list)
    res = requests.get('http://api.jolpi.ca/ergast/f1/2025/last/results')
    data = res.json()
    results = data['MRData']['RaceTable']['Races'][0]['Results']
    for result in results: 
        driver = result['Driver']['driverId'] 
        constructor = result['Constructor']['constructorId']
        if driver in drivers: 
            dataSet['driver_id'].append(driver)
            dataSet['constructor'].append(constructor)
    df = pd.DataFrame(dataSet)
    return df

# DF of Grid Position (Starting) 
def getGridPosition(drivers, yr, circuit):
    dataSet = defaultdict(list)
    race = fastf1.get_session(yr, circuit, 'R')
    race.load()

    for driver in drivers: 
        code = drivers[driver]
        pos_series = race.results.loc[race.results['Abbreviation']==code, 'GridPosition']
        pos = np.nan
        dataSet['driver_id'].append(driver)
        if not pos_series.empty:
            pos = int(round(pos_series.iloc[0]))
        dataSet['grid_position'].append(pos)
    return pd.DataFrame(dataSet)

# DF of Finish Position
def getFinishPosition(drivers, yr, circuit, roundNum):
    dataSet = defaultdict(list)
    race = fastf1.get_session(yr, circuit, 'R')
    race.load()
    for driver in drivers: 
        code = drivers[driver]
        pos_series = race.results.loc[race.results['Abbreviation']==code, 'Position']
        pos = np.nan
        dataSet['driver_id'].append(driver)
        if not pos_series.empty:
            pos = int(round(pos_series.iloc[0]))
        dataSet[f'finish_r{roundNum}'].append(pos)
    return pd.DataFrame(dataSet)

# DF of Avg Finishes
def getAvgFinish(cache_file):
    df_cached = pd.read_csv(cache_file)
    dataSet = defaultdict(list)
    cols = ['finish_r1', 'finish_r2', 'finish_r3', 'finish_r4', 'finish_r5']
    for _, row in df_cached.iterrows(): 
        dataSet['driver_id'].append(row['driver_id'])
        total, rowLen = 0, 5
        for col in cols: 
            if pd.notna(row[col]):
                total += row[col]
            else:
                total += 25
        if rowLen != 0: 
            avg = total / rowLen
        else: 
            avg = np.nan
        dataSet['avg_finish'].append(avg)
    return pd.DataFrame(dataSet)

# DF of Constuctor Standings
def getConstructorStandings(cache_file): 
    res = requests.get('http://api.jolpi.ca/ergast/f1/2025/14/constructorstandings')
    data = res.json()
    cons_standings = {}
    dataSet = defaultdict(list)
    standings = data['MRData']['StandingsTable']['StandingsLists'][0]['ConstructorStandings']
    for std in standings: 
        cons_standings[std['Constructor']['constructorId']] = std['position']
    df = pd.read_csv(cache_file)
    for driver in df['driver_id']:
        cons = df.loc[df['driver_id']==driver, 'constructor'].iloc[0]
        dataSet['driver_id'].append(driver)
        dataSet['constructor_standing'].append(int(cons_standings[cons]))
    return pd.DataFrame(dataSet)
        
# TODO Get avg qualifying pos        
def getAvgQuali(cache_file):
    print()


# Get Actual Race Results (Testing Data)
def getRaceResults(yr, round_num): 
    dataSet = defaultdict(list)
    res = requests.get(f'http://api.jolpi.ca/ergast/f1/{yr}/{round_num}/results')
    data = res.json()
    results = data['MRData']['RaceTable']['Races'][0]['Results']
    for result in results: 
        #print(result['position'])
        #print(result['Driver']['driverId'])
        dataSet['driver_id'].append(result['Driver']['driverId'])
        dataSet['actual_result'].append(result['position'])
    return pd.DataFrame(dataSet)

#------------------------------COMMANDS------------------------------#
cache_file = 'cache.csv'
base_dir = os.path.dirname(__file__)
file_path = os.path.join(base_dir, cache_file)

#drivers = getDriverIDs() 
#constructors= getConstructors(drivers)
#updateCache(file_path, constructors)
#last_five_rounds = getLastFiveRounds(drivers, 6)        # Rounds 1 - 5
#updateCache(file_path, last_five_rounds)
#avg_last_five = getAvg(cache_file)
#updateCache(file_path, avg_last_five)
#prev_yr_time = getPrevYrTime(drivers, 2024, 'Miami')
#updateCache(file_path, prev_yr_time)
#driver_standings = getDriverStandings()
#updateCache(file_path, driver_standings)
#gridPositions = getGridPosition(drivers, 2025, 'Miami')
#updateCache(file_path, gridPositions)
#finish= getFinishPosition(drivers, 2025, 'Jeddah', 5)
#avg_finish = getAvgFinish(file_path)
#updateCache(file_path, avg_finish)
#constructor_standings = getConstructorStandings(file_path)
#updateCache(file_path, constructor_standings)
#driver_standings = getDriverStandings()
#updateCache(file_path, driver_standings)
#results = getRaceResults(2025, 6)
#updateCache(file_path, results)



'''# Changing CSV File Format
df = pd.read_csv(file_path)
df.drop(columns=['actual_result_x', 'actual_result_y'], inplace=True)        # Delete Columns
df = df.sort_values(by='driver_standing', ascending=True)                       # Rearrange Columns in Ascending Order
df.to_csv(file_path, index=False)'''




#-------------------------------------RUN-------------------------------------#
# Files 
#cache_file = 'cache.csv'
#base_dir = os.path.dirname(__file__)
#file_path = os.path.join(base_dir, cache_file)

# getResults(13)                                    # Race Results from Spain -> Belgium GP 
# getDriverIDs()                                    # Dict of (id, driver_name) pair
# df_drivers = getDrivers()                         # DF of Drivers with 'driver' column
# drivers_encoded = encodeDrivers(df_drivers)       # DF of One-Hot Encoded Drivers
#drivers = getDriverIDs()                          # DF of Drivers Assigned to Jolpica API Driver ID
# print(getPrevLapTime(drivers))                    # DF of Drivers Previous Year Circuit Lap Times
# circuits = getCircuits()
# print(circuits)
#print(getCurrentForm(drivers, 14))
#prevRounds = getCurrentForm(drivers, 14)
#print(prevRounds)
#addToCache(prevRounds,cache_file)
#constructors= getConstructors(drivers)
#print(updateCache(file_path, constructors))
#print(updateCache(file_path, prevRounds))
#print(getPrevAvg(drivers))
#prevRounds = getCurrentForm(drivers, 6)
#updateCache(file_path, constructors)
#prev_avg_times = getAvg(file_path)
#driver_standings = getDriverStandings()
#updateCache(file_path, driver_standings)
#print(getPrevYrTime(drivers, 2024, 'Miami'))

#------------------------------COMMANDS------------------------------#






        
        