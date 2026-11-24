# YTL Bukit Sagu | CCUS Decision & Optimization Tool

A native Streamlit dashboard for the USM EKC 503 Group 2 case study. The model adapts the submitted Week 5–7 coursework. Costs, prices, process inputs and carbon revenues are illustrative screening assumptions.

## Deploy privately on Streamlit Community Cloud

1. Extract this ZIP and commit its contents to the root of a **private GitHub repository** you administer. Include the hidden `.streamlit` folder so the app uses the supplied theme.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), select **Create app** and use the repository and branch containing the files. Connect your private GitHub repository if it does not appear.
3. Set **Main file path** to `streamlit_app.py`. Select **Python 3.12** under Advanced settings, then deploy. The app needs no secrets or external databases.
4. Check the app's sharing settings for private visibility. Use the generated `.streamlit.app` URL. Invite your lecturer as a viewer through Streamlit if you want them to access it privately.

If you already have a private Streamlit app for this project, commit this package to the branch and path it uses. Community Cloud updates deployed apps when the source changes. Follow the private access settings above before adding any viewers.

[Streamlit deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) · [Private app sharing](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app)

## Run on your computer

From the extracted folder, using Python 3.12:

```sh
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Run `python test_model.py` to verify the submitted baseline and optimization constraints.

## Dashboard

| View | What you can do |
| --- | --- |
| Overview | Edit capture technology, efficiency, carbon price, aggregate price and utility costs. Read the six KPIs and compare full and right-sized capture designs. |
| Carbon & finance | Trace capture, fixation, venting and net avoidance. Review costs, revenues, break-even and the three investment boundaries. |
| Sensitivity | Sweep carbon price, aggregate price, utility price, capture efficiency or the saleable aggregate fraction. Inspect the chart and its values. |
| Optimization | Search both technologies for maximum NPV, maximum net avoidance or minimum abatement cost. Apply a treatment cap, avoidance target or non-negative NPV requirement. |
| Assumptions | Review inputs by pathway, workbook provenance, methods and validation gaps. |

The CSV button exports the current right-sized scenario. Switching technology loads its reference capture efficiency. The comparison and optimization then use the current sidebar efficiency for both technologies.

At the default solid adsorption assumptions, the integrated case treats **55.79%** of kiln flue gas, returns **USD 12.21 million** NPV and avoids **46,063 tCO₂e/year**. Verify the facility data and commercial assumptions before engineering or investment use.
