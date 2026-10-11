import { BookOpen, BrainCircuit, UserRound } from 'lucide-react'

// Asistanın arayüzde görünen kimliği ve kapsamı. Backend'de yeni kaynaklar
// indekslendikçe (backend/atilim_assistant/ingestion/sources.py) buradaki metinler güncellenir.
export const assistant = {
  name: 'Akademik Asistan',
  university: {
    name: 'Atılım Üniversitesi',
    shortName: 'Atılım',
    url: 'https://www.atilim.edu.tr/tr',
  },
  scopeLabel: 'ATILIM ÜNİVERSİTESİ · YAZILIM MÜHENDİSLİĞİ',
  welcomeDescription:
    'Akademik kadromuz, araştırma alanları ve daha fazlası hakkında merak ettiklerini sor.',
  welcomeFootnote: 'Cevaplar üniversitenin web sitesindeki bilgilere dayanır.',
  sidebarHelp: 'Akademik personel, araştırma alanları ve iletişim bilgileri hakkında soru sor.',
  links: [
    {
      label: 'Akademik kadro',
      url: 'https://www.atilim.edu.tr/tr/se/page/2286/akademik-personel',
    },
  ],
  suggestions: [
    {
      icon: UserRound,
      title: 'Akademik kadroyu tanı',
      prompt: 'Yazılım Mühendisliği bölümündeki akademik personeli tanıtır mısın?',
    },
    {
      icon: BrainCircuit,
      title: 'Araştırma konuları',
      prompt: 'Makine öğrenmesi üzerine çalışan akademisyenler kimler?',
    },
    {
      icon: BookOpen,
      title: 'Bir akademisyeni keşfet',
      prompt: 'Ali Yazıcı’nın araştırma konuları neler?',
    },
  ],
}
