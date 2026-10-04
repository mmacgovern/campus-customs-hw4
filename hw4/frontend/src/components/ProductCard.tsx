import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { formatPrice } from '../api'

interface Props {
  productId: string
  name: string
  price: number
  imageUrl: string
  info: string
  // Small label above the name, e.g. "Hoodie".
  eyebrow?: string
  // Position in the grid, used to stagger the fade-in.
  index?: number
}

// One product tile. Used by the Products grid and by chat search results;
// both link to the same single-item page.
export default function ProductCard({ productId, name, price, imageUrl, info, eyebrow, index = 0 }: Props) {
  return (
    <Link
      to={`/products/${productId}`}
      className="product-card card-enter"
      style={{ '--i': Math.min(index, 12) } as CSSProperties}
    >
      <div className="product-card-media">
        <img src={imageUrl} alt={name} loading="lazy" />
        <span className="product-card-cta" aria-hidden="true">
          View details →
        </span>
      </div>
      <div className="product-card-body">
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h3>{name}</h3>
        <p className="desc">{info}</p>
        <p className="price">{formatPrice(price)}</p>
      </div>
    </Link>
  )
}
