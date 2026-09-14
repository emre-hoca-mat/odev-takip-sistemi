import os
import urllib.parse
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Ödev & Başarı Takip Sistemi", page_icon="📊", layout="wide")
st.title("📚 Matematik Özel Ders Ödev & Başarı Takip Sistemi")

DOSYA_ADI = "odevler.csv"
SUTUNLAR = ["Öğrenci", "Konu", "Soru Sayısı", "Durum", "Tarih", "Doğru", "Yanlış", "Boş", "Net", "Başarı (%)"]

# Veri dosyasını kontrol et ve yükle
if os.path.exists(DOSYA_ADI):
    df = pd.read_csv(DOSYA_ADI)
    for sutun in SUTUNLAR:
        if sutun not in df.columns:
            if sutun in ["Doğru", "Yanlış", "Boş"]:
                df[sutun] = 0
            elif sutun in ["Net", "Başarı (%)"]:
                df[sutun] = 0.0
            else:
                df[sutun] = "-"
else:
    df = pd.DataFrame(columns=SUTUNLAR)
    df.to_csv(DOSYA_ADI, index=False)

tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Ödev Listesi", 
    "➕ Yeni Ödev Ekle", 
    "✍️ Ödev Değerlendir (D/Y/B Gir)", 
    "📈 Başarı Analizi & Veli WhatsApp Raporu"
])

# ==========================================
# 1. SEKME: ÖDEV LİSTESİ VE FİLTRELEME
# ==========================================
with tab1:
    st.header("📋 Kayıtlı Ödev Listesi")
    
    if not df.empty:
        ogrenci_listesi = ["Tüm Öğrenciler"] + sorted(list(df["Öğrenci"].unique()))
        secilen_ogrenci = st.selectbox("🎯 Öğrenciye Göre Filtrele:", ogrenci_listesi)
        
        filtreli_df = df if secilen_ogrenci == "Tüm Öğrenciler" else df[df["Öğrenci"] == secilen_ogrenci]
        st.dataframe(filtreli_df, use_container_width=True)
        
        st.subheader("📊 Özet İstatistikler")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Toplam Ödev", len(filtreli_df))
        col2.metric("Tamamlanan Ödev", len(filtreli_df[filtreli_df["Durum"] == "Tamamlandı"]))
        
        degerlendirilmis = filtreli_df[filtreli_df["Durum"] == "Tamamlandı"]
        ort_net = round(degerlendirilmis["Net"].mean(), 2) if not degerlendirilmis.empty else 0.0
        ort_basari = round(degerlendirilmis["Başarı (%)"].mean(), 1) if not degerlendirilmis.empty else 0.0
        
        col3.metric("Ortalama Net", f"{ort_net} Net")
        col4.metric("Ortalama Başarı", f"%{ort_basari}")
        
        csv_data = filtreli_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Bu Listeyi Excel (CSV) Olarak İndir",
            data=csv_data,
            file_name=f"odev_listesi_{secilen_ogrenci}.csv",
            mime="text/csv"
        )
    else:
        st.info("Henüz eklenmiş bir ödev bulunmuyor.")

