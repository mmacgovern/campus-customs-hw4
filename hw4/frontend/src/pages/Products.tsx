import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchProducts } from '../api'
import type { Product } from '../api'
import ProductCard from '../components/ProductCard'
import { CATEGORY_LABELS, CATEGORY_SINGULAR } from '../categories'

// Same categories as the chatbot's search tool (the backend sets `category`).
const CATEGORIES = [
  { value: '', label: 'All categories' },
  ...Object.entries(CATEGORY_LABELS).map(([value, label]) => ({ value, label })),
]

const SORTS = [
  { value: 'name', label: 'Name A–Z' },
  { value: 'price-asc', label: 'Price: low to high' },
  { value: 'price-desc', label: 'Price: high to low' },
]

function shorten(text: string, max = 90): string {
  return text.length <= max ? text : text.slice(0, max).trimEnd() + '…'
}

function matchesSearch(p: Product, words: string[]): boolean {
  const haystack = [p.name, p.description, p.garment_type, ...p.colors, ...p.search_tags]
    .join(' ')
    .toLowerCase()
  return words.every((w) => haystack.includes(w))
}

export default function Products() {
  const [products, setProducts] = useState<Product[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  // Filters live in the URL so back, refresh, and shared links keep them.
  const [params, setParams] = useSearchParams()
  const query = params.get('q') ?? ''
  const category = params.get('category') ?? ''
  const sort = params.get('sort') ?? 'name'

  useEffect(() => {
    fetchProducts()
      .then(setProducts)
      .catch(() => setError('Could not load products. Is the backend running on port 8000?'))
      .finally(() => setLoading(false))
  }, [])

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }

  const visible = useMemo(() => {
    const words = query.toLowerCase().split(/\s+/).filter(Boolean)
    const list = products.filter(
      (p) => (!category || p.category === category) && matchesSearch(p, words),
    )
    if (sort === 'price-asc') list.sort((a, b) => a.price - b.price || a.name.localeCompare(b.name))
    else if (sort === 'price-desc') list.sort((a, b) => b.price - a.price || a.name.localeCompare(b.name))
    else list.sort((a, b) => a.name.localeCompare(b.name))
    return list
  }, [products, query, category, sort])

  const filtered = Boolean(query || category || sort !== 'name')

  return (
    <>
      <header className="page-header">
        <p className="eyebrow">The collection</p>
        <h1>{category ? CATEGORY_LABELS[category] ?? 'Products' : 'All products'}</h1>
        <p className="page-sub">
          Hoodies, crewnecks, tees and more, in sizes XS to XXL. Click any item for sizes and live
          stock.
        </p>
      </header>

      <div className="product-toolbar" role="search">
        <input
          type="search"
          placeholder="Search products (e.g. Davenport, hockey, navy)…"
          aria-label="Search products"
          value={query}
          onChange={(e) => setParam('q', e.target.value)}
        />
        <select
          aria-label="Category"
          value={category}
          onChange={(e) => setParam('category', e.target.value)}
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
        <select
          aria-label="Sort by"
          value={sort}
          onChange={(e) => setParam('sort', e.target.value === 'name' ? '' : e.target.value)}
        >
          {SORTS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
        {filtered && (
          <button className="link-button" onClick={() => setParams({}, { replace: true })}>
            Clear filters
          </button>
        )}
      </div>

      {loading && <p>Loading…</p>}
      {error && <p className="error">{error}</p>}
      {!loading && !error && (
        <p className="muted result-count">
          Showing {visible.length} of {products.length} products
        </p>
      )}
      {!loading && !error && visible.length === 0 && (
        <p>No products match your search. Try a different word or category.</p>
      )}

      <div className="product-grid">
        {visible.map((p, i) => (
          <ProductCard
            key={p.product_id}
            index={i}
            eyebrow={CATEGORY_SINGULAR[p.category] ?? p.garment_type}
            productId={p.product_id}
            name={p.name}
            price={p.price}
            imageUrl={p.image_url}
            info={shorten(p.description)}
          />
        ))}
      </div>
    </>
  )
}
