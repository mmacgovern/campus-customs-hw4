import { Route, Routes, useLocation } from 'react-router-dom'
import NavBar from './components/NavBar'
import Footer from './components/Footer'
import ChatPanel from './components/ChatPanel'
import Home from './pages/Home'
import Products from './pages/Products'
import ProductPage from './pages/ProductPage'
import About from './pages/About'
import Login from './pages/Login'
import CreateAccount from './pages/CreateAccount'
import ChatResultsPage from './pages/ChatResultsPage'
import { useAuth } from './auth'

export default function App() {
  const { user, loading } = useAuth()
  const { pathname } = useLocation()
  return (
    <>
      <NavBar />
      {/* Keyed by path so each page fades in on navigation (filters on
          /products change only the query string, so they don't re-animate). */}
      <main className="container page-enter" key={pathname}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:productId" element={<ProductPage />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<Login />} />
          <Route path="/create-account" element={<CreateAccount />} />
          <Route path="/chat-results" element={<ChatResultsPage />} />
          <Route path="*" element={<p>Page not found.</p>} />
        </Routes>
      </main>
      <Footer />
      {/* New key per user: logging in or out gives a fresh panel. */}
      {!loading && <ChatPanel key={user?.id ?? 'guest'} />}
    </>
  )
}
