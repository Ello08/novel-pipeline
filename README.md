# Novel Pipeline

Bölüm bölüm yayınlanan web romanlarını indirip metin, görsel ve **EPUB** çıktısına dönüştüren genel amaçlı bir komut satırı aracı.

Belirli bir siteye, hesaba veya API anahtarına bağlı değildir. İçerik kutusu ve "sonraki bölüm" bağlantısı CSS seçicileriyle uyarlanır.

## Özellikler

- **Sıralı çekim:** Her bölümden sonra "sonraki" bağlantısını bulur; farklı alan adına geçmez.
- **Kaldığı yerden devam:** `_state.json` sayesinde yarıda kalan indirme tekrar başlatıldığında tamamlanan bölümleri atlar.
- **Eksik gövde koruması:** HTTP 200 gelse bile "Loading..." veya "yüklenemedi" ile biten sayfaları kaydetmez.
- **Kısa bölüm uyarısı:** Önceki bölümlere göre anormal kısa metinleri işaretler; `audit` bunları hata olarak raporlar.
- **Rate limit dostu:** İstekler arasında bekleme, 429/5xx için `Retry-After` destekli kademeli yeniden deneme.
- **Görsel desteği:** Lazy-load özniteliklerini okur, görselleri doğrular, küçük/reklam görsellerini ve tekrarları eler.
- **EPUB üretimi:** Bölümleri içindekiler tablosuyla paketler, görselleri metindeki konumuna yerleştirir.
- **Tarayıcı modu:** JavaScript ile yüklenen sayfalar için isteğe bağlı Selenium/Chromium desteği.
- **Denetim:** `audit` komutu eksik numara, birebir kopya, kısa bölüm ve HTTP hatalarını tek seferde kontrol eder.

## Gereksinimler

- Python 3.10 veya üzeri
- İnternet bağlantısı
- Tarayıcı modu için Chromium/Chrome ve ChromeDriver (isteğe bağlı)

## Kurulum

```bash
git clone https://github.com/Ello08/novel-pipeline.git
cd novel-pipeline

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Tarayıcı modunu kullanmayacaksanız Selenium'u atlayabilirsiniz:

```bash
python -m pip install beautifulsoup4 ebooklib Pillow requests
```

Kurulumu paket olarak yapmak isterseniz:

```bash
python -m pip install -e .
# tarayıcı modu dahil:
python -m pip install -e ".[browser]"
```

## Hızlı başlangıç

Önce tek sayfayı inceleyin. Metin uzunluğu, görsel sayısı ve sonraki bağlantı görünmelidir:

```bash
python -m novel_pipeline probe \
  --url 'https://example.org/story/chapter-1'
```

Ardından ilk 5 bölümü deneyin:

```bash
python -m novel_pipeline fetch \
  --url 'https://example.org/story/chapter-1' \
  --slug example-story \
  --max-chapters 5 \
  --delay 2.5 \
  --images
```

Sonuçları denetleyip EPUB üretin:

```bash
python -m novel_pipeline audit --slug example-story --expected 5
python -m novel_pipeline epub \
  --slug example-story \
  --title 'Example Story' \
  --author 'Author' \
  --lang en
```

Çıktı:

```
output/
├── txt/example-story/
│   ├── 0001.txt
│   ├── 0002.txt
│   ├── _state.json
│   └── _report.json
├── img/example-story/
│   └── 0001/
│       ├── 01.jpg
│       └── _manifest.json
└── epub/
    └── example-story.epub
