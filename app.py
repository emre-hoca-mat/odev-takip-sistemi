import datetime
from datetime import date
import io
import urllib.parse
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(
    page_title="Özel Ders, Ajanda & Günlük Ödev Takip Sistemi",
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
SUTUNLAR_DERS = ["Öğrenci", "Tarih", "Saat", "Konu / Not", "Durum"]

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


def dersleri_yukle():
  try:
    data = conn.read(worksheet="Dersler", ttl=0)
    return data if not data.empty else pd.DataFrame(columns=SUTUNLAR_DERS)
  except Exception:
    return pd.DataFrame(columns=SUTUNLAR_DERS)


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


def dersleri_kaydet(df):
  try:
    conn.update(worksheet="Dersler", data=df)
  except Exception:
    pass


df_odev = odevleri_yukle()
df_ogrenci = ogrencileri_yukle()
df_ders = dersleri_yukle()

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

for s in SUTUNLAR_DERS:
  if s not in df_ders.columns:
    df_ders[s] = "-"

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
  st.title(f"🎓 {secilen_ogrenci} — Öğrenci Portalı")

  col_s1, col_s2 = st.columns([2, 1])
  with col_s1:
    st.info(
        f"👋 Hoş geldin **{secilen_ogrenci}**! Günlük ödevlerini tamamlayınca"
        " Doğru ve Yanlış sayılarını girip kaydedebilirsin."
    )
  with col_s2:
    secilen_tarih = st.date_input("📅 Tarih Seçin:", date.today())

  tarih_str = secilen_tarih.strftime("%d-%m-%Y")
  st.divider()

  # Öğrencinin o günkü ders saati
  bugun_dersler = df_ders[
      (df_ders["Öğrenci"] == secilen_ogrenci)
      & (df_ders["Tarih"].astype(str) == tarih_str)
  ]
  if not bugun_dersler.empty:
    st.subheader(f"📆 {tarih_str} Tarihindeki Ders Saatiniz")
    for _, d_row in bugun_dersler.iterrows():
      st.warning(
          f"⏰ **Ders Saati:** {d_row['Saat']} | 📖 **Konu:**"
          f" {d_row['Konu / Not']} | 📌 **Durum:** {d_row['Durum']}"
      )
    st.write("---")

  # Ödevler
  st.subheader(f"📌 {tarih_str} Günlük Ödev Listesi")
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
      st_soru = int(row["Soru Sayısı"]) if str(row["Soru Sayısı"]).isdigit() else 30
      st_d_init = int(row["Doğru"]) if str(row["Doğru"]).isdigit() else 0
      st_y_init = int(row["Yanlış"]) if str(row["Yanlış"]).isdigit() else 0

      status_badge = "✅ Tamamlandı" if row["Durum"] == "Tamamlandı" else "⏳ Bekliyor"
      
      with st.expander(
          f"📖 **{row['Konu']}** ({st_soru} Soru) — `{status_badge}`",
          expanded=(row["Durum"] != "Tamamlandı"),
      ):
        st.write("✍️ **Çözdüğünüz Doğru / Yanlış Sayılarını Girin:**")
        st_col1, st_col2, st_col3 = st.columns(3)

        with st_col1:
          st_d = st.number_input(
              "Doğru Sayısı",
              min_value=0,
              max_value=st_soru,
              value=min(st_d_init, st_soru),
              key=f"st_d_link_{idx}",
          )
        with st_col2:
          st_y = st.number_input(
              "Yanlış Sayısı",
              min_value=0,
              max_value=st_soru - st_d,
              value=min(st_y_init, st_soru - st_d),
              key=f"st_y_link_{idx}",
          )
        with st_col3:
          st_b = st_soru - (st_d + st_y)
          st.metric("Otomatik Boş Sayısı", st_b)

        st_net = max(0.0, st_d - (st_y / 4.0))
        st_basari = round((st_net / float(st_soru)) * 100, 1) if st_soru > 0 else 0.0

        st.info(
            f"🧮 **Hesaplanan Net:** {st_net:.2f} | 🎯 **Başarı Oranı:** %{st_basari}"
        )

        if st.button("💾 Sonuçlarımı Kaydet & Tamamla", key=f"btn_st_save_link_{idx}"):
          df_odev.at[idx, "Doğru"] = st_d
          df_odev.at[idx, "Yanlış"] = st_y
          df_odev.at[idx, "Boş"] = st_b
          df_odev.at[idx, "Net"] = st_net
          df_odev.at[idx, "Başarı (%)"] = st_basari
          df_odev.at[idx, "Durum"] = "Tamamlandı"

          odevleri_kaydet(df_odev)
          st.toast("🎉 Ödev sonuçlarınız başarıyla kaydedildi!")
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
  # 2A: GENEL ÖĞRENCİ MODU
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

      bugun_dersler = df_ders[
          (df_ders["Öğrenci"] == secilen_ogrenci)
          & (df_ders["Tarih"].astype(str) == tarih_str)
      ]
      if not bugun_dersler.empty:
        st.subheader(f"📆 {tarih_str} Tarihindeki Ders Saatiniz")
        for _, d_row in bugun_dersler.iterrows():
          st.warning(
              f"⏰ **Ders Saati:** {d_row['Saat']} | 📖 **Konu:**"
              f" {d_row['Konu / Not']} | 📌 **Durum:** {d_row['Durum']}"
          )
        st.write("---")

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
          st_soru = int(row["Soru Sayısı"]) if str(row["Soru Sayısı"]).isdigit() else 30
          st_d_init = int(row["Doğru"]) if str(row["Doğru"]).isdigit() else 0
          st_y_init = int(row["Yanlış"]) if str(row["Yanlış"]).isdigit() else 0

          status_badge = "✅ Tamamlandı" if row["Durum"] == "Tamamlandı" else "⏳ Bekliyor"

          with st.expander(
              f"📖 **{row['Konu']}** ({st_soru} Soru) — `{status_badge}`",
              expanded=(row["Durum"] != "Tamamlandı"),
          ):
            st.write("✍️ **Çözdüğünüz Doğru / Yanlış Sayılarını Girin:**")
            st_col1, st_col2, st_col3 = st.columns(3)

            with st_col1:
              st_d = st.number_input(
                  "Doğru Sayısı",
                  min_value=0,
                  max_value=st_soru,
                  value=min(st_d_init, st_soru),
                  key=f"st_d_genel_{idx}",
              )
            with st_col2:
              st_y = st.number_input(
                  "Yanlış Sayısı",
                  min_value=0,
                  max_value=st_soru - st_d,
                  value=min(st_y_init, st_soru - st_d),
                  key=f"st_y_genel_{idx}",
              )
            with st_col3:
              st_b = st_soru - (st_d + st_y)
              st.metric("Otomatik Boş Sayısı", st_b)

            st_net = max(0.0, st_d - (st_y / 4.0))
            st_basari = round((st_net / float(st_soru)) * 100, 1) if st_soru > 0 else 0.0

            st.info(
                f"🧮 **Hesaplanan Net:** {st_net:.2f} | 🎯 **Başarı Oranı:** %{st_basari}"
            )

            if st.button("💾 Sonuçlarımı Kaydet & Tamamla", key=f"btn_st_save_genel_{idx}"):
              df_odev.at[idx, "Doğru"] = st_d
              df_odev.at[idx, "Yanlış"] = st_y
              df_odev.at[idx, "Boş"] = st_b
              df_odev.at[idx, "Net"] = st_net
              df_odev.at[idx, "Başarı (%)"] = st_basari
              df_odev.at[idx, "Durum"] = "Tamamlandı"

              odevleri_kaydet(df_odev)
              st.toast("🎉 Ödev sonuçlarınız başarıyla kaydedildi!")
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
          tab_eksik,
          tab_dersler,
          tab_haftalik,
          tab_ogrenci,
          tab_odevler,
          tab_rapor,
          tab_export,
      ) = st.tabs([
          "➕ Günlük Ödev Ver",
          "✍️ Ödev Düzenle & Değerlendir",
          "🎯 Konu Eksik Haritası",
          "📆 Ders Programı & Ajanda",
          "📅 Günlük / Haftalık Takvim",
          "👤 Öğrenci Yönetimi & Özel Linkler",
          "📋 Ödev Kartı & Geçmiş",
          "📲 Veli WhatsApp Raporu",
          "📥 Rapor İndir (Excel / CSV)",
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
                "Hedeflanan Soru Sayısı", min_value=1, value=30, step=5
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
                      "Doğru",
                      "Yanlış",
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
          st.write("📊 **Soru / Net Değerlendirmesi:**")

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

      # 3. SEKME: KONU EKSİK HARİTASI
      with tab_eksik:
        st.header(f"🎯 Konu Bazlı Eksik Haritası ve Analiz — {secili_ogrenci}")

        eksik_df = (
            df_odev
            if secili_ogrenci == "Tüm Öğrenciler"
            else df_odev[df_odev["Öğrenci"] == secili_ogrenci]
        )

        eval_df = eksik_df[eksik_df["Durum"].isin(["Tamamlandı", "Eksik"])].copy()

        if not eval_df.empty:
          eval_df["Başarı (%)"] = pd.to_numeric(
              eval_df["Başarı (%)"], errors="coerce"
          ).fillna(0.0)
          eval_df["Net"] = pd.to_numeric(
              eval_df["Net"], errors="coerce"
          ).fillna(0.0)
          eval_df["Soru Sayısı"] = pd.to_numeric(
              eval_df["Soru Sayısı"], errors="coerce"
          ).fillna(0)

          konu_ozet = (
              eval_df.groupby("Konu")
              .agg(
                  Ortalama_Basari=("Başarı (%)", "mean"),
                  Toplam_Net=("Net", "sum"),
                  Toplam_Soru=("Soru Sayısı", "sum"),
                  Odev_Sayisi=("Konu", "count"),
              )
              .reset_index()
          )

          konu_ozet["Ortalama_Basari"] = konu_ozet["Ortalama_Basari"].round(1)

          kritik_sayisi = len(konu_ozet[konu_ozet["Ortalama_Basari"] < 60])
          orta_sayisi = len(
              konu_ozet[
                  (konu_ozet["Ortalama_Basari"] >= 60)
                  & (konu_ozet["Ortalama_Basari"] < 80)
              ]
          )
          iyi_sayisi = len(konu_ozet[konu_ozet["Ortalama_Basari"] >= 80])

          m_k1, m_k2, m_k3 = st.columns(3)
          m_k1.metric("🔴 Kritik Konular (<%60)", f"{kritik_sayisi} Konu")
          m_k2.metric("🟡 Pekiştirilmeli (%60-%80)", f"{orta_sayisi} Konu")
          m_k3.metric("🟢 Kavranmış Konular (≥%80)", f"{iyi_sayisi} Konu")

          st.divider()

          col_h1, col_h2 = st.columns([1, 1])

          with col_h1:
            st.subheader("🔴 Kritik Konular (Acil Tekrar Edilmeli)")
            kritik_df = konu_ozet[konu_ozet["Ortalama_Basari"] < 60]
            if not kritik_df.empty:
              for _, k_row in kritik_df.iterrows():
                st.error(
                    f"📖 **{k_row['Konu']}**\n\n"
                    f"🎯 Ortalama Başarı: **%{k_row['Ortalama_Basari']}** | "
                    f"🧮 Toplam Net: {k_row['Toplam_Net']} | "
                    f"❓ Çözülen Soru: {k_row['Toplam_Soru']}"
                )
            else:
              st.success("Tebrikler! Kritik düzeyde eksik olan konu bulunmuyor.")

            st.subheader("🟡 Pekiştirilmeli (Soru Çözümü Yapılmalı)")
            orta_df = konu_ozet[
                (konu_ozet["Ortalama_Basari"] >= 60)
                & (konu_ozet["Ortalama_Basari"] < 80)
            ]
            if not orta_df.empty:
              for _, o_row in orta_df.iterrows():
                st.warning(
                    f"📖 **{o_row['Konu']}**\n\n"
                    f"🎯 Ortalama Başarı: **%{o_row['Ortalama_Basari']}** | "
                    f"🧮 Toplam Net: {o_row['Toplam_Net']} | "
                    f"❓ Çözülen Soru: {o_row['Toplam_Soru']}"
                )
            else:
              st.info("Pekiştirilmesi gereken orta düzey konu yok.")

          with col_h2:
            st.subheader("🟢 Kavranmış Konular (Başarılı)")
            iyi_df = konu_ozet[konu_ozet["Ortalama_Basari"] >= 80]
            if not iyi_df.empty:
              for _, i_row in iyi_df.iterrows():
                st.success(
                    f"📖 **{i_row['Konu']}**\n\n"
                    f"🎯 Ortalama Başarı: **%{i_row['Ortalama_Basari']}** | "
                    f"🧮 Toplam Net: {i_row['Toplam_Net']} | "
                    f"❓ Çözülen Soru: {i_row['Toplam_Soru']}"
                )
            else:
              st.caption("Henüz %80 üstü başarı sağlanan konu bulunmuyor.")

          st.divider()
          st.subheader("📊 Tüm Konuların Detaylı Listesi")
          st.dataframe(
              konu_ozet.rename(
                  columns={
                      "Konu": "Matematik Konusu",
                      "Ortalama_Basari": "Ortalama Başarı (%)",
                      "Toplam_Net": "Toplam Net",
                      "Toplam_Soru": "Çözülen Soru Sayısı",
                      "Odev_Sayisi": "Ödev Sayısı",
                  }
              ),
              use_container_width=True,
          )
        else:
          st.info(
              "Eksik haritası çıkarılabilmesi için değerlendirilmiş veya"
              " öğrenci tarafından Doğru/Yanlış sayısı girilmiş ödev bulunması"
              " gerekmektedir."
          )

      # 4. SEKME: DERS PROGRAMI & AJANDA
      with tab_dersler:
        st.header("📆 Özel Ders Programı & Ajanda Takibi")

        col_d1, col_d2 = st.columns([1, 1])

        with col_d1:
          st.subheader("➕ Yeni Ders Planla")
          with st.form("yeni_ders_formu", clear_on_submit=True):
            d_ogr = st.selectbox(
                "Öğrenci Seçin:",
                tum_ogrenciler if tum_ogrenciler else ["Kayıtlı Öğrenci Yok"],
            )
            d_tarih = st.date_input("Ders Tarihi:", date.today())
            d_saat = st.text_input(
                "Ders Saat Aralığı (Örn: 15:30 - 17:00)", value="16:00 - 17:30"
            )
            d_konu = st.text_input(
                "Ders Konusu / Notu (Örn: Logaritma 2. Ders)"
            )
            d_durum = st.selectbox(
                "Ders Durumu:", ["Planlandı", "Yapıldı", "İptal Edildi"]
            )

            btn_ders_ekle = st.form_submit_button("Dersi Ajandaya Ekle")

            if btn_ders_ekle:
              if d_ogr == "Kayıtlı Öğrenci Yok":
                st.error("Önce bir öğrenci kaydetmelisiniz!")
              else:
                yeni_ders_df = pd.DataFrame([{
                    "Öğrenci": d_ogr,
                    "Tarih": d_tarih.strftime("%d-%m-%Y"),
                    "Saat": d_saat.strip(),
                    "Konu / Not": d_konu.strip(),
                    "Durum": d_durum,
                }])
                df_ders = pd.concat(
                    [df_ders, yeni_ders_df], ignore_index=True
                )
                dersleri_kaydet(df_ders)
                st.success(
                    f"✅ {d_ogr} için {d_tarih.strftime('%d-%m-%Y')} saat {d_saat}"
                    " dersi planlandı!"
                )
                st.rerun()

        with col_d2:
          st.subheader("✏️ Planlanan Dersleri Düzenle / İptal Et")
          if not df_ders.empty:
            filtre_d_df = (
                df_ders
                if secili_ogrenci == "Tüm Öğrenciler"
                else df_ders[df_ders["Öğrenci"] == secili_ogrenci]
            )
            if not filtre_d_df.empty:
              d_gosterim = filtre_d_df.copy()
              d_gosterim.index = d_gosterim.index + 1
              st.dataframe(d_gosterim, use_container_width=True)

              d_sira = st.number_input(
                  "Düzenlenecek Ders Sıra No:",
                  min_value=1,
                  max_value=len(filtre_d_df),
                  value=1,
                  step=1,
              )
              g_d_idx = filtre_d_df.index[d_sira - 1]
              mev_ders = df_ders.loc[g_d_idx]

              new_d_durum = st.selectbox(
                  "Ders Durumunu Güncelle:",
                  ["Planlandı", "Yapıldı", "İptal Edildi"],
                  index=[
                      "Planlandı",
                      "Yapıldı",
                      "İptal Edildi",
                  ].index(
                      mev_ders["Durum"]
                      if mev_ders["Durum"]
                      in ["Planlandı", "Yapıldı", "İptal Edildi"]
                      else 0
                  ),
                  key="sb_d_durum_edit",
              )

              d_btn_c1, d_btn_c2 = st.columns(2)
              with d_btn_c1:
                if st.button("💾 Ders Durumunu Kaydet"):
                  df_ders.at[g_d_idx, "Durum"] = new_d_durum
                  dersleri_kaydet(df_ders)
                  st.success("Ders durumu güncellendi!")
                  st.rerun()
              with d_btn_c2:
                if st.button("❌ Dersi Ajandadan Sil"):
                  df_ders = df_ders.drop(index=g_d_idx).reset_index(drop=True)
                  dersleri_kaydet(df_ders)
                  st.warning("Ders kaydı silindi.")
                  st.rerun()
            else:
              st.info("Bu öğrenci için kayıtlı ders bulunmuyor.")
          else:
            st.info("Henüz ajandada ders kaydı yok.")

        st.divider()
        st.subheader(f"📅 Haftalık Ders Ajandası Görünümü — {secili_ogrenci}")

        filtre_ders_takvim = (
            df_ders
            if secili_ogrenci == "Tüm Öğrenciler"
            else df_ders[df_ders["Öğrenci"] == secili_ogrenci]
        )
        if not filtre_ders_takvim.empty:
          filtre_ders_takvim = filtre_ders_takvim.copy()
          filtre_ders_takvim["Tarih_DT"] = pd.to_datetime(
              filtre_ders_takvim["Tarih"], format="%d-%m-%Y", errors="coerce"
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
          cols_d = st.columns(7)

          for i, gun in enumerate(gun_isimleri):
            with cols_d[i]:
              st.markdown(f"### {gun}")
              gunluk_d = filtre_ders_takvim[
                  filtre_ders_takvim["Tarih_DT"].dt.dayofweek == i
              ]
              if not gunluk_d.empty:
                for _, r_d in gunluk_d.iterrows():
                  d_status_icon = (
                      "🟢"
                      if r_d["Durum"] == "Yapıldı"
                      else ("🟡" if r_d["Durum"] == "Planlandı" else "🔴")
                  )
                  st.warning(
                      f"{d_status_icon} **{r_d['Öğrenci']}**\n\n"
                      f"⏰ {r_d['Saat']}\n\n"
                      f"📖 {r_d['Konu / Not']}\n\n"
                      f"📅 {r_d['Tarih']}"
                  )
              else:
                st.caption("Ders yok")

      # 5. SEKME: GÜNLÜK / HAFTALIK TAKVİM
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

      # 6. SEKME: ÖĞRENCİ YÖNETİMİ & ÖZEL LİNKLER
      with tab_ogrenci:
        st.header("👤 Öğrenci Kayıt, Düzenleme ve Özel Erişim Linkleri")

        base_url_input = st.text_input(
            "🌐 Canlı Uygulama Web Adresiniz (URL):",
            value="https://odev-takip-sistemi-cueteauhyqpemrrmmar7tt.streamlit.app/",
            help="Tarayıcı adres çubuğundaki ana site adresinizi buraya yapıştırın.",
        )

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

          st.divider()

          st.subheader("✏️ Öğrenci Bilgilerini Düzenle ve Sil")
          if not df_ogrenci.empty and len(df_ogrenci) > 0:
            secilen_duzen_ogrenci = st.selectbox(
                "Düzenlenecek / Silinecek Öğrenciyi Seçin:",
                df_ogrenci["Öğrenci Adı"].unique(),
                key="sb_duzen_ogrenci",
            )

            ogrenci_row_idx = df_ogrenci[
                df_ogrenci["Öğrenci Adı"] == secilen_duzen_ogrenci
            ].index[0]
            mevcut_ogrenci = df_ogrenci.loc[ogrenci_row_idx]

            with st.form("ogrenci_duzenle_formu"):
              d_y_adi = st.text_input(
                  "Öğrenci Adı Soyadı",
                  value=str(mevcut_ogrenci["Öğrenci Adı"]),
              )
              d_y_sinif = st.text_input(
                  "Sınıfı / Seviyesi",
                  value=str(mevcut_ogrenci["Sınıf / Seviye"]),
              )
              d_y_tel = st.text_input(
                  "Veli Telefon Numarası",
                  value=str(mevcut_ogrenci["Veli Telefonu"]),
              )
              d_y_not = st.text_area(
                  "Özel Notlar", value=str(mevcut_ogrenci["Notlar"])
              )

              btn_col_o1, btn_col_o2 = st.columns(2)
              with btn_col_o1:
                btn_ogrenci_guncelle = st.form_submit_button("💾 Güncelle")
              with btn_col_o2:
                btn_ogrenci_sil = st.form_submit_button("❌ Öğrenciyi Sil")

              if btn_ogrenci_guncelle:
                eski_isim = mevcut_ogrenci["Öğrenci Adı"]
                yeni_isim = d_y_adi.strip()
                if yeni_isim == "":
                  st.error("Öğrenci adı boş bırakılamaz!")
                else:
                  df_ogrenci.at[ogrenci_row_idx, "Öğrenci Adı"] = yeni_isim
                  df_ogrenci.at[ogrenci_row_idx, "Sınıf / Seviye"] = (
                      d_y_sinif.strip()
                  )
                  df_ogrenci.at[ogrenci_row_idx, "Veli Telefonu"] = (
                      d_y_tel.strip()
                  )
                  df_ogrenci.at[ogrenci_row_idx, "Notlar"] = d_y_not.strip()
                  ogrencileri_kaydet(df_ogrenci)

                  if eski_isim != yeni_isim and not df_odev.empty:
                    df_odev.loc[df_odev["Öğrenci"] == eski_isim, "Öğrenci"] = (
                        yeni_isim
                    )
                    odevleri_kaydet(df_odev)

                  st.success(f"{yeni_isim} bilgileri başarıyla güncellendi!")
                  st.rerun()

              if btn_ogrenci_sil:
                silinen_isim = mevcut_ogrenci["Öğrenci Adı"]
                df_ogrenci = df_ogrenci.drop(index=ogrenci_row_idx).reset_index(
                    drop=True
                )
                ogrencileri_kaydet(df_ogrenci)
                st.warning(f"{silinen_isim} sistemden silindi.")
                st.rerun()
          else:
            st.info("Kayıtlı öğrenci bulunmuyor.")

        with col_o2:
          st.subheader("🔗 Öğrenciye Özel Giriş Linkleri")
          st.caption(
              "Yukarıya ana site adresinizi yapıştırdıktan sonra oluşan özel"
              " linkleri öğrencilerinize gönderebilirsiniz."
          )

          clean_base_url = base_url_input.rstrip("/")

          if tum_ogrenciler:
            for ogr in tum_ogrenciler:
              encoded_name = urllib.parse.quote(ogr)
              ogrenci_linki = f"{clean_base_url}/?ogrenci={encoded_name}"

              st.text_input(
                  f"📌 {ogr} Özel Giriş Linki:",
                  value=ogrenci_linki,
                  key=f"link_input_{ogr}",
              )
          else:
            st.info("Kayıtlı öğrenci bulunmuyor.")

      # 7. SEKME: ÖDEV KARTLARI
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

      # 8. SEKME: VELİ WHATSAPP RAPORU
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

      # 9. SEKME: RAPOR İNDİR (EXCEL / CSV)
      with tab_export:
        st.header(f"📥 Rapor İndir (Excel / CSV) — {secili_ogrenci}")
        st.write(
            "Seçilen öğrenciye veya tüm öğrencilere ait ödev, konu analizi ve"
            " ders ajandası verilerini Excel uyumlu CSV formatında"
            " indirebilirsiniz."
        )

        col_exp1, col_exp2, col_exp3 = st.columns(3)

        with col_exp1:
          st.subheader("📋 Ödev & Performans Raporu")
          exp_odev_df = (
              df_odev
              if secili_ogrenci == "Tüm Öğrenciler"
              else df_odev[df_odev["Öğrenci"] == secili_ogrenci]
          )

          if not exp_odev_df.empty:
            csv_odev = exp_odev_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="⬇️ Ödev Raporunu İndir (.csv)",
                data=csv_odev,
                file_name=f"{secili_ogrenci}_Odev_Raporu.csv",
                mime="text/csv",
                use_container_width=True,
            )
          else:
            st.caption("İndirilecek ödev verisi yok.")

        with col_exp2:
          st.subheader("🎯 Konu Eksik & Başarı Raporu")
          exp_eval_df = (
              df_odev
              if secili_ogrenci == "Tüm Öğrenciler"
              else df_odev[df_odev["Öğrenci"] == secili_ogrenci]
          )
          exp_eval_df = exp_eval_df[
              exp_eval_df["Durum"].isin(["Tamamlandı", "Eksik"])
          ].copy()

          if not exp_eval_df.empty:
            exp_eval_df["Başarı (%)"] = pd.to_numeric(
                exp_eval_df["Başarı (%)"], errors="coerce"
            ).fillna(0.0)
            exp_eval_df["Net"] = pd.to_numeric(
                exp_eval_df["Net"], errors="coerce"
            ).fillna(0.0)
            exp_eval_df["Soru Sayısı"] = pd.to_numeric(
                exp_eval_df["Soru Sayısı"], errors="coerce"
            ).fillna(0)

            exp_konu = (
                exp_eval_df.groupby("Konu")
                .agg(
                    Ortalama_Basari=("Başarı (%)", "mean"),
                    Toplam_Net=("Net", "sum"),
                    Toplam_Soru=("Soru Sayısı", "sum"),
                    Odev_Sayisi=("Konu", "count"),
                )
                .reset_index()
            )
            exp_konu["Ortalama_Basari"] = exp_konu["Ortalama_Basari"].round(1)

            csv_konu = exp_konu.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="⬇️ Konu Analiz Raporunu İndir (.csv)",
                data=csv_konu,
                file_name=f"{secili_ogrenci}_Konu_Analiz_Raporu.csv",
                mime="text/csv",
                use_container_width=True,
            )
          else:
            st.caption("İndirilecek değerlendirilmiş konu verisi yok.")

        with col_exp3:
          st.subheader("📆 Ders Ajandası Raporu")
          exp_ders_df = (
              df_ders
              if secili_ogrenci == "Tüm Öğrenciler"
              else df_ders[df_ders["Öğrenci"] == secili_ogrenci]
          )

          if not exp_ders_df.empty:
            csv_ders = exp_ders_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="⬇️ Ders Ajandası Raporunu İndir (.csv)",
                data=csv_ders,
                file_name=f"{secili_ogrenci}_Ders_Ajandasi.csv",
                mime="text/csv",
                use_container_width=True,
            )
          else:
            st.caption("İndirilecek ders ajandası verisi yok.")