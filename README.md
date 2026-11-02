# Proyek Analisis Data: E-Commerce Public Dataset (Olist)

Analisis data pesanan *delivered* periode **Januari 2017 – Agustus 2018** untuk menjawab:
1. Kategori produk apa yang menyumbang revenue tertinggi dan terendah?
2. Seberapa besar keterlambatan pengiriman memengaruhi review score, dan state mana yang paling sering terlambat?

Analisis lanjutan: RFM Analysis dan Geospatial Analysis.

## Struktur Direktori
```
submission
├── dashboard
│   ├── main_data.csv
│   └── dashboard.py
├── data/                (9 berkas CSV dataset asli)
├── notebook.ipynb
├── README.md
├── requirements.txt
└── url.txt
```

## Setup Environment
```
python -m venv venv
venv\Scripts\activate        # Windows  (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
```

## Menjalankan Dashboard
Dari folder `submission`:
```
streamlit run dashboard/dashboard.py
```
Dashboard terbuka di http://localhost:8501.

## Menjalankan Ulang Notebook
Buka `notebook.ipynb` dari folder `submission` (path data relatif: `data/`), lalu *Run All*. Notebook akan menghasilkan ulang `dashboard/main_data.csv`.
