import requests
import numpy as np
import pandas as pd
import fastf1
import sys
from collections import defaultdict



#--------------------------------FUNCTIONS------------------------------------#
# Example Dataframe
def getDataFrame(): 
    s = pd.Series(["Max", "Charles", "Lewis"], index=[1,2,3])
    d = pd.DataFrame({
        "Belgium": pd.Series(["Max", "Charles", "Lewis"], index=[1,2,3]), 
        "Austria": pd.Series(["Lando", "Oscar", "Charles"], index=[1,2,3])
    })
    print(d)

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

'''# Assign Driver to their Num
def getDriverIDs():
    driver_ids = {}
    res = requests.get('http://api.jolpi.ca/ergast/f1/2025/drivers')
    data = res.json()
    drivers = data['MRData']['DriverTable']['Drivers']
    for driver in drivers: 
        id = int(driver['permanentNumber'])
        driver_ids[id] = f'{driver['givenName']} {driver['familyName']}'
    return driver_ids'''

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

# Assign Driver to their ID (Jolpica API notation)
def getDriverIDs(): 
    res = requests.get('http://api.jolpi.ca/ergast/f1/2025/driverstandings')
    data  = res.json()
    driver_ids = []
    standings = data['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings']
    for std in standings:   
        driver_ids.append(std['Driver']['driverId'])
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
def getPrevLapTime(drivers): 
    dataSet = defaultdict(list)
    race = fastf1.get_session(2024, 'Miami', 'R')
    race.load()
    for driver in drivers: 
        abb = driver[0:3].upper()
        avg_lap_time = 0
        if len(race.laps.pick_drivers(abb)) != 0:
            laps = race.laps.pick_drivers(abb).pick_not_deleted()
            avg_lap_time = laps['LapTime'].mean()
        dataSet['driver_id'].append(driver)
        dataSet['prev_lap_time'].append(avg_lap_time)    
    df = pd.DataFrame(dataSet)
    return df

# Feature - Lap Times for Last 5 Rounds
def getCurrentForm(drivers, round_num): 
    locations = []
    dataSet = defaultdict(list)
    for i in range((round_num -5), round_num):
        res = requests.get(f'http://api.jolpi.ca/ergast/f1/2025/{i}/races')
        data = res.json()
        location = data['MRData']['RaceTable']['Races'][0]['Circuit']['Location']['locality']
        locations.append(location)

    for driver in drivers: 
        abb = driver[0:3].upper()
        dataSet['driver_id'].append(driver)
        for i in range(0,5):
            race = fastf1.get_session(2025, locations[i], 'R')
            race.load()
            avg_lap_time = 0
            if len(race.laps.pick_drivers(abb)) != 0:
                laps = race.laps.pick_drivers(abb).pick_not_deleted()
                avg_lap_time = laps['LapTime'].mean()
            dataSet[f'prev_lap_time_r{i+1}'].append(avg_lap_time)
    df = pd.DataFrame(dataSet)
    return df

    

#-------------------------------------RUN-------------------------------------#

# getResults(13)                                    # Race Results from Spain -> Belgium GP 
# getDriverIDs()                                    # Dict of (id, driver_name) pair
# df_drivers = getDrivers()                         # DF of Drivers with 'driver' column
# drivers_encoded = encodeDrivers(df_drivers)       # DF of One-Hot Encoded Drivers
# getDriverStandings(df_drivers)                    # DF of Current Driver Standings
drivers = getDriverIDs()                          # DF of Drivers Assigned to Jolpica API Driver ID
# print(getPrevLapTime(drivers))                    # DF of Drivers Previous Year Circuit Lap Times
#circuits = getCircuits()
# print(circuits)
print(getCurrentForm(drivers, 14))






        
        