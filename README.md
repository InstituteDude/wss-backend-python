# WSS Face Recognition Backend

Backend Python untuk face recognition menggunakan Flask + dlib + PostgreSQL.

## Persyaratan
- Python 3.10+
- PostgreSQL
- CMake (untuk compile dlib)
- Visual Studio Build Tools / GCC

## Instalasi

```bash
# 1. Buat virtual environment
python -m venv venv

# 2. Aktifkan virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup PostgreSQL
# Buat database: wss_face_recognition

# 5. Set environment variables (atau buat .env file)
export DATABASE_URL=postgresql://user:password@localhost:5432/wss_face_recognition

# 6. Jalankan server
python app.py
```

## API Documentation

Swagger UI tersedia di: `http://localhost:5000/swagger`

## API Endpoints

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| POST | /api/face/register | Daftarkan wajah baru |
| POST | /api/face/verify | Verifikasi wajah |
| GET | /api/face/list | Lihat daftar wajah |
| DELETE | /api/face/{id} | Hapus wajah |
| GET | /api/health | Health check |

## Struktur Folder
```
wss-client-electron-backend/
├── app.py                  # Entry point
├── config.py               # Konfigurasi
├── requirements.txt        # Dependencies
├── models/
│   ├── __init__.py
│   └── database.py         # PostgreSQL models
├── services/
│   ├── __init__.py
│   └── face_service.py     # Face recognition logic
├── routes/
│   ├── __init__.py
│   └── face_routes.py      # API routes
└── uploads/                # Temporary uploads
```