```

## Komutlar

| Komut | Görev |
|---|---|
| `probe` | Tek sayfayı indirir; başlık, metin, görsel adayı ve sonraki bağlantıyı yazdırır. Kayıt yapmaz. |
| `fetch` | Bölümleri sırayla indirir; metni ve isteğe bağlı görselleri kaydeder. |
| `epub` | İndirilen metin ve görsellerden EPUB üretir. İnternet isteği atmaz. |
| `audit` | Eksik numara, kopya, kısa bölüm ve HTTP hatalarını kontrol eder. |

### `fetch` seçenekleri

| Seçenek | Açıklama |
|---|---|
| `--url` | Serinin **ilk** bölümünün adresi. |
| `--slug` | Çıktı klasörü adı. Harf, rakam, `-` ve `_` kullanılabilir. |
| `--max-chapters` | En fazla bölüm sayısı. `0` sonraki bağlantı kalmayıncaya kadar devam eder. Varsayılan: `1`. |
| `--delay` | İstekler arası bekleme (saniye). Varsayılan: `2.5`. |
| `--images` | Bölüm görsellerini indir ve EPUB için manifest oluştur. |
| `--content-selector` | Metnin bulunduğu CSS seçicisi, örn. `.chapter-content`. |
| `--next-selector` | Sonraki bölüm bağlantısının CSS seçicisi, örn. `a.next`. |
| `--min-chars` | Kabul edilen en düşük metin uzunluğu. Varsayılan: `200`. |
| `--browser` | Sayfayı Selenium/Chromium ile aç. |
| `--headless` | Tarayıcıyı ekransız çalıştır. Yalnız `--browser` ile kullanılır. |
| `--output` | Çıktı kök klasörü. Varsayılan: `output`. |

### `epub` seçenekleri

| Seçenek | Açıklama |
|---|---|
| `--slug` | `txt/` ve `img/` altındaki kaynak klasör. |
| `--title` | Kitap başlığı. Verilmezse slug'dan üretilir. |
| `--author` | Yazar adı. |
| `--lang` | EPUB dili, örn. `tr`, `en`. Varsayılan: `en`. |

### `audit` seçenekleri

| Seçenek | Açıklama |
|---|---|
| `--slug` | Denetlenecek çıktı klasörü. |
| `--expected` | Beklenen en az bölüm sayısı. Eksikse komut hata koduyla çıkar. |
| `--min-chars` | Bir bölümün kabul edilen en düşük uzunluğu. Varsayılan: `200`. |
| `--output` | Çıktı kök klasörü. Varsayılan: `output`. |

## Nasıl çalışır?

1. `fetch`, sayfayı indirir ve `extract` ile içerik kutusunu bulur.
2. Paragrafları ve içerik kutusundaki `<img>` etiketlerini çıkarır.
3. Bölüm metnini `txt/<slug>/0001.txt` olarak atomik biçimde yazar.
4. `--images` açıksa görselleri indirir, Pillow ile doğrular, 400 pikselden küçük olanları ve tekrarları eler.
5. Görselin kaçıncı paragraftan sonra geldiğini `_manifest.json` içine kaydeder.
6. `epub`, bu dosyaları okuyup her bölüm için XHTML üretir; görselleri `after_para` konumuna yerleştirir.

EPUB üretiminde siteye istek atılmaz; `txt/` ve `img/` klasörleri tek kaynaktır.

## Görsel işleme

- `data-src`, `data-original` ve `src` sırayla denenir.
- `data:` ve `blob:` adresleri indirilmez.
- JPEG, PNG, WEBP ve GIF kabul edilir; SVG atlanır.
- Kısa kenarı 400 pikselden küçük görseller elenir.
- Aynı görsel SHA-256 özetiyle bir kez kaydedilir.
- İndirilemeyen görsel metin indirmesini durdurmaz; hata `_manifest.json` içindeki `errors` listesine yazılır.

## Devam etme ve rate limit

Aynı komutu tekrar çalıştırmak güvenlidir. `_state.json` tamamlanan son bölümü ve sıradaki adresi tutar. Yarım kalan bir koşu, kaldığı bölümden devam eder.

- 429 ve 5xx yanıtlarında `Retry-After` okunur; yoksa kademeli bekleme uygulanır.
- 403/404 gibi kalıcı hatalarda işlem durur ve hata `_report.json` dosyasına yazılır.
- Varsayılan 2,5 saniyelik aralık, 100 bölümde yaklaşık 4–5 dakikalık bir çalışma demektir.
- Sunucunun kurallarına ve `robots.txt` dosyasına uyun; izniniz olmayan içeriği indirmeyin.

## Tarayıcı modu

Gövdeyi JavaScript ile yükleyen sayfalar için:

```bash
python -m novel_pipeline probe \
  --url 'https://example.org/story/chapter-1' \
  --browser \
  --content-selector '#reader-text'

python -m novel_pipeline fetch \
  --url 'https://example.org/story/chapter-1' \
  --slug example-story \
  --max-chapters 100 \
  --delay 2.5 \
  --browser \
  --content-selector '#reader-text'
```

Tarayıcı oturumu seri boyunca açık kalır. Ekransız sunucuda `--headless` eklenebilir; ancak insan doğrulaması isteyen siteler ekransız modda metin vermeyebilir. Araç doğrulama korumasını aşmaya çalışmaz.

## Sınırlamalar

- Tek sayfada birden fazla bölüm bulunan yapılar tek bölüm olarak alınır.
- CSS `background-image` ile eklenen görseller yakalanmaz.
- Lazy-load için yalnız `data-src`, `data-original` ve `src` desteklenir.
- Tarayıcı modunda görseller normal HTTP oturumuyla indirilir; yalnız tarayıcı çerezine bağlı görseller alınamayabilir.
- DRM, ödeme duvarı, hesap gereksinimi veya erişim koruması aşılmaz.
- Site yapısı değişirse `--content-selector` ve `--next-selector` güncellenmelidir.

## Testler

Testler ağ erişimi kullanmaz:

```bash
python -m unittest discover -s tests -v
```

## Gizlilik ve anahtarlar

Bu depo hiçbir API anahtarı, çerez, oturum bilgisi veya indirilmiş kitap metni içermez. `.gitignore`; `output/`, `txt/`, `img/`, `epub/`, loglar, `.env` dosyaları ve anahtar benzeri dosyaları dışarıda tutar.

## Lisans

[MIT](LICENSE)
