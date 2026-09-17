import gradio as gr
import sqlite3
import numpy as np
import pandas as pd

def create_gradio_dataframe():
    connection = sqlite3.connect("data/taiwan_presidential_election_2024.db")
    votes_by_village = pd.read_sql("""SELECT * FROM votes_by_village;""",con=connection)
    connection.close()

    total_votes = votes_by_village["sum_of_votes"].sum()
    total_notes_by_candidate = votes_by_village.groupby(["candidate_number"])["sum_of_votes"].sum()
    country_percentage = total_notes_by_candidate / total_votes
    vector_a = country_percentage.values


    groupby_variable = ["county","town","village"]
    groupby_variable_by_candidate = ["county", "town","village","candidate_number"]
    village_total_votes = votes_by_village.groupby(groupby_variable)["sum_of_votes"].sum().reset_index()

    merged_votes_by_village = pd.merge(votes_by_village,village_total_votes,
                                    left_on=groupby_variable, right_on=groupby_variable,
                                    how="left")
    merged_votes_by_village["village_percentage"] = merged_votes_by_village["sum_of_votes_x"] / merged_votes_by_village["sum_of_votes_y"]
    pivot_votes_by_village = merged_votes_by_village.pivot(index=groupby_variable,
                                columns="candidate_number",
                                values="village_percentage").reset_index()
    pivot_votes_by_village = pivot_votes_by_village.rename_axis(None, axis=1)

    cosine_similarities = []
    length_vector_a = pow((vector_a**2).sum(), 0.5)
    for row in pivot_votes_by_village.iterrows():
        vector_bi = np.array([row[1][1], row[1][2], row[1][3]])
        vector_a_dot_vector_bi = np.dot(vector_a, vector_bi)
        length_vector_bi = pow((vector_bi**2).sum(), 0.5)
        cosine_similarity = vector_a_dot_vector_bi / (length_vector_a * length_vector_bi)
        cosine_similarities.append(float(cosine_similarity))

    cosine_similarity_db = pivot_votes_by_village.loc[:,:]
    cosine_similarity_db["cosine_similarity"] = cosine_similarities
    cosine_similarity_db = cosine_similarity_db.sort_values(["cosine_similarity", "county", "town", "village"], 
                                                            ascending=[False, True, True, True])
    cosine_similarity_db = cosine_similarity_db.reset_index(drop=True).reset_index()
    cosine_similarity_db["index"] = cosine_similarity_db["index"] + 1
    column_names_to_revise = {1:"candidates_1",
                            2:"candidates_2",
                            3:"candidates_3",
                            "index": "similarity_rank"
                            }
    cosine_similarity_db = cosine_similarity_db.rename(columns=column_names_to_revise)
    return vector_a, cosine_similarity_db

def filter_county_town_village(df, county_name, town_name, village_name):
    condition_county = df["county"] == county_name
    condition_town = df["town"] == town_name
    condition_village = df["village"] == village_name
    return df[condition_county & condition_town & condition_village]

country_percentage, gradio_dataframe = create_gradio_dataframe()
ko_wu, lai_hsiao, hou_chao = country_percentage

interface = gr.Interface(fn=filter_county_town_village,
                         inputs=[
                                 gr.DataFrame(gradio_dataframe),
                                 "text",
                                 "text",
                                 "text"
                                 ],
                         outputs="dataframe",
                         title="找出章魚里",
                         description=f"輸入你想篩選的縣市、鄉鎮市區、村鄰里:  (柯吳配, 賴蕭配, 侯趟配) = ({ko_wu:.6f}, {lai_hsiao:.6f}, {hou_chao:.6f})"
)
interface.launch()

