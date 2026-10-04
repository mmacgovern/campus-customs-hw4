import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'

// Category tiles use real catalogue photos and open the filtered Products page.
const TILES = [
  { category: 'hoodie', label: 'Hoodies', image: '/images/basic-hoodie-big-yale.jpg' },
  { category: 'crewneck', label: 'Crewnecks', image: '/images/davenport-college-crewneck.jpg' },
  { category: 't-shirt', label: 'T-shirts', image: '/images/boola-boola-t-shirt.jpg' },
  { category: 'quarter-zip', label: 'Quarter-zips', image: '/images/berkeley-1-4-zip.jpg' },
]

export default function Home() {
  return (
    <>
      <section className="hero">
        <div className="hero-inner">
          <p className="eyebrow eyebrow-light">New Haven, Connecticut</p>
          <h1>
            Wear your <em>Blue.</em>
          </h1>
          <p className="hero-lede">
            Campus Customs is New Haven's home for Bulldog gear: soft hoodies, everyday tees,
            residential college crewnecks and game-day favorites, steps from Yale's campus.
          </p>
          <div className="hero-actions">
            <Link to="/products" className="button button-light">
              Shop the collection
            </Link>
            <Link to="/about" className="button button-ghost">
              Our story
            </Link>
          </div>
        </div>
        <div className="hero-pennant" aria-hidden="true">
          <span>YALE</span>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <p className="eyebrow">Shop by category</p>
          <h2>Find your fit</h2>
        </div>
        <div className="category-tiles">
          {TILES.map((t, i) => (
            <Link
              key={t.category}
              to={`/products?category=${t.category}`}
              className="category-tile card-enter"
              style={{ '--i': i } as CSSProperties}
            >
              <img src={t.image} alt="" loading="lazy" />
              <span className="category-label">
                {t.label} <span aria-hidden="true">→</span>
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section className="section features">
        <div className="feature">
          <span className="feature-icon" aria-hidden="true">
            Y
          </span>
          <h3>Made for every Yalie</h3>
          <p>
            From first-years to alumni back for reunion weekend, and the families cheering them
            on, there's something here for everyone.
          </p>
        </div>
        <div className="feature">
          <span className="feature-icon" aria-hidden="true">
            ✦
          </span>
          <h3>Your college, your colors</h3>
          <p>
            Rep your residential college, your sport or your graduate school with designs that go
            beyond the classic big "Yale."
          </p>
        </div>
        <div className="feature">
          <span className="feature-icon" aria-hidden="true">
            ?
          </span>
          <h3>Ask our assistant</h3>
          <p>
            Not sure what fits? Open the chat in the corner and we'll find the right piece in the
            right size, with live stock.
          </p>
        </div>
      </section>

      <section className="section visit-band">
        <div>
          <p className="eyebrow eyebrow-light">Visit the shop</p>
          <h2>57 Broadway, New Haven</h2>
          <p>Right across from campus. Stop in between classes or on your way through town.</p>
        </div>
        <Link to="/about" className="button button-light">
          About Campus Customs
        </Link>
      </section>
    </>
  )
}
