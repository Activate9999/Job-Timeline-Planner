import os
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm


class DataLoader:

    def __init__(self):

        self.dataset_paths = [
            "data/raw/aquaint_timeml_1.0",
            "data/raw/TimeBank-dense-master"
        ]


    def get_all_files(self):

        files = []

        for dataset in self.dataset_paths:

            if not os.path.exists(dataset):
                continue

            for root, _, filenames in os.walk(dataset):

                for file in filenames:

                    if file.endswith(".tml"):

                        files.append(os.path.join(root, file))

        return files


    def extract_text(self, filepath):

        try:

            with open(filepath, "r", encoding="utf-8") as file:

                soup = BeautifulSoup(file.read(), "xml")

            timeml = soup.find("TimeML")

            if timeml is None:
                return ""

            text = []

            for item in timeml.contents:

                if getattr(item, "name", None) in [
                    "MAKEINSTANCE",
                    "TLINK",
                    "SLINK",
                    "ALINK"
                ]:
                    break

                if isinstance(item, str):

                    text.append(item.strip())

                else:

                    text.append(item.get_text(" ", strip=True))

            return " ".join(text)

        except Exception as e:

            print(e)

            return ""


    def load(self):

        files = self.get_all_files()

        print(f"\nTotal Files : {len(files)}\n")

        rows = []

        for file in tqdm(files):

            rows.append({

                "Filename": os.path.basename(file),

                "Path": file,

                "Text": self.extract_text(file)

            })

        df = pd.DataFrame(rows)

        os.makedirs("data/processed", exist_ok=True)

        df.to_csv(
            "data/processed/raw_documents.csv",
            index=False
        )

        print("\nDataset Saved!")

        print(df.head())

        return df


if __name__ == "__main__":

    loader = DataLoader()

    loader.load()