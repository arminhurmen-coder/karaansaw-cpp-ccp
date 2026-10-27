# Karaansaw Cutting Tool Economics — web app prototype

A Streamlit web application for sales engineers to compare existing and proposed cutting tools during customer meetings.

## Visual and workflow features
- Customer-meeting dashboard with branded navy / teal / gold styling.
- CPP and CCP KPI cards for quick discussion.
- Comparison charts for annual costs, tool life and assessed benefits.
- Separate tabs for overview, detailed cost breakdown and report export.
- Customer-ready PDF export and JSON calculation-data export.
- Editable inputs for measured trial data and supporting-cost assumptions.

## Run locally (Windows)
1. Install Python 3.10 or newer.
2. Extract this ZIP and open the `karaansaw_cpp_ccp_webapp` folder.
3. Open Command Prompt in that folder and run:
   ```bat
   py -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   streamlit run app.py
   ```
4. Open `http://localhost:8501` in your browser.

## Publish as one shareable link
The app needs to be hosted before salespeople can use one shared URL. A straightforward route is Streamlit Community Cloud:
1. Put `app.py` and `requirements.txt` in a GitHub repository.
2. Sign in to Streamlit Community Cloud and create an app connected to that repository.
3. Set the main file to `app.py` and deploy.
4. Share the generated `https://....streamlit.app` URL with the sales team.

I cannot create the final hosted URL without access to an authorized hosting account/repository. Do not upload customer-sensitive data to a public repository or use a public deployment for confidential customer/pricing data. This prototype does not include user login or central report storage; reports are generated for download in the user's session. For company-wide use with confidential data, deploy behind company-approved access controls.

## Calculation and validation notes
- CPP = insert price / (average accepted pieces per edge × usable edges per insert).
- Annual volume = monthly accepted production × 12.
- CCP is an internal comparison measure, not the complete factory cost per part.
- Default supporting-cost values are illustrative; replace them with customer/factory evidence.
- Released machine capacity valued at an hourly rate is not automatically cash savings.
- Cutting-cycle-time differences are not priced in this prototype.
- Before customer use, validate the calculation engine against approved reference cases and obtain engineering/finance sign-off.
