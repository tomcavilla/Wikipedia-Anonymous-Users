import requests, re, geoip2.database, json, os
from datetime import datetime
from bs4 import BeautifulSoup as bs
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor
import seaborn as sns


class page_list:
    # Class to handle Wikipedia page list operations.

    def __init__(self, name):
        '''
        Initialize the page list with the given name.
            name: str - Name of the page list.
            return: None
        '''
        self.name = name
        self.page_titles = self.get_page_titles() # Contains the titles of the pages in the list.
        self.pages = self.collect_pages() # Contains the page objects for the titles in the list.

    def get_page_titles(self):
        '''
        Get the titles of the pages in the list.
            return: list - List of page titles.
        '''
        path = "Lists/" + self.name + ".json"
        with open(path, 'r') as file:
            data = json.load(file)

        return data
    
    def collect_pages(self):
        '''
        Get the page objects for the titles in the list.
            return: list - List of page objects.
        '''
        pages = []
        # Use ThreadPoolExecutor to gather pages concurrently.
        with ThreadPoolExecutor() as executor:
            pages = list(executor.map(lambda title: page(title, self.name), self.page_titles))
        return pages
    
    def plot_world_totals(self):
        '''
        Plot the world map with the total edits for each country.
            return: None
        '''
        # Get the total edits for each country.
        countries = {}
        for page in self.pages:
            country_data = page.countries()
            for country, count in country_data.items():
                if country in countries:
                    countries[country] += count
                else:
                    countries[country] = count

        # Plot the world map.
        title1 = f"Locations of Anonymous Editors for all pages in the {self.name} list."
        title2 = f"Map of Anonymous Editor Locations for all pages in the {self.name} list."
        fileloc1 = f"{self.name}/World_Maps/World.png"
        fileloc2 = f"{self.name}/World_Maps/"
        if not os.path.exists(f"{self.name}/World_Maps/"):
            os.mkdir(f"{self.name}/World_Maps/")
        self.plot_world_map(countries, title1, title2, fileloc1, fileloc2)


    def plot_world_map(self, countries, title1, title2, fileloc1, fileloc2):
        '''
        Plot the world map with the total edits for each country.
            countries: dict - Dictionary of countries and their counts.
            title1: str - Title of the World Map.
            title2: str - Title of the Continent Maps.
            fileloc1: str - File location for the world map.
            fileloc2: str - File location for the continent maps.
            return: None
            
        '''
        # Json file including country names and their equivalents used by the GeoPandas world map.
        with open("World_Map_Data/Equivs.json", "r") as file:
            equivs = json.load(file)

        # If the country name differs from the name used in the GeoPandas world map, replace it with the equivalent name.
        replace = []
        for country in countries:
            if country in list(equivs.keys()):
                replace.append(country)

        for country in replace:
            countries[equivs[country]] = countries[country]
            del countries[country]
        
        # Load the world map data
        world = gpd.read_file("World_Map_Data/ne_110m_admin_0_countries.shp")
        # Majority of Russia is in Asia, but map considers it Europe.
        world.loc[world["NAME"] == "Russia", "CONTINENT"] = "Asia"

        # Combine the json data with the world map data.
        data = pd.DataFrame(list(countries.items()), columns=['country', 'count'])
        world = world.merge(data, how='left', left_on='NAME', right_on='country')

        # Plot the heatmap
        fig, ax = plt.subplots(1, 1, figsize=(15, 10))
        world.boundary.plot(ax=ax)
        world.plot(column='count', ax=ax, vmin=0, vmax=max(countries.values()), legend=True, cmap='Blues', missing_kwds={
            "color": "lightgrey",
            "label": "Missing values"
        })

        plt.title(title1)
        plt.savefig(fileloc1, dpi=300)
        plt.close()

        continents = ["Africa", "Asia", "North America", "South America", "Europe", "Oceania"]
        for continent in continents:
            self.plot_continent_map(world, continent, title2, fileloc2, max(countries.values()))

    def plot_continent_map(self, world, continent, title, fileloc, maximum):
        '''
        Plot the continent map with the total edits for each country.
            world: GeoDataFrame - World map data.
            continent: str - Continent name.
            title: str - Title of the continent map.
            fileloc: str - File location for the continent map.
            maximum: int - Maximum value for the color scale.
            return: None 
        '''

        fig = plt.figure(figsize=(20, 10))
        ax = fig.add_subplot()



        # Extract all countries in the continent.
        continent_data = world[world["CONTINENT"] == continent]


        # Set the projection for each continent.
        projections = {
            "Africa": "ESRI:102022",
            "Asia": "ESRI:102025",
            "Europe": "ESRI:102013",
            "North America": "ESRI:102008",
            "South America": "ESRI:102015",
            "Oceania": "EPSG:3112"
        }

        if continent in projections:
            continent_data = continent_data.to_crs(projections[continent])


        # Plot the heatmap
        fig, ax = plt.subplots(1, 1, figsize=(15, 10))
        continent_data.boundary.plot(ax=ax)
        continent_data.plot(column='count', ax=ax, vmin=0, vmax=maximum, legend=True, cmap='Blues', missing_kwds={
            "color": "lightgrey",
            "label": "Missing values"
        })

        plt.title(f"{continent} - {title}") 
        file_loc = fileloc + f"{continent}.png"
        plt.savefig(file_loc, dpi=300)
        plt.close()

    def country_probability(self):
        '''
        Calculate the probabilities that an edit out of all pages in the list come from a specific country.
        Plot a heatmap to show the top 4 countries for the list.
            return: None
        '''
        total = 0
        country_overalls = {}
        probabilities = {}
        for page in self.pages:
            total += page.anon
            countries = page.countries()
            for country, count in countries.items():
                if country in country_overalls:
                    country_overalls[country] += count
                else:
                    country_overalls[country] = count
            
        for country, count in country_overalls.items():
            probabilities[country] = count / total


        # Convert to DataFrame
        df = pd.DataFrame(list(probabilities.items()), columns=["Country", "Probability"])

        # Sort and select top 4
        top4 = df.sort_values(by="Probability", ascending=False).head(4).set_index("Country")

        # Plot heatmap
        sns.set_theme(style="whitegrid")
        plt.figure(figsize=(6, 2.5))
        sns.heatmap(top4, annot=True, cmap="Purples", linewidths=0.5, cbar=False)

        plt.title(f"{self.name} - Top Anonymous Editor Countries")
        plt.tight_layout()
        plt.savefig(f"{self.name}/Country_Probabilities.png", dpi=300)
        plt.close()




