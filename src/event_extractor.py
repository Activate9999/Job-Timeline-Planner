import os
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm


class EventExtractor:

    def __init__(self):

        self.dataset_paths = [
            "data/raw/aquaint_timeml_1.0",
            "data/raw/TimeBank-dense-master"
        ]

    def get_files(self):

        files = []

        for dataset in self.dataset_paths:

            if not os.path.exists(dataset):
                continue

            for root, _, filenames in os.walk(dataset):

                for file in filenames:

                    if file.endswith(".tml"):

                        files.append(os.path.join(root, file))

        return files

    def extract_events(self, filepath):

        rows = []

        try:

            with open(filepath, "r", encoding="utf-8") as file:

                soup = BeautifulSoup(file.read(), "xml")

            makeinstance = {}

            for m in soup.find_all("MAKEINSTANCE"):

                makeinstance[m["eventID"]] = {
                    "Tense": m.get("tense", ""),
                    "Aspect": m.get("aspect", ""),
                    "Polarity": m.get("polarity", ""),
                    "POS": m.get("pos", "")
                }

            for event in soup.find_all("EVENT"):

                eid = event.get("eid", "")

                info = makeinstance.get(
                    eid,
                    {
                        "Tense": "",
                        "Aspect": "",
                        "Polarity": "",
                        "POS": ""
                    }
                )

                rows.append({

                    "Filename": os.path.basename(filepath),

                    "Event_ID": eid,

                    "Event": event.get_text(strip=True),

                    "Class": event.get("class", ""),

                    "Tense": info["Tense"],

                    "Aspect": info["Aspect"],

                    "Polarity": info["Polarity"],

                    "POS": info["POS"]

                })

        except Exception as e:

            print(filepath)

            print(e)

        return rows

    def build_dataset(self):

        files = self.get_files()

        dataset = []

        print(f"\nProcessing {len(files)} files...\n")

        for file in tqdm(files):

            dataset.extend(
                self.extract_events(file)
            )

        df = pd.DataFrame(dataset)

        os.makedirs("data/processed", exist_ok=True)

        output = "data/processed/events.csv"

        df.to_csv(output, index=False)

        print("\nEvents extracted successfully!")

        print(df.head())

        print(f"\nTotal Events : {len(df)}")

        return df


if __name__ == "__main__":

    extractor = EventExtractor()

    extractor.build_dataset()