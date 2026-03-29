import warnings
warnings.filterwarnings('ignore')
import os
import secrets
import io
import pandas as pd
import time

from quart import Quart, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from datetime import datetime
from src.utility import users, get_home_dropdwon_info
from src.functions import *

# --------------------
# USER-ISOLATED STORAGE
# --------------------
user_store = {}   # username → {"metadata":{}, "similarity_df": dataframe}


# --------------------
# APP CONFIG
# --------------------
USERS = users.get("Users")
current_date = str(datetime.now()).split(" ")[0]

app = Quart(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(24))

dataset    = load_dataset()
title_list = ["All"] + [ row for row in dataset["Title"].unique().tolist()]

# print("title_list",title_list)

# --------------------
# HELPERS
# --------------------
def get_user_meta(username):
    """Return per-user isolated metadata."""
    if username not in user_store:
        user_store[username] = {
            "metadata": get_home_dropdwon_info(),
            "similarity_df": None
        }

        user_store[username]["metadata"]['user_awareness'] = title_list
        print("user_awareness", user_store[username]["metadata"])
    return user_store[username]["metadata"]


def set_user_meta(username, metadata):
    user_store[username]["metadata"] = metadata


def set_user_similarity(username, df):
    user_store[username]["similarity_df"] = df


def get_user_similarity(username):
    return user_store[username].get("similarity_df")


# --------------------
# LOGIN
# --------------------
@app.route("/login", methods=["GET", "POST"])
async def login():
    if request.method == "POST":
        form = await request.form
        username = form.get("username")
        password = form.get("password")

        if USERS.get(username) == password:
            session["username"] = username

            if username not in user_store:
                user_store[username] = {
                    "metadata": get_home_dropdwon_info(),
                    "similarity_df": None
                }

            await flash("Login successful!", "success")
            return redirect(url_for("home"))

        else:
            await flash("Invalid credentials", "danger")

    return await render_template("login.html")


# --------------------
# LOGOUT
# --------------------
@app.route("/logout")
async def logout():
    username = session.get("username")

    if username in user_store:
        del user_store[username]   # delete only this user's data

    session.clear()
    await flash("Logged out", "info")
    return redirect(url_for("login"))


# --------------------
# HOME PAGE
# --------------------
@app.route("/")
async def home():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]

    metadata = get_user_meta(username)
    similarity_df = get_user_similarity(username)

    metadata["timestamp"] = int(time.time())

    if similarity_df is not None and similarity_df.shape[0] != 0:

        filtered = similarity_df[
            similarity_df["Score"] >= float(metadata["selected_similarity"])
        ].sort_values("Score", ascending=False)

        # Frequency Plot
        if filtered.shape[0] != 0:
            metadata["frequency_plot"] = word_frequency_plot(username, filtered, "Issue")
        else:
            metadata["frequency_plot"] = None

        # Ticket count & range
        if filtered.shape[0] != 0:
            min_s = filtered["Score"].min()
            max_s = filtered["Score"].max()

            metadata["number_of_ticket"] = filtered.shape[0]
            metadata["similarity_range"] = f"{round(min_s,2)} (min) to {round(max_s,2)} (max)"

            # Recommendations
            limit = int(metadata["selected_recommandation"])
            recs = []

            for row in filtered.iloc[:limit, :].values:
                recs.append(
                    TicketDataModel(
                        name=row[0],
                        similarity_score=round(row[1], 2),
                        other=row[2] if type(row[2]) != float else None,
                        issue=row[3] if type(row[3]) != float else None,
                        rca=row[4] if type(row[4]) != float else None,
                        resolution=row[5] if type(row[5]) != float else None,
                        short_description=row[6] if type(row[6]) != float else None,
                        resolution_category=row[7] if type(row[7]) != float else None,
                    )
                )

            metadata["recommandations"] = recs

        else:
            metadata["number_of_ticket"] = "0"
            metadata["similarity_range"] = "0"
            metadata["recommandations"] = []
            metadata["frequency_plot"] = None

    else:
        metadata["number_of_ticket"] = "0"
        metadata["similarity_range"] = "0"
        metadata["recommandations"] = []
        metadata["frequency_plot"] = None

    set_user_meta(username, metadata)

    return await render_template(
        "home.html",
        username=username,
        form_data=metadata,
        current_date=current_date,
        years=current_date.split("-")[0],
    )


# --------------------
# HOME FORM SUBMIT
# --------------------
@app.route("/submit_home_form", methods=["POST"])
async def submit_home_form():
    username = session["username"]
    metadata = get_user_meta(username)

    form = await request.form
    rec = form.get("number_of_recommendation")
    sim = form.get("similarity_score_limit")

    metadata["selected_recommandation"] = rec
    metadata["selected_similarity"] = sim
    metadata["timestamp"] = int(time.time())

    metadata = get_updated_dropdown_info(
        metadata=metadata,
        form_info={"number_of_recommendation": rec, "similarity_score_limit": sim},
    )

    set_user_meta(username, metadata)
    await flash("Form submitted!", "success")
    return redirect(url_for("home"))


# --------------------
# USER INPUT FORM SUBMIT
# --------------------
@app.route("/submit_user_input_form", methods=["POST"])
async def submit_user_input_form():
    username = session["username"]
    metadata = get_user_meta(username)

    form = await request.form
    issue_info = form.get("issue_info")
    reporting_parameter = form.get("report_paramerter")
    user_awareness = form.get("user_awareness")

    print(f"issue_info: {issue_info}, reporting_parameter: {reporting_parameter}, user_awareness: {user_awareness}")
    
    print("user_awareness:", user_awareness,'\n\n')

    if user_awareness!="All":
        dataset_upg = dataset[dataset["Title"]==user_awareness]
    else:
        dataset_upg = dataset

    sim_df = get_similarity_search(issue_info, dataset_upg)

    if reporting_parameter.lower() != "other":
        sim_df["filter_info"] = (
            sim_df["Issue"] + " " + sim_df["Title"] + " " + sim_df["Short Description"]
        )
        sim_df["match"] = sim_df["filter_info"].apply(
            lambda t: word_matching(reporting_parameter, str(t))
        )
        sim_df = sim_df[sim_df["match"] == True]
        sim_df.drop(columns=["filter_info", "match"], inplace=True)

    # save DF separately
    set_user_similarity(username, sim_df)

    metadata["report_paramerter"] = reporting_parameter
    # metadata["user_awareness"] = [user_awareness]

    metadata["user_awareness"] = [user_awareness] + [row for row in title_list if row != user_awareness]
    metadata["issue_info"] = issue_info
    metadata["timestamp"] = int(time.time())

    set_user_meta(username, metadata)

    await flash("Submitted!", "success")
    return redirect(url_for("home"))


# --------------------
# DOWNLOAD EXCEL
# --------------------
@app.route("/download_excel")
async def download_excel():
    username = session["username"]
    metadata = get_user_meta(username)

    recs = metadata.get("recommandations", [])

    df = pd.DataFrame([row.model_dump() for row in recs]) if len(recs) else pd.DataFrame()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Sheet1")
    output.seek(0)

    return await send_file(
        output,
        as_attachment=True,
        attachment_filename="recommendations.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/download_sample_data")
async def download_sample_data():
    username = session["username"]
    metadata = get_user_meta(username)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as w:
        dataset.to_excel(w, index=False, sheet_name="Sheet1")
    output.seek(0)

    return await send_file(
        output,
        as_attachment=True,
        attachment_filename="sample_dataset.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# --------------------
# RUN
# --------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)