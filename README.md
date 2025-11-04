# 🛠 Agentic RAG-Based Mining Accident Analysis System

### 🚀 Harnessing AI for Safer Mines in India

Mining accidents have historically posed severe risks to workers and industries across India.  
This project leverages *Agentic AI, **Retrieval-Augmented Generation (RAG), and **autonomous NLP pipelines* to digitize, analyze, and monitor mining accident data — enhancing predictive safety and compliance automation.

---

## 🧩 Key Features

### 🔍 1. RAG-Based Query Answering
- Implemented a *Retrieval-Augmented Generation (RAG)* system powered by *LangChain, **Sentence Transformers, and **Pinecone*.
- Users can ask *natural language questions* related to mining accidents — the system retrieves relevant context from historical DGMS data and the latest *Sanket Statistical Reports*.
- Queries like:
  > “Show the major causes of underground mining accidents in Jharkhand between 2018–2021.”

---

### 📊 2. Data Visualization Dashboard
- Displays *interactive charts and graphs* for:
  - Accident distribution by *State, **District, **Year, and **Cause*.
  - Frequency of accidents by *mine type* (coal, metal, stone).
- Built using *React, **Chart.js, and **Recharts* for clean, real-time visual analytics.

---

### 📘 3. Database Insights on Jupyter Notebook
- Performed *exploratory data analysis (EDA)* and visualization on:
  - Tables like Minerals, Mine Types, and Accident Records.
  - Trends and correlations between minerals and accident occurrences.
- Helps analysts and safety officers derive deep insights before deploying models.

---

### 🤖 4. ML Model for Future Predictions
- A *time-series regression model* trained to *predict future mineral values and production trends*.
- Provides proactive insight into which mining sectors might face higher risk or resource decline.

---

### 🕵‍♂ 5. Automated Agentic System
- An *autonomous safety monitoring agent* built with *BeautifulSoup* + *LangChain Agents*.
- Periodically scrapes the [DGMS India](https://www.dgms.gov.in/) website to:
  1. Detect and download the *latest Sanket Statistical Analysis PDF*.
  2. Convert PDF → CSV → JSON automatically.
  3. Update *Pinecone vector embeddings* dynamically.
  4. Trigger *RAG model retraining or re-indexing* for real-time data accuracy.

✅ This ensures *all AI responses* and *insights* are based on the *most recent DGMS data*, not outdated information.

---

## 🧠 System Architecture
```

┌──────────────────────────┐
                │      React Frontend      │
                │ • RAG Query Interface    │
                │ • Visualization Dashboard│
                │ • Report Generator       │
                └──────────┬───────────────┘
                           │
                  (Axios REST Calls)
                           │
            ┌──────────────▼─────────────────┐
            │         FastAPI Backend         │
            │ • Query Processing              │
            │ • File Upload & Conversion      │
            │ • Agent Trigger APIs            │
            │ • Integration with LangChain     │
            └──────────────┬─────────────────┘
                           │
            ┌──────────────▼─────────────────┐
            │       LangChain RAG Engine      │
            │ • Sentence Transformers Embed   │
            │ • Pinecone Vector Search DB     │
            │ • LLM Query Answering (RAG)     │
            └──────────────┬─────────────────┘
                           │
            ┌──────────────▼─────────────────┐
            │   Automated Web Agent (BS4)     │
            │ • Scrape DGMS “Sanket” Reports  │
            │ • PDF→CSV→JSON Conversion       │
            │ • Auto-update Embeddings        │
            └──────────────┬─────────────────┘
                           │
            ┌──────────────▼─────────────────┐
            │       Database Layer            │
            │ • MongoDB / PostgreSQL          │
            │ • Accident, Minerals, Mines     │
            │ • Metadata + Logs               │
            └──────────────┬─────────────────┘
                           │
            ┌──────────────▼─────────────────┐
            │   Jupyter Notebook (EDA Layer)  │
            │ • Data Exploration & Modeling   │
            │ • Visual Validation of Trends   │
            └────────────────────────────────┘

            ---
```

## 🧰 Tech Stack

### *Frontend*
- React.js
- Tailwind CSS / Bootstrap
- Recharts / Chart.js

### *Backend*
- FastAPI (Python)
- LangChain Framework
- Pinecone Vector DB
- Sentence Transformers (Embeddings)
- Transformers (for LLM fine-tuning)

### *Agent Layer*
- BeautifulSoup (Web Scraping)
- PyPDF2 / pdfplumber (PDF Parsing)
- pandas (CSV & JSON handling)
- Cron jobs / Async Tasks for automation

### *Database*
- MongoDB Atlas (preferred for unstructured data)
- PostgreSQL (for structured tabular datasets)

### *Data Science*
- scikit-learn / XGBoost (Prediction Model)
- Jupyter Notebook (Visualization & Analysis)
- Matplotlib, Seaborn (EDA)

---

## ⚠ Challenges Faced

1. *Complex Data Extraction:* DGMS “Sanket” PDFs had inconsistent structures, requiring multiple regex and NLP cleaning steps.  
2. *Dynamic Embedding Updates:* Managing seamless vector updates in Pinecone without downtime was challenging.  
3. *Time Constraints:* Due to limited hackathon time, *full frontend integration* for all visualizations wasn’t possible — so detailed data visualizations were demonstrated via *Jupyter Notebook* instead.  
4. *Limited Computational Resources:* Handling large embeddings and transformer-based models required optimization and batch processing.  
5. *Agent Reliability:* Ensuring that automated agents correctly detected and parsed new Sanket files during runtime.

---

## 🌟 Future Scope

1. *Integration with IoT Sensors:* Real-time incident detection from mine equipment logs or environmental sensors (gas, vibration, temperature).  
2. *Interactive Chat Assistant:* A domain-specific conversational AI for DGMS officers, powered by fine-tuned LLMs (e.g., Llama 3 or Gemma 2).  
3. *Multi-lingual Support:* Enable Hindi and regional language understanding for local operators.  
4. *Real-Time Alert System:* Push notifications for abnormal trends (e.g., “Spike in roof collapse incidents in Odisha mines”).  
5. *Comprehensive Web Dashboard:* Integration of all visualizations and reports into a single full-stack web interface.  
6. *Explainable AI (XAI):* Display “reasoning” or “evidence chain” behind AI predictions or recommendations.  
7. *Regulatory Compliance Reports:* Automatically generate DGMS-compliant audit reports using updated data.

---

## 🧪 Example Workflow

1. *Agent Scrapes DGMS:*  
   → Downloads the latest Sanket report.  
2. *Data Pipeline Converts:*  
   → PDF → CSV → JSON → Embeddings (Pinecone).  
3. *RAG Engine Updates:*  
   → Vector store refreshed with new context.  
4. *User Queries:*  
   → “What are the most common mining hazards in 2022?”  
5. *System Responds:*  
   → Retrieves data → Summarizes insights → Displays visualization & text answer.

---

## 🏆 Impact

This system demonstrates how *Agentic AI* can go beyond passive analytics —  
creating a *self-updating, autonomous mining safety monitoring platform* that:
- Enhances *worker safety*
- Reduces *human labor*
- Improves *regulatory transparency*
- Enables *data-driven decision-making*

---
