import os
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm


class TimeExtractor:

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

    def extract_times(self, filepath):

        rows = []

        try:

            with open(filepath, "r", encoding="utf-8") as file:

                soup = BeautifulSoup(file.read(), "xml")

            for timex in soup.find_all("TIMEX3"):

                rows.append({

                    "Filename": os.path.basename(filepath),

                    "Time_ID": timex.get("tid", ""),

                    "Time_Expression": timex.get_text(strip=True),

                    "Type": timex.get("type", ""),

                    "Value": timex.get("value", ""),

                    "Function_In_Document": timex.get("functionInDocument", ""),

                    "Temporal_Function": timex.get("temporalFunction", "")

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
                self.extract_times(file)
            )

        df = pd.DataFrame(dataset)

        os.makedirs("data/processed", exist_ok=True)

        output = "data/processed/times.csv"

        df.to_csv(output, index=False)

        print("\nTime expressions extracted successfully!")

        print(df.head())

        print(f"\nTotal Time Expressions : {len(df)}")

        return df


if __name__ == "__main__":

    extractor = TimeExtractor()

    extractor.build_dataset()