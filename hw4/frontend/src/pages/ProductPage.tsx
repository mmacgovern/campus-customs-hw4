import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { fetchProduct, formatPrice } from '../api'
import type { ProductDetail, SizeStock } from '../api'
import { CATEGORY_LABELS, CATEGORY_SINGULAR } from '../categories'

interface LoadState {
  id: string
  product?: ProductDetail
  error?: string
}

function stockLabel(s: SizeStock): string {
  if (s.quantity === 0) return 'Sold out'
  if (s.low_stock) return `Only ${s.quantity} left`
  return `${s.quantity} in stock`
}

export default function ProductPage() {
  const { productId = '' } = useParams()
  const [state, setState] = useState<LoadState>({ id: '' })
  const navigate = useNavigate()
  // Opened from inside the app (grid or chat results): go back there.
  const cameFromApp = useLocation().key !== 'default'

  useEffect(() => {
    fetchProduct(productId)
      .then((product) => setState({ id: productId, product }))
      .catch(() => setState({ id: productId, error: 'Product not found.' }))
  }, [productId])

  // Until the fetch for the current productId finishes, show a skeleton.
  if (state.id !== productId) {
    return (
      <div className="product-detail" aria-busy="true">
        <div className="skeleton skeleton-image" />
        <div className="product-info">
          <div className="skeleton skeleton-line" style={{ width: '40%' }} />
          <div className="skeleton skeleton-title" />
          <div className="skeleton skeleton-line" />
          <div className="skeleton skeleton-line" style={{ width: '80%' }} />
        </div>
      </div>
    )
  }
  if (state.error || !state.product) return <p className="error">{state.error}</p>
  const product = state.product
  const inStock = product.sizes.filter((s) => s.quantity > 0).length

  return (
    <>
      <nav className="breadcrumb" aria-label="Breadcrumb">
        {cameFromApp ? (
          <button className="link-button" onClick={() => navigate(-1)}>
            ← Back
          </button>
        ) : (
          <Link to="/products">← Back to products</Link>
        )}
        <span aria-hidden="true">/</span>
        <Link to={`/products?category=${product.category}`}>
          {CATEGORY_LABELS[product.category] ?? 'Products'}
        </Link>
      </nav>

      <div className="product-detail">
        <div className="product-gallery">
          <img src={product.image_url} alt={product.name} />
        </div>

        <div className="product-info">
          <p className="eyebrow">{CATEGORY_SINGULAR[product.category] ?? product.garment_type}</p>
          <h1>{product.name}</h1>
          <p className="price price-large">{formatPrice(product.price)}</p>
          <p className="product-description">{product.description}</p>

          <h2 className="detail-heading">Colors</h2>
          <ul className="color-chips">
            {product.colors.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>

          <h2 className="detail-heading">
            Sizes &amp; stock{' '}
            <span className="muted">
              ({inStock} of {product.sizes.length} sizes available)
            </span>
          </h2>
          <ul className="size-grid">
            {product.sizes.map((s) => (
              <li
                key={s.size}
                className={`size-tile${s.quantity === 0 ? ' sold-out' : ''}${s.low_stock ? ' low' : ''}`}
              >
                <span className="size-name">{s.size}</span>
                <span className="size-stock">{stockLabel(s)}</span>
              </li>
            ))}
          </ul>

          <p className="assist-hint">
            Questions about fit or a sold-out size? Open <strong>Chat with us</strong> and ask "is
            this in stock in medium?"
          </p>
        </div>
      </div>
    </>
  )
}
