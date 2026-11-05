import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

const resources = {
  en: {
    translation: {
      title: 'Accel Business',
      subtitle: 'Go digital in one sitting',
      start: 'Get started',
      advisor: 'Talk to Advisor',
      advisor_desc: 'AI advisor in your language',
      quote: 'Get Quote',
      quote_desc: 'Transparent pricing',
      kyc: 'Complete KYC',
      kyc_desc: 'Smart KYC in minutes',
      track: 'Track Order',
      track_desc: 'Track your activation',
      office: 'Back Office',
      hero_stat: '5,000 leads → 368 activations (7.4%) · 17.6 days avg',
      see_quote: 'See quote',
      change_something: 'Change something',
      talk_to_person: 'Talk to a person',
      proceed_to_kyc: 'Proceed to KYC',
      consent_title: 'Your data, your control',
      consent_kyc: 'I consent to KYC verification processing',
      consent_marketing: 'I consent to marketing communications (optional)',
      next: 'Continue',
      type_message: 'Type your answer…',
      send: 'Send',
      monthly: 'per month',
      gst: 'GST (18%)',
      setup: 'One-time setup',
      first_bill: 'First bill estimate',
      saving: 'Bundle saving vs buying separately',
    }
  },
  hi: {
    translation: {
      title: 'Accel Business',
      subtitle: 'एक बार में डिजिटल बनें',
      start: 'शुरू करें',
      advisor: 'सलाहकार से बात करें',
      advisor_desc: 'आपकी भाषा में AI सलाह',
      quote: 'कोटेशन लें',
      quote_desc: 'पारदर्शी मूल्य निर्धारण',
      kyc: 'KYC पूरा करें',
      kyc_desc: 'मिनटों में स्मार्ट KYC',
      track: 'ऑर्डर ट्रैक करें',
      track_desc: 'एक्टिवेशन ट्रैक करें',
      office: 'बैक ऑफिस',
      hero_stat: '5,000 लीड्स → 368 एक्टिवेशन (7.4%) · औसत 17.6 दिन',
      see_quote: 'कोटेशन देखें',
      change_something: 'कुछ बदलें',
      talk_to_person: 'किसी से बात करें',
      proceed_to_kyc: 'KYC की ओर जाएं',
      consent_title: 'आपका डेटा, आपका नियंत्रण',
      consent_kyc: 'मैं KYC सत्यापन के लिए सहमति देता/देती हूं',
      consent_marketing: 'मैं मार्केटिंग संचार के लिए सहमति देता/देती हूं (वैकल्पिक)',
      next: 'आगे बढ़ें',
      type_message: 'अपना जवाब टाइप करें…',
      send: 'भेजें',
      monthly: 'प्रति माह',
      gst: 'GST (18%)',
      setup: 'एकमुश्त सेटअप',
      first_bill: 'पहले बिल का अनुमान',
      saving: 'अलग खरीदने की तुलना में बचत',
    }
  }
}

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: 'hi',
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false
    }
  })

export default i18n
