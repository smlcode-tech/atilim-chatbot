/**
 * Giriş noktası: uygulamayı `index.html`'deki `#root` öğesine bağlar. StrictMode geliştirmede
 * etkileri iki kez çalıştırarak temizlenmeyen yan etkileri görünür kılar (bkz. `useAuth`'taki
 * Google düğmesi koruması).
 */
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
