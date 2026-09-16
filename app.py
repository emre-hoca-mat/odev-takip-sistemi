import datetime
from datetime import date
import urllib.parse
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(
    page_title="Emre Kaya-Özel Ders Ödev Takip Sistemi",
    page_icon="📝",
    layout="wide",
)

# Öğretmen Giriş Şifresi
OGRETMEN_SIFRESI = "35Da0474"

SUTUNLAR_ODEV = [
    "Öğrenci",
    "Konu",
    "Soru Sayısı",
    "Durum",
    "Tarih",
    "Doğru",
    "Yanlış",
    "Boş",
    "Net",
    "Başarı (%)",
]
SUTUNLAR_OGRENCI = ["Öğrenci Adı", "Sınıf / Seviye", "Veli Telefonu", "Notlar"]

conn = st.connection("gsheets", type=GSheetsConnection)


# --- VERİ YÜKLEME VE KAYDETME FONKSİYONLARI ---
def odevleri_yukle():
  try:
    data = conn.read(worksheet="Ödevler", ttl=0)
    return data if not data.empty else pd.DataFrame(columns=SUTUNLAR_ODEV)
  except Exception:
    try:
      data = conn.read(worksheet="Sayfa1", ttl=0)
      return data if not data.empty else pd.DataFrame(columns=SUTUNLAR_ODEV)
    except Exception:
      try:
        data = conn.read(ttl=0)
        return data if not data.empty else pd.DataFrame(columns=SUTUNLAR_ODEV)
      except Exception:
        return pd.DataFrame(columns=SUTUNLAR_ODEV)


def ogrencileri_yukle():
  try:
    data = conn.read(worksheet="Öğrenciler", ttl=0)
    return data if not data.empty else pd.DataFrame(columns=SUTUNLAR_OGRENCI)
  except Exception:
    return pd.DataFrame(columns=SUTUNLAR_OGRENCI)


def odevleri_kaydet(df):
  try:
    conn.update(worksheet="Ödevler", data=df)
  except Exception:
    try:
      conn.update(worksheet="Sayfa1", data=df)
    except Exception:
      conn.update(data=df)


def ogrencileri_kaydet(df):
  try:
    conn.update(worksheet="Öğrenciler", data=df)
  except Exception:
    conn.update(data=df)


df_odev = odevleri_yukle()
df_ogrenci = ogrencileri_yukle()

# Eksik sütun kontrolü
for s in SUTUNLAR_ODEV:
  if s not in df_odev.columns:
    df_odev[s] = (
        0
        if s in ["Doğru", "Yanlış", "Boş"]
        else (0.0 if s in ["Net", "Başarı (%)"] else "-")
    )

for s in SUTUNLAR_OGRENCI:
  if s not in df_ogrenci.columns:
    df_ogrenci[s] = "-"

kayitli_isimler = (
    list(df_ogrenci["Öğrenci Adı"].dropna().unique())
    if not df_ogrenci.empty
    else []
)
odevdeki_isimler = (
    list(df_odev["Öğrenci"].dropna().unique()) if not df_odev.empty else []
)
tum_ogrenciler = sorted(list(set(kayitli_isimler + odevdeki_isimler)))

# --- URL PARAMETRE KONTROLÜ (ÖĞRENCİYE ÖZEL LİNK) ---
query_ogrenci = st.query_params.get("ogrenci", None)

