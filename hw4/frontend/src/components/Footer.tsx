import { Link } from 'react-router-dom'
import Crest from './Crest'

const YEAR = new Date().getFullYear()

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <Crest size={40} />
          <div>
            <p className="footer-name">Campus Customs</p>
            <p>Bulldog gear from a family-run New Haven shop.</p>
          </div>
        </div>
        <div>
          <p className="footer-heading">Shop</p>
          <Link to="/products">All products</Link>
          <Link to="/products?category=hoodie">Hoodies</Link>
          <Link to="/products?category=crewneck">Crewnecks</Link>
          <Link to="/products?category=t-shirt">T-shirts</Link>
        </div>
        <div>
          <p className="footer-heading">Visit</p>
          <p>57 Broadway</p>
          <p>New Haven, CT 06511</p>
          <Link to="/about">Our story</Link>
        </div>
      </div>
      <p className="footer-fine">© {YEAR} Campus Customs · Boola boola!</p>
    </footer>
  )
}
