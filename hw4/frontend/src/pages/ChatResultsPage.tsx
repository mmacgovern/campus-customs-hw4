import { Link, useNavigate } from 'react-router-dom'
import ProductCard from '../components/ProductCard'
import { useChatResults } from '../chatResults'

export default function ChatResultsPage() {
  const { results, setResults } = useChatResults()
  const navigate = useNavigate()

  if (!results) {
    return (
      <>
        <header className="page-header">
          <p className="eyebrow">From the assistant</p>
          <h1>Chat results</h1>
        </header>
        <p>
          Ask the assistant something like "what hoodies do you have?" and matching products will
          appear here. Or browse all <Link to="/products">products</Link>.
        </p>
      </>
    )
  }

  function clear() {
    setResults(null)
    navigate('/products')
  }

  return (
    <>
      <div className="results-header">
        <div className="page-header">
          <p className="eyebrow">From the assistant</p>
          <h1>Chat results</h1>
          <p className="muted">
            You asked: “{results.question}” · {results.products.length} product
            {results.products.length === 1 ? '' : 's'}
          </p>
        </div>
        <button className="link-button" onClick={clear}>
          Clear results
        </button>
      </div>
      <div className="product-grid">
        {results.products.map((p, i) => (
          <ProductCard
            key={p.product_id}
            index={i}
            productId={p.product_id}
            name={p.name}
            price={p.price}
            imageUrl={p.image_url}
            info={p.short_description}
          />
        ))}
      </div>
    </>
  )
}
