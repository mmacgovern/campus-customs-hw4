import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import Crest from './Crest'

const links = [
  { to: '/', label: 'Home' },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const close = () => setMenuOpen(false)

  async function handleLogout() {
    close()
    await logout()
    navigate('/')
  }

  return (
    <header className="site-header">
      <div className="announcement">
        <span>Family-run on Broadway since the 1970s</span>
        <span className="announcement-dot" aria-hidden="true">
          ·
        </span>
        <span>Printed &amp; embroidered in New Haven</span>
      </div>
      <div className="navbar">
        <Link to="/" className="brand" onClick={close}>
          <Crest />
          <span className="brand-text">
            <span className="brand-name">Campus Customs</span>
            <span className="brand-tag">New Haven · Est. 1970s</span>
          </span>
        </Link>

        <button
          className="menu-toggle"
          aria-expanded={menuOpen}
          aria-controls="main-nav"
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          onClick={() => setMenuOpen((o) => !o)}
        >
          <span />
          <span />
          <span />
        </button>

        <nav id="main-nav" className={menuOpen ? 'open' : ''}>
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.to === '/'} onClick={close}>
              {l.label}
            </NavLink>
          ))}
          {!loading &&
            (user ? (
              <>
                <span className="nav-user">Hi, {user.first_name}</span>
                <button className="nav-button" onClick={handleLogout}>
                  Log out
                </button>
              </>
            ) : (
              <>
                <NavLink to="/login" onClick={close}>
                  Log in
                </NavLink>
                <NavLink to="/create-account" className="nav-cta" onClick={close}>
                  Create account
                </NavLink>
              </>
            ))}
        </nav>
      </div>
    </header>
  )
}
