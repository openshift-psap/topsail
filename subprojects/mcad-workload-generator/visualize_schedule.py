import sys
import pandas as pd
import plotly.express as px
import json
import pathlib

import logging
logging.getLogger().setLevel(logging.INFO)

IMAGE_HEIGHT = 650
IMAGE_WIDTH = 1200

def save(fig, name, name_suffix, artifact_dir):
    logging.info(f"Saving the {name} into schedule_result_{name_suffix}.{{html,png}} ...")
    fig.write_html(artifact_dir / f"schedule_result_{name_suffix}.html")
    fig.write_image(artifact_dir / f"schedule_result_{name_suffix}.png", width=IMAGE_WIDTH, height=IMAGE_HEIGHT)

def main(artifact_dir=pathlib.Path("."), schedule_result=None):
    if schedule_result is None:
        logging.info("Loading the json file ...")
        with open(artifact_dir / "schedule_result.json") as f:
            schedule_result = json.load(f)

    logging.info("Preparing the dataframe ...")
    df = pd.DataFrame(schedule_result)

    logging.info("Generating the histogram ...")
    save(px.histogram(df, x="delay"),
         "distribution histogram", "hist",
         artifact_dir)

    df = df.sort_values(by=["delay"])

    logging.info("Generating the line ...")
    save(px.line(df, y="delay"),
         "scheduling timeline", "timeline",
         artifact_dir)

if __name__ == "__main__":
    sys.exit(main())
