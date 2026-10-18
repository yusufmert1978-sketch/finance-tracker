# 💵 Mert Finans - Kişisel & Kurumsal Finansal Yönetim Sistemi

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-black.svg?logo=flask&logoColor=white)](https://palletsprojects.com/p/flask/)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Chart.js](https://img.shields.io/badge/Charts-Chart.js-FF6384.svg?logo=chartdotjs&logoColor=white)](https://www.chartjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Bireysel kullanıcılar ve şirketler için gelir, gider, bütçe planlaması, abonelik takibi ve finansal durum analizini tek bir modern çatı altında toplayan kapsamlı bir finansal yönetim web uygulamasıdır.

---

## ✨ Temel Özellikler

- 📊 **Gelir & Gider Yönetimi:**
  - Gelir ve giderleri kategori, tarih ve tutar bazlı kaydetme ve düzenleme.
  - Kategoriye, işlem tipine, fiyata ve tarihe göre çoklu filtreleme & arama motoru.
  - Kategori dağılımını gösteren **Doughnut Grafiği** ve son 6 ayı kıyaslayan **Aylık Gelir/Gider Trend Çizgi Grafiği** (Chart.js).

- 🎯 **Aylık Bütçe & Hedefleme:**
  - Kullanıcıya özel aylık harcama bütçesi limiti belirleme.
  - Anlık harcama oranı ve kalan bütçeyi gösteren dinamik ilerleme çubuğu.

- 🩺 **Akıllı Finansal Sağlık Skoru:**
  - Tasarruf oranı, bütçe disiplini ve işlem geçmişini analiz eden özel puanlama algoritması (0-100 puan).
  - Skora göre renk kodlu sağlık durumu (*Mükemmel, İyi, Orta, Dikkat Edilmeli*).

- 🤖 **Akıllı Finans Danışmanı & Tahminleme:**
  - Kullanıcının harcama alışkanlıklarını analiz ederek gelecek ayın tahmini giderini hesaplama.
  - Bütçe aşımı veya yüksek kategori harcamaları durumunda proaktif finansal tasarruf tavsiyeleri.

- 📅 **Sabit Gider & Abonelik Takibi:**
  - Netflix, kira, faturalar gibi yinelenen ödemelerin gün bazlı takibi.
  - Ayı geldikçe tek tıkla doğrudan hesap hareketlerine işleme kolaylığı.

- 📑 **Kurumsal Düzeyde Raporlama (PDF & Excel):**
  - **Excel Dökümü:** Microsoft SpreadsheetML (XML) standardında, profesyonel kurumsal renk ve tipografi stilleriyle biçimlendirilmiş tam hesap ekstresi indirme.
  - **Yazdırılabilir PDF Raporu:** Şık hesap özeti ve döküm şablonu.

- 👑 **Kapsamlı Yönetici (Admin) Paneli:**
  - Şirketli ve bireysel müşterileri ayrıştırarak listeleme.
  - Yöneticinin tüm kullanıcıların hesap hareketlerini ve finansal durumlarını inceleyebilmesi.

- 🛡️ **Güvenlik & Rol Tabanlı Yetkilendirme:**
  - `Werkzeug` Scrypt algoritmasıyla tek yönlü şifrelenmiş parola saklama.
  - Rol tabanlı erişim kontrolü (`admin` ve `user`).

---

## 🛠️ Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| **Backend** | Python 3, Flask |
| **ORM & Veritabanı** | Flask-SQLAlchemy, SQLite |
| **Frontend** | HTML5, CSS3 (Modern Glassmorphic Dark UI), JavaScript |
| **Veri Görselleştirme** | Chart.js |
| **Raporlama Çıktıları** | Microsoft XML SpreadsheetML, Yazdırılabilir HTML/PDF |
| **Güvenlik** | Werkzeug Security (Scrypt Hashing), Session Yönetimi |

---

## 🔑 Demo Giriş Bilgileri

Projeyi yerelinizde çalıştırdığınızda otomatik olarak aşağıdaki test hesapları oluşturulur:

| Rol | Kullanıcı Adı | Şifre | Açıklama |
|---|---|---|---|
| 👤 **Standart Kullanıcı** | `mert` | `Mert12345` | Bireysel finans paneli ve grafikler |
| 👑 **Yönetici (Admin)** | `admin` | `admin123` | Tüm kullanıcıları ve şirketleri yönetme paneli |

---

## 🚀 Kurulum ve Çalıştırma

### 1. Repoyu Klonlayın
```bash
git clone https://github.com/yusufmert1978-sketch/mert-finans.git
cd mert-finans
```

### 2. Sanal Ortam (Virtual Environment) Oluşturun ve Aktifleştirin

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### 4. Uygulamayı Başlatın
```bash
python app.py
```

Tarayıcınızdan **`http://127.0.0.1:5001`** adresine giderek uygulamayı kullanmaya başlayabilirsiniz.

---

## 📁 Proje Dizin Yapısı

```text
├── app.py                  # Flask ana uygulama motoru, modeller ve rotalar
├── requirements.txt        # Gerekli Python bağımlılıkları
├── .gitignore              # Git tarafından yok sayılacak dosyalar
├── README.md               # Proje tanıtım ve dokümantasyon dosyası
└── templates/              # Jinja2 HTML şablonları
    ├── login.html          # Giriş ekranı (Demo kartı ile)
    ├── register.html       # Yeni kullanıcı kayıt ekranı
    ├── index.html          # Kullanıcı ana paneli (Grafikler, işlemler, skor)
    ├── admin_panel.html    # Yönetici kontrol paneli
    ├── edit.html           # İşlem düzenleme sayfası
    ├── ayarlar.html        # Profil ve bütçe ayarları
    ├── pdf_sablon.html     # Yazdırılabilir resmi rapor şablonu
    ├── 404.html            # Özel 404 Hata sayfası
    └── 500.html            # Özel 500 Sunucu Hatası sayfası
```

---

## 👨‍💻 Geliştirici

**Mert Zerdali**  
- GitHub: [@yusufmert1978-sketch](https://github.com/yusufmert1978-sketch)  
- E-Posta: [yusufmert1978@gmail.com](mailto:yusufmert1978@gmail.com)

---

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) kapsamında açık kaynak olarak paylaşılmıştır.
