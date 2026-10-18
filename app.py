from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import random
import re
import csv
import io

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'finance_tracker_secret_2026')

# Veritabanı Yapılandırması
base_dir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'finans.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MODELLER ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')
    sirket = db.Column(db.String(100), nullable=True)
    tc_no = db.Column(db.String(11), nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=True)  
    telefon = db.Column(db.String(20), nullable=True)               
    two_fa_code = db.Column(db.String(6), nullable=True)
    butce_hedefi = db.Column(db.Float, default=0.0) # Aylık harcama bütçesi limiti
    kategoriler = db.relationship('Kategori', backref='user', lazy=True, cascade="all, delete-orphan")
    islemler = db.relationship('Islem', backref='user', lazy=True, cascade="all, delete-orphan")
    abonelikler = db.relationship('Abonelik', backref='user', lazy=True, cascade="all, delete-orphan")

class Kategori(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Islem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tip = db.Column(db.String(10), nullable=False) # 'gelir' veya 'gider'
    baslik = db.Column(db.String(100), nullable=False, default="Açıklamasız İşlem")
    kategori = db.Column(db.String(50), nullable=False)
    miktar = db.Column(db.Float, nullable=False)
    tarih = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Abonelik(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(100), nullable=False) # Örn: Netflix, Kira, İnternet Faturası
    miktar = db.Column(db.Float, nullable=False)
    kategori = db.Column(db.String(50), nullable=False)
    gun = db.Column(db.Integer, nullable=False, default=1) # Her ayın kaçıncı günü ödenecek (1-31)
    aktif = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# --- GÜVENLİK FONKSİYONU ---
def sifre_guvenli_mi(sifre):
    if len(sifre) < 8:
        return False
    if not re.search(r"[A-Z]", sifre):
        return False
    if not re.search(r"[a-z]", sifre):
        return False
    if not re.search(r"[0-9]", sifre):
        return False
    return True

# --- ROTALAR / KONTROLLER ---

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session['role'] == 'admin':
        return redirect(url_for('admin_panel'))
        
    return redirect(url_for('user_detail', user_id=session['user_id']))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            
            if user.role == 'admin':
                return redirect(url_for('admin_panel'))
            return redirect(url_for('index'))
        else:
            flash("Geçersiz kullanıcı adı veya şifre!")
            
    return render_template('login.html')

@app.route('/verify_2fa', methods=['GET', 'POST'])
def verify_2fa():
    # 2FA geçici olarak devre dışı bırakıldığı için ana sayfaya yönlendirilir
    if 'user_id' in session:
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        telefon = request.form.get('telefon')
        sirket = request.form.get('sirket')
        tc_no = request.form.get('tc_no')
        
        if not sifre_guvenli_mi(password):
            flash("Şifre en az 8 karakter olmalı, en az bir büyük harf, bir küçük harf ve bir rakam içermelidir!")
            return render_template('register.html')
            
        if User.query.filter_by(username=username).first():
            flash("Bu kullanıcı adı zaten alınmış!")
            return render_template('register.html')
            
        hashed_password = generate_password_hash(password, method='scrypt')
        new_user = User(
            username=username, 
            password=hashed_password,
            email=email if email else None,
            telefon=telefon if telefon else None,
            sirket=sirket if sirket else None,
            tc_no=tc_no if tc_no else None,
            role='user',
            butce_hedefi=0.0
        )
        db.session.add(new_user)
        db.session.commit()
        
        varsayilan_kategoriler = ['Maaş', 'Gıda', 'Fatura', 'Eğlence', 'Kira', 'Ulaşım']
        for kat_ad in varsayilan_kategoriler:
            db.session.add(Kategori(ad=kat_ad, user_id=new_user.id))
        db.session.commit()
        
        flash("Kayıt başarılı! Şimdi giriş yapabilirsiniz.")
        return redirect(url_for('login'))
        
    return render_template('register.html')


@app.route('/admin_panel')
def admin_panel():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
        
    all_users = User.query.filter(User.username != 'admin').all()
    sirketli = {}
    sirketsiz = []
    
    for u in all_users:
        if u.sirket and u.sirket.strip() != "":
            if u.sirket not in sirketli:
                sirketli[u.sirket] = []
            sirketli[u.sirket].append(u)
        else:
            sirketsiz.append(u)
            
    return render_template('admin_panel.html', sirketli=sirketli, sirketsiz=sirketsiz)

@app.route('/user_detail/<int:user_id>')
def user_detail(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if session['role'] != 'admin' and session['user_id'] != user_id:
        return "Bu sayfayı görüntülemek için yetkiniz yok!", 403
        
    bakilan_user = User.query.get_or_404(user_id)
    kategoriler = Kategori.query.filter_by(user_id=user_id).all()
    abonelikler = Abonelik.query.filter_by(user_id=user_id).all()
    
    tip_filtresi = request.args.get('tip', 'hepsi')
    kat_filtresi = request.args.get('kategori', 'hepsi')
    min_fiyat = request.args.get('min_fiyat', '')
    max_fiyat = request.args.get('max_fiyat', '')
    sirala = request.args.get('sirala', 'en_yeni')
    
    query = Islem.query.filter_by(user_id=user_id)
    
    if tip_filtresi in ['gelir', 'gider']:
        query = query.filter_by(tip=tip_filtresi)
    if kat_filtresi != 'hepsi':
        query = query.filter_by(kategori=kat_filtresi)
        
    if min_fiyat:
        try: query = query.filter(Islem.miktar >= float(min_fiyat))
        except ValueError: pass
    if max_fiyat:
        try: query = query.filter(Islem.miktar <= float(max_fiyat))
        except ValueError: pass
            
    if sirala == 'en_eski': query = query.order_by(Islem.tarih.asc())
    elif sirala == 'coktan_aza': query = query.order_by(Islem.miktar.desc())
    elif sirala == 'azdan_coga': query = query.order_by(Islem.miktar.asc())
    else: query = query.order_by(Islem.tarih.desc())
        
    islemler = query.all()
    tum_islemler = Islem.query.filter_by(user_id=user_id).all()
    
    # --- CHART 1: KATEGORİSEL GİDER VERİSİ (PASTA/HALKA GRAFİĞİ) ---
    gider_verileri = {}
    for i in islemler:
        if i.tip == 'gider':
            gider_verileri[i.kategori] = gider_verileri.get(i.kategori, 0) + i.miktar
            
    chart_labels = list(gider_verileri.keys())
    chart_values = list(gider_verileri.values())
    
    # Genel Toplamlar
    toplam_gelir = sum(i.miktar for i in tum_islemler if i.tip == 'gelir')
    toplam_gider = sum(i.miktar for i in tum_islemler if i.tip == 'gider')
    net_durum = toplam_gelir - toplam_gider
    
    # --- CHART 2: SON 6 AYIN GELİR - GİDER TRENDİ (ÇİZGİ GRAFİĞİ) ---
    aylar_tr = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    simdi = datetime.utcnow()
    trend_labels = []
    trend_gelirler = []
    trend_giderler = []
    
    for month_offset in range(5, -1, -1):
        # Son 6 ayı hesapla
        yil = simdi.year
        ay = simdi.month - month_offset
        while ay <= 0:
            ay += 12
            yil -= 1
            
        ay_adi = aylar_tr[ay - 1]
        trend_labels.append(f"{ay_adi}")
        
        # Bu aya ait işlemleri filtrele
        ay_gelir = sum(i.miktar for i in tum_islemler if i.tip == 'gelir' and i.tarih.year == yil and i.tarih.month == ay)
        ay_gider = sum(i.miktar for i in tum_islemler if i.tip == 'gider' and i.tarih.year == yil and i.tarih.month == ay)
        
        trend_gelirler.append(ay_gelir)
        trend_giderler.append(ay_gider)
        
    # --- BU AYIN BÜTÇE HESABI & İLERLEME ÇUBUĞU ---
    bu_ay_gider = sum(i.miktar for i in tum_islemler if i.tip == 'gider' and i.tarih.year == simdi.year and i.tarih.month == simdi.month)
    bu_ay_gelir = sum(i.miktar for i in tum_islemler if i.tip == 'gelir' and i.tarih.year == simdi.year and i.tarih.month == simdi.month)
    
    butce_hedefi = bakilan_user.butce_hedefi if bakilan_user.butce_hedefi else 0.0
    butce_yuzdesi = int((bu_ay_gider / butce_hedefi) * 100) if butce_hedefi > 0 else 0
    butce_kalan = max(0.0, butce_hedefi - bu_ay_gider) if butce_hedefi > 0 else 0.0
    
    # --- FİNANSAL SAĞLIK SKORU (0 - 100 PUAN) ---
    saglik_puani = 50
    if toplam_gelir > 0:
        tasarruf_orani = (toplam_gelir - toplam_gider) / toplam_gelir
        if tasarruf_orani >= 0.30:
            saglik_puani += 30
        elif tasarruf_orani >= 0.15:
            saglik_puani += 20
        elif tasarruf_orani >= 0.0:
            saglik_puani += 10
        else:
            saglik_puani -= 25
            
    if butce_hedefi > 0:
        if bu_ay_gider <= butce_hedefi:
            saglik_puani += 20
        else:
            saglik_puani -= 20
    else:
        saglik_puani += 10
        
    if len(tum_islemler) >= 5:
        saglik_puani += 10
        
    saglik_puani = max(10, min(100, saglik_puani))
    
    if saglik_puani >= 80:
        saglik_durumu = "Mükemmel"
        saglik_renk = "#10b981"
    elif saglik_puani >= 60:
        saglik_durumu = "İyi"
        saglik_renk = "#3b82f6"
    elif saglik_puani >= 40:
        saglik_durumu = "Orta"
        saglik_renk = "#f59e0b"
    else:
        saglik_durumu = "Dikkat Edilmeli"
        saglik_renk = "#ef4444"
        
    # --- AKILLI FİNANS DANIŞMANI & TAHMİNLEME ---
    akilli_tavsiyeler = []
    
    # Gelecek ay tahmini harcama
    aktif_ay_sayisi = max(1, len(set(i.tarih.strftime('%Y-%m') for i in tum_islemler if i.tip == 'gider')))
    tahmin_gelecek_ay_gider = round(toplam_gider / aktif_ay_sayisi, 2) if toplam_gider > 0 else 0.0
    
    if butce_hedefi > 0 and bu_ay_gider > butce_hedefi * 0.9:
        akilli_tavsiyeler.append("⚠️ Aylık belirlediğiniz bütçe limitinizin %90'ını aştınız. Kalan günlerde harcamalarınızı kısmanız önerilir.")
        
    if net_durum < 0:
        akilli_tavsiyeler.append("📉 Toplam gideriniz gelirinizi aşıyor! Acil tasarruf planı oluşturmanız önerilir.")
    elif toplam_gelir > 0 and (toplam_gelir - toplam_gider) / toplam_gelir >= 0.2:
        akilli_tavsiyeler.append("🌟 Harika tasarruf oranı! Gelirinizin %20'sinden fazlasını biriktiriyorsunuz. Birikimlerinizi değerlendirebilirsiniz.")
        
    if gider_verileri:
        en_cok_kat = max(gider_verileri, key=gider_verileri.get)
        akilli_tavsiyeler.append(f"🏷️ En yüksek harcamanız '{en_cok_kat}' kategorisinde ({gider_verileri[en_cok_kat]} TL). Bu alandaki giderleri optimize edebilirsiniz.")
        
    if not akilli_tavsiyeler:
        akilli_tavsiyeler.append("💡 Harcamalarınız dengeli görünüyor. Düzenli gelir ve gider girişi yaparak finansal durumunuzu takipte kalın.")
    
    # Bugünün günü (Abonelik takibi için)
    bugunun_gunu = datetime.utcnow().day
    
    return render_template('index.html', 
                           bakilan_user=bakilan_user, 
                           islemler=islemler, 
                           kategoriler=kategoriler,
                           abonelikler=abonelikler,
                           gelir=toplam_gelir, 
                           gider=toplam_gider, 
                           net=net_durum,
                           bu_ay_gelir=bu_ay_gelir,
                           bu_ay_gider=bu_ay_gider,
                           butce_hedefi=butce_hedefi,
                           butce_yuzdesi=butce_yuzdesi,
                           butce_kalan=butce_kalan,
                           saglik_puani=saglik_puani,
                           saglik_durumu=saglik_durumu,
                           saglik_renk=saglik_renk,
                           akilli_tavsiyeler=akilli_tavsiyeler,
                           tahmin_gelecek_ay_gider=tahmin_gelecek_ay_gider,
                           secili_tip=tip_filtresi,
                           secili_kat=kat_filtresi,
                           min_fiyat=min_fiyat,
                           max_fiyat=max_fiyat,
                           secili_sirala=sirala,
                           chart_labels=chart_labels,
                           chart_values=chart_values,
                           trend_labels=trend_labels,
                           trend_gelirler=trend_gelirler,
                           trend_giderler=trend_giderler,
                           bugunun_gunu=bugunun_gunu)

@app.route('/butce_guncelle/<int:user_id>', methods=['POST'])
def butce_guncelle(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if session['role'] != 'admin' and session['user_id'] != user_id:
        return "Yetkisiz İşlem!", 403
        
    user = User.query.get_or_404(user_id)
    yeni_hedef = request.form.get('butce_hedefi', 0)
    try:
        user.butce_hedefi = max(0.0, float(yeni_hedef))
        db.session.commit()
        flash("Aylık bütçe hedefiniz başarıyla güncellendi!", "success")
    except ValueError:
        flash("Geçersiz bütçe tutarı!", "danger")
        
    return redirect(url_for('user_detail', user_id=user_id))

@app.route('/islem_ekle/<int:target_user_id>', methods=['POST'])
def islem_ekle(target_user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if session['role'] != 'admin' and session['user_id'] != target_user_id:
        return "Yetkisiz İşlem!", 403
        
    tip = request.form.get('tip')
    baslik = request.form.get('baslik')
    kategori = request.form.get('kategori')
    miktar = float(request.form.get('miktar', 0))
    tarih_str = request.form.get('tarih')
    
    tarih = datetime.strptime(tarih_str, '%Y-%m-%d') if tarih_str else datetime.utcnow()
    if not baslik or baslik.strip() == "":
        baslik = "Açıklamasız İşlem"
        
    yeni_islem = Islem(tip=tip, baslik=baslik, kategori=kategori, miktar=miktar, tarih=tarih, user_id=target_user_id)
    db.session.add(yeni_islem)
    db.session.commit()
    
    return redirect(url_for('user_detail', user_id=target_user_id))

@app.route('/abonelik_ekle/<int:user_id>', methods=['POST'])
def abonelik_ekle(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if session['role'] != 'admin' and session['user_id'] != user_id:
        return "Yetkisiz İşlem!", 403
        
    baslik = request.form.get('baslik', '').strip()
    miktar = float(request.form.get('miktar', 0))
    kategori = request.form.get('kategori', 'Fatura')
    gun = int(request.form.get('gun', 1))
    
    if baslik and miktar > 0:
        yeni_abo = Abonelik(baslik=baslik, miktar=miktar, kategori=kategori, gun=gun, user_id=user_id)
        db.session.add(yeni_abo)
        db.session.commit()
        flash("Sabit gider / abonelik başarıyla eklendi.", "success")
        
    return redirect(url_for('user_detail', user_id=user_id))

@app.route('/abonelik_sil/<int:abo_id>')
def abonelik_sil(abo_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    abo = Abonelik.query.get_or_404(abo_id)
    target_user_id = abo.user_id
    
    if session['role'] != 'admin' and session['user_id'] != target_user_id:
        return "Yetkisiz İşlem!", 403
        
    db.session.delete(abo)
    db.session.commit()
    flash("Abonelik kaydı silindi.", "info")
    return redirect(url_for('user_detail', user_id=target_user_id))

@app.route('/abonelik_ode/<int:abo_id>')
def abonelik_ode(abo_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    abo = Abonelik.query.get_or_404(abo_id)
    target_user_id = abo.user_id
    
    if session['role'] != 'admin' and session['user_id'] != target_user_id:
        return "Yetkisiz İşlem!", 403
        
    # Aboneliği doğrudan gider işlemi olarak kaydet
    yeni_islem = Islem(
        tip='gider',
        baslik=f"{abo.baslik} (Sabit Ödeme)",
        kategori=abo.kategori,
        miktar=abo.miktar,
        tarih=datetime.utcnow(),
        user_id=target_user_id
    )
    db.session.add(yeni_islem)
    db.session.commit()
    flash(f"'{abo.baslik}' ödemesi ({abo.miktar} TL) bu ayki hesap hareketlerine başarıyla işlendi!", "success")
    return redirect(url_for('user_detail', user_id=target_user_id))

@app.route('/edit/<int:islem_id>', methods=['GET', 'POST'])
def edit(islem_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    islem = Islem.query.get_or_404(islem_id)
    if session['role'] != 'admin' and session['user_id'] != islem.user_id:
        return "Bu işlemi düzenleme yetkiniz yok!", 403
        
    if request.method == 'POST':
        islem.tip = request.form.get('tip')
        baslik_input = request.form.get('baslik')
        islem.baslik = baslik_input if baslik_input and baslik_input.strip() != "" else "Açıklamasız İşlem"
        islem.kategori = request.form.get('kategori')
        islem.miktar = float(request.form.get('miktar', 0))
        
        tarih_str = request.form.get('tarih')
        if tarih_str:
            islem.tarih = datetime.strptime(tarih_str, '%Y-%m-%d')
            
        db.session.commit()
        return redirect(url_for('user_detail', user_id=islem.user_id))
        
    kategoriler = Kategori.query.filter_by(user_id=islem.user_id).all()
    return render_template('edit.html', islem=islem, kategoriler=kategoriler)

@app.route('/sil/<int:islem_id>')
def sil(islem_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    islem = Islem.query.get_or_404(islem_id)
    target_user_id = islem.user_id
    
    if session['role'] != 'admin' and session['user_id'] != target_user_id:
        return "Yetkisiz İşlem!", 403
        
    db.session.delete(islem)
    db.session.commit()
    return redirect(url_for('user_detail', user_id=target_user_id))

@app.route('/kategori_ekle/<int:target_user_id>', methods=['POST'])
def kategori_ekle(target_user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if session['role'] != 'admin' and session['user_id'] != target_user_id:
        return "Yetkisiz İşlem!", 403
        
    ad = request.form.get('kategori_ad').capitalize()
    if ad and not Kategori.query.filter_by(ad=ad, user_id=target_user_id).first():
        db.session.add(Kategori(ad=ad, user_id=target_user_id))
        db.session.commit()
        
    return redirect(url_for('user_detail', user_id=target_user_id))

@app.route('/kategori_sil/<int:kat_id>/<int:target_user_id>')
def kategori_sil(kat_id, target_user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if session['role'] != 'admin' and session['user_id'] != target_user_id:
        return "Yetkisiz İşlem!", 403
        
    kat = Kategori.query.get(kat_id)
    if kat:
        db.session.delete(kat)
        db.session.commit()
        
    return redirect(url_for('user_detail', user_id=target_user_id))

@app.route('/ayarlar', methods=['GET', 'POST'])
def ayarlar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user = User.query.get_or_404(session['user_id'])
    
    if request.method == 'POST':
        yeni_email = request.form.get('email')
        yeni_telefon = request.form.get('telefon')
        yeni_sirket = request.form.get('sirket')
        butce_hedefi = request.form.get('butce_hedefi')
        mevcut_sifre = request.form.get('mevcut_sifre')
        yeni_sifre = request.form.get('yeni_sifre')
        
        user.email = yeni_email if yeni_email else None
        user.telefon = yeni_telefon if yeni_telefon else None
        user.sirket = yeni_sirket if yeni_sirket else None
        
        if butce_hedefi:
            try:
                user.butce_hedefi = max(0.0, float(butce_hedefi))
            except ValueError:
                pass
        
        if mevcut_sifre and yeni_sifre:
            if check_password_hash(user.password, mevcut_sifre):
                if not sifre_guvenli_mi(yeni_sifre):
                    flash("Yeni şifre en az 8 karakter olmalı, en az bir büyük harf, bir küçük harf ve bir rakam içermelidir!", "danger")
                    return render_template('ayarlar.html', user=user)
                user.password = generate_password_hash(yeni_sifre, method='scrypt')
                flash("Şifreniz başarıyla güncellendi.", "success")
            else:
                flash("Mevcut şifreniz hatalı! Şifre değiştirilemedi.", "danger")
                db.session.commit()
                return render_template('ayarlar.html', user=user)
                
        db.session.commit()
        flash("Profil bilgileriniz başarıyla güncellendi.", "success")
        return redirect(url_for('user_detail', user_id=user.id))
        
    return render_template('ayarlar.html', user=user)

@app.route('/rapor_pdf/<int:user_id>')
def rapor_pdf(user_id):
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    if session['role'] != 'admin' and session['user_id'] != user_id: 
        return "Yetkisiz!", 403
    
    u = User.query.get_or_404(user_id)
    
    tip_filtresi = request.args.get('tip', 'hepsi')
    kat_filtresi = request.args.get('kategori', 'hepsi')
    min_fiyat = request.args.get('min_fiyat', '')
    max_fiyat = request.args.get('max_fiyat', '')
    sirala = request.args.get('sirala', 'en_yeni')
    
    query = Islem.query.filter_by(user_id=user_id)
    
    if tip_filtresi in ['gelir', 'gider']:
        query = query.filter_by(tip=tip_filtresi)
    if kat_filtresi != 'hepsi':
        query = query.filter_by(kategori=kat_filtresi)
        
    if min_fiyat:
        try: query = query.filter(Islem.miktar >= float(min_fiyat))
        except ValueError: pass
    if max_fiyat:
        try: query = query.filter(Islem.miktar <= float(max_fiyat))
        except ValueError: pass
            
    if sirala == 'en_eski': query = query.order_by(Islem.tarih.asc())
    elif sirala == 'coktan_aza': query = query.order_by(Islem.miktar.desc())
    elif sirala == 'azdan_coga': query = query.order_by(Islem.miktar.asc())
    else: query = query.order_by(Islem.tarih.desc())
        
    islemler = query.all()
    
    # Genel Toplamlar
    tum_islemler = Islem.query.filter_by(user_id=user_id).all()
    gelir = sum(i.miktar for i in tum_islemler if i.tip == 'gelir')
    gider = sum(i.miktar for i in tum_islemler if i.tip == 'gider')
    net = gelir - gider
    
    # Kategori Bazlı Gider Özeti
    kategori_ozet = {}
    for i in tum_islemler:
        if i.tip == 'gider':
            kategori_ozet[i.kategori] = kategori_ozet.get(i.kategori, 0) + i.miktar
            
    now = datetime.now()
    tarih_rapor = now.strftime('%d.%m.%Y %H:%M')
    tarih_kod = now.strftime('%Y%m%d-%H%M')
    
    rendered = render_template('pdf_sablon.html', 
                               u=u, 
                               islemler=islemler, 
                               gelir=gelir, 
                               gider=gider, 
                               net=net,
                               kategori_ozet=kategori_ozet,
                               tarih_rapor=tarih_rapor,
                               tarih_kod=tarih_kod,
                               secili_tip=tip_filtresi,
                               secili_kat=kat_filtresi)
    
    response = make_response(rendered)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

@app.route('/rapor_excel/<int:user_id>')
def rapor_excel(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['role'] != 'admin' and session['user_id'] != user_id:
        return "Yetkisiz!", 403
        
    u = User.query.get_or_404(user_id)
    islemler = Islem.query.filter_by(user_id=user_id).order_by(Islem.tarih.desc()).all()
    
    toplam_gelir = sum(i.miktar for i in islemler if i.tip == 'gelir')
    toplam_gider = sum(i.miktar for i in islemler if i.tip == 'gider')
    net_durum = toplam_gelir - toplam_gider
    
    # Kategori bazlı gider analizi
    kategori_gider = {}
    for i in islemler:
        if i.tip == 'gider':
            kategori_gider[i.kategori] = kategori_gider.get(i.kategori, 0) + i.miktar
            
    now = datetime.now()
    tarih_rapor = now.strftime('%d.%m.%Y %H:%M')
    tarih_kod = now.strftime('%Y%m%d-%H%M')
    
    # XML Güvenli Metin Temizleme
    import html as html_lib
    esc = html_lib.escape
    
    u_username = esc(u.username)
    u_sirket = esc(u.sirket) if u.sirket else 'Bireysel'
    u_email = esc(u.email) if u.email else 'Belirtilmedi'
    
    # SpreadsheetML Excel XML Şablonu
    xml_parts = []
    xml_parts.append('<?xml version="1.0" encoding="utf-8"?>')
    xml_parts.append('<?mso-application progid="Excel.Sheet"?>')
    xml_parts.append('<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"')
    xml_parts.append(' xmlns:o="urn:schemas-microsoft-com:office:office"')
    xml_parts.append(' xmlns:x="urn:schemas-microsoft-com:office:excel"')
    xml_parts.append(' xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"')
    xml_parts.append(' xmlns:html="http://www.w3.org/TR/REC-html40">')
    xml_parts.append(' <DocumentProperties xmlns="urn:schemas-microsoft-com:office:office">')
    xml_parts.append('  <Author>Finance Tracker</Author>')
    xml_parts.append('  <Title>Resmi Finans Raporu</Title>')
    xml_parts.append(' </DocumentProperties>')
    xml_parts.append(' <Styles>')
    xml_parts.append('  <Style ss:ID="Default" ss:Name="Normal">')
    xml_parts.append('   <Alignment ss:Vertical="Center"/>')
    xml_parts.append('   <Font ss:FontName="Calibri" ss:Size="11" ss:Color="#1E293B"/>')
    xml_parts.append('  </Style>')
    xml_parts.append('  <Style ss:ID="MainTitle">')
    xml_parts.append('   <Font ss:FontName="Calibri" ss:Size="16" ss:Bold="1" ss:Color="#0F172A"/>')
    xml_parts.append('   <Alignment ss:Vertical="Center"/>')
    xml_parts.append('  </Style>')
    xml_parts.append('  <Style ss:ID="Subtitle">')
    xml_parts.append('   <Font ss:FontName="Calibri" ss:Size="11" ss:Italic="1" ss:Color="#64748B"/>')
    xml_parts.append('   <Alignment ss:Vertical="Center"/>')
    xml_parts.append('  </Style>')
    xml_parts.append('  <Style ss:ID="InfoLabel">')
    xml_parts.append('   <Font ss:FontName="Calibri" ss:Size="10" ss:Bold="1" ss:Color="#334155"/>')
    xml_parts.append('   <Interior ss:Color="#F1F5F9" ss:Pattern="Solid"/>')
    xml_parts.append('   <Borders>')
    xml_parts.append('    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>')
    xml_parts.append('    <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>')
    xml_parts.append('    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>')
    xml_parts.append('    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>')
    xml_parts.append('   </Borders>')
    xml_parts.append('  </Style>')
    xml_parts.append('  <Style ss:ID="InfoValue">')
    xml_parts.append('   <Font ss:FontName="Calibri" ss:Size="10" ss:Color="#0F172A"/>')
    xml_parts.append('   <Interior ss:Color="#FFFFFF" ss:Pattern="Solid"/>')
    xml_parts.append('   <Borders>')
    xml_parts.append('    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>')
    xml_parts.append('    <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>')
    xml_parts.append('    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>')
    xml_parts.append('    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>')
    xml_parts.append('   </Borders>')
    xml_parts.append('  </Style>')
    xml_parts.append('  <Style ss:ID="CardGelir">')
    xml_parts.append('   <Font ss:FontName="Calibri" ss:Size="12" ss:Bold="1" ss:Color="#065F46"/>')
    xml_parts.append('   <Interior ss:Color="#D1FAE5" ss:Pattern="Solid"/>')
    xml_parts.append('   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>')
    xml_parts.append('   <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#A7F3D0"/><Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#A7F3D0"/><Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#A7F3D0"/><Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#A7F3D0"/></Borders>')
    xml_parts.append('  </Style>')
    xml_parts.append('  <Style ss:ID="CardGider">')
    xml_parts.append('   <Font ss:FontName="Calibri" ss:Size="12" ss:Bold="1" ss:Color="#991B1B"/>')
    xml_parts.append('   <Interior ss:Color="#FEE2E2" ss:Pattern="Solid"/>')
    xml_parts.append('   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>')
    xml_parts.append('   <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#FECACA"/><Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#FECACA"/><Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#FECACA"/><Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#FECACA"/></Borders>')
    xml_parts.append('  </Style>')
    xml_parts.append('  <Style ss:ID="CardNet">')
    xml_parts.append('   <Font ss:FontName="Calibri" ss:Size="12" ss:Bold="1" ss:Color="#1E40AF"/>')
    xml_parts.append('   <Interior ss:Color="#DBEAFE" ss:Pattern="Solid"/>')
    xml_parts.append('   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>')
    xml_parts.append('   <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFDBFE"/><Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFDBFE"/><Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFDBFE"/><Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#BFDBFE"/></Borders>')
    xml_parts.append('  </Style>')
    xml_parts.append('  <Style ss:ID="SectionHeader">')
    xml_parts.append('   <Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1" ss:Color="#1E293B"/>')
    xml_parts.append('   <Interior ss:Color="#E2E8F0" ss:Pattern="Solid"/>')
    xml_parts.append('   <Alignment ss:Vertical="Center"/>')
    xml_parts.append('   <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/></Borders>')
    xml_parts.append('  </Style>')
    xml_parts.append('  <Style ss:ID="TableHeader">')
    xml_parts.append('   <Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1" ss:Color="#FFFFFF"/>')
    xml_parts.append('   <Interior ss:Color="#1E293B" ss:Pattern="Solid"/>')
    xml_parts.append('   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>')
    xml_parts.append('   <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="2" ss:Color="#0F172A"/></Borders>')
    xml_parts.append('  </Style>')
    xml_parts.append('  <Style ss:ID="DataRowEven">')
    xml_parts.append('   <Interior ss:Color="#F8FAFC" ss:Pattern="Solid"/>')
    xml_parts.append('   <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/></Borders>')
    xml_parts.append('  </Style>')
    xml_parts.append('  <Style ss:ID="DataRowOdd">')
    xml_parts.append('   <Interior ss:Color="#FFFFFF" ss:Pattern="Solid"/>')
    xml_parts.append('   <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/></Borders>')
    xml_parts.append('  </Style>')
    xml_parts.append('  <Style ss:ID="GelirBadge">')
    xml_parts.append('   <Font ss:FontName="Calibri" ss:Size="10" ss:Bold="1" ss:Color="#065F46"/>')
    xml_parts.append('   <Interior ss:Color="#D1FAE5" ss:Pattern="Solid"/>')
    xml_parts.append('   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>')
    xml_parts.append('   <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/></Borders>')
    xml_parts.append('  </Style>')
    xml_parts.append('  <Style ss:ID="GiderBadge">')
    xml_parts.append('   <Font ss:FontName="Calibri" ss:Size="10" ss:Bold="1" ss:Color="#991B1B"/>')
    xml_parts.append('   <Interior ss:Color="#FEE2E2" ss:Pattern="Solid"/>')
    xml_parts.append('   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>')
    xml_parts.append('   <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/></Borders>')
    xml_parts.append('  </Style>')
    xml_parts.append('  <Style ss:ID="MoneyGelir">')
    xml_parts.append('   <Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1" ss:Color="#059669"/>')
    xml_parts.append('   <NumberFormat ss:Format="#,##0.00\\ &quot;TL&quot;"/>')
    xml_parts.append('   <Alignment ss:Horizontal="Right" ss:Vertical="Center"/>')
    xml_parts.append('   <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/></Borders>')
    xml_parts.append('  </Style>')
    xml_parts.append('  <Style ss:ID="MoneyGider">')
    xml_parts.append('   <Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1" ss:Color="#DC2626"/>')
    xml_parts.append('   <NumberFormat ss:Format="#,##0.00\\ &quot;TL&quot;"/>')
    xml_parts.append('   <Alignment ss:Horizontal="Right" ss:Vertical="Center"/>')
    xml_parts.append('   <Borders><Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/></Borders>')
    xml_parts.append('  </Style>')
    xml_parts.append('  <Style ss:ID="TotalRow">')
    xml_parts.append('   <Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1" ss:Color="#0F172A"/>')
    xml_parts.append('   <Interior ss:Color="#F1F5F9" ss:Pattern="Solid"/>')
    xml_parts.append('   <Borders>')
    xml_parts.append('    <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>')
    xml_parts.append('    <Border ss:Position="Bottom" ss:LineStyle="Double" ss:Weight="3" ss:Color="#0F172A"/>')
    xml_parts.append('   </Borders>')
    xml_parts.append('  </Style>')
    xml_parts.append('  <Style ss:ID="TotalMoney">')
    xml_parts.append('   <Font ss:FontName="Calibri" ss:Size="12" ss:Bold="1" ss:Color="#0F172A"/>')
    xml_parts.append('   <Interior ss:Color="#F1F5F9" ss:Pattern="Solid"/>')
    xml_parts.append('   <NumberFormat ss:Format="#,##0.00\\ &quot;TL&quot;"/>')
    xml_parts.append('   <Alignment ss:Horizontal="Right" ss:Vertical="Center"/>')
    xml_parts.append('   <Borders>')
    xml_parts.append('    <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>')
    xml_parts.append('    <Border ss:Position="Bottom" ss:LineStyle="Double" ss:Weight="3" ss:Color="#0F172A"/>')
    xml_parts.append('   </Borders>')
    xml_parts.append('  </Style>')
    xml_parts.append(' </Styles>')
    xml_parts.append(' <Worksheet ss:Name="Finansal Rapor">')
    xml_parts.append('  <Table ss:DefaultRowHeight="20">')
    xml_parts.append('   <Column ss:Width="45"/>')
    xml_parts.append('   <Column ss:Width="95"/>')
    xml_parts.append('   <Column ss:Width="230"/>')
    xml_parts.append('   <Column ss:Width="130"/>')
    xml_parts.append('   <Column ss:Width="85"/>')
    xml_parts.append('   <Column ss:Width="125"/>')
    
    # 1. Başlık Alanı
    xml_parts.append('   <Row ss:Height="26">')
    xml_parts.append('    <Cell ss:MergeAcross="5" ss:StyleID="MainTitle"><Data ss:Type="String">FINANCE TRACKER YÖNETİM SİSTEMİ</Data></Cell>')
    xml_parts.append('   </Row>')
    xml_parts.append('   <Row ss:Height="18">')
    xml_parts.append('    <Cell ss:MergeAcross="5" ss:StyleID="Subtitle"><Data ss:Type="String">Resmi Müşteri Hesap Ekstresi ve Finansal Durum Raporu</Data></Cell>')
    xml_parts.append('   </Row>')
    xml_parts.append('   <Row ss:Height="8"></Row>')
    
    # 2. Kullanıcı ve Rapor Bilgi Kartı
    xml_parts.append('   <Row ss:Height="21">')
    xml_parts.append('    <Cell ss:StyleID="InfoLabel"><Data ss:Type="String">Hesap Sahibi:</Data></Cell>')
    xml_parts.append(f'    <Cell ss:MergeAcross="1" ss:StyleID="InfoValue"><Data ss:Type="String">{u_username}</Data></Cell>')
    xml_parts.append('    <Cell ss:StyleID="InfoLabel"><Data ss:Type="String">Rapor Tarihi:</Data></Cell>')
    xml_parts.append(f'    <Cell ss:MergeAcross="1" ss:StyleID="InfoValue"><Data ss:Type="String">{tarih_rapor}</Data></Cell>')
    xml_parts.append('   </Row>')
    xml_parts.append('   <Row ss:Height="21">')
    xml_parts.append('    <Cell ss:StyleID="InfoLabel"><Data ss:Type="String">Şirket / Kurum:</Data></Cell>')
    xml_parts.append(f'    <Cell ss:MergeAcross="1" ss:StyleID="InfoValue"><Data ss:Type="String">{u_sirket}</Data></Cell>')
    xml_parts.append('    <Cell ss:StyleID="InfoLabel"><Data ss:Type="String">Rapor Kodu:</Data></Cell>')
    xml_parts.append(f'    <Cell ss:MergeAcross="1" ss:StyleID="InfoValue"><Data ss:Type="String">RPR-{u.id}-{tarih_kod}</Data></Cell>')
    xml_parts.append('   </Row>')
    xml_parts.append('   <Row ss:Height="10"></Row>')
    
    # 3. Finansal Özet KPI Kartları
    xml_parts.append('   <Row ss:Height="28">')
    xml_parts.append(f'    <Cell ss:MergeAcross="1" ss:StyleID="CardGelir"><Data ss:Type="String">TOPLAM GELİR: +{toplam_gelir:,.2f} TL</Data></Cell>')
    xml_parts.append(f'    <Cell ss:MergeAcross="1" ss:StyleID="CardGider"><Data ss:Type="String">TOPLAM GİDER: -{toplam_gider:,.2f} TL</Data></Cell>')
    xml_parts.append(f'    <Cell ss:MergeAcross="1" ss:StyleID="CardNet"><Data ss:Type="String">NET DURUM: {net_durum:,.2f} TL</Data></Cell>')
    xml_parts.append('   </Row>')
    xml_parts.append('   <Row ss:Height="12"></Row>')
    
    # 4. Kategori Bazlı Harcama Dağılımı (Varsa)
    if kategori_gider:
        xml_parts.append('   <Row ss:Height="22">')
        xml_parts.append('    <Cell ss:MergeAcross="5" ss:StyleID="SectionHeader"><Data ss:Type="String">🏷️ GİDER KATEGORİ DAĞILIMI</Data></Cell>')
        xml_parts.append('   </Row>')
        for kat, amt in kategori_gider.items():
            oran = (amt / toplam_gider * 100) if toplam_gider > 0 else 0
            xml_parts.append('   <Row ss:Height="20">')
            xml_parts.append(f'    <Cell ss:MergeAcross="2" ss:StyleID="DataRowEven"><Data ss:Type="String">🏷️ {esc(kat)}</Data></Cell>')
            xml_parts.append(f'    <Cell ss:StyleID="DataRowEven"><Data ss:Type="String">%{oran:.1f} Pay</Data></Cell>')
            xml_parts.append(f'    <Cell ss:MergeAcross="1" ss:StyleID="MoneyGider"><Data ss:Type="Number">{amt}</Data></Cell>')
            xml_parts.append('   </Row>')
        xml_parts.append('   <Row ss:Height="10"></Row>')
    
    # 5. Detaylı İşlem Tablosu Başlığı
    xml_parts.append('   <Row ss:Height="22">')
    xml_parts.append('    <Cell ss:MergeAcross="5" ss:StyleID="SectionHeader"><Data ss:Type="String">📋 DETAYLI HESAP HAREKETLERİ DÖKÜMÜ</Data></Cell>')
    xml_parts.append('   </Row>')
    
    xml_parts.append('   <Row ss:Height="24">')
    xml_parts.append('    <Cell ss:StyleID="TableHeader"><Data ss:Type="String">Sıra</Data></Cell>')
    xml_parts.append('    <Cell ss:StyleID="TableHeader"><Data ss:Type="String">Tarih</Data></Cell>')
    xml_parts.append('    <Cell ss:StyleID="TableHeader"><Data ss:Type="String">İşlem Açıklaması</Data></Cell>')
    xml_parts.append('    <Cell ss:StyleID="TableHeader"><Data ss:Type="String">Kategori</Data></Cell>')
    xml_parts.append('    <Cell ss:StyleID="TableHeader"><Data ss:Type="String">İşlem Türü</Data></Cell>')
    xml_parts.append('    <Cell ss:StyleID="TableHeader"><Data ss:Type="String">Tutar (TL)</Data></Cell>')
    xml_parts.append('   </Row>')
    
    # 6. İşlem Satırları
    for idx, i in enumerate(islemler, 1):
        row_style = "DataRowEven" if idx % 2 == 0 else "DataRowOdd"
        badge_style = "GelirBadge" if i.tip == 'gelir' else "GiderBadge"
        money_style = "MoneyGelir" if i.tip == 'gelir' else "MoneyGider"
        
        tarih_str = i.tarih.strftime('%d.%m.%Y')
        baslik_str = esc(i.baslik) if i.baslik else "Açıklamasız İşlem"
        kat_str = esc(i.kategori)
        tip_str = "GELİR (+)" if i.tip == 'gelir' else "GİDER (-)"
        
        xml_parts.append('   <Row ss:Height="22">')
        xml_parts.append(f'    <Cell ss:StyleID="{row_style}"><Data ss:Type="Number">{idx}</Data></Cell>')
        xml_parts.append(f'    <Cell ss:StyleID="{row_style}"><Data ss:Type="String">{tarih_str}</Data></Cell>')
        xml_parts.append(f'    <Cell ss:StyleID="{row_style}"><Data ss:Type="String">{baslik_str}</Data></Cell>')
        xml_parts.append(f'    <Cell ss:StyleID="{row_style}"><Data ss:Type="String">{kat_str}</Data></Cell>')
        xml_parts.append(f'    <Cell ss:StyleID="{badge_style}"><Data ss:Type="String">{tip_str}</Data></Cell>')
        xml_parts.append(f'    <Cell ss:StyleID="{money_style}"><Data ss:Type="Number">{i.miktar}</Data></Cell>')
        xml_parts.append('   </Row>')
        
    if not islemler:
        xml_parts.append('   <Row ss:Height="22">')
        xml_parts.append('    <Cell ss:MergeAcross="5" ss:StyleID="DataRowOdd"><Data ss:Type="String">Bu hesaba ait herhangi bir işlem hareketi bulunmamaktadır.</Data></Cell>')
        xml_parts.append('   </Row>')
        
    # 7. Alt Toplam Satırı
    xml_parts.append('   <Row ss:Height="24">')
    xml_parts.append('    <Cell ss:MergeAcross="4" ss:StyleID="TotalRow"><Data ss:Type="String">GENEL NET BAKİYE TOPLAMI:</Data></Cell>')
    xml_parts.append(f'    <Cell ss:StyleID="TotalMoney"><Data ss:Type="Number">{net_durum}</Data></Cell>')
    xml_parts.append('   </Row>')
    
    xml_parts.append('  </Table>')
    xml_parts.append(' </Worksheet>')
    xml_parts.append('</Workbook>')
    
    xml_content = "\n".join(xml_parts)
    filename = f"Finans_Raporu_{u.username}_{now.strftime('%Y%m%d')}.xls"
    
    return Response(
        xml_content,
        mimetype="application/vnd.ms-excel; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- HATA YÖNETİMİ ---
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # SQLite geriye dönük kolon uyumluluğu kontrolü
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text("ALTER TABLE user ADD COLUMN butce_hedefi FLOAT DEFAULT 0.0"))
                conn.commit()
        except Exception:
            pass
        
        if not User.query.filter_by(role='admin').first():
            admin_hashed = generate_password_hash("admin123", method='scrypt')
            default_admin = User(username="admin", password=admin_hashed, role="admin")
            db.session.add(default_admin)
            
        if not User.query.filter_by(username='mert').first():
            mert_hashed = generate_password_hash("Mert12345", method='scrypt')
            default_user = User(username="mert", password=mert_hashed, role="user", email="yusufmert1978@gmail.com")
            db.session.add(default_user)
            
        db.session.commit()
        print("⭐ Varsayılan hesaplar ve veritabanı hazır!")
            
    app.run(debug=True, port=5001)