# ==========================================
# GÖRÜNÜM 1: ÖĞRENCİYE ÖZEL KİLİTLİ SAYFA (ÖZEL LİNK İLE GİRİŞ)
# ==========================================
if query_ogrenci and query_ogrenci in tum_ogrenciler:
  secilen_ogrenci = query_ogrenci
  st.title(f"🎓 {secilen_ogrenci} — Ödev Portalı")

  col_s1, col_s2 = st.columns([2, 1])
  with col_s1:
    st.info(f"👋 Hoş geldin **{secilen_ogrenci}**! Günlük ödevlerini buradan takip edebilirsin.")
  with col_s2:
    secilen_tarih = st.date_input("📅 Tarih Seçin:", date.today())

  tarih_str = secilen_tarih.strftime("%d-%m-%Y")
  st.divider()

  ogrenci_odevleri = df_odev[
      (df_odev["Öğrenci"] == secilen_ogrenci)
      & (df_odev["Tarih"].astype(str) == tarih_str)
  ].copy()

  if not ogrenci_odevleri.empty:
    toplam_odev = len(ogrenci_odevleri)
    tamamlanan_odev = len(
        ogrenci_odevleri[ogrenci_odevleri["Durum"] == "Tamamlandı"]
    )

    ilerleme = tamamlanan_odev / toplam_odev
    st.progress(ilerleme)
    st.caption(
        f"📊 **Günün Tamamlanma Oranı:** %{int(ilerleme * 100)} ({tamamlanan_odev}/{toplam_odev} Ödev Yapıldı)"
    )
    st.write("---")

    for idx, row in ogrenci_odevleri.iterrows():
      is_completed = row["Durum"] == "Tamamlandı"

      c_col1, c_col2 = st.columns([4, 1])
      with c_col1:
        st.markdown(
            f"📖 **{row['Konu']}** — `{row['Soru Sayısı']} Soru`"
        )
      with c_col2:
        yeni_durum_check = st.checkbox(
            "Tamamladım", value=is_completed, key=f"chk_link_{idx}"
        )

      if yeni_durum_check != is_completed:
        df_odev.at[idx, "Durum"] = (
            "Tamamlandı" if yeni_durum_check else "Verildi"
        )
        odevleri_kaydet(df_odev)
        if yeni_durum_check:
          st.toast("🎉 Tebrikler! Ödev tamamlandı olarak işaretlendi.")
        st.rerun()

      st.divider()
  else:
    st.info(f"🎉 {tarih_str} tarihi için tanımlanmış bir ödeviniz bulunmuyor!")

