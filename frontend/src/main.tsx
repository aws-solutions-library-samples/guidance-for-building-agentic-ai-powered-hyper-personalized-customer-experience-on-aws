import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Provider } from 'react-redux'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { store } from './store'
import './index.css'
import Home from './components/Home'
import Chat from './components/Chat'
import SearchResults from './components/SearchResults'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Provider store={store}>
      <Router>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/search" element={<SearchResults />} />
        </Routes>
      </Router>
    </Provider>
  </StrictMode>,
)
