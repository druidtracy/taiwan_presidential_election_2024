import os
import re
import sqlite3
import pandas as pd

class CreateTaiwanPresidentialElection2024DB:
    def __init__(self):
        file_names = os.listdir("data")
        county_names = []
        for file_name in file_names:
            if ".xlsx" in file_name:
                file_name_split = re.split("\\(|\\)", file_name)
                county_names.append(file_name_split[1])
        self.county_names = county_names

    def tidy_county_dataframe(self, county_names: str):
        file_path = f"data/總統-A05-4-候選人得票數一覽表-各投開票所({county_names}).xlsx"
        df = pd.read_excel(file_path, skiprows=[0, 3, 4])
        df = df.iloc[:,:6]
        cadidates_info = df.iloc[0,3:].values.tolist()
        df.columns = ["town","village","polling_place"] + cadidates_info
        df.loc[:,"town"] = df["town"].ffill()
        df.loc[:,"town"] = df["town"].str.strip()
        df = df.dropna()
        df["polling_place"] = df["polling_place"].astype(int)
        id_variables_for_melt = ["town","village","polling_place"]
        melted_df = pd.melt(df, id_vars=id_variables_for_melt, value_vars = cadidates_info, var_name = "candidate", value_name="votes")
        melted_df["county"] = county_names
        return melted_df

    def concat_county_dataframe(self):
        country_df = pd.DataFrame()
        for county_name in self.county_names:
            county_df = self.tidy_county_dataframe(county_name)
            country_df = pd.concat([country_df, county_df])
        country_df = country_df.reset_index(drop=True)
        numbers, candidates = [], []
        for element in country_df["candidate"].str.split("\n"): #[(1), name1, name2]
            number = re.sub(r"[()]", "", element[0])
            candidate = element[1] + "/" + element[2]
            numbers.append(int(number))
            candidates.append(candidate)
        presidential_votes = country_df.loc[:, ["county","town","village","polling_place"]]
        presidential_votes["number"] = numbers
        presidential_votes["candidate"] = candidates
        presidential_votes["votes"] = country_df["votes"].values
        return presidential_votes

    def create_database(self):
        presidential_votes = self.concat_county_dataframe()

        polling_place_df = presidential_votes.groupby(["county","town","village", "polling_place"]).count().reset_index()
        polling_place_df = polling_place_df.loc[:, ["county","town","village", "polling_place"]]
        polling_place_df = polling_place_df.reset_index()
        polling_place_df["index"] = polling_place_df["index"] + 1
        polling_place_df = polling_place_df.rename(columns={"index":"id"})
        # print(polling_place_df) #(17795, 5)

        candidates_df = presidential_votes.groupby(["number","candidate"]).count().reset_index()
        candidates_df = candidates_df.loc[:,["number","candidate"]]
        candidates_df = candidates_df.reset_index()
        candidates_df["index"] = candidates_df["index"] + 1
        candidates_df = candidates_df.rename(columns={"index":"id"})
        # print(candidates_df) #(3, 3)

        join_key = ["county", "town","village","polling_place"]
        votes_df = pd.merge(presidential_votes, polling_place_df, 
                            left_on=join_key, right_on=join_key, 
                            how="left")
        votes_df = votes_df.loc[:,["id", "number", "votes"]]
        votes_df = votes_df.rename(columns={"id":"polling_place_id", 
                                            "number":"candidate_id"})
        # print(votes_df)
        
        connection = sqlite3.connect("data/taiwan_presidential_election_2024.db")
        polling_place_df.to_sql("polling_places", con=connection, if_exists="replace", index=False)
        candidates_df.to_sql("candidates", con=connection, if_exists="replace", index=False)
        votes_df.to_sql("votes", con=connection, if_exists="replace", index=False)

        cur = connection.cursor()
        drop_view_sql = """DROP VIEW IF EXISTS votes_by_village;"""
        create_view_sql = """
        CREATE VIEW votes_by_village AS
        SELECT polling_places.county,
               polling_places.town,
               polling_places.village,
               candidates.id AS candidate_number,
               sum(votes.votes) AS sum_of_votes
            FROM votes
            LEFT JOIN polling_places
            ON votes.polling_place_id = polling_places.id
            LEFT JOIN candidates
            ON votes.candidate_id = candidates.id
            group by polling_places.county,
                     polling_places.town,
                     polling_places.village,
                     candidates.id
        """
        cur.execute(drop_view_sql)
        cur.execute(create_view_sql)
        connection.close()



create_taiwan_presidential_election_2024 = CreateTaiwanPresidentialElection2024DB()
create_taiwan_presidential_election_2024.create_database()