# ==========================================
# GÖRÜNÜM 2: GENEL UYGULAMA (ÖĞRETMEN VEYA GENEL ÖĞRENCİ MODU)
# ==========================================
else:
  st.sidebar.title("🎓 Sistem Menüsü")
  kullanici_rolu = st.sidebar.radio(
      "Giriş Modu Seçin:", ["🎓 Genel Öğrenci Modu", "👨‍🏫 Öğretmen Modu"]
  )

  # ------------------------------------------
  # 2A: GENEL ÖĞRENCİ MODU (TÜM ÖĞRENCİ LİSTESİNDEN SEÇİM)
  # ------------------------------------------
  if kullanici_rolu == "🎓 Genel Öğrenci Modu":
    st.title("🎓 Öğrenci Günlük Ödev Portalı")

    if tum_ogrenciler:
      col_s1, col_s2 = st.columns(2)
      with col_s1:
        secilen_ogrenci = st.selectbox("👤 Adınızı Seçin:", tum_ogrenciler)
      with col_s2:
        secilen_tarih = st.date_input("📅 Tarih Seçin:", date.today())

      tarih_str = secilen_tarih.strftime("%d-%m-%Y")

      st.divider()
      st.subheader(f"📌 {secilen_ogrenci} — {tarih_str} Günlük Ödev Listesi")

      ogrenci_odevleri = df_odev[
          (df_odev["Öğrenci"] == secilen_ogrenci)
          & (df_odev["Tarih"].astype(str) == tarih_str)
      ].copy()

      if not ogrenci_odevleri.empty:
        toplam_odev = len(ogrenci_odevleri)
        tamamlanan_odev = len(
            ogrenci_odevleri[ogrenci_odevleri["Durum"] == "Tamamlandı"]
        )

        ilerleme = tamamlanan_odev / toplam_odev
        st.progress(ilerleme)
        st.caption(
            f"📊 **Günün Tamamlanma Oranı:** %{int(ilerleme * 100)} ({tamamlanan_odev}/{toplam_odev} Ödev Yapıldı)"
        )
        st.write("---")

        for idx, row in ogrenci_odevleri.iterrows():
          is_completed = row["Durum"] == "Tamamlandı"

          c_col1, c_col2 = st.columns([4, 1])
          with c_col1:
            st.markdown(
                f"📖 **{row['Konu']}** — `{row['Soru Sayısı']} Soru`"
            )
          with c_col2:
            yeni_durum_check = st.checkbox(
                "Tamamladım", value=is_completed, key=f"chk_{idx}"
            )

          if yeni_durum_check != is_completed:
            df_odev.at[idx, "Durum"] = (
                "Tamamlandı" if yeni_durum_check else "Verildi"
            )
            odevleri_kaydet(df_odev)
            if yeni_durum_check:
              st.toast("🎉 Tebrikler! Ödev tamamlandı olarak işaretlendi.")
            st.rerun()

          st.divider()
      else:
        st.info(
            f"🎉 {tarih_str} tarihi için tanımlanmış bir ödeviniz bulunmuyor!"
        )
    else:
      st.warning("Sistemde henüz kayıtlı öğrenci bulunmuyor.")

  # ------------------------------------------
  # 2B: ÖĞRETMEN MODU (ŞİFRE KORUMALI)
  # ------------------------------------------
  else:
    st.sidebar.markdown("---")
    sifre_giris = st.sidebar.text_input(
        "🔒 Öğretmen Şifresi:", type="password"
    )

    if sifre_giris != OGRETMEN_SIFRESI:
      st.title("🔒 Öğretmen Paneli Şifreli")
      st.warning(
          "Lütfen sol menüdeki **Öğretmen Şifresi** alanına geçerli şifreyi"
          " giriniz."
      )
      st.info("💡 Varsayılan öğretmen şifreniz: `1234`")
    else:
      st.title("👨‍🏫 Matematik Özel Ders & Öğrenci Yönetim Paneli")

      secili_ogrenci = st.sidebar.selectbox(
          "Filtrelenecek Öğrenci:", ["Tüm Öğrenciler"] + tum_ogrenciler
      )

      (
          tab_ekle,
          tab_degerlendir,
          tab_haftalik,
          tab_ogrenci,
          tab_odevler,
          tab_rapor,
      ) = st.tabs([
          "➕ Günlük Ödev Ver",
          "✍️ Ödev Düzenle & Değerlendir",
          "📅 Günlük / Haftalık Takvim",
          "👤 Öğrenci Yönetimi & Özel Linkler",
          "📋 Ödev Kartı & Geçmiş",
          "📲 Veli WhatsApp Raporu",
      ])

      # 1. SEKME: GÜNLÜK ÖDEV VER
      with tab_ekle:
        st.header("➕ Günlük Ödev Tanımla")
        with st.form("yeni_odev_formu_v3", clear_on_submit=True):
          col_e1, col_e2 = st.columns(2)
          with col_e1:
            varsayilan_index = (
                tum_ogrenciler.index(secili_ogrenci)
                if secili_ogrenci in tum_ogrenciler
                else 0
            )
            o_secim = st.selectbox(
                "Öğrenci Seçin:",
                tum_ogrenciler if tum_ogrenciler else ["Öğrenci Bulunamadı"],
                index=varsayilan_index,
            )
            o_konu = st.text_input(
                "Ödev Ders/Konu (Örn: Matematik - Üslü Sayılar Test 2)"
            )
          with col_e2:
            o_soru = st.number_input(
                "Hedeflenen Soru Sayısı", min_value=1, value=30, step=5
            )
            o_tarih = st.date_input("Ödev Hangi Gün Yapılacak?", date.today())

          btn_odev_kaydet = st.form_submit_button("Ödevi Tanımla")

          if btn_odev_kaydet:
            if o_secim == "Öğrenci Bulunamadı" or o_konu.strip() == "":
              st.error("Lütfen geçerli bir öğrenci ve konu girin!")
            else:
              yeni_odev_kayit = pd.DataFrame([{
                  "Öğrenci": o_secim,
                  "Konu": o_konu.strip(),
                  "Soru Sayısı": o_soru,
                  "Durum": "Verildi",
                  "Tarih": o_tarih.strftime("%d-%m-%Y"),
                  "Doğru": 0,
                  "Yanlış": 0,
                  "Boş": 0,
                  "Net": 0.0,
                  "Başarı (%)": 0.0,
              }])
              df_odev = pd.concat([df_odev, yeni_odev_kayit], ignore_index=True)
              odevleri_kaydet(df_odev)
              st.success(
                  f"✅ {o_secim} için {o_tarih.strftime('%d-%m-%Y')} gününe ödev"
                  " tanımlandı!"
              )
              st.rerun()

      # 2. SEKME: ÖDEV DÜZENLE & DEĞERLENDİR
      with tab_degerlendir:
        st.header(
            f"✍️ Ödev Bilgilerini Düzenle & Değerlendir — {secili_ogrenci}"
        )
        islem_df = (
            df_odev
            if secili_ogrenci == "Tüm Öğrenciler"
            else df_odev[df_odev["Öğrenci"] == secili_ogrenci]
        )

        if not islem_df.empty:
          islem_df_gosterim = islem_df.copy()
          islem_df_gosterim.index = islem_df_gosterim.index + 1
          st.dataframe(
              islem_df_gosterim[
                  [
                      "Öğrenci",
                      "Konu",
                      "Soru Sayısı",
                      "Tarih",
                      "Durum",
                      "Net",
                      "Başarı (%)",
                  ]
              ],
              use_container_width=True,
          )

          secilen_sira = st.number_input(
              "Düzenlenecek Ödevin Sıra Numarası:",
              min_value=1,
              max_value=len(islem_df),
              value=1,
              step=1,
          )
          gercek_index = islem_df.index[secilen_sira - 1]
          mevcut_odev = df_odev.loc[gercek_index]

          st.subheader(
              f"📌 Düzenlenen Ödev: {mevcut_odev['Öğrenci']} —"
              f" {mevcut_odev['Konu']}"
          )

          col_m1, col_m2 = st.columns(2)
          with col_m1:
            curr_student_idx = (
                tum_ogrenciler.index(mevcut_odev["Öğrenci"])
                if mevcut_odev["Öğrenci"] in tum_ogrenciler
                else 0
            )
            duzen_ogrenci = st.selectbox(
                "Öğrenci:", tum_ogrenciler, index=curr_student_idx
            )
            duzen_konu = st.text_input(
                "Ödev Konusu:", value=str(mevcut_odev["Konu"])
            )

            try:
              curr_date = datetime.datetime.strptime(
                  str(mevcut_odev["Tarih"]), "%d-%m-%Y"
              ).date()
            except Exception:
              curr_date = date.today()

            duzen_tarih = st.date_input(
                "Ödev Yapılacak Tarih:", value=curr_date
            )

          with col_m2:
            try:
              init_soru = int(mevcut_odev["Soru Sayısı"])
            except Exception:
              init_soru = 30

            duzen_soru = st.number_input(
                "Hedeflanan Soru Sayısı:", min_value=1, value=init_soru, step=5
            )

            durum_options = ["Verildi", "Tamamlandı", "Eksik", "Yapılmadı"]
            curr_durum_idx = (
                durum_options.index(mevcut_odev["Durum"])
                if mevcut_odev["Durum"] in durum_options
                else 0
            )
            duzen_durum = st.selectbox(
                "Ödev Durumu:", durum_options, index=curr_durum_idx
            )

          st.markdown("---")
          st.write("📊 **Soru / Net Değerlendirmesi (İsteğe Bağlı):**")

          cd1, cd2, cd3 = st.columns(3)
          with cd1:
            try:
              init_d = int(mevcut_odev["Doğru"])
            except Exception:
              init_d = 0
            d_sayi = st.number_input(
                "Doğru Sayısı",
                min_value=0,
                max_value=int(duzen_soru),
                value=min(init_d, int(duzen_soru)),
            )
          with cd2:
            try:
              init_y = int(mevcut_odev["Yanlış"])
            except Exception:
              init_y = 0
            y_sayi = st.number_input(
                "Yanlış Sayısı",
                min_value=0,
                max_value=int(duzen_soru) - d_sayi,
                value=min(init_y, int(duzen_soru) - d_sayi),
            )
          with cd3:
            b_sayi = int(duzen_soru) - (d_sayi + y_sayi)
            st.metric("Otomatik Boş Sayısı", b_sayi)

          h_net = max(0.0, d_sayi - (y_sayi / 4.0))
          h_basari = (
              round((h_net / float(duzen_soru)) * 100, 1)
              if float(duzen_soru) > 0
              else 0.0
          )

          st.info(
              f"🧮 **Hesaplanan Net:** {h_net:.2f} | 🎯 **Başarı Oranı:**"
              f" %{h_basari}"
          )

          btn_col1, btn_col2 = st.columns(2)
          with btn_col1:
            if st.button("💾 Değişiklikleri Kaydet"):
              df_odev.at[gercek_index, "Öğrenci"] = duzen_ogrenci
              df_odev.at[gercek_index, "Konu"] = duzen_konu
              df_odev.at[gercek_index, "Soru Sayısı"] = duzen_soru
              df_odev.at[gercek_index, "Tarih"] = duzen_tarih.strftime(
                  "%d-%m-%Y"
              )
              df_odev.at[gercek_index, "Durum"] = duzen_durum
              df_odev.at[gercek_index, "Doğru"] = d_sayi
              df_odev.at[gercek_index, "Yanlış"] = y_sayi
              df_odev.at[gercek_index, "Boş"] = b_sayi
              df_odev.at[gercek_index, "Net"] = h_net
              df_odev.at[gercek_index, "Başarı (%)"] = h_basari

              odevleri_kaydet(df_odev)
              st.success("Ödev bilgileri başarıyla güncellendi!")
              st.rerun()

          with btn_col2:
            if st.button("❌ Bu Ödevi Sil"):
              df_odev = df_odev.drop(index=gercek_index).reset_index(drop=True)
              odevleri_kaydet(df_odev)
              st.warning("Ödev silindi.")
              st.rerun()
        else:
          st.info("Düzenlenecek veya değerlendirilecek ödev bulunmuyor.")

      # 3. SEKME: GÜNLÜK / HAFTALIK TAKVİM
      with tab_haftalik:
        st.header(f"📅 Günlük / Haftalık Takvim — {secili_ogrenci}")

        filtre_df = (
            df_odev
            if secili_ogrenci == "Tüm Öğrenciler"
            else df_odev[df_odev["Öğrenci"] == secili_ogrenci]
        )

        if not filtre_df.empty:
          filtre_df = filtre_df.copy()
          filtre_df["Tarih_DT"] = pd.to_datetime(
              filtre_df["Tarih"], format="%d-%m-%Y", errors="coerce"
          )

          gun_isimleri = [
              "Pazartesi",
              "Salı",
              "Çarşamba",
              "Perşembe",
              "Cuma",
              "Cumartesi",
              "Pazar",
          ]
          cols = st.columns(7)

          for i, gun in enumerate(gun_isimleri):
            with cols[i]:
              st.markdown(f"### {gun}")
              gunluk_odevler = filtre_df[
                  filtre_df["Tarih_DT"].dt.dayofweek == i
              ]

              if not gunluk_odevler.empty:
                for _, row in gunluk_odevler.iterrows():
                  durum_renk = "✅" if row["Durum"] == "Tamamlandı" else "⏳"
                  st.info(
                      f"{durum_renk} **{row['Öğrenci']}**\n\n"
                      f"📖 {row['Konu']}\n\n"
                      f"❓ {row['Soru Sayısı']} Soru\n\n"
                      f"📅 {row['Tarih']}"
                  )
              else:
                st.caption("Ödev yok")
        else:
          st.info("Gösterilecek ödev bulunmuyor.")

      # 4. SEKME: ÖĞRENCİ YÖNETİMİ & ÖZEL LİNKLER
      with tab_ogrenci:
        st.header("👤 Öğrenci Kayıt ve Özel Erişim Linkleri")
        col_o1, col_o2 = st.columns([1, 1])

        with col_o1:
          st.subheader("➕ Yeni Öğrenci Ekle")
          with st.form("yeni_ogrenci_formu", clear_on_submit=True):
            y_adi = st.text_input("Öğrenci Adı Soyadı")
            y_sinif = st.text_input("Sınıfı / Seviyesi")
            y_tel = st.text_input("Veli Telefon Numarası")
            y_not = st.text_area("Özel Notlar")
            btn_ogrenci_ekle = st.form_submit_button("Öğrenciyi Kaydet")

            if btn_ogrenci_ekle:
              if y_adi.strip() == "":
                st.error("Öğrenci Adı alanı boş bırakılamaz!")
              else:
                yeni_ogrenci_data = pd.DataFrame([{
                    "Öğrenci Adı": y_adi.strip(),
                    "Sınıf / Seviye": y_sinif.strip(),
                    "Veli Telefonu": y_tel.strip(),
                    "Notlar": y_not.strip(),
                }])
                df_ogrenci = pd.concat(
                    [df_ogrenci, yeni_ogrenci_data], ignore_index=True
                )
                ogrencileri_kaydet(df_ogrenci)
                st.success(f"{y_adi} başarıyla kaydedildi!")
                st.rerun()

        with col_o2:
          st.subheader("🔗 Öğrenciye Özel Giriş Linkleri")
          st.caption("Aşağıdaki özel linkleri kopyalayıp sadece ilgili öğrenciye gönderebilirsiniz. Öğrenci bu linkle girdiğinde sadece kendi ödevlerini görür.")

          if tum_ogrenciler:
            for ogr in tum_ogrenciler:
              encoded_name = urllib.parse.quote(ogr)
              # Streamlit Cloud adresi veya yerel adres
              link = f"https://odev-takip.streamlit.app/?ogrenci={encoded_name}"
              st.text_input(f"📌 {ogr} Özel Giriş Linki:", value=link, key=f"link_input_{ogr}")
          else:
            st.info("Kayıtlı öğrenci bulunmuyor.")

      # 5. SEKME: ÖDEV KARTLARI
      with tab_odevler:
        st.header(f"📋 Tüm Ödev Geçmişi — {secili_ogrenci}")
        filtreli_odevler = (
            df_odev
            if secili_ogrenci == "Tüm Öğrenciler"
            else df_odev[df_odev["Öğrenci"] == secili_ogrenci]
        )

        if not filtreli_odevler.empty:
          st.dataframe(filtreli_odevler, use_container_width=True)
          st.subheader("📊 Performans Özeti")
          m1, m2, m3, m4 = st.columns(4)
          m1.metric("Toplam Ödev", len(filtreli_odevler))
          m2.metric(
              "Tamamlanan",
              len(filtreli_odevler[filtreli_odevler["Durum"] == "Tamamlandı"]),
          )

          tamamlananlar = filtreli_odevler[
              filtreli_odevler["Durum"] == "Tamamlandı"
          ]
          ort_net = (
              round(
                  pd.to_numeric(tamamlananlar["Net"], errors="coerce").mean(), 2
              )
              if not tamamlananlar.empty
              else 0.0
          )
          ort_basari = (
              round(
                  pd.to_numeric(
                      tamamlananlar["Başarı (%)"], errors="coerce"
                  ).mean(),
                  1,
              )
              if not tamamlananlar.empty
              else 0.0
          )

          m3.metric("Ortalama Net", f"{ort_net} Net")
          m4.metric("Ortalama Başarı", f"%{ort_basari}")

      # 6. SEKME: VELİ WHATSAPP RAPORU
      with tab_rapor:
        st.header(f"📲 Veli WhatsApp Raporu — {secili_ogrenci}")
        rapor_df = (
            df_odev
            if secili_ogrenci == "Tüm Öğrenciler"
            else df_odev[df_odev["Öğrenci"] == secili_ogrenci]
        )

        if not rapor_df.empty and secili_ogrenci != "Tüm Öğrenciler":
          odev_listesi_rapor = ["Tüm Ödevlerin Genel Özeti"] + list(
              rapor_df["Konu"] + " (" + rapor_df["Tarih"] + ")"
          )
          secilen_r_odev = st.selectbox(
              "Raporlanacak İçeriği Seçin:", odev_listesi_rapor
          )
          ogretmen_notu = st.text_area(
              "Öğretmen Değerlendirme Notu:",
              "Öğrencimiz derste gayet gayretli, günlük ödev takibine devam"
              " edelim.",
          )

          if secilen_r_odev == "Tüm Ödevlerin Genel Özeti":
            toplam_o = len(rapor_df)
            tamamlanan_o = len(rapor_df[rapor_df["Durum"] == "Tamamlandı"])
            ort_n = round(pd.to_numeric(rapor_df["Net"], errors="coerce").mean(), 2)
            ort_b = round(
                pd.to_numeric(rapor_df["Başarı (%)"], errors="coerce").mean(), 1
            )

            wa_mesaj = (
                f"Sayın Velimiz,\n\n"
                f"📚 *{secili_ogrenci}* isimli öğrencimizin Matematik Özel Ders"
                " genel ödev durumu aşağıdadır:\n\n"
                f"🔹 Toplam Ödev Sayısı: {toplam_o}\n"
                f"✅ Tamamlanan Ödev: {tamamlanan_o}\n"
                f"📊 Ortalama Net: {ort_n}\n"
                f"🎯 Genel Başarı Oranı: %{ort_b}\n\n"
                f"📝 *Öğretmen Notu:* {ogretmen_notu}\n\n"
                "İyi günler dilerim."
            )
          else:
            secilen_idx = odev_listesi_rapor.index(secilen_r_odev) - 1
            tek_o = rapor_df.iloc[secilen_idx]
            wa_mesaj = (
                f"Sayın Velimiz,\n\n"
                f"📚 *{secili_ogrenci}* isimli öğrencimizin son ödev sonucu"
                " aşağıdadır:\n\n"
                f"📖 *Konu:* {tek_o['Konu']}\n"
                f"❓ *Soru Sayısı:* {tek_o['Soru Sayısı']}\n"
                f"✅ *Doğru:* {tek_o['Doğru']} | ❌ *Yanlış:* {tek_o['Yanlış']} | ⚪"
                f" *Boş:* {tek_o['Boş']}\n"
                f"🧮 *Net:* {tek_o['Net']}\n"
                f"🎯 *Başarı Oranı:* %{tek_o['Başarı (%)']}\n\n"
                f"📝 *Öğretmen Notu:* {ogretmen_notu}\n\n"
                "İyi günler dilerim."
            )

          encoded_mesaj = urllib.parse.quote(wa_mesaj)
          wa_link = f"https://wa.me/?text={encoded_mesaj}"

          st.markdown("### Mesaj Önizlemesi:")
          st.code(wa_mesaj, language="markdown")
          st.link_button(
              "🚀 WhatsApp'ta Velisine Gönder",
              wa_link,
              type="primary",
              use_container_width=True,
          )
        else:
          st.info(
              "Lütfen sol menüden WhatsApp raporu oluşturmak istediğiniz tek bir"
              " öğrenci seçin."
          )