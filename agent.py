import os
import re
import requests
import fitz
import pandas as pd
from bs4 import BeautifulSoup
from langchain_community.document_loaders import PyPDFLoader
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec

# -------------------------------------------------------------------
# 1️⃣  Get latest Sanket PDF link directly from DGMS site
# -------------------------------------------------------------------
def get_latest_sanket_link():
    url = "https://dgms.gov.in/UserView/index?mid=1650"
    print("🌐 Scraping DGMS Sanket page...")

    response = requests.get(url, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    pdf_links = [
        "https://dgms.gov.in" + a["href"]
        for a in soup.find_all("a", href=True)
        if a["href"].endswith(".pdf") and "sanket" in a["href"].lower()
    ]

    if not pdf_links:
        raise ValueError("❌ No Sanket PDFs found on DGMS page.")

    latest_pdf = pdf_links[-1]  # usually the latest one is last
    print(f"📄 Latest Sanket PDF link found: {latest_pdf}")
    return latest_pdf


# -------------------------------------------------------------------
# 2️⃣  Download the latest PDF
# -------------------------------------------------------------------
def download_pdf(pdf_url, save_path="latest_sanket.pdf"):
    print(f"⬇ Downloading: {pdf_url}")
    response = requests.get(pdf_url, stream=True)
    if response.status_code != 200:
        raise Exception(f"❌ Failed to download PDF. Status: {response.status_code}")

    with open(save_path, "wb") as f:
        f.write(response.content)
    print(f"✅ PDF saved as {save_path}")
    return save_path


# -------------------------------------------------------------------
# 3️⃣  Extract text and convert PDF → CSV
# -------------------------------------------------------------------
def extract_text(path):
    text = ""
    with fitz.open(path) as pdf:
        for num, page in enumerate(pdf, start=1):
            text += page.get_text("text")
    return text


def extract_accident_blocks(text):
    pattern = r"(Date\s*-\s.*?averted\.)"
    matches = re.findall(pattern, text, re.S | re.I)
    return matches


def parse_accident_entry(entry):
    data = {}

    date_match = re.search(r"Date\s*-\s*(.?)\s+Mine\s-", entry, re.S | re.I)
    data["Date"] = date_match.group(1).strip() if date_match else None

    mine_match = re.search(r"Mine\s*-\s*(.?)\s+Time\s-", entry, re.S | re.I)
    data["Mine"] = mine_match.group(1).strip() if mine_match else None

    time_match = re.search(r"Time\s*-\s*(.?)\s+Owner\s-", entry, re.S | re.I)
    data["Time"] = time_match.group(1).strip() if time_match else None

    owner_match = re.search(r"Owner\s*-\s*(.?)\s(?:Dist\.?|District)\s*-\s*", entry, re.S | re.I)
    data["Owner"] = owner_match.group(1).strip() if owner_match else None

    dist_state_match = re.search(r"Dist\.\s*-\s*([^,]+),\s*State\s*-\s*([^\n]+)", entry, re.S | re.I)
    if dist_state_match:
        data["District"] = dist_state_match.group(1).strip()
        data["State"] = dist_state_match.group(2).strip()
    else:
        data["District"], data["State"] = None, None

    persons_match = re.search(r"Person\(s\)\s*Killed\s*:\s*(.*?)\n\s*While", entry, re.S | re.I)
    data["Persons_Killed"] = persons_match.group(1).strip() if persons_match else None

    desc_match = re.search(r"(While.*?)(?=\bHad\b)", entry, re.S | re.I)
    data["Description"] = re.sub(r"\s+", " ", desc_match.group(1).strip()) if desc_match else None

    precaution_match = re.search(r"(Had.*?averted\.)", entry, re.S | re.I)
    data["Precaution"] = re.sub(r"\s+", " ", precaution_match.group(1).strip()) if precaution_match else None

    return data


def pdf_to_csv(pdf_path, output_csv="dgms_accidents.csv"):
    text = extract_text(pdf_path)
    blocks = extract_accident_blocks(text)
    print(f"✅ Found {len(blocks)} accident entries.")

    parsed_records = [parse_accident_entry(b) for b in blocks]
    df = pd.DataFrame(parsed_records)
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"📁 Saved structured data to {output_csv}")
    return df

# -------------------------------------------------------------------
# 4️⃣ Convert CSV → JSON
# -------------------------------------------------------------------
def csv_to_json(csv_path="dgms_accidents.csv", json_path="dgms_accidents.json"):
    df = pd.read_csv(csv_path)
    df.to_json(json_path, orient="records", indent=4)
    print(f"📄 Converted CSV → JSON at {json_path}")
    return json_path


# -------------------------------------------------------------------
# 5️⃣ Insert into Pinecone using SentenceTransformer
# -------------------------------------------------------------------
def insert_to_pinecone(json_path):
    model = SentenceTransformer("all-MiniLM-L6-v2")
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

    index_name = os.getenv("PINECONE_INDEX")
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )

    index = pc.Index(index_name)
    df = pd.read_json(json_path)

    for i, row in df.iterrows():
        text = f"{row['Description']} {row['Precaution']}"
        vector = model.encode(text).tolist()

        index.upsert(
            vectors=[
                {
                    "id": str(i),
                    "values": vector,
                    "metadata": {
                        "Date": row.get("Date"),
                        "Mine": row.get("Mine"),
                        "District": row.get("District"),
                        "State": row.get("State"),
                        "Persons_Killed": row.get("Persons_Killed"),
                    },
                }
            ]
        )

    print(f"✅ Inserted {len(df)} vectors into Pinecone.")


# -------------------------------------------------------------------
# 🚀 MAIN AGENTIC PIPELINE
# -------------------------------------------------------------------
def main():
    pdf_url = get_latest_sanket_link()
    pdf_path = download_pdf(pdf_url)
    pdf_to_csv(pdf_path)
    json_path = csv_to_json()
    insert_to_pinecone(json_path)
    print("🎯 Full agentic pipeline completed successfully!")


if _name_ == "_main_":
    main()