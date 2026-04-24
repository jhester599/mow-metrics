Project Prompt for Coding Agent
Role & Objective
You are an expert Python developer and automation engineer. Your task is to build a complete GitHub repository for a lightweight, free-to-host Streamlit dashboard. The application is a decision-support tool designed to track weekly lawn mowing schedules, predict if a mow occurred based on weather data, and allow the user to confirm/deny the prediction for monthly billing reconciliation.

Tech Stack & Constraints

Frontend & App Framework: Python with Streamlit.

Database/Persistence: Google Sheets (using gspread or Streamlit's st.connection).

Weather API: Open-Meteo API (free, no auth required).

Automation: GitHub Actions.

Hosting: Streamlit Community Cloud.

Core Features & Requirements

1. User Onboarding & Seasonality Setup (The UI)

Build a "Setup / New User" flow in the Streamlit app where a user can establish their profile.

Inputs must include: Username, Calendar Year (e.g., 2026), Location (Zip code or Lat/Lon), and Expected Mow Day (e.g., Wednesday).

Seasonality Logic: The app must determine a realistic "Mowing Season" (Start Date and End Date) based on the provided location.

Requirement: Research and implement a lightweight heuristic or lookup mechanism to estimate this (e.g., mapping USDA hardiness zones or latitude to active growing months).

Prototype Default: For the zip code 44236, the application should default the active mowing season to April 1 through November 30.

Save these configuration details to a designated Users_Config tab in the Google Sheet.

2. The Data Schema (Google Sheets)

Design a Google Sheet schema with two main areas:

Users_Config Tab: Columns for Username, Active Year, Location, Mow Day, Season Start, and Season End.

Log Tab: A centralized log storing the records. Columns must include: Username, Year, Date (expected mow date), Expected Day, Weather Summary, Raw API JSON, Predicted Status (Mowed / Skipped), and Confirmed Status (Pending / Yes / No). Note: The data should be easily filterable by Username and Year.

3. The Automation Engine (GitHub Actions + Python Script)

Write an independent Python script fetch_and_predict.py triggered by a daily GitHub Actions cron job.

The script should:

Read the Users_Config tab to loop through all active users for the current calendar year.

Seasonality Check: For each user, verify if today's date falls within their defined Season Start and Season End. If outside the season, skip the user entirely.

Determine if yesterday was the user's Expected Mow Day.

If yes, query the Open-Meteo API for yesterday's precipitation data at their location.

Implement prediction logic: If significant rainfall occurred during typical working hours, predict Skipped. Otherwise, predict Mowed.

Append a new row to the Log tab with the prediction. The Confirmed Status should default to "Pending".

4. The Reconciliation Dashboard (Streamlit Frontend)

The main Streamlit view should act as a user-specific dashboard. The user selects their Username and the Year from a dropdown menu.

The app fetches the Log tab, filters by the selected User/Year, and displays it as an interactive table or dataframe.

For any row where the Confirmed Status is "Pending", provide a simple UI element allowing the user to manually confirm "Yes, mowed" or "No, skipped" based on observation.

Instantly write manual overrides back to the Google Sheet.

Include a summary metric at the top showing "Total Confirmed Mows This Month" (dynamically calculated based on the current month) for easy billing reconciliation.

5. Repository Structure & Documentation
Please generate the full directory structure, including:

app.py (The Streamlit dashboard)

fetch_and_predict.py (The backend automation script)

.github/workflows/weather_check.yml (The cron job configuration)

requirements.txt

README.md (Including clear instructions on setting up Google Sheets Service Account credentials and GitHub Secrets).

Please begin by outlining the file structure and explaining your approach to the geographic seasonality logic. Then, provide the code for each file sequentially. Ensure all code is highly documented.
