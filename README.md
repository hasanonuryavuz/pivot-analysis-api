# Devasa Veri · Pivot Analiz API

**1 milyon satış kaydını RAM üzerinde analiz eden, kullanıcı tarafından seçilen eksenlerle dinamik çapraz tablo oluşturan FastAPI + Polars projesi.**

Bölge ve kategoriye göre toplam satış adedini öğrenmek için bir milyon kaydı istemciye taşımaya gerek yoktur. Bu API veriyi bir kez üretir, istenen özeti hesaplar ve 7 × 5 hücrelik satış matrisini JSON olarak döndürür.

## Hızlı başlangıç

Python **3.12** önerilir. Komutları README'nin bulunduğu proje klasöründe çalıştırın.

### Windows / PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

### macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload
```

Tarayıcıda [Swagger UI](http://127.0.0.1:8000/docs) adresini açın. `GET /pivot` → **Try it out** → **Execute** ile deneyin.

## API kullanımı

| Endpoint | İşlev |
| --- | --- |
| `GET /` | Proje bilgisi ve örnek sorgu |
| `GET /health` | Hazır olma durumu ve kayıt sayısı |
| `GET /dataset` | Şema, tablo boyutu, üretim süresi ve 5 örnek kayıt |
| `GET /pivot` | Dinamik eksenlerle toplam satış adedi |
| `GET /docs` | Etkileşimli Swagger arayüzü |

### Bölge × kategori

```text
http://127.0.0.1:8000/pivot?row=Bolge&column=Kategori
```

### Kategori × bölge

```text
http://127.0.0.1:8000/pivot?row=Kategori&column=Bolge
```

### Ocak ayı: tarih × kategori

```text
http://127.0.0.1:8000/pivot?row=Tarih&column=Kategori&start_date=2025-01-01&end_date=2025-01-31
```

| Parametre | Varsayılan | Açıklama |
| --- | --- | --- |
| `row` | `Bolge` | `Tarih`, `Bolge` veya `Kategori` |
| `column` | `Kategori` | Satır ekseninden farklı bir eksen |
| `start_date` | Yok | Dahil başlangıç tarihi; `YYYY-MM-DD` |
| `end_date` | Yok | Dahil bitiş tarihi; `YYYY-MM-DD` |

Eksen isimleri büyük/küçük harfe duyarlıdır ve URL'de ASCII yazılır. Geçersiz eksen, aynı iki eksen, hatalı tarih ve ters tarih aralığı `422` döndürür. Kayıt bulunmazsa başarılı yanıt içinde `data: []` ve sıfır toplam döner. Veri olan satır/sütunlar arasındaki eksik kombinasyonlar `0` ile doldurulur.

### Yanıt biçimi

Aşağıdaki küçük örnek, dört kayıtlık test verisinin sonucudur; gerçek milyon satırlık verinin çıktısı değildir.

```json
{
  "meta": {
    "row": "Bolge",
    "column": "Kategori",
    "aggregation": "sum",
    "source_rows": 4,
    "matched_rows": 4,
    "total_sales": 42,
    "result_rows": 2,
    "result_columns": 2,
    "elapsed_ms": 0.5
  },
  "columns": ["Bolge", "Gida", "Giyim"],
  "data": [
    {"Bolge": "Ege", "Gida": 30, "Giyim": 7},
    {"Bolge": "Marmara", "Gida": 0, "Giyim": 5}
  ]
}
```

`elapsed_ms` örnekte temsilidir; API her istekte gerçek işlem süresini ölçer. `result_columns` yalnızca değer sütunlarını sayar; satır etiketi sütunu bu sayıya dahil değildir.

## Nasıl çalışır?

1. FastAPI `lifespan` başlangıcında 1.000.000 kayıt oluşturulur. Her sorguda yeniden veri üretilmez.
2. NumPy sabit `seed=42` ile vektörleştirilmiş rastgele değerler üretir. Polars bu değerlerden tarih, bölge, kategori ve satış adedi sütunlarını oluşturur.
3. `DataFrame.lazy()` ile sorgu planı kurulur. Tarih filtreleri ve iki eksene göre `group_by().agg(sum)` işlemleri `collect()` çağrısında yürütülür.
4. Küçülen özet üzerinde `DataFrame.pivot(on=..., aggregate_function="sum")` çağrılır. Böylece hem lazy analiz hem açık bir `.pivot()` kullanımı gösterilir.
5. Tarihler ISO metne çevrilir, eksik hücreler sıfırlanır, satır/sütunlar sıralanır ve özet JSON döndürülür.

Bu proje Polars **1.35.2** ile test edilmiştir. Seçilen sürümde lazy toplama sonrası eager pivot yaklaşımı kullanılır. Kaynak: [Polars pivot dokümantasyonu](https://docs.pola.rs/api/python/version/1/reference/dataframe/api/polars.DataFrame.pivot.html).

CPU işlemi içeren endpoint senkron `def` ile tanımlanır; FastAPI bu işi thread pool'da çalıştırır. Veri istekler tarafından değiştirilmez. [FastAPI açıklaması](https://fastapi.tiangolo.com/async/).

## Veri sözlüğü

| Sütun | Polars tipi | İçerik |
| --- | --- | --- |
| `Tarih` | Date | 2025 yılındaki rastgele gün |
| `Bolge` | Categorical | Türkiye'nin 7 coğrafi bölgesi |
| `Kategori` | Categorical | Elektronik, Gida, Giyim, Kitap, Mobilya |
| `Satis_Adedi` | Int64 | 1–100 arasında rastgele adet |

Veriler sentetiktir; gerçek müşteri veya ticari veri içermez. Sabit seed aynı ortamda tekrarlanabilir sonuç verir. Satış toplamı Int64 ile hesaplanır.

## Ölçülen performans

Bu teslimin Linux / Python 3.12.14 / Polars 1.35.2 ortamında:

| Ölçüm | Sonuç |
| --- | --- |
| Kayıt sayısı | 1.000.000 |
| Veri üretimi | 381,503 ms |
| Polars tablosunun tahmini boyutu | 19,073 MiB |
| Bölge × kategori analizi; 7 tekrar medyan | 8,611 ms |
| Özet matris | 7 satır × 5 değer sütunu |

Ham sonuçlar: [`benchmark-results.json`](benchmark-results.json).

Bu süreler donanıma, yük durumuna ve eksen seçimine göre değişir; performans garantisi değildir. Analiz süresi lazy toplama, pivot ve Python sözlüklerine dönüşümü kapsar; HTTP aktarımı ve JSON kodlama süresini kapsamaz. Tahmini tablo boyutu tüm uygulamanın RAM tüketimi değildir; veri üretiminde geçici diziler de kullanılır.

Yeniden ölçmek için:

```bash
python -m scripts.benchmark
```

Burada `python`, bağımlılıkları kurduğunuz sanal ortamın Python'udur. Windows'ta `.\.venv\Scripts\python.exe`, macOS/Linux'ta `.venv/bin/python` kullanabilirsiniz.

## Doğrulama

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

**15 test**: elle hesaplanmış hücreler, eksik kombinasyonlar, altı eksen çiftinin bağımsız Python hesabıyla karşılaştırılması, dahil tarih sınırları, boş sonuç, hatalı istekler, başlangıç yaşam döngüsü, dokümantasyon erişimi, sabit seed ve milyon satırda toplamın korunması.

GitHub Actions her push ve pull request'te testleri çalıştırır. CI sonucu, dosyalar GitHub'a yüklendikten sonra Actions sekmesinden görülebilir.

## Proje düzeni

| Dosya | Sorumluluk |
| --- | --- |
| `app/main.py` | Uygulama başlangıcı, endpoint'ler, parametre doğrulaması |
| `app/data.py` | Sentetik satış verisi üretimi |
| `app/analysis.py` | Lazy analiz, pivot ve yanıt biçimi |
| `tests/test_api.py` | Doğruluk ve API testleri |
| `scripts/benchmark.py` | Tekrarlanabilir süre ölçümü |
| `requirements.txt` | Doğrudan çalışma bağımlılıkları |
| `requirements-dev.txt` | Test bağımlılıkları |
| `requirements-lock.txt` | Teslimde test edilen tam bağımlılık listesi |
| `.github/workflows/tests.yml` | Otomatik test iş akışı |

Tam olarak test edilen bağımlılıkları kurmak isterseniz `python -m pip install -r requirements-lock.txt` kullanın.

## Tasarım sınırları

- Veritabanı ve kalıcı depolama yoktur. Yeniden başlatmada veri tekrar üretilir.
- Her worker kendi milyon satırlık tablosunu tutar. Eğitim projesi için tek worker yeterlidir.
- Tarih ekseni daha geniş JSON üretir; her pivotun 7 × 5 olması beklenmez.
- Kimlik doğrulama, dışarıdan veri yükleme ve istek kotası bu eğitim projesinin kapsamı dışındadır.
- Lazy sorgu RAM'de mevcut tablo üzerinde çalışır; veri üretiminin kendisi lazy değildir.