# ==========================================
# 2. SEKME: YENİ ÖDEV EKLE
# ==========================================
with tab2:
    st.header("➕ Yeni Ödev Kaydı")
    
    with st.form("yeni_odev_formu", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            ogrenci = st.text_input("Öğrenci Adı Soyadı")
            konu = st.text_input("Konu (Örn: Türev, Üslü Sayılar)")
        with col_b:
            soru_sayisi = st.number_input("Hedeflenen Soru Sayısı", min_value=1, value=50, step=5)
            tarih = st.date_input("Son Teslim Tarihi")
            
        kaydet = st.form_submit_button("Ödevi Tanımla")
        
        if kaydet:
            if ogrenci.strip() == "" or konu.strip() == "":
                st.error("Lütfen Öğrenci Adı ve Konu alanlarını doldurun!")
            else:
                yeni_kayit = pd.DataFrame([{
                    "Öğrenci": ogrenci.strip(),
                    "Konu": konu.strip(),
                    "Soru Sayısı": soru_sayisi,
                    "Durum": "Verildi",
                    "Tarih": tarih.strftime("%d-%m-%Y"),
                    "Doğru": 0,
                    "Yanlış": 0,
                    "Boş": 0,
                    "Net": 0.0,
                    "Başarı (%)": 0.0
                }])
                df = pd.concat([df, yeni_kayit], ignore_index=True)
                df.to_csv(DOSYA_ADI, index=False)
                st.success(f"{ogrenci} için ödev tanımlandı!")
                st.rerun()

# ==========================================
# 3. SEKME: ÖDEV DEĞERLENDİR (D/Y/B GİR)
# ==========================================
with tab3:
    st.header("✍️ Ödev Değerlendirme ve Sonuç Girişi")
    
    if not df.empty:
        df_gosterim = df.copy()
        df_gosterim.index = df_gosterim.index + 1
        
        st.write("Sonucunu girmek istediğiniz ödevin **Sıra Numarasını** seçin:")
        st.dataframe(df_gosterim[["Öğrenci", "Konu", "Soru Sayısı", "Durum", "Net", "Başarı (%)"]], use_container_width=True)
        
        secilen_sira = st.number_input("İşlem Yapılacak Ödev Sıra No:", min_value=1, max_value=len(df), value=1, step=1)
        gercek_index = secilen_sira - 1
        mevcut_odev = df.iloc[gercek_index]
        
        st.subheader(f"📌 Seçilen Ödev: {mevcut_odev['Öğrenci']} — {mevcut_odev['Konu']} ({mevcut_odev['Soru Sayısı']} Soru)")
        
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            dogru = st.number_input("Doğru Sayısı", min_value=0, max_value=int(mevcut_odev["Soru Sayısı"]), value=int(mevcut_odev["Doğru"]))
        with col_d2:
            yanlis = st.number_input("Yanlış Sayısı", min_value=0, max_value=int(mevcut_odev["Soru Sayısı"]) - dogru, value=int(mevcut_odev["Yanlış"]))
        with col_d3:
            bos = int(mevcut_odev["Soru Sayısı"]) - (dogru + yanlis)
            st.metric("Otomatik Hesaplanan Boş", bos)
            
        durum_secimi = st.selectbox("Ödev Durumu:", ["Tamamlandı", "Eksik", "Yapılmadı"])
        
        hesaplanan_net = max(0.0, dogru - (yanlis / 4.0))
        toplam_soru = float(mevcut_odev["Soru Sayısı"])
        basari_yuzdesi = round((hesaplanan_net / toplam_soru) * 100, 1) if toplam_soru > 0 else 0.0
        
        st.info(f"🧮 **Hesaplanan Net:** {hesaplanan_net:.2f} | 🎯 **Başarı Oranı:** %{basari_yuzdesi}")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("💾 Değerlendirmeyi Kaydet"):
                df.at[gercek_index, "Doğru"] = dogru
                df.at[gercek_index, "Yanlış"] = yanlis
                df.at[gercek_index, "Boş"] = bos
                df.at[gercek_index, "Net"] = hesaplanan_net
                df.at[gercek_index, "Başarı (%)"] = basari_yuzdesi
                df.at[gercek_index, "Durum"] = durum_secimi
                
                df.to_csv(DOSYA_ADI, index=False)
                st.success("Sonuçlar başarıyla kaydedildi!")
                st.rerun()
        with col_btn2:
            if st.button("❌ Ödevi Sil"):
                df = df.drop(index=gercek_index).reset_index(drop=True)
                df.to_csv(DOSYA_ADI, index=False)
                st.warning("Ödev silindi!")
                st.rerun()
    else:
        st.info("Değerlendirilecek ödev bulunmuyor.")

# ==========================================
# 4. SEKME: ÖĞRENCİ BAŞARI ANALİZİ & VELİ WHATSAPP RAPORU
# ==========================================
with tab4:
    st.header("📈 Öğrenci Başarı Analizi & Veli Raporu")
    
    if not df.empty:
        ogrenciler = sorted(list(df["Öğrenci"].unique()))
        secilen_analiz_ogrenci = st.selectbox("Analiz ve Rapor İçin Öğrenci Seçin:", ogrenciler)
        
        ogrenci_df = df[df["Öğrenci"] == secilen_analiz_ogrenci]
        
        if not ogrenci_df.empty:
            col_g1, col_g2 = st.columns([2, 1])
            
            with col_g1:
                st.subheader("📊 Konu Bazlı Başarı Grafiği (%)")
                tamamlanan_df = ogrenci_df[ogrenci_df["Durum"] != "Yapılmadı"]
                if not tamamlanan_df.empty:
                    st.bar_chart(tamamlanan_df.set_index("Konu")[["Başarı (%)"]])
                else:
                    st.info("Grafik için henüz tamamlanmış ödev bulunmuyor.")
                    
                st.subheader("📝 Detaylı Performans Geçmişi")
                st.dataframe(ogrenci_df[["Konu", "Soru Sayısı", "Doğru", "Yanlış", "Boş", "Net", "Başarı (%)", "Tarih"]], use_container_width=True)

            # VELİ WHATSAPP RAPOR MODÜLÜ
            with col_g2:
                st.subheader("📲 Veli WhatsApp Raporu")
                
                # Raporlanacak özel bir ödev seçimi veya genel özet
                odev_secenekleri = ["Tüm Ödevlerin Genel Özeti"] + list(ogrenci_df["Konu"] + " (" + ogrenci_df["Tarih"] + ")")
                secilen_odev_rapor = st.selectbox("Raporlanacak Ödevi Seçin:", odev_secenekleri)
                
                ogretmen_notu = st.text_area("Öğretmen Notu / Değerlendirme (İsteğe Bağlı):", "Öğrencimiz derste gayet gayretli, ödev takibine devam edelim.")
                
                if secilen_odev_rapor == "Tüm Ödevlerin Genel Özeti":
                    toplam_o = len(ogrenci_df)
                    tamamlanan_o = len(ogrenci_df[ogrenci_df["Durum"] == "Tamamlandı"])
                    ort_n = round(ogrenci_df["Net"].mean(), 2)
                    ort_b = round(ogrenci_df["Başarı (%)"].mean(), 1)
                    
                    wa_mesaj = (
                        f"Sayın Velimiz,\n\n"
                        f"📚 *{secilen_analiz_ogrenci}* isimli öğrencimizin Matematik Özel Ders genel ödev durumu aşağıdadır:\n\n"
                        f"🔹 Toplam Ödev Sayısı: {toplam_o}\n"
                        f"✅ Tamamlanan Ödev: {tamamlanan_o}\n"
                        f"📊 Ortalama Net: {ort_n}\n"
                        f"🎯 Genel Başarı Oranı: %{ort_b}\n\n"
                        f"📝 *Öğretmen Notu:* {ogretmen_notu}\n\n"
                        f"İyi günler dilerim."
                    )
                else:
                    # Seçilen tek bir ödevin detay mesajı
                    secilen_index = odev_secenekleri.index(secilen_odev_rapor) - 1
                    tek_odev = ogrenci_df.iloc[secilen_index]
                    
                    wa_mesaj = (
                        f"Sayın Velimiz,\n\n"
                        f"📚 *{secilen_analiz_ogrenci}* isimli öğrencimizin son ödev sonucu aşağıdadır:\n\n"
                        f"📖 *Konu:* {tek_odev['Konu']}\n"
                        f"❓ *Soru Sayısı:* {tek_odev['Soru Sayısı']}\n"
                        f"✅ *Doğru:* {tek_odev['Doğru']} | ❌ *Yanlış:* {tek_odev['Yanlış']} | ⚪ *Boş:* {tek_odev['Boş']}\n"
                        f"🧮 *Net:* {tek_odev['Net']}\n"
                        f"🎯 *Başarı Oranı:* %{tek_odev['Başarı (%)']}\n\n"
                        f"📝 *Öğretmen Notu:* {ogretmen_notu}\n\n"
                        f"İyi günler dilerim."
                    )
                
                # WhatsApp Web/Mobil Linkini Oluşturma
                encoded_mesaj = urllib.parse.quote(wa_mesaj)
                wa_link = f"https://wa.me/?text={encoded_mesaj}"
                
                st.markdown("### Mesaj Önizlemesi:")
                st.code(wa_mesaj, language="markdown")
                
                st.link_button("🚀 WhatsApp'ta Velisine Gönder", wa_link, type="primary", use_container_width=True)
        else:
            st.warning("Bu öğrenciye ait henüz ödev kaydı yok.")
    else:
        st.info("Henüz analiz edilecek veri yok.")