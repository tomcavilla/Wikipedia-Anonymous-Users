from classes import page_list
from datetime import datetime
import pickle, os, json
from matplotlib import pyplot as plt
import numpy as np
plt.rcParams.update({'figure.max_open_warning': 0})

graph_colours = ["#876FD4", "#C7C7C7", "#92C5F9"]


if __name__ == "__main__":
    lists = ["Countries", "Leaders", "Brands", "Sports"]
    '''
    Countries - List of all UN recognised countries, taken from the UN website.
    Leaders - List of all current world leaders, taken from the CIA website.
    Brands - Top 100 brands in the world, taken from Interbrand.
    Sports - List of all current olympic sports, taken from Olympics.com.
    '''

    # Check if the class already exists. If it does, load it from the pickle file.
    # If it doesn't, create a new instance.
    list_objects = []
    for i in lists:
        if os.path.exists(f"Classes/{i}.pkl"):
            with open(f"Classes/{i}.pkl", "rb") as file:
                i = pickle.load(file)
                list_objects.append(i)
        else:
            i = page_list(i)
            list_objects.append(i)

 
    protections = []
    list_reg_edit_averages = []
    list_anon_edit_averages = []
    list_comment_probabilities = []
    reverts = {}

    for i in list_objects:
        # Basic statistics about the list.
        anon = 0
        total = 0
        max_revs = 0
        max_page = ""
        for j in i.pages:
            anon += j.anon
            total += j.rev_count
            if j.rev_count > max_revs:
                max_revs = j.rev_count
                max_page = j.title


        print(f"{i.name} - Total Edits: {total}, Anonymous Edits: {anon}, Ratio: {anon / total}")
        print(f"Most Edited Page: {max_page} - {max_revs} Edits")


        # Graphs for all lists.

        # Average Edit Size by User Type per Page

        page_data = {}
        protections_indiv = []
        reverts[i.name] = [0,0]
        for j in i.pages:
            
            revisions = list(j.revisions)[::-1]  # Reverse the list, oldest first.
            prev_size = 0

            anon_edits = []
            reg_edits = []

            protections_indiv.append(j.protection())

            page_reverts_r, page_reverts_a = j.reversions()
            reverts[i.name][0] += page_reverts_r
            reverts[i.name][1] += page_reverts_a

            for rev in revisions:
                # Size returns the page size after the edit is made. Therefore the delta between that and the previous size is the edit size.
                size = rev.get('size', 0)
                change = size - prev_size
                prev_size = size

                if change == 0:
                    continue

                if rev.get('anon') is not None:
                    anon_edits.append(change)
                else:
                    reg_edits.append(change)

            # Store the average edit sizes per page for each user type.
            if anon_edits or reg_edits:
                page_data[j.title] = {
                    'anon_avg': sum(anon_edits) / len(anon_edits) if anon_edits else 0,
                    'reg_avg': sum(reg_edits) / len(reg_edits) if reg_edits else 0
                }

        # Plotting
        titles = list(page_data.keys())
        anon_avg_sizes = [page_data[title]['anon_avg'] for title in titles]
        reg_avg_sizes = [page_data[title]['reg_avg'] for title in titles]

        list_reg_edit_averages.append(sum(reg_avg_sizes) / len(reg_avg_sizes))
        list_anon_edit_averages.append(sum(anon_avg_sizes) / len(anon_avg_sizes))

        fig, ax = plt.subplots(figsize=(20, 6))

        x = np.arange(len(titles))
        width = 0.35

        ax.bar(x - width/2, anon_avg_sizes, width=width, label='Anonymous', color=graph_colours[0])
        ax.bar(x + width/2, reg_avg_sizes, width=width, label='Registered', color=graph_colours[2])

        ax.set_xlabel("Page")
        ax.set_ylabel("Average Edit Size (Bytes)")
        ax.set_title(f"{i.name} - Average Edit Size by User Type per Page")
        ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1))
        fig.savefig(f"{i.name}/Avg_Edit_Size.png", dpi=300)
        plt.close()
            
        # Plot the world + continent maps for the list - where anonymous users are located.            
        i.plot_world_totals()
        # Plot the edit timelines for each of the pages.
        [j.graph_timeline() for j in i.pages]

        # Plot the largest edit probabilities for each page.
        i.country_probability()

        # Analyse the likelihood of a user to leave a comment on a page for either user type.
        anons = []
        regs = []
        # Lists of the probabilities for each page.
        for j in i.pages:
            anon = []
            reg = []

            for rev in j.revisions:
                if rev.get('anon') is not None:
                    anon.append(rev)
                else:
                    reg.append(rev)
            
            anon_comments = [rev for rev in anon if rev.get('comment')]
            reg_comments = [rev for rev in reg if rev.get('comment')]

            if len(anon) != 0:
                anons.append(len(anon_comments) / len(anon))
            else:
                anons.append(0)
            if len(reg) != 0:
                regs.append(len(reg_comments) / len(reg))
            else: 
                regs.append(0)


        list_comment_probabilities.append([sum(anons) / len(anons), sum(regs) / len(regs)])
        # Plotting

        page_titles = [j.title for j in i.pages]
        bar_width = 0.5
        bar_gap = 0.5      # space between paired bars
        group_gap = 0.4    # space between groups

        # Compute evenly spaced group centers
        x = [i * (bar_width * 2 + bar_gap + group_gap) for i in range(len(page_titles))]

        # Bar positions with gap between them
        anon_positions = [pos - (bar_width + bar_gap) / 2 for pos in x]
        reg_positions = [pos + (bar_width + bar_gap) / 2 for pos in x]

        plt.figure(figsize=(15, 6))
        plt.bar(anon_positions, anons, width=bar_width, label='Anonymous Users', color=graph_colours[0])
        plt.bar(reg_positions, regs, width=bar_width, label='Registered Users', color=graph_colours[1])

        plt.xlabel('Page')
        plt.ylabel('Probability of Leaving a Comment')
        plt.title(f'{i.name} - Likelihood of Leaving a Comment by User Type per Page')
        plt.legend()
        plt.tight_layout()

        plt.savefig(f"{i.name}/Likelihood_Comment.png", dpi=300)
        plt.close()

        protections.append(protections_indiv)

        if i.name == "Countries":
            # Country List Specific Graphs
            anons = {}
            ratios = {}
            for j in i.pages:
                title = j.title
                title = title.replace("_", " ")
                anons[title] = j.anon
                ratios[title] = j.ratio


            i.plot_world_map(anons, "Anonymous Edits to Country Wikipedia Pages", "Anonymous Edits to Country Wikipedia Pages", "Countries/World_Maps_Pages/Anon_Totals/World.png", "Countries/World_Maps_Pages/Anon_Totals/")
            i.plot_world_map(ratios, "Ratio of Anonymous Edits to Total Edits on Country Wikipedia Pages", "Ratio of Anonymous Edits to Total Edits on Country Wikipedia Pages", "Countries/World_Maps_Pages/Ratios/World.png", "Countries/World_Maps_Pages/Ratios/")


            # Create scatter plot of Development Index vs. % Anonymous Edits
            region_colours = {
                "Africa": "red",
                "Asia": "blue",
                "North America": "green",
                "South America": "orange",
                "Europe": "purple",
                "Oceania": "brown",
                "Central America": "pink",
                "Caribbean": "yellow",
            }
            revision_data = {}
            for country in i.pages:
                revision_data[country.title] = [country.rev_count, country.anon]

            dev_data = json.load(open("World_Map_Data/Country_HDI.json", "r"))

            x_values = []  # Development Index
            y_values = []  # % Anonymous Edits
            colours = []

            # Data for individual regions
            region_data = {region: {"x": [], "y": []} for region in region_colours}

            for country in revision_data:
                if country in dev_data and revision_data[country][0] > 0:  # Ensure country exists in both.
                    total_revisions = revision_data[country][0]
                    anon_revisions = revision_data[country][1]
                    dev_index = dev_data[country]
                    region = ""
                    with open("World_Map_Data/Country-Region.json", "r") as file:
                        region_mapping = json.load(file)
                    
                    for r, countries in region_mapping.items():
                        if country in countries:
                            region = r


                    if dev_index is not None and dev_index >= 0 and region in region_colours:
                        anon = (anon_revisions / total_revisions) * 100
                        x_values.append(dev_index)
                        y_values.append(anon)
                        colours.append(region_colours[region])

                        # Add data to the corresponding region
                        region_data[region]["x"].append(dev_index)
                        region_data[region]["y"].append(anon)
                
            # Axis Limits to keep all graphs consistent.
            x_min, x_max = min(x_values) - 0.1, max(x_values) + 0.1
            y_min, y_max = 0, max(y_values) + 5

            # Create overall scatter plot
            plt.figure(figsize=(10, 6))
            plt.scatter(x_values, y_values, c=colours, alpha=0.6, edgecolors="black")
            
            plt.xlabel("Development Index")
            plt.ylabel("Percentage of Anonymous Edits")
            plt.title("Development Index vs. Percentage of Anonymous Wikipedia Edits")
            plt.xlim(x_min, x_max)
            plt.ylim(y_min, y_max)

            legend_labels = [plt.Line2D([0], [0], marker='o', color='w', label=region, markerfacecolor=colour, markersize=10) for region, colour in region_colours.items()]
            plt.legend(handles=legend_labels, title="Region", loc="upper left", bbox_to_anchor=(1.05, 1))
            
            plt.grid(True, linestyle="--", alpha=0.5)
            plt.tight_layout()
            plt.savefig("Countries/Development_Index/Overall.png", dpi=300)
            plt.close()

            # Create individual scatter plots for each region
            for region, data in region_data.items():
                plt.figure(figsize=(10, 6))
                plt.scatter(data["x"], data["y"], c=region_colours[region], alpha=0.6, edgecolors="black")
                
                plt.xlabel("Development Index")
                plt.ylabel("Percentage of Anonymous Edits")
                plt.title(f"Development Index vs. Percentage of Anonymous Edits ({region})")
                plt.xlim(x_min, x_max)
                plt.ylim(y_min, y_max)
                
                plt.grid(True, linestyle="--", alpha=0.5)
                plt.tight_layout()
                plt.savefig(f"Countries/Development_Index/{region}.png", dpi=300)
                plt.close()



            # Median Scatter Plot


            # Prepare median values
            region_medians_x = []
            region_medians_y = []
            region_median_colours = []

            for region, data in region_data.items():
                if data["x"] and data["y"]:
                    median_x = np.median(data["x"])
                    median_y = np.median(data["y"])
                    region_medians_x.append(median_x)
                    region_medians_y.append(median_y)
                    region_median_colours.append(region_colours[region])



            # Create scatter plot for medians
            plt.figure(figsize=(10, 6))
            plt.scatter(region_medians_x, region_medians_y, c=region_median_colours, alpha=0.8, edgecolors="black", s=100)

            # Add region labels next to each point
            for i, region in enumerate(region_colours.keys()):
                if i < len(region_medians_x):
                    plt.text(region_medians_x[i] + 0.01, region_medians_y[i], region, fontsize=9, va='center')

            plt.xlabel("Development Index")
            plt.ylabel("Percentage of Anonymous Edits")
            plt.title("Development Index vs. Percentage Anonymous Wikipedia Edits Medians for Region")
            plt.xlim(x_min, x_max)
            plt.ylim(y_min, y_max)

            plt.grid(True, linestyle="--", alpha=0.5)
            plt.tight_layout()
            plt.savefig("Countries/Development_Index/Region_Medians.png", dpi=300)
            plt.close()

            # Create Box Plot for each Region.

            plt.figure(figsize=(10, 6))

            # Plot boxplots for each region
            for region, data in region_data.items():
                position = list(region_colours.keys()).index(region)
                plt.boxplot(data["y"], positions=[position], widths=0.5)

            plt.xticks(range(len(region_colours)), region_colours.keys(), rotation=45)
            plt.xlabel("Region")
            plt.ylabel("Percentage of Anonymous Edits")
            plt.title("Box Plot of Anonymous Edits by Region")
            plt.grid(True, linestyle="--", alpha=0.5)

            plt.tight_layout()
            plt.savefig("Countries/Boxplot.png", dpi=300)
            plt.close()



    # Grouped Bar Plot for the average edit size, for each user type, for each list.
    x = np.arange(4)
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))


    reg_bars = ax.bar(x, [i for i in list_reg_edit_averages], width=width, label='Registered', color=graph_colours[1])
    anon_bars = ax.bar(x, [i for i in list_anon_edit_averages], width=width, label='Anonymous', color=graph_colours[0])
    


    ax.set_ylabel("Average Edit Size (Bytes)")
    ax.set_title('Average Edit Size by User Type for Each List')

    ax.set_xticks(x, labels=lists)
    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1))

    for bars in [anon_bars, reg_bars]:
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.2f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig("Overall/Average_Edit_Size.png", dpi=300)
    plt.close()


    # Grouped Bar Plot for the average comment probability, for each user type, for each list.
    fig, ax = plt.subplots(figsize=(10, 6))
    reg_bars = ax.bar(x-width/2, [i[1] for i in list_comment_probabilities], width=width, label='Registered', color=graph_colours[1])
    anon_bars = ax.bar(x+width/2, [i[0] for i in list_comment_probabilities], width=width, label='Anonymous', color=graph_colours[0])
    ax.set_ylabel("Probability of Leaving a Comment")
    ax.set_title('Likelihood of Leaving a Comment by User Type for Each List')

    ax.set_xticks(x, labels=lists)
    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1))
    for bars in [anon_bars, reg_bars]:
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.2f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig("Overall/Likelihood_Comment.png", dpi=300)
    plt.close()

        

    # Plot the protection proportions for each list in pie charts on the same plot.

    labels = ['Protected', 'Unprotected']
    fig, axs = plt.subplots(2,2, figsize=(10, 8))
    prot_proportions = []
    for p_list in protections:
        protected = p_list.count(True)
        total = len(p_list)
        prot_proportions.append(round((protected / total) * 100))

    axs[0,0].pie([prot_proportions[0], 100 - prot_proportions[0]], colors=[graph_colours[0], graph_colours[1]], labels=labels, autopct='%1.1f%%', startangle=90)
    axs[0,0].set_title('Countries')

    axs[0,1].pie([prot_proportions[1], 100 - prot_proportions[1]], colors=[graph_colours[0], graph_colours[1]], labels=labels, autopct='%1.1f%%', startangle=90)
    axs[0,1].set_title('Leaders')

    axs[1,0].pie([prot_proportions[2], 100 - prot_proportions[2]], colors=[graph_colours[0], graph_colours[1]], labels=labels, autopct='%1.1f%%', startangle=90)
    axs[1,0].set_title('Brands')

    axs[1,1].pie([prot_proportions[3], 100 - prot_proportions[3]], colors=[graph_colours[0], graph_colours[1]], labels=labels, autopct='%1.1f%%', startangle=90)
    axs[1,1].set_title('Sports')
    plt.tight_layout()
    plt.savefig("Overall/Protection_Proportions.png", dpi=300)


    # Group Bar Plot for the number of instant reversions for each user type, for each list.
    
    registered = [reverts[x][0] for x in lists]
    anonymous = [reverts[x][1] for x in lists]

    x = np.arange(len(lists))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    reg_bars = ax.bar(x-width/2, registered, width=width, label='Registered', color=graph_colours[1])
    anon_bars = ax.bar(x+width/2, anonymous, width=width, label='Anonymous', color=graph_colours[0])
    ax.set_ylabel("Number of Instant Reversions")
    ax.set_title('Number of Instant Reversions by User Type for Each List')
    ax.set_xticks(x, labels=lists)
    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1))
    for bars in [anon_bars, reg_bars]:
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig("Overall/Instant_Reversions.png", dpi=300)
    plt.close()
    


    for i in list_objects:
        # Save all current objects to their individual pickle files.
        with open(f"Classes/{i.name}.pkl", "wb") as file:
            pickle.dump(i, file)

        
        



    
    