class page:
    # Class to handle individual page operations.

    def __init__(self, title, list_name):
        '''
        Initialize the page with the given title and list name.
            title: str - Wikipedia page title.
            list_name: str - Name of the page list the page belongs to.
            return: None
        '''
        self.title = title
        self.list_name = list_name
        self.revisions = self.gather_revisions(title, 2000000) # Gather all revisions for the page.
        # No page has more than 2 million revisions.
        self.rev_count = len(self.revisions) # Count the number of revisions.
        self.registered, self.anon = self.counts() # Count the number of registered and anonymous users.
        self.ratio = self.anon / self.registered # Ratio of anonymous to registered users.

    def gather_revisions(self, title, limit):
        '''
        Gather revisions for the given wikipedia page.
            title: str - Wikipedia page title.
            limit: int - Number of revisions to gather.
            return: list - List of revisions.
        '''

        url = "https://en.wikipedia.org/w/api.php"
        revisions = []
        continue_param = None

        while True:
            # Set up the parameters for the API request.
            params = {
                "action": "query",
                "format": "json",
                "prop": "revisions",
                "titles": title,
                "rvprop": "ids|timestamp|user|anon|comment|size",
                "rvlimit": limit,
            }

            # Add continuation parameter if required.
            if continue_param:
                params["rvcontinue"] = continue_param

            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                page_id = next(iter(data['query']['pages']))
                # Gather revisions from the response.
                revisions += data['query']['pages'][page_id].get('revisions', [])

                # Check if there is further revisions to fetch.
                if "continue" in data:
                    continue_param = data["continue"]["rvcontinue"]
                else:
                    break  # No more revisions.

            except requests.exceptions.RequestException as e:
                print(f"Error fetching revisions for {title}: {e}")
                break

        print(f"Fetched {len(revisions)} revisions for {title}.")
        return revisions
    
    def counts(self):
        '''
        Count the number of registered and anonymous users.
            return: tuple - Number of registered and anonymous users.
        '''
        anon = 0
        registered = 0
        for rev in self.revisions:
            # Check if the user is anonymous.
            if rev.get('user') != None:
                # Check if the user is an IP address
                ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                if re.findall(ip_pattern, rev.get('user')):
                    # If the user is an IP address, increment the anonymous count
                    anon += 1
                else:
                    registered += 1

        return registered, anon
    
    def protection(self):
        '''
        Check if the page is protected.
            return: bool - True if the page is protected, False otherwise.
        '''
        formatted_page = self.title
        # Replace special characters with url encoding.
        formatted_page = formatted_page.replace(" ", "%20")
        formatted_page = formatted_page.replace("_", "%20")
        response = requests.get("https://en.wikipedia.org/w/api.php?action=query&prop=info&format=json&inprop=protection&titles=" + formatted_page)
        if response.status_code == 200:
            data = response.json()
            page_data = data["query"]["pages"]
            for key in page_data:
                protection = page_data[key]["protection"]
                if protection == []:
                    return False
                else:
                    return True
        else:
            print("Failed to fetch the webpage.")
            print("Response Code: ", response.status_code)
            return self.protection()
    
    def ip_loc(self, ip):
        '''
        Get the country location for the given IP address.
            ip: str - IP address.
            return: str - Country name.
        '''

        try:
            reader = geoip2.database.Reader('Geolocation/GeoLite2-Country.mmdb')
            response = reader.country(ip)
            country = str(response.country.name)
            if country == "United States":
                country = "United States of America"
            elif country == "The Netherlands":
                country = "Netherlands"
            elif country == "Türkiye":
                country = "Turkey"
            elif country == "DR Congo":
                country = "Democratic Republic of the Congo"

            return country
        except geoip2.errors.AddressNotFoundError:
            return "Unknown"
        except ValueError:
            return "Unknown"
        
    def countries(self):
        '''
        Get the countries of the users who edited the page.
            return: dict - Dictionary of countries and their counts.
        '''

        countries = {}
        for rev in self.revisions:
            # Check if the user is anonymous.
            if rev.get('user') != None:
                # Check if the user is an IP address
                ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                if re.findall(ip_pattern, rev.get('user')):
                    # If the user is an IP address, get the country
                    country = self.ip_loc(rev.get('user'))
                    if country in countries:
                        countries[country] += 1
                    else:
                        countries[country] = 1

        return countries
    
    def graph_timeline(self):
        '''
        Graph the timeline of revisions.
            return: None
        
        Graph is saved at "List_Name/Timelines/Title.png"
        '''

        time_dict = {
                # [registered, anon]
                2001 : [0,0],
                2002 : [0,0],
                2003 : [0,0],
                2004 : [0,0],
                2005 : [0,0],
                2006 : [0,0],
                2007 : [0,0],
                2008 : [0,0],
                2009 : [0,0],
                2010 : [0,0],
                2011 : [0,0],
                2012 : [0,0],
                2013 : [0,0],
                2014 : [0,0],
                2015 : [0,0],
                2016 : [0,0],
                2017 : [0,0],
                2018 : [0,0],
                2019 : [0,0],
                2020 : [0,0],
                2021 : [0,0],
                2022 : [0,0],
                2023 : [0,0],
                2024 : [0,0]
            }

        for rev in self.revisions:
            timestamp = datetime.strptime(rev.get('timestamp'), "%Y-%m-%dT%H:%M:%SZ")
            year = timestamp.year
            if year != 2025:
                user = rev.get('user')
                if user != None:
                    # Check if the user is an IP address
                    ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                    if re.findall(ip_pattern, user):
                        # If the user is an IP address, increment the anonymous count
                        time_dict[year][1] += 1
                    else:
                        # If the user is not an IP address, increment the registered count
                        time_dict[year][0] += 1


        years = list(time_dict.keys())
        registered = [values[0] for values in time_dict.values()]
        anon = [values[1] for values in time_dict.values()]

        # Plot the graph
        plt.figure(figsize=(12, 6))
        plt.plot(years, registered, label='Registered Users', color='#C7C7C7', marker='o', linestyle='-')
        plt.plot(years, anon, label='Anonymous Users', color='#876FD4', marker='o', linestyle='-')

        # Add labels and title
        plt.xlabel('Year')
        plt.ylabel('Number of Edits')
        plt.suptitle(f'Edit Timeline for {self.title} Wikipedia Page')
        plt.title("Registered Edits vs Anonymous Edits")
        plt.legend()
        plt.grid(True)
        file_path = self.list_name + "/Timelines/" + self.title + ".png"
        if not os.path.exists(f"{self.list_name}/Timelines/"):
            os.mkdir(f"{self.list_name}/Timelines/")
        
        plt.savefig(file_path)
        plt.close()


    def reversions(self):
        '''
        Gather the number of edits reverted straight after being made for each user type.
            return: list - Number of instantly reverted edits for registered and anonymous users.
        '''

        # List to store the number of edits reverted straight after being made for each user type.
        # [registered, anon]
        reverts = [0, 0]

        for i in range(len(self.revisions)-2):
            # Get Revision Size
            size1 = int(self.revisions[i].get('size'))
            size2 = int(self.revisions[i+1].get('size'))
            size3 = int(self.revisions[i+2].get('size'))

            delta1 = size1 - size2
            delta2 = size2 - size3

            if delta1 == -delta2 and delta1 != 0:
                # If the size of the next revision is the negative of the current revision, the revision was reverted.
                if self.revisions[i+1].get('anon') is not None:
                    reverts[1] += 1
                else:
                    reverts[0] += 1

        return reverts[0], reverts[1]


        

            




            
        


    


            