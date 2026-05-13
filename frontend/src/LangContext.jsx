import { createContext, useContext, useState, useEffect } from 'react'
import T from './i18n'

const LangContext = createContext()

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(() => localStorage.getItem('lang') || 'en')

  const setLang = (l) => {
    setLangState(l)
    localStorage.setItem('lang', l)
  }

  useEffect(() => {
    document.documentElement.dir  = lang === 'he' ? 'rtl' : 'ltr'
    document.documentElement.lang = lang
  }, [lang])

  const t = (key) => T[lang]?.[key] ?? T.en[key] ?? key

  return (
    <LangContext.Provider value={{ lang, setLang, t, isHe: lang === 'he' }}>
      {children}
    </LangContext.Provider>
  )
}

export const useLang = () => useContext(LangContext)
